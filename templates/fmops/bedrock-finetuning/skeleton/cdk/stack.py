"""Amazon Bedrock Fine-Tuning Pipeline CDK Stack.

This stack provisions:
- S3 buckets for training data and model output (SSE-KMS, versioning)
- IAM role for Bedrock model customization
- Lambda function for data validation (JSONL format, size limits)
- Lambda function for starting Bedrock customization jobs
- Lambda function for polling job status
- Step Functions state machine (validate -> start -> poll -> notify)
- SNS topic for notifications (conditional)
- CloudWatch log groups
"""

from typing import Any, Optional
import json
import aws_cdk as cdk
from aws_cdk import (
    Stack,
    CfnOutput,
    Tags,
    Duration,
    RemovalPolicy,
)
from aws_cdk import aws_s3 as s3
from aws_cdk import aws_kms as kms
from aws_cdk import aws_iam as iam
from aws_cdk import aws_lambda as lambda_
from aws_cdk import aws_stepfunctions as sfn
from aws_cdk import aws_stepfunctions_tasks as tasks
from aws_cdk import aws_sns as sns
from aws_cdk import aws_sns_subscriptions as subscriptions
from aws_cdk import aws_logs as logs
from constructs import Construct


class BedrockFinetuningStack(Stack):
    """Amazon Bedrock Model Fine-Tuning Pipeline."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        component_name: str,
        base_model_id: str,
        customization_type: str = "FINE_TUNING",
        training_epochs: int = 3,
        batch_size: int = 8,
        learning_rate: float = 0.00001,
        warmup_ratio: float = 0.1,
        enable_data_validation: bool = True,
        max_training_data_size_mb: int = 100,
        validation_data_ratio: float = 0.2,
        enable_provisioned_throughput: bool = False,
        provisioned_model_units: int = 1,
        enable_notifications: bool = True,
        notification_email: Optional[str] = None,
        environment: str = "dev",
        **kwargs: Any,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        removal = RemovalPolicy.DESTROY if environment == "dev" else RemovalPolicy.RETAIN
        auto_delete = environment == "dev"

        # ------------------------------------------------------------------ #
        # KMS Key for encryption at rest
        # ------------------------------------------------------------------ #
        encryption_key = kms.Key(
            self,
            "EncryptionKey",
            alias=f"{component_name}-{environment}-key",
            enable_key_rotation=True,
            removal_policy=removal,
            description=f"Encryption key for {component_name} Bedrock fine-tuning",
        )

        # ------------------------------------------------------------------ #
        # S3 bucket — training data
        # ------------------------------------------------------------------ #
        training_bucket = s3.Bucket(
            self,
            "TrainingDataBucket",
            bucket_name=f"{component_name}-{environment}-training-data-{self.account}",
            encryption=s3.BucketEncryption.KMS,
            encryption_key=encryption_key,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy=removal,
            auto_delete_objects=auto_delete,
            versioned=True,
            enforce_ssl=True,
        )

        # ------------------------------------------------------------------ #
        # S3 bucket — model output
        # ------------------------------------------------------------------ #
        output_bucket = s3.Bucket(
            self,
            "ModelOutputBucket",
            bucket_name=f"{component_name}-{environment}-model-output-{self.account}",
            encryption=s3.BucketEncryption.KMS,
            encryption_key=encryption_key,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy=removal,
            auto_delete_objects=auto_delete,
            versioned=True,
            enforce_ssl=True,
        )

        # ------------------------------------------------------------------ #
        # IAM role — Bedrock customization
        # ------------------------------------------------------------------ #
        bedrock_role = iam.Role(
            self,
            "BedrockCustomizationRole",
            role_name=f"{component_name}-{environment}-bedrock-role",
            assumed_by=iam.ServicePrincipal("bedrock.amazonaws.com"),
            description="Role assumed by Bedrock for model customization jobs",
        )

        training_bucket.grant_read(bedrock_role)
        output_bucket.grant_read_write(bedrock_role)

        bedrock_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "bedrock:CreateModelCustomizationJob",
                    "bedrock:GetModelCustomizationJob",
                    "bedrock:StopModelCustomizationJob",
                    "bedrock:ListModelCustomizationJobs",
                    "bedrock:GetCustomModel",
                    "bedrock:ListCustomModels",
                    "bedrock:CreateProvisionedModelThroughput",
                    "bedrock:GetProvisionedModelThroughput",
                ],
                resources=["*"],
            )
        )

        # ------------------------------------------------------------------ #
        # SNS topic — notifications (conditional)
        # ------------------------------------------------------------------ #
        notification_topic = None
        if enable_notifications:
            notification_topic = sns.Topic(
                self,
                "NotificationTopic",
                topic_name=f"{component_name}-{environment}-finetuning-notifications",
                display_name=f"{component_name} Fine-Tuning Notifications",
                master_key=encryption_key,
            )

            if notification_email:
                notification_topic.add_subscription(
                    subscriptions.EmailSubscription(notification_email)
                )

        # ------------------------------------------------------------------ #
        # Lambda — data validator
        # ------------------------------------------------------------------ #
        validator_lambda = None
        if enable_data_validation:
            validator_log_group = logs.LogGroup(
                self,
                "ValidatorLogGroup",
                log_group_name=f"/aws/lambda/{component_name}-{environment}-data-validator",
                retention=logs.RetentionDays.ONE_MONTH,
                removal_policy=RemovalPolicy.DESTROY,
            )

            validator_lambda = lambda_.Function(
                self,
                "DataValidatorFunction",
                function_name=f"{component_name}-{environment}-data-validator",
                runtime=lambda_.Runtime.PYTHON_3_11,
                handler="index.handler",
                code=lambda_.Code.from_inline(self._get_validator_code()),
                timeout=Duration.minutes(5),
                memory_size=1024,
                environment={
                    "MAX_FILE_SIZE_MB": str(max_training_data_size_mb),
                    "CUSTOMIZATION_TYPE": customization_type,
                },
                log_group=validator_log_group,
            )
            training_bucket.grant_read(validator_lambda)

        # ------------------------------------------------------------------ #
        # Lambda — start fine-tuning job
        # ------------------------------------------------------------------ #
        start_job_log_group = logs.LogGroup(
            self,
            "StartJobLogGroup",
            log_group_name=f"/aws/lambda/{component_name}-{environment}-start-finetuning",
            retention=logs.RetentionDays.ONE_MONTH,
            removal_policy=RemovalPolicy.DESTROY,
        )

        start_job_lambda = lambda_.Function(
            self,
            "StartJobFunction",
            function_name=f"{component_name}-{environment}-start-finetuning",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="index.handler",
            code=lambda_.Code.from_inline(self._get_start_job_code()),
            timeout=Duration.minutes(5),
            memory_size=256,
            environment={
                "BASE_MODEL_ID": base_model_id,
                "CUSTOMIZATION_TYPE": customization_type,
                "BEDROCK_ROLE_ARN": bedrock_role.role_arn,
                "OUTPUT_BUCKET": output_bucket.bucket_name,
                "TRAINING_EPOCHS": str(training_epochs),
                "BATCH_SIZE": str(batch_size),
                "LEARNING_RATE": str(learning_rate),
                "WARMUP_RATIO": str(warmup_ratio),
            },
            log_group=start_job_log_group,
        )

        # Bedrock customization job APIs don't support resource-level
        # permissions, so this action must use "*". Everything else is scoped.
        start_job_lambda.add_to_role_policy(
            iam.PolicyStatement(
                sid="CreateCustomizationJob",
                actions=["bedrock:CreateModelCustomizationJob"],
                resources=["*"],
            )
        )

        # Only allow passing the Bedrock service role that this stack creates,
        # and only to the Bedrock service.
        start_job_lambda.add_to_role_policy(
            iam.PolicyStatement(
                sid="PassBedrockCustomizationRole",
                actions=["iam:PassRole"],
                resources=[bedrock_role.role_arn],
                conditions={
                    "StringEquals": {
                        "iam:PassedToService": "bedrock.amazonaws.com",
                    },
                },
            )
        )

        # ------------------------------------------------------------------ #
        # Lambda — check job status
        # ------------------------------------------------------------------ #
        check_status_log_group = logs.LogGroup(
            self,
            "CheckStatusLogGroup",
            log_group_name=f"/aws/lambda/{component_name}-{environment}-check-status",
            retention=logs.RetentionDays.ONE_MONTH,
            removal_policy=RemovalPolicy.DESTROY,
        )

        check_status_lambda = lambda_.Function(
            self,
            "CheckStatusFunction",
            function_name=f"{component_name}-{environment}-check-status",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="index.handler",
            code=lambda_.Code.from_inline(self._get_check_status_code()),
            timeout=Duration.minutes(1),
            memory_size=256,
            log_group=check_status_log_group,
        )

        check_status_lambda.add_to_role_policy(
            iam.PolicyStatement(
                actions=["bedrock:GetModelCustomizationJob"],
                resources=["*"],
            )
        )

        # ------------------------------------------------------------------ #
        # Step Functions — orchestration workflow
        # ------------------------------------------------------------------ #

        # Validate data (optional first step)
        validate_task = None
        if validator_lambda:
            validate_task = tasks.LambdaInvoke(
                self,
                "ValidateData",
                lambda_function=validator_lambda,
                output_path="$.Payload",
                result_path="$.validationResult",
            )

        # Start fine-tuning job
        start_job_task = tasks.LambdaInvoke(
            self,
            "StartFineTuningJob",
            lambda_function=start_job_lambda,
            output_path="$.Payload",
            result_path="$.jobResult",
        )

        # Wait between status checks
        wait_state = sfn.Wait(
            self,
            "WaitForJob",
            time=sfn.WaitTime.duration(Duration.minutes(5)),
        )

        # Check job status
        check_status_task = tasks.LambdaInvoke(
            self,
            "CheckJobStatus",
            lambda_function=check_status_lambda,
            output_path="$.Payload",
            result_path="$.statusResult",
        )

        # Terminal states
        job_succeeded = sfn.Succeed(self, "JobSucceeded")
        job_failed = sfn.Fail(
            self, "JobFailed",
            error="FineTuningFailed",
            cause="The fine-tuning job failed",
        )

        # Notification states (if enabled)
        notify_success = None
        notify_failure = None
        if notification_topic:
            notify_success = tasks.SnsPublish(
                self,
                "NotifySuccess",
                topic=notification_topic,
                message=sfn.TaskInput.from_json_path_at("$.statusResult"),
                subject=f"[{component_name}] Fine-Tuning Job Completed Successfully",
            )
            notify_success.next(job_succeeded)

            notify_failure = tasks.SnsPublish(
                self,
                "NotifyFailure",
                topic=notification_topic,
                message=sfn.TaskInput.from_json_path_at("$.statusResult"),
                subject=f"[{component_name}] Fine-Tuning Job Failed",
            )
            notify_failure.next(job_failed)

        # Choice: is job complete?
        is_complete = sfn.Choice(self, "IsJobComplete")
        is_complete.when(
            sfn.Condition.string_equals("$.statusResult.status", "Completed"),
            notify_success if notify_success else job_succeeded,
        )
        is_complete.when(
            sfn.Condition.string_equals("$.statusResult.status", "Failed"),
            notify_failure if notify_failure else job_failed,
        )
        is_complete.when(
            sfn.Condition.string_equals("$.statusResult.status", "Stopped"),
            notify_failure if notify_failure else job_failed,
        )
        is_complete.otherwise(wait_state)

        # Wire: wait -> check -> choice
        wait_state.next(check_status_task)
        check_status_task.next(is_complete)

        # Build chain based on validation toggle
        if validate_task:
            validation_choice = sfn.Choice(self, "ValidationPassed")
            validation_choice.when(
                sfn.Condition.boolean_equals("$.validationResult.valid", True),
                start_job_task,
            )
            validation_choice.otherwise(
                sfn.Fail(
                    self, "ValidationFailed",
                    error="DataValidationFailed",
                    cause="Training data validation failed",
                )
            )
            validate_task.next(validation_choice)
            chain = validate_task
        else:
            chain = start_job_task

        start_job_task.next(wait_state)

        # Create the state machine
        sfn_log_group = logs.LogGroup(
            self,
            "StateMachineLogGroup",
            log_group_name=f"/aws/stepfunctions/{component_name}-{environment}-finetuning",
            retention=logs.RetentionDays.ONE_MONTH,
            removal_policy=RemovalPolicy.DESTROY,
        )

        state_machine = sfn.StateMachine(
            self,
            "FineTuningWorkflow",
            state_machine_name=f"{component_name}-{environment}-finetuning-workflow",
            definition_body=sfn.DefinitionBody.from_chainable(chain),
            timeout=Duration.hours(24),
            logs=sfn.LogOptions(
                destination=sfn_log_group,
                level=sfn.LogLevel.ALL,
            ),
        )

        # ------------------------------------------------------------------ #
        # Tags
        # ------------------------------------------------------------------ #
        Tags.of(self).add("Name", component_name)
        Tags.of(self).add("environment", environment)
        Tags.of(self).add("owner", component_name)
        Tags.of(self).add("genforge:managed", "true")

        # ------------------------------------------------------------------ #
        # Outputs
        # ------------------------------------------------------------------ #
        CfnOutput(
            self, "TrainingBucketName",
            value=training_bucket.bucket_name,
            description="S3 bucket for training data",
        )
        CfnOutput(
            self, "OutputBucketName",
            value=output_bucket.bucket_name,
            description="S3 bucket for model outputs",
        )
        CfnOutput(
            self, "StateMachineArn",
            value=state_machine.state_machine_arn,
            description="Step Functions state machine ARN",
        )
        CfnOutput(
            self, "BedrockRoleArn",
            value=bedrock_role.role_arn,
            description="IAM role ARN for Bedrock customization",
        )
        if notification_topic:
            CfnOutput(
                self, "NotificationTopicArn",
                value=notification_topic.topic_arn,
                description="SNS topic for notifications",
            )

    # ====================================================================== #
    # Lambda inline code helpers
    # ====================================================================== #

    @staticmethod
    def _get_validator_code() -> str:
        return '''
import json
import boto3
import os

s3 = boto3.client("s3")


def handler(event, context):
    """Validate training data format and size."""
    bucket = event.get("bucket") or event.get("trainingDataS3Uri", "").split("/")[2]
    key = event.get("key") or "/".join(event.get("trainingDataS3Uri", "").split("/")[3:])

    max_size = int(os.environ.get("MAX_FILE_SIZE_MB", "100")) * 1024 * 1024
    customization_type = os.environ.get("CUSTOMIZATION_TYPE", "FINE_TUNING")

    errors = []

    try:
        response = s3.head_object(Bucket=bucket, Key=key)
        file_size = response["ContentLength"]

        if file_size > max_size:
            errors.append(
                f"File size ({file_size / 1024 / 1024:.2f} MB) exceeds maximum "
                f"({max_size / 1024 / 1024} MB)"
            )

        obj = s3.get_object(Bucket=bucket, Key=key)
        content = obj["Body"].read().decode("utf-8")
        lines = content.strip().split("\\n")

        if len(lines) < 10:
            errors.append(
                f"Insufficient training samples: {len(lines)} (minimum 10 required)"
            )

        for i, line in enumerate(lines[:100]):
            try:
                data = json.loads(line)
                if customization_type == "FINE_TUNING":
                    if "prompt" not in data or "completion" not in data:
                        errors.append(f"Line {i+1}: Missing 'prompt' or 'completion' field")
                        break
                else:
                    if "input" not in data:
                        errors.append(f"Line {i+1}: Missing 'input' field")
                        break
            except json.JSONDecodeError:
                errors.append(f"Line {i+1}: Invalid JSON format")
                break

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "sampleCount": len(lines),
            "fileSizeMb": round(file_size / 1024 / 1024, 2),
            "bucket": bucket,
            "key": key,
        }

    except Exception as e:
        return {"valid": False, "errors": [str(e)], "bucket": bucket, "key": key}
'''

    @staticmethod
    def _get_start_job_code() -> str:
        return '''
import json
import boto3
import os
from datetime import datetime

bedrock = boto3.client("bedrock")


def handler(event, context):
    """Start a Bedrock model customization job."""
    job_name = event.get(
        "jobName", f"finetuning-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    )
    training_uri = event.get("trainingDataS3Uri")
    validation_uri = event.get("validationDataS3Uri")

    if "validationResult" in event:
        bucket = event["validationResult"].get("bucket")
        key = event["validationResult"].get("key")
        training_uri = training_uri or f"s3://{bucket}/{key}"

    base_model = os.environ["BASE_MODEL_ID"]
    customization = os.environ["CUSTOMIZATION_TYPE"]
    role_arn = os.environ["BEDROCK_ROLE_ARN"]
    output_bucket = os.environ["OUTPUT_BUCKET"]

    params = {
        "jobName": job_name,
        "customModelName": f"{job_name}-model",
        "roleArn": role_arn,
        "baseModelIdentifier": base_model,
        "customizationType": customization,
        "trainingDataConfig": {"s3Uri": training_uri},
        "outputDataConfig": {"s3Uri": f"s3://{output_bucket}/{job_name}/"},
        "hyperParameters": {
            "epochCount": os.environ.get("TRAINING_EPOCHS", "3"),
            "batchSize": os.environ.get("BATCH_SIZE", "8"),
            "learningRate": os.environ.get("LEARNING_RATE", "0.00001"),
            "warmupRatio": os.environ.get("WARMUP_RATIO", "0.1"),
        },
    }

    if validation_uri:
        params["validationDataConfig"] = {"s3Uri": validation_uri}

    try:
        response = bedrock.create_model_customization_job(**params)
        return {
            "success": True,
            "jobArn": response["jobArn"],
            "jobName": job_name,
            "status": "InProgress",
        }
    except Exception as e:
        return {"success": False, "error": str(e), "jobName": job_name}
'''

    @staticmethod
    def _get_check_status_code() -> str:
        return '''
import boto3

bedrock = boto3.client("bedrock")


def handler(event, context):
    """Check the status of a Bedrock customization job."""
    job_arn = event.get("jobResult", {}).get("jobArn") or event.get("jobArn")

    if not job_arn:
        return {"status": "Failed", "error": "No job ARN provided"}

    try:
        response = bedrock.get_model_customization_job(jobIdentifier=job_arn)
        return {
            "status": response["status"],
            "jobArn": job_arn,
            "jobName": response.get("jobName"),
            "customModelArn": response.get("outputModelArn"),
            "failureMessage": response.get("failureMessage"),
            "trainingMetrics": response.get("trainingMetrics"),
            "validationMetrics": response.get("validationMetrics"),
        }
    except Exception as e:
        return {"status": "Failed", "error": str(e), "jobArn": job_arn}
'''

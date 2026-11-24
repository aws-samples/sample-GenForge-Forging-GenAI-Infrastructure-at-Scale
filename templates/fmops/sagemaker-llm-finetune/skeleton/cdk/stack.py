"""SageMaker LLM Fine-Tuning CDK Stack.

This stack provisions:
- S3 bucket for training data and model artifacts (SSE-KMS)
- IAM role for SageMaker Training (sagemaker:*, s3:*, ecr:*, cloudwatch:*, logs:*)
- IAM role for Step Functions
- Lambda function: start-training (creates SageMaker Training Job with LoRA config)
- Lambda function: check-status (polls training job status)
- Step Functions state machine (orchestrates: start -> poll -> complete)
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
from aws_cdk import aws_logs as logs
from constructs import Construct


# HuggingFace training DLC account IDs per region
HF_DLC_ACCOUNTS = {
    "us-east-1": "763104351884",
    "us-west-2": "763104351884",
    "eu-west-1": "763104351884",
}


class SageMakerLLMFineTuneStack(Stack):
    """SageMaker LLM Fine-Tuning with LoRA."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        component_name: str,
        base_model: str,
        instance_type: str = "ml.g5.2xlarge",
        instance_count: int = 1,
        epochs: int = 3,
        lora_rank: int = 16,
        learning_rate: float = 0.0002,
        training_data_s3_path: Optional[str] = None,
        validation_split: float = 0.1,
        environment: str = "dev",
        **kwargs: Any,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        removal = RemovalPolicy.DESTROY if environment == "dev" else RemovalPolicy.RETAIN
        auto_delete = environment == "dev"

        # ------------------------------------------------------------------ #
        # KMS Key
        # ------------------------------------------------------------------ #
        encryption_key = kms.Key(
            self,
            "EncryptionKey",
            alias=f"{component_name}-{environment}-finetune-key",
            enable_key_rotation=True,
            removal_policy=removal,
            description=f"Encryption key for {component_name} LLM fine-tuning",
        )

        # ------------------------------------------------------------------ #
        # S3 bucket — training data + model artifacts
        # ------------------------------------------------------------------ #
        data_bucket = s3.Bucket(
            self,
            "DataBucket",
            bucket_name=f"{component_name}-{environment}-data-{self.account}",
            encryption=s3.BucketEncryption.KMS,
            encryption_key=encryption_key,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy=removal,
            auto_delete_objects=auto_delete,
            versioned=True,
            enforce_ssl=True,
        )

        # ------------------------------------------------------------------ #
        # IAM role — SageMaker Training
        # ------------------------------------------------------------------ #
        # Least-privilege replacement for the AmazonSageMakerFullAccess managed
        # policy. Scoped to the training jobs this stack creates plus the
        # dependencies SageMaker needs at training time (ECR pull, CloudWatch
        # logs and metrics, and read/write on the data bucket).
        sagemaker_role = iam.Role(
            self,
            "SageMakerTrainingRole",
            role_name=f"{component_name}-{environment}-training-role",
            assumed_by=iam.ServicePrincipal("sagemaker.amazonaws.com"),
            description=(
                f"Scoped SageMaker training role for {component_name} "
                f"({environment}) - no managed policies attached."
            ),
        )

        # Data bucket read/write (already scoped to this bucket via CDK grants).
        data_bucket.grant_read_write(sagemaker_role)

        # SageMaker training-job APIs, scoped to jobs this stack owns.
        sagemaker_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "sagemaker:CreateTrainingJob",
                    "sagemaker:DescribeTrainingJob",
                    "sagemaker:StopTrainingJob",
                    "sagemaker:AddTags",
                    "sagemaker:ListTags",
                ],
                resources=[
                    f"arn:aws:sagemaker:{self.region}:{self.account}:training-job/{component_name}-{environment}-*",
                ],
            )
        )

        # Read-only access to HuggingFace DLC images and any customer-supplied
        # image in the same account.
        sagemaker_role.add_to_policy(
            iam.PolicyStatement(
                sid="ECRImagePull",
                actions=[
                    "ecr:GetDownloadUrlForLayer",
                    "ecr:BatchGetImage",
                    "ecr:BatchCheckLayerAvailability",
                ],
                resources=[
                    f"arn:aws:ecr:{self.region}:{self.account}:repository/*",
                    # HuggingFace DLC public image repositories (per region).
                    f"arn:aws:ecr:{self.region}:763104351884:repository/huggingface-pytorch-training",
                ],
            )
        )

        sagemaker_role.add_to_policy(
            iam.PolicyStatement(
                sid="ECRAuthToken",
                actions=["ecr:GetAuthorizationToken"],
                resources=["*"],  # GetAuthorizationToken does not support resource-level permissions.
            )
        )

        # Training-job log groups and metric emission (scoped to SageMaker
        # namespace + this stack's log groups).
        sagemaker_role.add_to_policy(
            iam.PolicyStatement(
                sid="TrainingJobLogs",
                actions=[
                    "logs:CreateLogGroup",
                    "logs:CreateLogStream",
                    "logs:PutLogEvents",
                    "logs:DescribeLogStreams",
                ],
                resources=[
                    f"arn:aws:logs:{self.region}:{self.account}:log-group:/aws/sagemaker/TrainingJobs*",
                ],
            )
        )

        sagemaker_role.add_to_policy(
            iam.PolicyStatement(
                sid="TrainingMetrics",
                actions=["cloudwatch:PutMetricData"],
                resources=["*"],
                conditions={
                    "StringEquals": {
                        "cloudwatch:namespace": ["AWS/SageMaker", "/aws/sagemaker"],
                    }
                },
            )
        )

        # ------------------------------------------------------------------ #
        # Lambda — start training job
        # ------------------------------------------------------------------ #
        start_training_log_group = logs.LogGroup(
            self,
            "StartTrainingLogGroup",
            log_group_name=f"/aws/lambda/{component_name}-{environment}-start-training",
            retention=logs.RetentionDays.ONE_MONTH,
            removal_policy=RemovalPolicy.DESTROY,
        )

        start_training_lambda = lambda_.Function(
            self,
            "StartTrainingFunction",
            function_name=f"{component_name}-{environment}-start-training",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="index.handler",
            code=lambda_.Code.from_inline(self._get_start_training_code()),
            timeout=Duration.minutes(5),
            memory_size=256,
            environment={
                "COMPONENT_NAME": component_name,
                "ENVIRONMENT": environment,
                "BASE_MODEL": base_model,
                "INSTANCE_TYPE": instance_type,
                "INSTANCE_COUNT": str(instance_count),
                "EPOCHS": str(epochs),
                "LORA_RANK": str(lora_rank),
                "LEARNING_RATE": str(learning_rate),
                "VALIDATION_SPLIT": str(validation_split),
                "SAGEMAKER_ROLE_ARN": sagemaker_role.role_arn,
                "DATA_BUCKET": data_bucket.bucket_name,
                "REGION": self.region,
            },
            log_group=start_training_log_group,
        )

        start_training_lambda.add_to_role_policy(
            iam.PolicyStatement(
                sid="StartTrainingJob",
                actions=[
                    "sagemaker:CreateTrainingJob",
                    "sagemaker:DescribeTrainingJob",
                    "sagemaker:AddTags",
                ],
                resources=[
                    f"arn:aws:sagemaker:{self.region}:{self.account}:training-job/{component_name}-{environment}-*",
                ],
            )
        )

        start_training_lambda.add_to_role_policy(
            iam.PolicyStatement(
                sid="PassSageMakerRole",
                actions=["iam:PassRole"],
                resources=[sagemaker_role.role_arn],
                conditions={
                    "StringEquals": {"iam:PassedToService": "sagemaker.amazonaws.com"},
                },
            )
        )

        # ------------------------------------------------------------------ #
        # Lambda — check training status
        # ------------------------------------------------------------------ #
        check_status_log_group = logs.LogGroup(
            self,
            "CheckStatusLogGroup",
            log_group_name=f"/aws/lambda/{component_name}-{environment}-check-training-status",
            retention=logs.RetentionDays.ONE_MONTH,
            removal_policy=RemovalPolicy.DESTROY,
        )

        check_status_lambda = lambda_.Function(
            self,
            "CheckStatusFunction",
            function_name=f"{component_name}-{environment}-check-training-status",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="index.handler",
            code=lambda_.Code.from_inline(self._get_check_status_code()),
            timeout=Duration.minutes(1),
            memory_size=256,
            log_group=check_status_log_group,
        )

        check_status_lambda.add_to_role_policy(
            iam.PolicyStatement(
                sid="DescribeTrainingJob",
                actions=["sagemaker:DescribeTrainingJob"],
                resources=[
                    f"arn:aws:sagemaker:{self.region}:{self.account}:training-job/{component_name}-{environment}-*",
                ],
            )
        )

        # ------------------------------------------------------------------ #
        # Step Functions — training orchestration
        # ------------------------------------------------------------------ #

        # Start training
        start_task = tasks.LambdaInvoke(
            self,
            "StartTrainingJob",
            lambda_function=start_training_lambda,
            output_path="$.Payload",
            result_path="$.trainingResult",
        )

        # Wait between status checks
        wait_state = sfn.Wait(
            self,
            "WaitForTraining",
            time=sfn.WaitTime.duration(Duration.minutes(5)),
        )

        # Check status
        check_status_task = tasks.LambdaInvoke(
            self,
            "CheckTrainingStatus",
            lambda_function=check_status_lambda,
            output_path="$.Payload",
            result_path="$.statusResult",
        )

        # Terminal states
        training_succeeded = sfn.Succeed(self, "TrainingSucceeded")
        training_failed = sfn.Fail(
            self, "TrainingFailed",
            error="TrainingJobFailed",
            cause="The SageMaker training job failed",
        )

        # Choice: is training complete?
        is_complete = sfn.Choice(self, "IsTrainingComplete")
        is_complete.when(
            sfn.Condition.string_equals("$.statusResult.status", "Completed"),
            training_succeeded,
        )
        is_complete.when(
            sfn.Condition.string_equals("$.statusResult.status", "Failed"),
            training_failed,
        )
        is_complete.when(
            sfn.Condition.string_equals("$.statusResult.status", "Stopped"),
            training_failed,
        )
        is_complete.otherwise(wait_state)

        # Wire: wait -> check -> choice
        wait_state.next(check_status_task)
        check_status_task.next(is_complete)

        # Chain: start -> wait
        start_task.next(wait_state)

        # Create state machine
        sfn_log_group = logs.LogGroup(
            self,
            "StateMachineLogGroup",
            log_group_name=f"/aws/stepfunctions/{component_name}-{environment}-training",
            retention=logs.RetentionDays.ONE_MONTH,
            removal_policy=RemovalPolicy.DESTROY,
        )

        state_machine = sfn.StateMachine(
            self,
            "TrainingWorkflow",
            state_machine_name=f"{component_name}-{environment}-training-workflow",
            definition_body=sfn.DefinitionBody.from_chainable(start_task),
            timeout=Duration.hours(48),
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
            self, "DataBucketName",
            value=data_bucket.bucket_name,
            description="S3 bucket for training data and model artifacts",
        )
        CfnOutput(
            self, "TrainingRoleArn",
            value=sagemaker_role.role_arn,
            description="SageMaker training role ARN",
        )
        CfnOutput(
            self, "StateMachineArn",
            value=state_machine.state_machine_arn,
            description="Step Functions state machine ARN",
        )
        CfnOutput(
            self, "TrainingJobNamePattern",
            value=f"{component_name}-{environment}-*",
            description="Pattern for SageMaker training job names",
        )

    # ====================================================================== #
    # Lambda inline code helpers
    # ====================================================================== #

    @staticmethod
    def _get_start_training_code() -> str:
        return '''
import json
import boto3
import os
from datetime import datetime

sagemaker = boto3.client("sagemaker")


def handler(event, context):
    """Start a SageMaker training job with LoRA fine-tuning configuration."""
    component = os.environ["COMPONENT_NAME"]
    environment = os.environ["ENVIRONMENT"]
    base_model = os.environ["BASE_MODEL"]
    instance_type = os.environ["INSTANCE_TYPE"]
    instance_count = int(os.environ["INSTANCE_COUNT"])
    epochs = os.environ["EPOCHS"]
    lora_rank = os.environ["LORA_RANK"]
    learning_rate = os.environ["LEARNING_RATE"]
    validation_split = os.environ["VALIDATION_SPLIT"]
    role_arn = os.environ["SAGEMAKER_ROLE_ARN"]
    data_bucket = os.environ["DATA_BUCKET"]
    region = os.environ["REGION"]

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    job_name = event.get("jobName", f"{component}-{environment}-{timestamp}")

    training_data_path = event.get(
        "trainingDataS3Path", f"s3://{data_bucket}/training-data/"
    )
    output_path = f"s3://{data_bucket}/model-artifacts/{job_name}/"

    # HuggingFace training DLC image
    dlc_account = "763104351884"
    image_uri = (
        f"{dlc_account}.dkr.ecr.{region}.amazonaws.com/"
        f"huggingface-pytorch-training:2.1.0-transformers4.36.0-gpu-py310-cu121-ubuntu20.04"
    )

    hyperparameters = {
        "model_id": base_model,
        "epochs": epochs,
        "lora_r": lora_rank,
        "lora_alpha": str(int(lora_rank) * 2),
        "lora_dropout": "0.05",
        "learning_rate": learning_rate,
        "per_device_train_batch_size": "4",
        "gradient_accumulation_steps": "4",
        "validation_split": validation_split,
        "fp16": "true",
        "use_peft": "true",
        "merge_weights": "false",
    }

    params = {
        "TrainingJobName": job_name,
        "RoleArn": role_arn,
        "AlgorithmSpecification": {
            "TrainingImage": image_uri,
            "TrainingInputMode": "File",
        },
        "HyperParameters": hyperparameters,
        "InputDataConfig": [
            {
                "ChannelName": "training",
                "DataSource": {
                    "S3DataSource": {
                        "S3DataType": "S3Prefix",
                        "S3Uri": training_data_path,
                        "S3DataDistributionType": "FullyReplicated",
                    }
                },
                "ContentType": "application/json",
            }
        ],
        "OutputDataConfig": {"S3OutputPath": output_path},
        "ResourceConfig": {
            "InstanceType": instance_type,
            "InstanceCount": instance_count,
            "VolumeSizeInGB": 100,
        },
        "StoppingCondition": {"MaxRuntimeInSeconds": 86400},
        "Tags": [
            {"Key": "Name", "Value": component},
            {"Key": "environment", "Value": environment},
            {"Key": "genforge:managed", "Value": "true"},
            {"Key": "base-model", "Value": base_model},
        ],
    }

    try:
        response = sagemaker.create_training_job(**params)
        return {
            "success": True,
            "trainingJobName": job_name,
            "trainingJobArn": response["TrainingJobArn"],
            "status": "InProgress",
        }
    except Exception as e:
        return {"success": False, "error": str(e), "trainingJobName": job_name}
'''

    @staticmethod
    def _get_check_status_code() -> str:
        return '''
import boto3

sagemaker = boto3.client("sagemaker")


def handler(event, context):
    """Check the status of a SageMaker training job."""
    job_name = (
        event.get("trainingResult", {}).get("trainingJobName")
        or event.get("trainingJobName")
    )

    if not job_name:
        return {"status": "Failed", "error": "No training job name provided"}

    try:
        response = sagemaker.describe_training_job(TrainingJobName=job_name)

        status = response["TrainingJobStatus"]
        result = {
            "status": status,
            "trainingJobName": job_name,
            "trainingJobArn": response.get("TrainingJobArn"),
        }

        if status == "Completed":
            result["modelArtifacts"] = response.get("ModelArtifacts", {}).get(
                "S3ModelArtifacts"
            )
            result["trainingMetrics"] = [
                {"name": m["MetricName"], "value": m["Value"]}
                for m in response.get("FinalMetricDataList", [])
            ]
            result["trainingDurationSeconds"] = response.get(
                "TrainingTimeInSeconds"
            )
            result["billableSeconds"] = response.get("BillableTimeInSeconds")

        elif status == "Failed":
            result["failureReason"] = response.get("FailureReason")

        return result

    except Exception as e:
        return {"status": "Failed", "error": str(e), "trainingJobName": job_name}
'''

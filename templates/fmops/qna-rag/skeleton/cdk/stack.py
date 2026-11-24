"""QnA RAG Pipeline CDK Stack.

This stack provisions:
- OpenSearch Serverless collection (VECTORSEARCH type) with encryption,
  network, and data access policies
- Cognito User Pool and App Client for authentication
- S3 bucket for document storage (SSE-KMS)
- Lambda function for document ingestion (S3 event -> chunk -> embed -> index)
- Lambda function for query handling (query -> embed -> search -> augment -> LLM)
- IAM roles with least-privilege Bedrock and OpenSearch permissions
- S3 event notifications to trigger ingestion Lambda
"""

from typing import Any, List
import json
import aws_cdk as cdk
from aws_cdk import (
    Stack,
    CfnOutput,
    Tags,
    Duration,
    RemovalPolicy,
)
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_s3 as s3
from aws_cdk import aws_s3_notifications as s3n
from aws_cdk import aws_kms as kms
from aws_cdk import aws_iam as iam
from aws_cdk import aws_lambda as lambda_
from aws_cdk import aws_opensearchserverless as oss
from aws_cdk import aws_cognito as cognito
from aws_cdk import aws_logs as logs
from constructs import Construct


class QnARagStack(Stack):
    """QnA Retrieval-Augmented Generation pipeline."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        component_name: str,
        vpc_id: str,
        private_subnet_ids: List[str],
        bedrock_model_id: str,
        embedding_model_id: str,
        collection_name: str = "rag-vectors",
        vector_index_name: str = "document-vectors",
        vector_dimensions: int = 1536,
        environment: str = "dev",
        opensearch_vpc_endpoint_id: str = "",
        **kwargs: Any,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        removal = RemovalPolicy.DESTROY if environment == "dev" else RemovalPolicy.RETAIN
        auto_delete = environment == "dev"

        # ------------------------------------------------------------------ #
        # VPC lookup
        # ------------------------------------------------------------------ #
        vpc = ec2.Vpc.from_lookup(self, "VPC", vpc_id=vpc_id)

        # Resolve private subnets for the OpenSearch VPC endpoint (created
        # below when the caller does not supply an existing endpoint).
        oss_subnets = [
            ec2.Subnet.from_subnet_id(self, f"OSSSubnet{i}", sid)
            for i, sid in enumerate(private_subnet_ids)
        ]

        # ------------------------------------------------------------------ #
        # KMS key
        # ------------------------------------------------------------------ #
        encryption_key = kms.Key(
            self,
            "EncryptionKey",
            alias=f"{component_name}-{environment}-rag-key",
            enable_key_rotation=True,
            removal_policy=removal,
            description=f"Encryption key for {component_name} RAG pipeline",
        )

        # ------------------------------------------------------------------ #
        # S3 bucket — document storage
        # ------------------------------------------------------------------ #
        documents_bucket = s3.Bucket(
            self,
            "DocumentsBucket",
            bucket_name=f"{component_name}-{environment}-documents-{self.account}",
            encryption=s3.BucketEncryption.KMS,
            encryption_key=encryption_key,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy=removal,
            auto_delete_objects=auto_delete,
            versioned=True,
            enforce_ssl=True,
        )

        # ------------------------------------------------------------------ #
        # Cognito User Pool
        # ------------------------------------------------------------------ #
        user_pool = cognito.UserPool(
            self,
            "UserPool",
            user_pool_name=f"{component_name}-{environment}-users",
            self_sign_up_enabled=True,
            sign_in_aliases=cognito.SignInAliases(email=True),
            auto_verify=cognito.AutoVerifiedAttrs(email=True),
            password_policy=cognito.PasswordPolicy(
                min_length=8,
                require_lowercase=True,
                require_uppercase=True,
                require_digits=True,
                require_symbols=True,
            ),
            removal_policy=removal,
        )

        user_pool_client = user_pool.add_client(
            "AppClient",
            user_pool_client_name=f"{component_name}-{environment}-app-client",
            auth_flows=cognito.AuthFlow(
                user_password=True,
                user_srp=True,
            ),
        )

        # ------------------------------------------------------------------ #
        # OpenSearch Serverless collection
        # ------------------------------------------------------------------ #
        encryption_policy = oss.CfnSecurityPolicy(
            self,
            "OSSEncryptionPolicy",
            name=f"{component_name}-{environment}-enc"[:32],
            type="encryption",
            policy=json.dumps({
                "Rules": [{
                    "ResourceType": "collection",
                    "Resource": [f"collection/{collection_name}"],
                }],
                "AWSOwnedKey": True,
            }),
        )

        # ------------------------------------------------------------------ #
        # OpenSearch Serverless VPC endpoint
        # ------------------------------------------------------------------ #
        # Restrict access to the collection to a VPC endpoint. Public internet
        # access is disabled via AllowFromPublic=False in the network policy.
        oss_endpoint_sg = ec2.SecurityGroup(
            self,
            "OSSEndpointSecurityGroup",
            vpc=vpc,
            description=f"Security group for {component_name} OpenSearch Serverless VPC endpoint",
            allow_all_outbound=True,
        )
        oss_endpoint_sg.add_ingress_rule(
            ec2.Peer.ipv4(vpc.vpc_cidr_block),
            ec2.Port.tcp(443),
            "Allow HTTPS from within the VPC",
        )

        if opensearch_vpc_endpoint_id:
            # Caller supplied a pre-existing VPC endpoint.
            vpce_id = opensearch_vpc_endpoint_id
        else:
            oss_vpc_endpoint = oss.CfnVpcEndpoint(
                self,
                "OSSVpcEndpoint",
                name=f"{component_name}-{environment}-oss-vpce"[:32],
                vpc_id=vpc_id,
                subnet_ids=[s.subnet_id for s in oss_subnets],
                security_group_ids=[oss_endpoint_sg.security_group_id],
            )
            vpce_id = oss_vpc_endpoint.attr_id

        network_policy = oss.CfnSecurityPolicy(
            self,
            "OSSNetworkPolicy",
            name=f"{component_name}-{environment}-net"[:32],
            type="network",
            policy=json.dumps([{
                "Rules": [{
                    "ResourceType": "collection",
                    "Resource": [f"collection/{collection_name}"],
                }],
                "AllowFromPublic": False,
                "SourceVPCEs": [vpce_id],
            }]),
        )

        data_access_policy = oss.CfnAccessPolicy(
            self,
            "OSSDataAccessPolicy",
            name=f"{component_name}-{environment}-dap"[:32],
            type="data",
            policy=json.dumps([{
                "Rules": [
                    {
                        "ResourceType": "index",
                        "Resource": [f"index/{collection_name}/*"],
                        "Permission": ["aoss:*"],
                    },
                    {
                        "ResourceType": "collection",
                        "Resource": [f"collection/{collection_name}"],
                        "Permission": ["aoss:*"],
                    },
                ],
                "Principal": [f"arn:aws:iam::{self.account}:root"],
            }]),
        )

        collection = oss.CfnCollection(
            self,
            "VectorCollection",
            name=collection_name,
            type="VECTORSEARCH",
            description=f"Vector store for {component_name} RAG pipeline",
        )
        collection.add_dependency(encryption_policy)
        collection.add_dependency(network_policy)
        collection.add_dependency(data_access_policy)

        # ------------------------------------------------------------------ #
        # IAM role — ingestion Lambda
        # ------------------------------------------------------------------ #
        ingestion_role = iam.Role(
            self,
            "IngestionRole",
            role_name=f"{component_name}-{environment}-ingestion-role",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSLambdaBasicExecutionRole"
                ),
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSLambdaVPCAccessExecutionRole"
                ),
            ],
        )

        ingestion_role.add_to_policy(
            iam.PolicyStatement(
                actions=["bedrock:InvokeModel"],
                resources=[
                    f"arn:aws:bedrock:{self.region}::foundation-model/{embedding_model_id}",
                ],
            )
        )

        # Scoped to the collection this stack creates only. Prevents the
        # ingestion Lambda from reading or writing to unrelated OpenSearch
        # Serverless collections in the account.
        ingestion_role.add_to_policy(
            iam.PolicyStatement(
                sid="OpenSearchIngest",
                actions=["aoss:APIAccessAll"],
                resources=[collection.attr_arn],
            )
        )

        documents_bucket.grant_read(ingestion_role)

        # ------------------------------------------------------------------ #
        # Lambda — document ingestion
        # ------------------------------------------------------------------ #
        ingestion_log_group = logs.LogGroup(
            self,
            "IngestionLogGroup",
            log_group_name=f"/aws/lambda/{component_name}-{environment}-ingest",
            retention=logs.RetentionDays.ONE_MONTH,
            removal_policy=RemovalPolicy.DESTROY,
        )

        ingestion_lambda = lambda_.Function(
            self,
            "IngestionFunction",
            function_name=f"{component_name}-{environment}-ingest",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="index.handler",
            code=lambda_.Code.from_inline(self._get_ingestion_code()),
            timeout=Duration.minutes(15),
            memory_size=1024,
            role=ingestion_role,
            environment={
                "COLLECTION_ENDPOINT": collection.attr_collection_endpoint,
                "INDEX_NAME": vector_index_name,
                "EMBEDDING_MODEL_ID": embedding_model_id,
                "VECTOR_DIMENSIONS": str(vector_dimensions),
            },
            log_group=ingestion_log_group,
        )

        # S3 event notification -> ingestion Lambda
        documents_bucket.add_event_notification(
            s3.EventType.OBJECT_CREATED,
            s3n.LambdaDestination(ingestion_lambda),
            s3.NotificationKeyFilter(prefix="documents/"),
        )

        # ------------------------------------------------------------------ #
        # IAM role — query Lambda
        # ------------------------------------------------------------------ #
        query_role = iam.Role(
            self,
            "QueryRole",
            role_name=f"{component_name}-{environment}-query-role",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSLambdaBasicExecutionRole"
                ),
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSLambdaVPCAccessExecutionRole"
                ),
            ],
        )

        query_role.add_to_policy(
            iam.PolicyStatement(
                actions=["bedrock:InvokeModel"],
                resources=[
                    f"arn:aws:bedrock:{self.region}::foundation-model/{bedrock_model_id}",
                    f"arn:aws:bedrock:{self.region}::foundation-model/{embedding_model_id}",
                ],
            )
        )

        # Scoped to the collection this stack creates only. Prevents the
        # query Lambda from reading unrelated OpenSearch Serverless
        # collections in the account.
        query_role.add_to_policy(
            iam.PolicyStatement(
                sid="OpenSearchQuery",
                actions=["aoss:APIAccessAll"],
                resources=[collection.attr_arn],
            )
        )

        # ------------------------------------------------------------------ #
        # Lambda — query handler
        # ------------------------------------------------------------------ #
        query_log_group = logs.LogGroup(
            self,
            "QueryLogGroup",
            log_group_name=f"/aws/lambda/{component_name}-{environment}-query",
            retention=logs.RetentionDays.ONE_MONTH,
            removal_policy=RemovalPolicy.DESTROY,
        )

        query_lambda = lambda_.Function(
            self,
            "QueryFunction",
            function_name=f"{component_name}-{environment}-query",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="index.handler",
            code=lambda_.Code.from_inline(self._get_query_code()),
            timeout=Duration.minutes(2),
            memory_size=512,
            role=query_role,
            environment={
                "COLLECTION_ENDPOINT": collection.attr_collection_endpoint,
                "INDEX_NAME": vector_index_name,
                "BEDROCK_MODEL_ID": bedrock_model_id,
                "EMBEDDING_MODEL_ID": embedding_model_id,
                "VECTOR_DIMENSIONS": str(vector_dimensions),
            },
            log_group=query_log_group,
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
        CfnOutput(self, "DocumentsBucketName", value=documents_bucket.bucket_name,
                  description="S3 bucket for document storage")
        CfnOutput(self, "UserPoolId", value=user_pool.user_pool_id,
                  description="Cognito User Pool ID")
        CfnOutput(self, "UserPoolClientId", value=user_pool_client.user_pool_client_id,
                  description="Cognito App Client ID")
        CfnOutput(self, "OpenSearchEndpoint", value=collection.attr_collection_endpoint,
                  description="OpenSearch Serverless collection endpoint")
        CfnOutput(self, "OpenSearchCollectionArn", value=collection.attr_arn,
                  description="OpenSearch Serverless collection ARN")
        CfnOutput(self, "IngestionFunctionArn", value=ingestion_lambda.function_arn,
                  description="Ingestion Lambda function ARN")
        CfnOutput(self, "QueryFunctionArn", value=query_lambda.function_arn,
                  description="Query Lambda function ARN")

    # ====================================================================== #
    # Lambda inline code helpers
    # ====================================================================== #

    @staticmethod
    def _get_ingestion_code() -> str:
        return '''
import json
import os
import boto3
import urllib.parse

s3 = boto3.client("s3")
bedrock = boto3.client("bedrock-runtime")

COLLECTION_ENDPOINT = os.environ["COLLECTION_ENDPOINT"]
INDEX_NAME = os.environ["INDEX_NAME"]
EMBEDDING_MODEL_ID = os.environ["EMBEDDING_MODEL_ID"]
VECTOR_DIMENSIONS = int(os.environ.get("VECTOR_DIMENSIONS", "1536"))

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200


def handler(event, context):
    """Process S3 events: download document, chunk text, embed, index in OpenSearch."""
    for record in event.get("Records", []):
        bucket = record["s3"]["bucket"]["name"]
        key = urllib.parse.unquote_plus(record["s3"]["object"]["key"])

        obj = s3.get_object(Bucket=bucket, Key=key)
        content = obj["Body"].read().decode("utf-8")

        chunks = chunk_text(content, CHUNK_SIZE, CHUNK_OVERLAP)
        print(f"Processing {key}: {len(chunks)} chunks")

        for i, chunk in enumerate(chunks):
            embedding = generate_embedding(chunk)
            index_document(key, i, chunk, embedding)

    return {"statusCode": 200, "body": "Ingestion complete"}


def chunk_text(text, chunk_size, overlap):
    """Split text into overlapping chunks."""
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start = end - overlap
    return chunks


def generate_embedding(text):
    """Generate embedding vector using Bedrock."""
    if "titan" in EMBEDDING_MODEL_ID.lower():
        body = json.dumps({"inputText": text})
    else:
        body = json.dumps({"texts": [text], "input_type": "search_document"})

    response = bedrock.invoke_model(modelId=EMBEDDING_MODEL_ID, body=body)
    result = json.loads(response["body"].read())

    if "embedding" in result:
        return result["embedding"]
    elif "embeddings" in result:
        return result["embeddings"][0]
    return result


def index_document(source_key, chunk_index, text, embedding):
    """Index a document chunk in OpenSearch Serverless."""
    from opensearchpy import OpenSearch, RequestsHttpConnection
    from requests_aws4auth import AWS4Auth
    import boto3 as b3

    session = b3.Session()
    credentials = session.get_credentials()
    region = session.region_name
    auth = AWS4Auth(
        credentials.access_key,
        credentials.secret_key,
        region,
        "aoss",
        session_token=credentials.token,
    )

    host = COLLECTION_ENDPOINT.replace("https://", "")
    client = OpenSearch(
        hosts=[{"host": host, "port": 443}],
        http_auth=auth,
        use_ssl=True,
        verify_certs=True,
        connection_class=RequestsHttpConnection,
    )

    document = {
        "text": text,
        "embedding": embedding,
        "source": source_key,
        "chunk_index": chunk_index,
    }

    client.index(index=INDEX_NAME, body=document)
'''

    @staticmethod
    def _get_query_code() -> str:
        return '''
import json
import os
import boto3

bedrock = boto3.client("bedrock-runtime")

COLLECTION_ENDPOINT = os.environ["COLLECTION_ENDPOINT"]
INDEX_NAME = os.environ["INDEX_NAME"]
BEDROCK_MODEL_ID = os.environ["BEDROCK_MODEL_ID"]
EMBEDDING_MODEL_ID = os.environ["EMBEDDING_MODEL_ID"]
VECTOR_DIMENSIONS = int(os.environ.get("VECTOR_DIMENSIONS", "1536"))


def handler(event, context):
    """Handle a query: embed question, search vectors, augment prompt, call LLM."""
    body = json.loads(event.get("body", "{}")) if isinstance(event.get("body"), str) else event
    question = body.get("question", "")

    if not question:
        return {"statusCode": 400, "body": json.dumps({"error": "question is required"})}

    query_embedding = generate_embedding(question)

    relevant_docs = search_vectors(query_embedding, k=5)

    context_text = "\\n\\n".join([doc["text"] for doc in relevant_docs])

    answer = generate_answer(question, context_text)

    return {
        "statusCode": 200,
        "body": json.dumps({
            "answer": answer,
            "sources": [{"source": doc.get("source", ""), "score": doc.get("score", 0)} for doc in relevant_docs],
        }),
    }


def generate_embedding(text):
    """Generate embedding vector using Bedrock."""
    if "titan" in EMBEDDING_MODEL_ID.lower():
        body = json.dumps({"inputText": text})
    else:
        body = json.dumps({"texts": [text], "input_type": "search_query"})

    response = bedrock.invoke_model(modelId=EMBEDDING_MODEL_ID, body=body)
    result = json.loads(response["body"].read())

    if "embedding" in result:
        return result["embedding"]
    elif "embeddings" in result:
        return result["embeddings"][0]
    return result


def search_vectors(embedding, k=5):
    """Search OpenSearch Serverless for similar vectors."""
    from opensearchpy import OpenSearch, RequestsHttpConnection
    from requests_aws4auth import AWS4Auth
    import boto3 as b3

    session = b3.Session()
    credentials = session.get_credentials()
    region = session.region_name
    auth = AWS4Auth(
        credentials.access_key,
        credentials.secret_key,
        region,
        "aoss",
        session_token=credentials.token,
    )

    host = COLLECTION_ENDPOINT.replace("https://", "")
    client = OpenSearch(
        hosts=[{"host": host, "port": 443}],
        http_auth=auth,
        use_ssl=True,
        verify_certs=True,
        connection_class=RequestsHttpConnection,
    )

    query = {
        "size": k,
        "query": {
            "knn": {
                "embedding": {
                    "vector": embedding,
                    "k": k,
                }
            }
        },
    }

    response = client.search(index=INDEX_NAME, body=query)
    results = []
    for hit in response["hits"]["hits"]:
        results.append({
            "text": hit["_source"].get("text", ""),
            "source": hit["_source"].get("source", ""),
            "score": hit["_score"],
        })
    return results


def generate_answer(question, context):
    """Generate an answer using the Bedrock LLM with retrieved context."""
    prompt = f"""Use the following context to answer the question. If the context does not
contain enough information, say so.

Context:
{context}

Question: {question}

Answer:"""

    if "anthropic" in BEDROCK_MODEL_ID:
        body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 1024,
            "temperature": 0.1,
        })
    elif "titan" in BEDROCK_MODEL_ID:
        body = json.dumps({
            "inputText": prompt,
            "textGenerationConfig": {"maxTokenCount": 1024, "temperature": 0.1},
        })
    else:
        body = json.dumps({"prompt": prompt, "max_tokens": 1024, "temperature": 0.1})

    response = bedrock.invoke_model(modelId=BEDROCK_MODEL_ID, body=body)
    result = json.loads(response["body"].read())

    if "content" in result:
        return result["content"][0]["text"]
    elif "results" in result:
        return result["results"][0]["outputText"]
    elif "generations" in result:
        return result["generations"][0]["text"]
    return str(result)
'''

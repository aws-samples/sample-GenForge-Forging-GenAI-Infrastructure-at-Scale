# ${{ values.name }} - QnA RAG Pipeline

Retrieval-Augmented Generation solution with Amazon Bedrock and OpenSearch Serverless, provisioned by GenForge.

## Architecture

```
+----------------------------------------------------------------------+
|                        QnA RAG Pipeline                               |
|                                                                      |
|  +------------+       +--------------+       +-------------------+   |
|  |  Documents |------>|  Ingestion   |------>| OpenSearch        |   |
|  |  (S3)      |       |  Lambda      |       | Serverless        |   |
|  +------------+       +--------------+       | (Vector Store)    |   |
|                             |                +-------------------+   |
|                             v                        |               |
|                       +-----------+                  |               |
|                       | Bedrock   |                  |               |
|                       | Embedding |                  v               |
|                       +-----------+           +-----------+          |
|                                               | Query     |          |
|  +------------+                               | Lambda    |          |
|  |  User      |------------------------------>|           |          |
|  |  Query     |                               +-----------+          |
|  +------------+                                      |               |
|                                                      v               |
|                                               +-----------+          |
|                                               | Bedrock   |          |
|                                               | LLM       |          |
|                                               +-----------+          |
|                                                      |               |
|  +------------+       +-------------+                |               |
|  | Cognito    |       |  Answer +   |<---------------+               |
|  | Auth       |       |  Sources   |                                 |
|  +------------+       +-------------+                                |
+----------------------------------------------------------------------+
```

## Configuration

| Parameter | Value |
|-----------|-------|
| Environment | ${{ values.environment }} |
| AWS Region | ${{ values.awsRegion }} |
| AWS Account | ${{ values.awsAccountId }} |
| LLM Model | ${{ values.bedrockModelId }} |
| Embedding Model | ${{ values.embeddingModelId }} |
| Vector Dimensions | ${{ values.vectorDimensions }} |
| Collection Name | ${{ values.collectionName }} |
| VPC | ${{ values.vpcId }} |

## Deployment

### Prerequisites

1. AWS account with OIDC provider configured for GitHub Actions
2. Bedrock model access granted in the AWS console
3. VPC with private subnets deployed (use GenForge VPC template)

### Deploy Infrastructure

Push to `main` branch or manually trigger the deploy workflow:

```bash
gh workflow run deploy.yml
```

### Destroy Infrastructure

```bash
gh workflow run destroy.yml -f confirm=destroy
```

## Usage

### 1. Upload Documents

```bash
aws s3 cp my-document.txt \
  s3://${{ values.name }}-${{ values.environment }}-documents-${{ values.awsAccountId }}/documents/
```

Documents uploaded to the `documents/` prefix are automatically processed by the ingestion Lambda.

### 2. Query the Pipeline

Invoke the query Lambda function:

```bash
aws lambda invoke \
  --function-name ${{ values.name }}-${{ values.environment }}-query \
  --payload '{"question": "What is...?"}' \
  response.json
```

### 3. Monitor

- **CloudWatch Logs**: `/aws/lambda/${{ values.name }}-${{ values.environment }}-ingest` and `...-query`
- **OpenSearch Console**: View collection metrics and index stats

## Support

For issues, contact the ${{ values.owner }} team.

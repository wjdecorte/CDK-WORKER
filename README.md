# Stitch Worker

A serverless event-driven document processing pipeline built with AWS CDK. This project creates a series of Lambda functions and SQS queues that process documents through various stages: extraction, block processing, summarization, question generation, and feature extraction.

## Architecture

The system consists of two main stacks:

### StitchWorkerStack
1. **EventBridge Bus**: Central event bus for all document processing events (`{prefix}-{suffix}-datastores-bus`)
2. **SQS Queues**: Message queues for each processing stage
3. **Lambda Functions**: Serverless functions that process documents at each stage
4. **EventBridge Rules**: Rules that route events between processing stages

### StitchOrchestrationStack
1. **EventBridge Bus**: Dedicated bus for orchestration events (`{prefix}-{suffix}-orchestrations`)
2. **SQS Queue**: Queue for orchestration events (`{prefix}-{suffix}-start-orchestration`)
3. **EventBridge Rule**: Rule to handle orchestration events

### Processing Flow

1. **Document Upload**:
   - S3 upload to `ayd-dev-files` bucket triggers initial event
   - Event is routed to document extraction queue

2. **Document Extraction**:
   - Processes uploaded document
   - Emits "Document Extraction Completed" event

3. **Block Processing**:
   - Processes document blocks
   - Emits "Block Processing Completed" event
   - Triggers subsequent processes based on metadata

4. **Document Summary**:
   - Generates document summary when block processing completes
   - Emits "DocumentSummaryGenerated" event

5. **Seed Questions** (Conditional):
   - Triggered when block processing completes and `seed_questions_list` exists in metadata
   - Generates questions from document
   - Emits "SeedQuestionsGenerated" event

6. **Feature Extraction** (Conditional):
   - Triggered when block processing completes and `feature_types` exists in metadata
   - Extracts specified features from document
   - Emits "FeatureExtractionCompleted" event

## Prerequisites

- Python 3.12 or later
- Node.js and npm
- AWS CDK CLI
- AWS CLI configured with appropriate credentials
- AWS account with sufficient permissions
- [uv](https://github.com/astral-sh/uv) - Fast Python package installer and resolver

## Setup

1. Install AWS CDK CLI:
```bash
npm install -g aws-cdk
```

2. Install Python dependencies using uv:
```bash
# Install uv if you haven't already
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv sync
```

3. Configure AWS credentials:
```bash
aws configure
```

## Deployment

1. Bootstrap CDK (first time only):
```bash
cdk bootstrap
```

2. Deploy the stack:
```bash
cdk deploy
```

## Configuration

The stack can be configured through the `cdk.json` file:

```json
{
  "context": {
    "region": "us-east-2",
    "account": "613563724766",
    "environment": "development",
    "tags": {
      "Project": "stitch-worker",
      "Environment": "development",
      "Owner": "Jason DeCorte"
    },
    "naming": {
      "prefix": "stitch",
      "suffix": "dev"
    }
  }
}
```

## Event Patterns

Each stage in the pipeline has specific event patterns:

1. **Document Upload**:
   - Source: `aws.s3`
   - Detail Type: `Object Created`
   - Bucket: `ayd-dev-files`
   - Object Key: Prefix `jdtest/` and suffix `.pdf`

2. **Document Extraction**:
   - Source: `aws.s3`
   - Detail Type: `Object Created`
   - Bucket: `ayd-dev-files`

3. **Block Processing**:
   - Source: `stitch.worker`
   - Detail Type: `Document Extraction Completed`

4. **Document Summary**:
   - Source: `stitch.worker`
   - Detail Type: `Block Processing Completed`

5. **Seed Questions**:
   - Source: `stitch.worker`
   - Detail Type: `Block Processing Completed`
   - Requires: `seed_questions_list` in metadata

6. **Feature Extraction**:
   - Source: `stitch.worker`
   - Detail Type: `Block Processing Completed`
   - Requires: `feature_types` in metadata

7. **Orchestration Events**:
   - Source: `stitch.orchestration`
   - Detail Type: `StartOrchestration`

## Lambda Functions

Each Lambda function:
- Runs on Python 3.12
- Has a 5-minute timeout
- Has permissions to:
  - Put events to EventBridge
  - Process messages from its SQS queue

## SQS Queues

Each queue:
- Has a 5-minute visibility timeout
- Retains messages for 14 days
- Is named with the pattern: `{prefix}-{suffix}-{process-name}`

## Cleanup

To remove all resources:
```bash
cdk destroy
```

## Development

1. Make changes to the stack in `src/stitch_worker/stitch_worker_stack.py`
2. Update Lambda function code in `src/stitch_worker/lambda/{process}/index.py`
3. Test changes:
```bash
cdk synth  # Generate CloudFormation template
cdk diff   # Compare with deployed stack
cdk deploy # Deploy changes
```

### Managing Dependencies

This project uses `uv` for dependency management. Here are some common commands:

```bash
# Install dependencies
uv sync

# Add a new dependency
uv add <package>

# Add a development dependency
uv add --group dev <package>

# Update dependencies
uv sync
```

## License

This project is licensed under the GNU General Public License v3.0 (GPL-3.0). See the [LICENSE](LICENSE) file for details.

The GPL-3.0 license grants you the freedom to:
- Use the software for any purpose
- Change the software to suit your needs
- Share the software with your friends and neighbors
- Share the changes you make

When you distribute the software, you must:
- Include the source code
- Include the license
- State significant changes made to the software
- Include the same license with your modifications

# Stitch Worker

A serverless event-driven document processing pipeline built with AWS CDK. This project creates a series of Lambda functions and SQS queues that process documents through various stages: extraction, block processing, summarization, question generation, and feature extraction.

## Architecture

The system consists of the following components:

1. **EventBridge Bus**: Central event bus for all document processing events
2. **SQS Queues**: Message queues for each processing stage
3. **Lambda Functions**: Serverless functions that process documents at each stage
4. **EventBridge Rules**: Rules that route events between processing stages

### Processing Flow

1. **Document Upload**:
   - S3 upload triggers initial event
   - Event is routed to document extraction queue

2. **Document Extraction**:
   - Processes uploaded document
   - Emits "Document Extraction Completed" event

3. **Block Processing**:
   - Processes document blocks
   - Emits "Block Processing Completed" event

4. **Document Summary**:
   - Generates document summary
   - Emits "Document Summary Generated" event

5. **Seed Questions**:
   - Generates questions from document
   - Emits "Seed Questions Generated" event

6. **Feature Extraction**:
   - Extracts features from document
   - Final stage in the pipeline

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

2. **Document Extraction**:
   - Source: `stitch.worker.document_extract`
   - Detail Type: `Document Extraction Completed`

3. **Block Processing**:
   - Source: `stitch.worker.block_processing`
   - Detail Type: `Block Processing Completed`

4. **Document Summary**:
   - Source: `stitch.worker.document_summary`
   - Detail Type: `Document Summary Generated`

5. **Seed Questions**:
   - Source: `stitch.worker.seed_questions`
   - Detail Type: `Seed Questions Generated`

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
- Is named with the pattern: `{prefix}-{process}-queue-{suffix}`

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
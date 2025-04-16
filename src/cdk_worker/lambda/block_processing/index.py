import json
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def handler(event, context):
    logger.info(f"Received event: {json.dumps(event)}")
    
    for record in event['Records']:
        message = json.loads(record['body'])
        logger.info(f"Processing blocks for: {message}")
        
        # Add block processing logic here
        
    return {
        'statusCode': 200,
        'body': json.dumps('Block processing completed successfully')
    }
 
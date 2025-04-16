import json
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def handler(event, context):
    logger.info(f"Received event: {json.dumps(event)}")
    
    for record in event['Records']:
        message = json.loads(record['body'])
        logger.info(f"Processing document extraction for: {message}")
        
        # Add document extraction logic here
        
    return {
        'statusCode': 200,
        'body': json.dumps('Document extraction completed successfully')
    }

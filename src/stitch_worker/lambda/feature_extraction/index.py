import json
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def handler(event, context):
    logger.info(f"Received event: {json.dumps(event)}")
    
    for record in event['Records']:
        message = json.loads(record['body'])
        logger.info(f"Extracting features for: {message}")
        
        # Add feature extraction logic here
        
    return {
        'statusCode': 200,
        'body': json.dumps('Feature extraction completed successfully')
    }

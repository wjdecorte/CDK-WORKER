import json
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def handler(event, context):
    logger.info(f"Received event: {json.dumps(event)}")
    
    for record in event['Records']:
        message = json.loads(record['body'])
        logger.info(f"Generating seed questions for: {message}")
        
        # Add seed question generation logic here
        
    return {
        'statusCode': 200,
        'body': json.dumps('Seed question generation completed successfully')
    }

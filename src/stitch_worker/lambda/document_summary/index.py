import json
import logging
import time
import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def handler(event, context):
    logger.info(f"Received event: {json.dumps(event)}")
    
    for record in event['Records']:
        message = json.loads(record['body'])
        logger.info(f"Generating summary for: {message}")
        
        # Add document summarization logic here
        time.sleep(30)

        # publish to event bus
        event_bus = boto3.client('events')
        event_bus.put_events(
            Entries=[
                {
                    'Source': 'aws.lambda.document_summary',
                    'DetailType': 'Document Summary Generated',
                    'Detail': json.dumps({
                        'message': message,
                        'status': 'COMPLETED'
                    }),
                    'EventBusName': 'stitch-event-bus-dev'  
                }
            ]
        )
        
    return {
        'statusCode': 200,
        'body': json.dumps('Document summarization completed successfully')
    }

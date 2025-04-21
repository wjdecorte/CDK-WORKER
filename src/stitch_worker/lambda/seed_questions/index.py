import json
import logging
import time
import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def handler(event, context):
    logger.info(f"Received event: {json.dumps(event)}")
    
    for record in event["Records"]:
        message = json.loads(record["body"])
        logger.info(f"Generating seed questions for: {message}")
        
        # Add seed question generation logic here
        time.sleep(30)

        # publish to event bus
        event_bus = boto3.client("events")
        response = event_bus.put_events(
            Entries=[
                {
                    "Source": "stitch.worker.seed_questions",
                    "DetailType": "Seed Questions Generated",
                    "Detail": json.dumps({
                        "message": message,
                        "status": "COMPLETED"
                    }),
                    "EventBusName": "stitch-event-bus-dev"  
                }
            ]
        )
        logger.info(f"Published to event bus: {response=}")
    return {
        "statusCode": 200,
        "body": json.dumps("Seed question generation completed successfully")
    }

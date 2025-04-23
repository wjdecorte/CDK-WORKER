import json
import logging
import time
import boto3
from random import randint

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def handler(event, context):
    logger.info(f"Received event: {json.dumps(event)}")

    for record in event["Records"]:
        message = json.loads(record["body"])
        logger.info(f"Processing blocks for: {message}")

        # Add block processing logic here
        time.sleep(randint(30, 60))

        # publish to event bus
        event_bus = boto3.client("events")
        response = event_bus.put_events(
            Entries=[
                {
                    "Source": "stitch.worker.block_processing",
                    "DetailType": "BlockProcessingCompleted",
                    "Detail": json.dumps(
                        {
                            "metadata": {
                                "document_id": message["detail"]["metadata"]["document_id"],
                                "seed_questions_list": message["detail"]["metadata"]["seed_questions_list"],
                                "feature_types": message["detail"]["metadata"]["feature_types"],
                            },
                            "data": {"status": "COMPLETED"},
                        }
                    ),
                    "EventBusName": "stitch-dev-datastores-bus",
                }
            ]
        )
        logger.info(f"Published to event bus: {response=}")
    return {"statusCode": 200, "body": json.dumps("Block processing completed successfully")}

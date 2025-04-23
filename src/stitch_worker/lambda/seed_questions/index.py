import json
import logging
import time
import boto3
from uuid import uuid4
from random import randint

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def handler(event, context):
    logger.info(f"Received event: {json.dumps(event)}")

    for record in event["Records"]:
        message = json.loads(record["body"])
        logger.info(f"Generating seed questions for: {message}")

        # Add seed question generation logic here
        time.sleep(randint(30, 60))
        seed_questions_id = str(uuid4())
        seed_questions_list = message["detail"]["metadata"]["seed_questions_list"]
        logger.info(f"{seed_questions_list=}")

        # publish to event bus
        event_bus = boto3.client("events")
        response = event_bus.put_events(
            Entries=[
                {
                    "Source": "stitch.worker.seed_questions",
                    "DetailType": "SeedQuestionsGenerated",
                    "Detail": json.dumps(
                        {
                            "metadata": {
                                "document_id": message["detail"]["metadata"]["document_id"],
                                "seed_questions_id": seed_questions_id,
                            },
                            "data": {"status": "COMPLETED"},
                        }
                    ),
                    "EventBusName": "stitch-dev-datastores-bus",
                }
            ]
        )
        logger.info(f"Published to event bus: {response=}")
    return {"statusCode": 200, "body": json.dumps("Seed question generation completed successfully")}

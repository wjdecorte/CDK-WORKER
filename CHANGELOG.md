# Changelog

All notable changes to this project will be documented in this file.

## [0.1.3] - 2025-07-15
- 2025-07-15 feat: add database connection details; add ec2 state changer handler and lambda; add boto3 to dependencies
- 2025-07-14 feat: move process definition to a separate yaml file
- 2025-07-14 feat: add dynamic update to hub url
- 2025-07-12 feat: add local deployment; add ec2 instance for hub; refactor code
- 2025-06-30 feat: add block refinement process
- 2025-06-26 build: fix handler path (stitch_worker to worker)
- 2025-06-25 feat: add block summarization process; set batch size to 1
- 2025-06-20 build: add lambda block summarization flag
- 2025-05-29 feat: split environment into default and process specific
- 2025-05-28 feat: add enable flag for processes; remove textract sync poc
- 2025-05-22 feat: setting priority for dotenv file over env vars
- 2025-05-22 feat: add new enums
- 2025-05-09 fix: add missing permission for notification lambda
- 2025-05-09 feat: change textract notification lambda to use image; changed local variables to class attributes
- 2025-05-08 feat: add memory size option to lambdas
- 2025-05-07 feat: convert lambda policies to a dynamic config
- 2025-05-07 fix: source for text-extract-sync
- 2025-05-07 feat: add split file and text extract sync lambdas
- 2025-05-07 feat: add text extract notification lambda and queue to subscribe to sns; move text extract notification code to separate method
- 2025-05-01 feat: add textract and s3 permissions to document extract lambda
- 2025-04-30 feat: remove lambda code and boto3 dependency
- 2025-04-30 feat: add iam role for textract to sns; remove role arn env variable; fix s3 upload rule to use wildcard
- 2025-04-30 feat: set logging format to JSON for Lambdas
- 2025-04-30 fix: add logging
- 2025-04-30 build: add settings using pydantic-settings
- 2025-04-30 feat: add SNS topic for textract notifications
- 2025-04-28 feat: update image tag
- 2025-04-28 feat: Convert Lambda's to use docker image instead of zip archive
- 2025-04-25 fix: fix variable attribute path (missing detail)
- 2025-04-24 fix: custom_event is no longer a dictionary so fixed it to use attributes instead
- 2025-04-24 feat: added Lambda powertools; implemented new custom models; fixed source in put events
- 2025-04-23 feat: changed source to stitch.worker
- 2025-04-23 feat: update README file
- 2025-04-23 feat: updated names to match new convention (stitch-dev and no resource in the name); Fixed import issue in Lambda (can't import stitch_worker); added more realistic event payloads
- 2025-04-22 feat: Add stitch orchestration stack; add enums for event types; test new event patterns for optional actions
- 2025-04-21 feat: add prefix and suffix conditons to S3 event pattern; add pre-commit config and ruff.toml config
- 2025-04-21 fix: convert single quotes to double quotes using AI Agent
- 2025-04-18 feat: remove requirements.txt file; add README.md file
- 2025-04-18 feat: changed event source from aws.lambda to stitch.worker; added response capture for put_events()
- 2025-04-18 feat: fixed detail type for s3; added condition for specific bucket
- 2025-04-17 feat: added event bus, event rules and tweaked the naming logic
- 2025-04-16 feat: renamed to stitch-worker
- 2025-04-16 feat: initial commit
- 2025-04-18 Initial commit

- 2025-07-15 feat: add database connection details; add ec2 state changer handler and lambda; add boto3 to dependencies
- 2025-07-14 feat: move process definition to a separate yaml file
- 2025-07-14 feat: add dynamic update to hub url
- 2025-07-12 feat: add local deployment; add ec2 instance for hub; refactor code
- 2025-06-30 feat: add block refinement process
- 2025-06-26 build: fix handler path (stitch_worker to worker)
- 2025-06-25 feat: add block summarization process; set batch size to 1
- 2025-06-20 build: add lambda block summarization flag
- 2025-05-29 feat: split environment into default and process specific
- 2025-05-28 feat: add enable flag for processes; remove textract sync poc
- 2025-05-22 feat: setting priority for dotenv file over env vars
- 2025-05-22 feat: add new enums
- 2025-05-09 fix: add missing permission for notification lambda
- 2025-05-09 feat: change textract notification lambda to use image; changed local variables to class attributes
- 2025-05-08 feat: add memory size option to lambdas
- 2025-05-07 feat: convert lambda policies to a dynamic config
- 2025-05-07 fix: source for text-extract-sync
- 2025-05-07 feat: add split file and text extract sync lambdas
- 2025-05-07 feat: add text extract notification lambda and queue to subscribe to sns; move text extract notification code to separate method
- 2025-05-01 feat: add textract and s3 permissions to document extract lambda
- 2025-04-30 feat: remove lambda code and boto3 dependency
- 2025-04-30 feat: add iam role for textract to sns; remove role arn env variable; fix s3 upload rule to use wildcard
- 2025-04-30 feat: set logging format to JSON for Lambdas
- 2025-04-30 fix: add logging
- 2025-04-30 build: add settings using pydantic-settings
- 2025-04-30 feat: add SNS topic for textract notifications
- 2025-04-28 feat: update image tag
- 2025-04-28 feat: Convert Lambda's to use docker image instead of zip archive
- 2025-04-25 fix: fix variable attribute path (missing detail)
- 2025-04-24 fix: custom_event is no longer a dictionary so fixed it to use attributes instead
- 2025-04-24 feat: added Lambda powertools; implemented new custom models; fixed source in put events
- 2025-04-23 feat: changed source to stitch.worker
- 2025-04-23 feat: update README file
- 2025-04-23 feat: updated names to match new convention (stitch-dev and no resource in the name); Fixed import issue in Lambda (can't import stitch_worker); added more realistic event payloads
- 2025-04-22 feat: Add stitch orchestration stack; add enums for event types; test new event patterns for optional actions
- 2025-04-21 feat: add prefix and suffix conditons to S3 event pattern; add pre-commit config and ruff.toml config
- 2025-04-21 fix: convert single quotes to double quotes using AI Agent
- 2025-04-18 feat: remove requirements.txt file; add README.md file
- 2025-04-18 feat: changed event source from aws.lambda to stitch.worker; added response capture for put_events()
- 2025-04-18 feat: fixed detail type for s3; added condition for specific bucket
- 2025-04-17 feat: added event bus, event rules and tweaked the naming logic
- 2025-04-16 feat: renamed to stitch-worker
- 2025-04-16 feat: initial commit
- 2025-04-18 Initial commit

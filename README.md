# aws-skeetbot

A serverless bot that automatically posts AWS service updates from the "What's New" RSS feed to BlueSky social network.

## Features

- 🤖 Automatic monitoring of AWS What's New RSS feed
- 🚀 Real-time posting to BlueSky
- 🧠 Optional AI-powered post summarization using Anthropic
- ⚡ Serverless architecture using AWS Lambda
- 🔄 Scheduled execution via EventBridge

## Architecture

The solution uses several AWS services:
- AWS Lambda for serverless execution
- EventBridge for scheduled triggers
- Systems Manager Parameter Store for secure configuration
- CloudWatch for logging and monitoring

## Prerequisites

- AWS Account with administrative access
- [SAM CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-sam-cli-install.html) installed
- BlueSky account and credentials
- (Optional) Anthropic API key for AI summarization

## Configuration

### Required Parameters

Set up the following parameters in AWS Systems Manager Parameter Store:

```sh
/aws-skeetbot/bluesky-identifier # Your BlueSky account identifier 
/aws-skeetbot/bluesky-password # Your BlueSky password/app password
(Optional) /aws-skeetbot/ANTHROPIC_API_KEY # Your Anthropic key if you want it to summarize for you
```

## Setup

1. Set up the required SSM parameters in your AWS account as detailed in the previous section.

2. Install the SAM CLI if you haven't already:

```sh
brew install aws-sam-cli   # For macOS
# For other operating systems, see AWS SAM CLI documentation
```

## Deployment

Clone this repository:

```sh
git clone https://github.com/yourusername/aws-skeetbot.git
cd aws-skeetbot
```

Build and deploy using SAM:

```sh
sam build
sam deploy
```

## How It Works
* The bot runs on a scheduled basis using AWS EventBridge
* Checks the AWS What's New RSS feed for new entries
* Posts new updates to BlueSky using the configured credentials
* Uses AWS Lambda for serverless execution

## Troubleshooting
* Check CloudWatch Logs for execution details
* Verify SSM parameters are correctly set
* Ensure Lambda has appropriate IAM permissions

## Contributing
Contributions welcome! Please feel free to submit issues and pull requests.

## License
MIT License
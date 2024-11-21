from atproto import Client, client_utils, exceptions
import os
import boto3
from aws_lambda_powertools.utilities import parameters
import time
import feedparser
from aws_lambda_powertools import Logger
from strip_tags import strip_tags

# Setting these up here so that they're only loaded once per function instantiation
ssm_provider = parameters.SSMProvider()
USERNAME = ssm_provider.get("/skeetbot/SKEETBOT_USERNAME", decrypt=True)
APP_PASSWORD = ssm_provider.get("/skeetbot/SKEETBOT_PASSWORD", decrypt=True)
posts_table = boto3.resource("dynamodb", region_name="us-west-2").Table(
    os.environ["PostsTableName"]
)
# I really don't want to see posts from a decade ago flooding BlueSky, do you?
recency_threshold = int(os.environ["PostRecencyThreshold"])
logger = Logger()
client = Client()
client.login(USERNAME, APP_PASSWORD)


# Truncating mid-word feels unnatural, so we'll trim to the last word instead.
def trim_to_last_word(text, max_length):
    if len(text) <= max_length:
        return text
    trimmed = text[:max_length].rsplit(" ", 1)[0].rstrip(",")
    return trimmed


def within(t: time.struct_time, minutes: int) -> bool:
    return abs(time.mktime(time.gmtime()) - time.mktime(t)) <= (minutes * 60)


def already_posted(guid: str) -> bool:
    return "Item" in posts_table.get_item(Key={"guid": guid})


def skeetit(entry, trim: int):
    payload = trim_to_last_word(
        entry.title + "\n\n" + strip_tags(entry.description), trim
    )
    logger.info(f"Posting {entry.guid} - {entry.title}")
    logger.info(f"Link length: {len(entry.link)}")
    text = (
        client_utils.TextBuilder()
        .link(entry.title, entry.link)
        .text("\n\n")
        .text(payload)
        .text("…")
    )
    client.send_post(text)
    return text


@logger.inject_lambda_context
def lambda_handler(event, context):
    for entry in feedparser.parse("http://aws.amazon.com/new/feed/").entries:
        if within(
            entry.published_parsed,
            minutes=recency_threshold,
            # I know, I know, there's a DynamoDB way to do this via ConditionExpression, but I haven't cracked it yet.
            # This means that there's a race condition here if two are invoked at (nearly) the same time.
        ) and not already_posted(entry.guid):
            logger.info(f"Posting {entry.guid} - {entry.title}")
            # This is so, so stupid. There's no (sane) way to know how long a post will be after formatting so I have to
            # iteratively back off if the API throws an error.
            trim = 290
            while trim >= 200:
                try:
                    skeetit(entry, trim)
                    posts_table.put_item(
                        Item={
                            "guid": entry.guid,
                            "title": entry.title,
                            "link": entry.link,
                        }
                    )
                    break
                except exceptions.BadRequestError as err:
                    logger.warning(
                        f"Failed to post with length limit={trim}: {str(err)}"
                    )
                    trim -= 5
            else:
                logger.error(f"Failed to post {entry.guid} after multiple attempts.")

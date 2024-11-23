from atproto import Client, client_utils, exceptions
import os
import boto3
from aws_lambda_powertools.utilities import parameters
import time
import feedparser
from aws_lambda_powertools import Logger
from strip_tags import strip_tags
from atproto.exceptions import RequestException


# Custom exception for rate limit exceeded
class RateLimitExceededError(Exception):
    pass


# This should be all the stuff you need to change if you want to customize this any
USERNAME_PARAM = os.environ.get(
    "SKEETBOT_USERNAME_PARAM", "/skeetbot/SKEETBOT_USERNAME"
)
PASSWORD_PARAM = os.environ.get(
    "SKEETBOT_PASSWORD_PARAM", "/skeetbot/SKEETBOT_PASSWORD"
)
RSS_FEED_URL = os.environ.get("RSS_FEED_URL", "http://aws.amazon.com/new/feed/")
REGION = "us-west-2"

# Setting these up here so that they're only loaded once per function instantiation
ssm_provider = parameters.SSMProvider()
USERNAME = ssm_provider.get(USERNAME_PARAM, decrypt=True)
APP_PASSWORD = ssm_provider.get(PASSWORD_PARAM, decrypt=True)
posts_table = boto3.resource("dynamodb", region_name=REGION).Table(
    os.environ["PostsTableName"]
)
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


# Check if the given time is within the specified number of minutes from now
def within(t: time.struct_time, minutes: int) -> bool:
    return abs(time.mktime(time.gmtime()) - time.mktime(t)) <= (minutes * 60)


# Check if the post with the given GUID has already been posted
def already_posted(guid: str) -> bool:
    return "Item" in posts_table.get_item(Key={"guid": guid})


# Post the entry to the client
def skeetit(entry, trim: int):
    payload = trim_to_last_word(strip_tags(entry.description), trim)
    logger.info(f"Posting {entry.guid} - {entry.title}")
    logger.info(f"Link length: {len(entry.link)}")
    text = (
        client_utils.TextBuilder()
        .link(entry.title, entry.link)
        .text("\n\n")
        .text(payload)
        .text("…")
    )
    try:
        client.send_post(text)
    except RequestException as err:
        if err.response.status_code == 429:
            logger.error("Rate limit exceeded.")
            raise RateLimitExceededError("Rate limit exceeded.")
        logger.error(f"Failed to post {entry.guid} after multiple attempts.")
        raise err
    return text


# Process each entry from the feed
def process_entry(entry):
    if within(entry.published_parsed, minutes=recency_threshold) and not already_posted(
        entry.guid
    ):
        logger.info(f"Posting {entry.guid} - {entry.title}")
        trim = 290
        while trim >= 100:
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
            except RateLimitExceededError:
                logger.error("Rate limit exceeded, stopping execution.")
                return False
            except exceptions.BadRequestError as err:
                logger.warning(f"Failed to post with length limit={trim}: {str(err)}")
                if err.response.status_code == 429:
                    logger.warning("Rate limited, backing off.")
                    break
                trim -= 15
                if trim < 100:
                    logger.error(
                        f"Failed to post {entry.guid} after multiple attempts."
                    )
        return True
    return False


# Lambda handler function
@logger.inject_lambda_context
def lambda_handler(event, context):
    for entry in feedparser.parse(RSS_FEED_URL).entries:
        if not process_entry(entry):
            break
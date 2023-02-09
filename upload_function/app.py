import json
import logging
import os
import re
import urllib.parse
import requests
from requests.exceptions import Timeout, HTTPError, RequestException

# useful for more indepth debugging
# import http
# http.client.HTTPConnection.debuglevel = 1

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

CLEAN_BUCKET = os.environ.get('CLEAN_BUCKET')
QUARANTINE_BUCKET = os.environ.get('QUARANTINE_BUCKET')

ATTACHMENT_HOST = os.environ.get('ATTACHMENT_HOST')
ATTACHMENT_KEY = os.environ.get('ATTACHMENT_KEY')
ATTACHMENT_TIMEOUT = int(os.environ.get('ATTACHMENT_TIMEOUT', 10))  # default value of 10 seconds
ATTACHMENT_URL = "/submissions/{}/question/{}/attachment/scanresult"

S3_DOMAIN_PATTERN = r's3(\..+)?\.amazonaws.com'

CONTENT_HEADERS = {"Content-Type": "application/json"}


def parse_s3_object_url(url_string) -> str:
    url = urllib.parse.urlparse(url_string)
    # check pre-signed URL type, path or virtual
    if re.fullmatch(S3_DOMAIN_PATTERN, url.netloc):
        bucket = url.path.split('/')[1]
        s3_object = '/'.join(url.path.split('/')[2:])
    else:
        bucket = url.netloc.split('.')[0]
        s3_object = url.path[1:]
    pathname = urllib.parse.unquote_plus(s3_object)

    logger.debug("Source Bucket: %s", str(bucket))
    logger.debug("Pathname: %s", pathname)
    return pathname


def parse_pathname(fullpath: str) -> object:
    sections = fullpath.split('/')
    if len(sections) != 4:
        logger.error("Could not identify Application ID, Subscription ID, Question ID and filename from: %s", fullpath)
        return "", ""

    application_id: str = sections[0]
    subscription_id: str = sections[1]
    question_id: str = sections[2]
    filename: str = sections[3]
    logger.info("Application: %s", application_id)
    logger.info("Subscription: %s", subscription_id)
    logger.info("Question: %s", question_id)
    logger.info("Filename: %s", filename)
    return subscription_id, question_id


def clean_result(message) -> bool:
    try:
        scanning_result = message['scanning_result']
        any_findings = scanning_result.get('Findings')
        return not any_findings
    except KeyError:
        return False


def update_attachment(subscription_id: str, question_id: str, pathname: str, is_clean: bool):
    logger.info("Update: Subscription: %s, Question: %s, Pathname: %s, Clean: %s",
                subscription_id, question_id, pathname, str(is_clean))
    url: str = ATTACHMENT_URL.format(subscription_id, question_id)
    endpoint: str = str(ATTACHMENT_HOST) + url
    logger.debug("Passing request to %s", endpoint)

    try:
        response = requests.put(endpoint, json={'uri': pathname, 'isClean': is_clean}, headers=CONTENT_HEADERS,
                                timeout=ATTACHMENT_TIMEOUT)
        response.raise_for_status()
        logger.info("Successful Update: Subscription: %s, Question: %s, Pathname: %s, Clean: %s",
                    subscription_id, question_id, pathname, str(is_clean))

    except HTTPError as err:
        logger.error("%s: Failed to update grant attachment for Subscription ID %s Question ID %s",
                     err, subscription_id, question_id)
    except Timeout:
        logger.error("Timeout during request to %s", endpoint)
    except requests.exceptions.ConnectionError:  # Need full definition due to Python internal ConnectionError
        logger.error("Failed to connect to %s", endpoint)
    except RequestException as err:
        logger.error("%s: Error during request to %s", err, endpoint)
    except Exception as e:
        logger.error("%s: Failure during connection to %s", e, endpoint)


def s3_location(is_clean: bool, pathname: str) -> str:
    bucket = CLEAN_BUCKET if is_clean else QUARANTINE_BUCKET
    return "s3://" + bucket + "/" + pathname


def lambda_handler(event, context):
    logger.debug("Received event: %s", json.dumps(event, indent=2))
    for record in event['Records']:
        message = json.loads(record['Sns']['Message'])
        logger.debug(json.dumps(message))

        if message['scanner_status'] != 0:
            logger.warning("Skip: %s ", message['scanner_status_message'])
            continue

        pathname = parse_s3_object_url(message['file_url'])
        subscription_id, question_id = parse_pathname(pathname)
        is_clean = clean_result(message)
        new_location = s3_location(is_clean, pathname)

        if subscription_id:
            update_attachment(subscription_id, question_id, new_location, is_clean)

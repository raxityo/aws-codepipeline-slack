import json
import logging
import os
from pydoc import cli

from slack_sdk import WebClient

logger = logging.getLogger()
logger.setLevel(logging.INFO)

slack_bot_token = os.getenv("SLACK_BOT_TOKEN")
client = WebClient(token=slack_bot_token)

SLACK_CHANNEL = os.getenv("SLACK_CHANNEL", "deployments")
SLACK_APP_ID = os.getenv("SLACK_APP_ID")

CHANNEL_CACHE = {}


def find_channel(name):
    if name in CHANNEL_CACHE:
        return CHANNEL_CACHE[name]

    r = client.conversations_list(exclude_archived=1)
    if 'error' in r:
        print("conversations.list")
        logger.error("error: {}".format(r['error']))
    else:
        for ch in r['channels']:
            if ch['name'] == name:
                CHANNEL_CACHE[name] = ch['id']
                return ch['id']

    return None


def find_msg(ch):
    return client.conversations_history(channel=ch)


def find_my_messages(ch_name, app_id=SLACK_APP_ID):
    ch_id = find_channel(ch_name)
    msg = find_msg(ch_id)
    if 'error' in msg:
        print("find_my_messages")
        logger.error("error: {}".format(msg['error']))
    else:
        for m in msg['messages']:
            if m.get('app_id') == app_id:
                yield m


MSG_CACHE = {}


def find_message_for_build(buildInfo):
    cached = MSG_CACHE.get(buildInfo.executionId)
    if cached:
        return cached

    for m in find_my_messages(SLACK_CHANNEL):
        for att in msg_attachments(m):
            if att.get('footer') == buildInfo.executionId:
                MSG_CACHE[buildInfo.executionId] = m
                return m
    return None


def msg_attachments(m):
    return m.get('attachments', [])


def msg_fields(m):
    for att in msg_attachments(m):
        for f in att['fields']:
            yield f


def post_build_msg(msgBuilder):
    if msgBuilder.messageId:
        ch_id = find_channel(SLACK_CHANNEL)
        msg = msgBuilder.message()
        r = update_msg(ch_id, msgBuilder.messageId, msg)
        logger.info(json.dumps(r, indent=2, default=str))
        if r['ok']:
            r['message']['ts'] = r['ts']
            MSG_CACHE[msgBuilder.buildInfo.executionId] = r['message']
        return r

    r = send_msg(SLACK_CHANNEL, msgBuilder.message())
    if r['ok']:
        #MSG_CACHE[msgBuilder.buildInfo.executionId] = r['ts']
        CHANNEL_CACHE[SLACK_CHANNEL] = r['channel']

    return r


def send_msg(ch, attachments):
    r = client.chat_postMessage(channel=ch,
                                attachments=attachments)
    return r


def update_msg(ch, ts, attachments):
    r = client.chat_update(channel=ch,
                           ts=ts,
                           attachments=attachments)
    return r

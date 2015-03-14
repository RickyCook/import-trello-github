#!/usr/bin/env python
import argparse
import json
import logging
import sys

import py.path
import requests

LOG_LEVELS = {logging.getLevelName(level): level for level in (
    logging.DEBUG,
    logging.INFO,
    logging.WARNING,
    logging.ERROR,
    logging.CRITICAL
)}


class LogLevelAction(argparse.Action):
    """
    Transform a log level name into a log level using LOG_LEVELS constant as a
    map
    """
    def __call__(self, parser, namespace, value, option_string=None):
        setattr(namespace, self.dest, LOG_LEVELS[value])


class PyPathLocalAction(argparse.Action):
    """
    Create a py.path.local object
    """
    def __call__(self, parser, namespace, value, option_string=None):
        setattr(namespace, self.dest, py.path.local(value))


parser = argparse.ArgumentParser(
    description="Import Trello cards JSON into GitHub issues"
)

parser.add_argument("--loglevel", choices=LOG_LEVELS.keys(),
                    action=LogLevelAction, default=logging.INFO,
                    help="Set the minimum level to show logs for")

parser.add_argument("--statedir", action=PyPathLocalAction,
                    help="Directory to store change state")
parser.add_argument("--githubroot",
                    default="https://api.github.com",
                    help="Root for the GitHub API")

parser.add_argument("trello_json", action=PyPathLocalAction,
                    help="JSON file exported from Trello")
parser.add_argument("github_owner",
                    help="Owner of the GitHub repo")
parser.add_argument("github_repo",
                    help="Repo in GitHub")

parser.add_argument("github_user",
                    help="Your GitHub username")
parser.add_argument("github_password",
                    help="Your GitHub password")


class Card(object):
    def __init__(self, card_data, statedir=None):
        self.card_data = card_data
        self.state_file = None

        if statedir:
            self.state_file = statedir.join('%s.json' % card_data['id'])

    @property
    def state(self):
        try:
            with self.state_file.open() as handle:
                return json.load(handle)

        except py.error.ENOENT:
            return None


def gh_request(path, args):
    req = requests.get('%s/%s' % (args.githubroot, path),
                       auth=(args.github_user, args.github_password))

    if not req.ok:
        data = req.json()
        message = data.get(
            'message',
            "HTTP error %d: %s" % (req.status_code, req.reason)
        )
        logging.getLogger('github').error(message)
        return False

    return req


def main():
    args = parser.parse_args()

    logging.basicConfig(
        level=args.loglevel,
        format='%(levelname)s %(asctime)s [%(name)s] :: %(message)s',
        stream=sys.stderr,
    )

    with args.trello_json.open() as handle:
        trello_data = json.load(handle)

    logging.info("Importing from %s (%s)",
                 trello_data.get('name', "Unknown Trello name"),
                 trello_data.get('url', "Unknown URL"))

    if args.statedir:
        args.statedir.ensure_dir()
        logging.debug("Saving state")

    cards_log = logging.getLogger("cards import")
    cards_log.info("Importing %d cards", len(trello_data['cards']))

    req = gh_request('user', args)
    if not req:
        sys.exit(1)

    logging.info(
        "Importing as GitHub user %s",
        req.json().get('name', "unknown user name")
    )

    for card_data in trello_data['cards']:
        cards_log.debug("Card %s", card_data['name'])
        card = Card(card_data, args.statedir)
        card.state

if __name__ == '__main__':
    main()

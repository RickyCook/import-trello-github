#!/usr/bin/env python
import argparse
import json
import logging
import sys

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

parser = argparse.ArgumentParser(
    description="Import Trello cards JSON into GitHub issues"
)

parser.add_argument("--loglevel", choices=LOG_LEVELS.keys(),
                    action=LogLevelAction, default=logging.INFO,
                    help="Set the minimum level to show logs for")

parser.add_argument("trello_json",
                    help="JSON file exported from Trello")
parser.add_argument("github_owner",
                    help="Owner of the GitHub repo")
parser.add_argument("github_repo",
                    help="Repo in GitHub")

def main():
    args = parser.parse_args()

    logging.basicConfig(
        level=args.loglevel,
        format='%(levelname)s %(asctime)s [%(name)s] :: %(message)s',
        stream=sys.stderr,
    )

    with open(args.trello_json) as handle:
        trello_data = json.load(handle)

    logging.info("Importing from %s (%s)",
                 trello_data.get('name', "Unknown Trello name"),
                 trello_data.get('url', "Unknown URL"))

if __name__ == '__main__':
    main()

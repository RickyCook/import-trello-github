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

LABEL_COLORS = {
    'green': '70B500',
    'yellow': 'F2D600',
    'orange': 'FF9F1A',
    'red': 'EB5A46',
    'purple': 'C377E0',
    'blue': '0079BF',
    'sky': '00C2E0',
    'lime': '51E898',
    'pink': 'FF78CB',
    'black': '4D4D4D',
}


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
parser.add_argument("--labelmaps", action=PyPathLocalAction,
                    help="Map Trello labels to GitHub labels")

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


def dict_merge_arrays(left, right):
    for rkey, rval in right.items():
        if rkey in left:
            left[rkey] = left[rkey] + rval

        else:
            left[rkey] = rval


class LabelsMapper(object):
    def __init__(self, trello_data, args):
        self.trello_data = trello_data
        self.args = args
        self._labelmaps = None
        self._milestones = None

    @property
    def labelmaps(self):
        if not self.args.labelmaps:
            self._labelmaps = {}

        else:
            try:
                with self.args.labelmaps.open() as handle:
                    self._labelmaps = json.load(handle)

            except py.error.ENOENT:
                self._labelmaps = {}

        return self._labelmaps

    @property
    def milestones(self):
        if self._milestones is None:
            req = gh_request(
                'repos/%s/%s/milestones' % (
                    self.args.github_owner,
                    self.args.github_repo,
                ),
                self.args,
            )
            if not req:
                self._milestones = {}

            else:
                self._milestones = {
                    milestone['title']: milestone['number']
                    for milestone in req.json()
                }

        return self._milestones


    def args_for(self, card_data):
        ret = {}

        try:
            card_list_name = next(list_data['name']
                                  for list_data in self.trello_data['lists']
                                  if list_data['id'] == card_data['idList'])

            self._apply_mappings_for(ret, card_list_name, 'lists')

        except KeyError:
            pass

        if card_data['labels']:
            for label_data in card_data['labels']:
                self._apply_mappings_for(ret, label_data['name'], 'labels')

        return ret

    def _apply_mappings_for(self, ret, value, map_from_type):
        from_type_mappings = self.labelmaps.get(map_from_type, {})
        for map_to_type in ('label', 'milestone'):
            try:
                mappings = from_type_mappings[value]
                dict_merge_arrays(ret, self._arg_for_mapping(
                    map_to_type, mappings[map_to_type]
                ))
                break

            except KeyError:
                pass

        else:
            dict_merge_arrays(ret, {'labels': [value]})

    def _arg_for_mapping(self, map_type, name):
        if map_type == 'label':
            if not isinstance(name, (list, tuple)):
                name = [name]

            return {'labels': name}

        if map_type == 'milestone':
            return {'milestone': self.milestones[name]}

        else:
            raise Exception("Unknown mapping type: %s" % map_type)


class Card(object):
    def __init__(self, card_data, args, labels_mapper):
        self.card_data = card_data
        self.state_file = None
        self.args = args
        self.labels_mapper = labels_mapper

        if args.statedir:
            self.state_file = args.statedir.join('%s.json' % card_data['id'])

    @property
    def state(self):
        try:
            with self.state_file.open() as handle:
                return json.load(handle)

        except py.error.ENOENT:
            return None

    def save(self):
        state = self.state
        if state:
            req_fn = requests.patch
            req_url = state['url']

        else:
            req_fn = None
            req_url = 'repos/%s/%s/issues' % (self.args.github_owner,
                                              self.args.github_repo)

            state = {}

        state['title'] = self.card_data['name']
        state['body'] = self.card_data['desc']

        state = dict(
            list(state.items()) +
            list(self.labels_mapper.args_for(self.card_data).items())
        )

        req = gh_request(
            req_url, self.args, data=state, req_fn=req_fn,
        )

        if not req:
            return False

        data = req.json()
        state['url'] = data['url']

        with self.state_file.open('w') as handle:
            json.dump(state, handle)

        return True


def gh_request(path, args, data=None, req_fn=None):
    if data:
        if req_fn is None:
            req_fn = requests.post

        data = json.dumps(data)

    elif req_fn is None:
        req_fn = requests.get

    if '://' not in path:
        req_url = '%s/%s' % (args.githubroot, path)

    else:
        req_url = path

    req = req_fn(req_url,
                 auth=(args.github_user, args.github_password),
                 data=data)

    if not req.ok:
        try:
            data = req.json()
            message = data.get(
                'message',
                "HTTP error %d: %s" % (req.status_code, req.reason)
            )

        except ValueError:
            message = "HTTP error %d: %s" % (req.status_code, req.reason)

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

    labels_log = logging.getLogger("labels import")
    req = gh_request('repos/%s/%s/labels' % (args.github_owner,
                                             args.github_repo),
                     args)
    if not req:
        sys.exit(1)

    for label_color, label_name in trello_data['labelNames'].items():
        if label_name == '':
            continue

        for github_label in req.json():
            if github_label['name'] == label_name:
                labels_log.debug("Already have label %s", label_name)
                break

        else:
            labels_log.info("Creating label %s", label_name)
            label_req = gh_request(
                'repos/%s/%s/labels' % (args.github_owner,
                                        args.github_repo),
                 args,
                 data={'name': label_name,
                       'color': LABEL_COLORS[label_color]
                       },
            )
            if not label_req:
                sys.exit(1)

    cards_log = logging.getLogger("cards import")
    cards_log.info("Importing %d cards", len(trello_data['cards']))

    req = gh_request('user', args)
    if not req:
        sys.exit(1)

    logging.info(
        "Importing as GitHub user %s",
        req.json().get('name', "unknown user name")
    )
    labels_mapper = LabelsMapper(trello_data, args)

    for card_data in trello_data['cards']:
        cards_log.debug("Card %s", card_data['name'])
        card = Card(card_data, args, labels_mapper)
        ok = card.save()
        return


if __name__ == '__main__':
    main()

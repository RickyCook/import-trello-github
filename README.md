# Trello to GitHub issues
Simple import of exported Trello cards into GitHub issues

## Requirements
- Python 3.4

## Label rewrites `--labelmaps`
The `labelmaps` argument takes a JSON file with any of the following keys:

- `labels`
- `lists`

Each of these will take the names described under them, and translate them to
labels, or milestones as specified.

**Example**
```json
{
    "labels": {
        "Really Hard": {"label": "8 points"}
    },
    "lists": {
        "Done": { "state": "closed" },
        "Doing": { "label": ["in progress", "now"] },
        "Next Up": { "milestone": "alpha 4",
                     "label": "some label" },
        "Beta icebox": { "milestone": "beta" }
    }
}
```

## Example
For the Trello board at https://trello.com/b/zaFPjsli/dockci

**mappings.json**
```json
{
    "lists": {
        "Done": {"state": "closed" },
        "Doing": { "label": "in progress" },
        "Next Up": { "milestone": "alpha 4" },
        "Beta icebox": { "milestone": "beta" }
    }
}
```

```
./import-issues.py --loglevel DEBUG \
                   --statedir state \
                   --labelmaps mappings.json \
                   trello.json rickycook dockci \
                   my@email.com mypasswordhere
```

The `--statedir` flag is recommended to allow recovery in case GitHub's abuse detection is triggered (see #5). If this happens, rerun the command with the same `--statedir` value as before.

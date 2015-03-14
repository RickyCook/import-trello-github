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

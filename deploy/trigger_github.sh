#!/bin/bash
# Triggers the Tacek GitHub Actions workflow via workflow_dispatch.
# Requires a GitHub PAT stored in ~/.github_pat (chmod 600).
#
# One-time setup on Oracle VM:
#   echo "ghp_YOUR_TOKEN_HERE" > ~/.github_pat
#   chmod 600 ~/.github_pat

PAT_FILE="$HOME/.github_pat"
REPO="invertedburger/Tacek"
WORKFLOW="build.yml"
BRANCH="main"

if [ ! -f "$PAT_FILE" ]; then
    echo "ERROR: $PAT_FILE not found. Create it with your GitHub PAT." >&2
    exit 1
fi

PAT=$(cat "$PAT_FILE")

HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
    -X POST \
    -H "Authorization: token $PAT" \
    -H "Accept: application/vnd.github.v3+json" \
    "https://api.github.com/repos/$REPO/actions/workflows/$WORKFLOW/dispatches" \
    -d "{\"ref\":\"$BRANCH\"}")

echo "$(date '+%Y-%m-%d %H:%M:%S %Z') — dispatch HTTP $HTTP_STATUS"

if [ "$HTTP_STATUS" != "204" ]; then
    echo "ERROR: unexpected status $HTTP_STATUS" >&2
    exit 1
fi

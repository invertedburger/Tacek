#!/bin/bash
# Oracle Free Tier setup for Tacek trigger-only mode.
# The VM only needs git + curl (both pre-installed on Oracle Linux/Ubuntu).
# Run once. Requires ~/.github_pat to exist first.

set -e

PAT_FILE="$HOME/.github_pat"
INSTALL_DIR="$HOME/tacek"

echo "=== GitHub PAT ==="
if [ ! -f "$PAT_FILE" ]; then
    echo "ERROR: $PAT_FILE not found."
    echo "Create it first:  echo 'ghp_YOUR_TOKEN' > ~/.github_pat && chmod 600 ~/.github_pat"
    exit 1
fi
chmod 600 "$PAT_FILE"
PAT=$(cat "$PAT_FILE" | tr -d '[:space:]')
REPO_URL="https://${PAT}@github.com/invertedburger/Tacek.git"

echo "=== Cloning / updating repo ==="
if [ -d "$INSTALL_DIR/.git" ]; then
    git -C "$INSTALL_DIR" remote set-url origin "$REPO_URL"
    git -C "$INSTALL_DIR" pull
else
    git clone "$REPO_URL" "$INSTALL_DIR"
fi

echo "=== Making trigger script executable ==="
chmod +x "$INSTALL_DIR/deploy/trigger_github.sh"

echo ""
echo "=== Done! Next steps ==="
echo "1. Test:         $INSTALL_DIR/deploy/trigger_github.sh"
echo "2. Install cron: crontab $INSTALL_DIR/deploy/crontab.txt"
echo "3. Verify cron:  crontab -l"

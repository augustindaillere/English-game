#!/usr/bin/env bash
# Run ON THE VPS by GitHub Actions. Usage: deploy.sh <branch> <folder>
set -euo pipefail

BRANCH="${1:-main}"
APP_DIR="${2:-/opt/english-game}"

cd "$APP_DIR"
echo "==> Deploying $BRANCH into $APP_DIR"
git fetch --quiet origin "$BRANCH"
git checkout --quiet -B "$BRANCH" "origin/$BRANCH"
git reset --hard --quiet "origin/$BRANCH"
git log --oneline -1

docker compose up -d --build --remove-orphans
docker image prune -f >/dev/null
docker compose ps

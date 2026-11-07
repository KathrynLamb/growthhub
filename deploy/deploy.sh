#!/usr/bin/env bash
# deploy/deploy.sh
# Run on the server as the growthhub user:  ./deploy/deploy.sh
# Pulls main, installs deps, migrates, collects static, reloads Apache, then checks /healthz.
set -euo pipefail

APP=/srv/growthhub/app
PY=/srv/growthhub/venv/bin/python
HEALTH_URL=${HEALTH_URL:-https://stories.flipwhizz.com/healthz}

cd "$APP"
PREVIOUS=$(git rev-parse HEAD)

git fetch --quiet origin main
git reset --hard origin/main
echo "Deploying $(git rev-parse --short HEAD) (was ${PREVIOUS:0:7})"

/srv/growthhub/venv/bin/pip install --quiet -r requirements.txt
$PY manage.py migrate --noinput
$PY manage.py collectstatic --noinput --verbosity 0
$PY manage.py check --deploy --fail-level ERROR

# Touching wsgi.py makes mod_wsgi daemon processes reload the code.
touch config/wsgi.py
sleep 3

if curl --fail --silent --max-time 10 "$HEALTH_URL" > /dev/null; then
  echo "Healthy."
else
  echo "Health check FAILED. Roll back with:"
  echo "  git reset --hard $PREVIOUS && touch config/wsgi.py"
  echo "(If the release included a migration, check RUNBOOK.md before rolling back.)"
  exit 1
fi

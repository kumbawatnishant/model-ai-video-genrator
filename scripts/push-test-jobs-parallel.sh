#!/usr/bin/env bash
# Send N test jobs in parallel to the backend /api/jobs endpoint.
# Usage: ./scripts/push-test-jobs-parallel.sh [N] [CONCURRENCY] [BASE_URL] [AUTH_TOKEN] [DELAY]
#   N - total number of jobs to send (default 100)
#   CONCURRENCY - number of parallel workers (default 10)
#   BASE_URL - base URL of backend (default http://localhost:4000)
#   AUTH_TOKEN - Authorization Bearer token (default demo-token)
#   DELAY - optional delay (seconds) between spawning jobs (default 0)

set -euo pipefail

TOTAL=${1:-100}
CONCURRENCY=${2:-10}
BASE_URL=${3:-http://localhost:4000}
TOKEN=${4:-demo-token}
DELAY=${5:-0}

echo "Pushing $TOTAL jobs with concurrency=$CONCURRENCY to $BASE_URL (token=$TOKEN)"

send_job() {
  local idx=$1
  local timestamp
  timestamp=$(date +%s%3N)
  local prompt
  prompt="Parallel test job ${idx} - ${timestamp} - Aria relaxed portrait"
  local payload
  payload=$(printf '{"prompt":"%s","settings":{"voice":"default","length":30}}' "$prompt")

  http_code=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE_URL/api/jobs" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $TOKEN" \
    -d "$payload") || http_code=000

  echo "[$idx] HTTP $http_code"
}

running=0
i=1
pids=()
while [ $i -le $TOTAL ]; do
  # wait if reach concurrency
  while [ $(jobs -pr | wc -l) -ge $CONCURRENCY ]; do
    sleep 0.05
  done

  send_job "$i" &
  pids+=($!)
  i=$((i+1))

  if (( $(echo "$DELAY > 0" | bc -l) )); then
    sleep $DELAY
  fi
done

# wait for all background jobs
wait

echo "All $TOTAL jobs pushed."

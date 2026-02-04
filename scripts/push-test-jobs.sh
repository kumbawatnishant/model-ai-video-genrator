#!/usr/bin/env bash
# Send N test jobs to the backend /api/jobs endpoint.
# Usage: ./scripts/push-test-jobs.sh [N] [BASE_URL] [AUTH_TOKEN] [DELAY]
#   N - number of jobs to send (default 5)
#   BASE_URL - base URL of backend (default http://localhost:4000)
#   AUTH_TOKEN - Authorization Bearer token (default demo-token)
#   DELAY - seconds to wait between requests (default 0.1)

set -euo pipefail

N=${1:-5}
BASE_URL=${2:-http://localhost:4000}
TOKEN=${3:-demo-token}
DELAY=${4:-0.1}

echo "Sending $N test jobs to $BASE_URL/api/jobs with token '$TOKEN' (delay ${DELAY}s)"

for i in $(seq 1 $N); do
  TIMESTAMP=$(date +%s%3N)
  PROMPT="Test job ${i} - id ${TIMESTAMP} - Aria, relaxed urban portrait, golden hour, denim jacket"
  JSON_PAYLOAD=$(printf '{"prompt":"%s","settings":{"voice":"default","length":30}}' "$PROMPT")

  HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE_URL/api/jobs" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $TOKEN" \
    -d "$JSON_PAYLOAD")

  echo "[$i/$N] HTTP $HTTP_CODE - prompt: ${PROMPT}"
  sleep $DELAY
done

echo "Done."
#!/usr/bin/env bash
# Send N test jobs to the backend /api/jobs endpoint.
# Usage: ./scripts/push-test-jobs.sh [N] [BASE_URL] [AUTH_TOKEN] [DELAY]
#   N - number of jobs to send (default 5)
#   BASE_URL - base URL of backend (default http://localhost:4000)
#   AUTH_TOKEN - Authorization Bearer token (default demo-token)
#   DELAY - seconds to wait between requests (default 0.1)

set -euo pipefail

N=${1:-5}
BASE_URL=${2:-http://localhost:4000}
TOKEN=${3:-demo-token}
DELAY=${4:-0.1}

echo "Sending $N test jobs to $BASE_URL/api/jobs with token '$TOKEN' (delay $DELAYs)"

for i in $(seq 1 $N); do
  TIMESTAMP=$(date +%s%3N)
  PROMPT="Test job ${i} - id ${TIMESTAMP} - Aria, relaxed urban portrait, golden hour, denim jacket"
  JSON_PAYLOAD=$(printf '{"prompt":"%s","settings":{"voice":"default","length":30}}' "$PROMPT")

  HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE_URL/api/jobs" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $TOKEN" \
    -d "$JSON_PAYLOAD")

  echo "[$i/$N] HTTP $HTTP_CODE - prompt: ${PROMPT}"
  sleep $DELAY
done

echo "Done."

#!/bin/sh
set -eu
REWARD_FILE=/logs/verifier/reward.txt
REPORT=/logs/verifier/dispatch-junit.xml
REPORT_TMP="${REPORT}.tmp.$$"
STATUS=/logs/verifier/verification-status.txt
mkdir -p /logs/verifier
complete=0
write_reward(){ chmod 0644 "$REWARD_FILE" 2>/dev/null || true; printf '%s\n' "$1" > "$REWARD_FILE"; chmod 0444 "$REWARD_FILE" 2>/dev/null || true; }
cleanup(){ code=$?; if [ "$complete" -ne 1 ]; then write_reward 0.000; printf 'INCOMPLETE\n' > "$STATUS"; fi; rm -f "$REPORT_TMP"; exit "$code"; }
trap cleanup EXIT INT TERM HUP
write_reward 0.000
printf 'INCOMPLETE\n' > "$STATUS"
cd /tests
set +e
timeout --signal=TERM --kill-after=10s 300s python3 -B -I -m pytest -q -p no:cacheprovider --junitxml="$REPORT_TMP" /tests/test_outputs.py >/logs/verifier/pytest.log 2>&1
rc=$?
set -e
if [ "$rc" -ne 0 ] || [ ! -s "$REPORT_TMP" ]; then exit 1; fi
python3 -B -I /tests/verify_junit.py "$REPORT_TMP" /tests/scoring.json
python3 -B -I /tests/score.py --config /tests/scoring.json --junit "$REPORT_TMP" --report-out /logs/verifier/scoring-report.json --reward-out "$REWARD_FILE"
mv -f "$REPORT_TMP" "$REPORT"
complete=1
write_reward 1.000
printf 'COMPLETED\n' > "$STATUS"
trap - EXIT INT TERM HUP
exit 0

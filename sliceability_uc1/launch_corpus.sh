#!/bin/bash
# Launch (or resume) the v5 corpus run detached; then block until it exits (for a watcher).
# usage: sliceability_uc1/launch_corpus.sh <run_id> [--no-wait]
set -u
RID="$1"
cd "$(dirname "$0")/.." || exit 1
RD="sliceability_uc1/runs/$RID"
caffeinate -i -s nohup .venv/bin/python -m sliceability_uc1.run_corpus --run-id "$RID" --steps all \
    >> "$RD/run.log" 2>&1 &
echo $! > "$RD/caffeinate.pid"
echo "launched at $(date -u +%FT%TZ); caffeinate pid $(cat $RD/caffeinate.pid)"
[ "${2:-}" = "--no-wait" ] && exit 0
sleep 5
PID=$(cat "$RD/pid")
while kill -0 "$PID" 2>/dev/null; do sleep 120; done
echo "run process $PID exited at $(date -u +%FT%TZ)"
tail -5 "$RD/run.log"

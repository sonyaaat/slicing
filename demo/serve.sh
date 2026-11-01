#!/bin/bash
# Serve the demo at http://localhost:8765 (index.html also opens directly from disk).
# Build the data first, once: .venv/bin/python demo/build_data.py
# Responses carry Cache-Control: no-store, so an edited file shows on a plain reload.
cd "$(dirname "$0")" || exit 1
PORT="${1:-8765}"
echo "Sliceability demo: http://localhost:$PORT"
exec python3 - "$PORT" <<'EOF'
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer


class NoCache(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()


ThreadingHTTPServer(("127.0.0.1", int(sys.argv[1])), NoCache).serve_forever()
EOF

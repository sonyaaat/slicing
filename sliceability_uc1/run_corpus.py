"""Sliceability v5 corpus run. From the repository root:

    .venv/bin/python -m sliceability_uc1.run_corpus --run-id <ts> --steps all

See code/v5_main.py for the options.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "code"))

from v5_main import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())

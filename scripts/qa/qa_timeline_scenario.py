#!/usr/bin/env python3
"""
Compatibilité : déclenche uniquement le scénario timeline via qa_metrics_validation.
"""

from __future__ import annotations

import sys

from qa_metrics_validation import main


def timeline_main(argv: list[str]) -> None:
    """Forwarder that keeps the legacy CLI entrypoint alive."""
    forwarded = ["--skip-metrics"]
    forwarded.extend(argv)
    main(forwarded)


if __name__ == "__main__":
    timeline_main(sys.argv[1:])

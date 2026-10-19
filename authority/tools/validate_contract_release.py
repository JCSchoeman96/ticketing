#!/usr/bin/env python3
"""Validate a contract release ZIP against the proposed bundle profile."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

if __package__:
    from .build_contract_release import ReleaseError, validate_bundle
else:
    from build_contract_release import ReleaseError, validate_bundle


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path, help="contract bundle ZIP to validate")
    args = parser.parse_args(argv)
    try:
        result = validate_bundle(args.bundle)
    except ReleaseError as error:
        parser.error(str(error))
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

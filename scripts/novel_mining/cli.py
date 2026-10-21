"""Read text and check evidence directly; no database, registry or progress log."""

import argparse
import json
from pathlib import Path

from .extractor import validate_claims
from .slicer import read_text


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest="command", required=True)
    for name in ("read", "check"):
        sub = subs.add_parser(name)
        sub.add_argument("file", type=Path, help="Text to read during this invocation")
        sub.add_argument("--encoding", default="utf-8-sig")
        sub.add_argument("--chapters", help="Optional temporary selection, e.g. 1-3; never saved")
        if name == "check":
            sub.add_argument("--claims", type=Path, required=True, help="JSON list of evidence-backed claims")
    args = parser.parse_args(argv)
    try:
        text = read_text(args.file, args.encoding, args.chapters)
        if args.command == "read":
            print(text)
        else:
            claims = json.loads(args.claims.read_text(encoding="utf-8-sig"))
            errors = validate_claims(text, claims)
            if errors:
                parser.exit(1, "\n".join(errors) + "\n")
            print("Evidence text matches. Review meaning before using it in formal worldbuilding.")
    except (OSError, ValueError, LookupError) as exc:
        parser.exit(1, f"Error: {exc}\n")


if __name__ == "__main__":
    main()

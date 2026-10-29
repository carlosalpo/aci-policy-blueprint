"""Small offline CLI. A new output directory is required for every build."""

import argparse
import os
import sys
from pathlib import Path

from . import __version__
from .compiler import artifacts
from .model import InputError, json_text, load
from .validation import validate


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Compile and review ACI application policy offline."
    )
    parser.add_argument(
        "--version", action="version", version=f"aci-policy-blueprint {__version__}"
    )
    commands = parser.add_subparsers(dest="command", required=True)
    for command in ("validate", "build"):
        sub = commands.add_parser(command)
        sub.add_argument("--input", type=Path, required=True)
        if command == "build":
            sub.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        data, source_hash = load(args.input)
        if args.command == "validate":
            result = validate(data)
            print(json_text(result), end="")
            return 0 if result["valid"] else 1
        files, valid = artifacts(data, source_hash)
        args.output.mkdir(mode=0o700, parents=False, exist_ok=False)
        # The manifest is the final completion marker; never overwrite an older run.
        for name, content in files.items():
            descriptor = os.open(args.output / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(content)
        print(
            f"{'VALID MODEL' if valid else 'INVALID MODEL'} | offline-model-only | "
            f"{len(files)} artifacts | no APIC connection"
        )
        return 0 if valid else 1
    except InputError as exc:
        print(f"Input error: {exc}", file=sys.stderr)
    except FileExistsError:
        print("Output exists; choose a new directory. No files overwritten.", file=sys.stderr)
    except OSError:
        print(
            "File operation failed. Check paths/permissions; a partial directory may remain. "
            "Without a manifest the build is incomplete.",
            file=sys.stderr,
        )
    return 2


if __name__ == "__main__":
    sys.exit(main())

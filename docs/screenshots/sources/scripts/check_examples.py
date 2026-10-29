"""Exercise installed CLI examples; preserve real output and verify artifact hashes."""

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

CASES = {
    "three-tier": (0, None),
    "tcp-and-udp": (0, None),
    "isolated-epgs": (0, "NO_CONTRACT"),
    "invalid-cross-vrf": (1, "CROSS_VRF"),
    "invalid-overlap": (1, "SUBNET_OVERLAP"),
    "invalid-reference": (1, "UNKNOWN_EPG"),
    "invalid-broad-ports": (1, "BROAD_PORT_RANGE"),
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    rows = []
    root = Path(__file__).resolve().parents[1]
    for name, (expected, expected_code) in CASES.items():
        output = args.output / name
        result = subprocess.run(
            [
                "aci-blueprint",
                "build",
                "--input",
                str(root / "examples" / f"{name}.json"),
                "--output",
                str(output),
            ],
            text=True,
            capture_output=True,
        )
        (args.output / f"{name}.txt").write_text(result.stdout + result.stderr)
        assert result.returncode == expected, (name, result.stderr)
        validation = json.loads((output / "validation.json").read_text())
        if expected_code:
            assert expected_code in {item["code"] for item in validation["findings"]}
        assert (output / "tenant.json").exists() == (expected == 0)
        manifest = json.loads((output / "manifest.json").read_text())
        for filename, digest in manifest["files"].items():
            assert hashlib.sha256((output / filename).read_bytes()).hexdigest() == digest
        rows.append({"case": name, "exit_code": result.returncode, "verified": True})
        print(f"PASS {name}: exit {expected}; artifact hashes verified")
    (args.output / "summary.json").write_text(json.dumps(rows, indent=2) + "\n")


if __name__ == "__main__":
    main()

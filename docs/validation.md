# Validation record

Scope: local compiler and CLI tests using synthetic requirements. **No APIC connection, deployment, fabric simulation or live packet test has been performed for this project.**

## Verified release candidate — 2026-10-29

- Source commit: `dfcb727d2de41ca9ee4a362613a3836c67d3a445`.
- Local installed package: Python 3.12.14, **94 tests passed**, Ruff checks and formatting passed.
- Seven installed-CLI scenarios passed with expected exit codes and artifact hashes.
- [GitHub Actions run 40935836140](https://github.com/carlosalpo/aci-policy-blueprint/actions/runs/40935836140): successful matrix on Python **3.11, 3.12 and 3.13**.
- Three-tier output: 1 tenant, 1 VRF, 3 BDs, 3 EPGs, 2 contracts, 2 filters, 2 entries and 4 matrix rows (two requested directions plus two reverse-port rules).

| Example | Expected result | Verified |
| --- | --- | --- |
| `three-tier` | Valid model, exit 0, payload generated | Yes |
| `tcp-and-udp` | Valid model, exit 0, payload generated | Yes |
| `isolated-epgs` | Valid model, exit 0, `NO_CONTRACT` warnings | Yes |
| `invalid-cross-vrf` | Invalid model, exit 1, `CROSS_VRF`, no payload | Yes |
| `invalid-overlap` | Invalid model, exit 1, `SUBNET_OVERLAP`, no payload | Yes |
| `invalid-reference` | Invalid model, exit 1, `UNKNOWN_EPG`, no payload | Yes |
| `invalid-broad-ports` | Invalid model, exit 1, `BROAD_PORT_RANGE`, no payload | Yes |

## What is tested

The test suite checks schema and bounds, malformed inputs, reference resolution, duplicate names, subnet semantics, cross-VRF rejection, contract endpoint cardinality, exact service ranges, reverse-port matrix entries, deterministic generation, hash integrity, output permissions and refusal to overwrite existing runs. It also disables socket creation during a build to verify offline execution.

The seven-case executable example matrix verifies exit codes, expected findings, payload presence/absence and every manifest artifact hash. CI repeats the suite and examples on Python 3.11, 3.12 and 3.13. The workflow's downloadable artifacts contain synthetic outputs only.

Interpretation: these tests demonstrate the implemented compiler behavior. They do not establish APIC schema acceptance, hardware support, fabric convergence, endpoint reachability, effective isolation or suitability for production.

Reproduce with the commands in the root README. Captures must identify their source commit and distinguish generated policy review from an APIC screenshot.

The [five-image capture gallery](screenshots/README.md) includes a separate successful execution of the installed package, original stdout/stderr, relative command records, source checks and a SHA-256 inventory.

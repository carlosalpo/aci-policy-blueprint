# ACI Policy Blueprint

[![CI](https://github.com/carlosalpo/aci-policy-blueprint/actions/workflows/ci.yml/badge.svg)](https://github.com/carlosalpo/aci-policy-blueprint/actions/workflows/ci.yml)

**Turn explicit application communication requirements into a reviewable Cisco ACI policy design.**

Describe your VRFs, bridge domains, application EPGs and service flows in JSON. Validate the relationships, then generate an APIC managed-object payload, a communication matrix and an engineering review from the same input.

The included three-tier example allows Web → App on TCP 8443 and App → Database on TCP 5432. Each flow gets its own contract and filter, with one consumer and one provider. The matrix also exposes the reverse-port rules, so reviewers can see both directions rather than assume stateful firewall behavior.

**v0.1.0 is an offline design compiler.** It does not connect to APIC, apply configuration or prove fabric reachability. Validation covers the supported input model and generated artifacts; APIC acceptance and live fabric testing have not been performed.

![Conceptual illustration of application requirements translated into ACI policy spaces](docs/illustrations/aci-policy-blueprint-cover.png)

*Conceptual illustration, not a test capture or an APIC topology. [Illustration context](docs/illustrations/README.md).*

## Quick start

Python 3.11 or newer; no runtime dependencies or Cisco credentials.

```sh
git clone https://github.com/carlosalpo/aci-policy-blueprint.git
cd aci-policy-blueprint
python3 -m venv .venv
. .venv/bin/activate
python -m pip install .

aci-blueprint validate --input examples/three-tier.json
aci-blueprint build --input examples/three-tier.json --output blueprint-demo
```

Open `blueprint-demo/review.md` first. Review `tenant.json` and `communications.csv` alongside the input. Every build requires a **new output directory** whose parent already exists; previous runs are never overwritten.

## What it catches

| Condition | Behavior |
| --- | --- |
| Missing VRF, bridge domain or EPG reference | Reject the design |
| Overlapping BD subnets within one VRF | Reject the design |
| Cross-VRF or same-EPG flow | Reject as outside this model |
| Duplicate identifiers or overlapping service ranges for the same pair/protocol | Reject ambiguous or redundant intent |
| Invalid gateway, reversed port range or range wider than 1,024 ports | Reject the design |
| Unknown input fields, duplicate JSON keys, unsupported types or protocols | Reject the input |
| EPG with no modeled contract or unused bridge domain | Emit a review warning; build remains valid |

Invalid designs produce findings and provenance, **without an APIC payload**. Schema/JSON errors produce exit 2 before creating output. See [input specification](docs/input-spec.md) for bounds and [design decisions](docs/design.md) for interpretation.

## Output package

| Artifact | Purpose |
| --- | --- |
| `intent.json` | Canonical, sorted requirements |
| `tenant.json` | Desired `fvTenant` tree with VRFs, BDs, EPGs, contracts and filters |
| `communications.csv` | Consumer/provider and reverse-port rules, explicitly stateless |
| `validation.json` | Stable finding codes and locations |
| `review.md` | Human-readable findings, object inventory, matrix and deployment boundaries |
| `manifest.json` | Tool version, original-input hash, canonical hash and artifact SHA-256 hashes |

The manifest is written last and acts as the completion marker. An invalid design has only `validation.json`, `review.md` and `manifest.json`; check `result` before consuming output. A directory without a manifest is incomplete. Hashes detect changed bytes relative to that manifest; they are not a digital signature.

## Examples you can reproduce

```sh
# Valid model: exit 0
aci-blueprint build --input examples/three-tier.json --output demo-valid

# Rejected design: exit 1, CROSS_VRF, no tenant.json
aci-blueprint build --input examples/invalid-cross-vrf.json --output demo-cross-vrf

# Valid but isolated EPGs: exit 0, NO_CONTRACT warnings
aci-blueprint build --input examples/isolated-epgs.json --output demo-isolated
```

Seven examples cover the three-tier design, mixed TCP/UDP, isolated EPGs, cross-VRF flows, overlapping subnets, missing references and broad port ranges. All example addresses are from the documentation range `192.0.2.0/24`; examples contain no client configurations or credentials.

Exit codes: **0** valid model (warnings possible), **1** semantic design errors, **2** invalid input, CLI usage or file-operation failure. A valid model still requires engineering review.

## Deliberate design boundaries

- One user tenant, multiple VRFs, IPv4 routed BDs, application EPGs and TCP/UDP service ranges.
- Contracts use VRF scope. Subjects use both directions with reverse filter ports. Filters are stateless; a reverse-port match is not evidence that a connection was initiated by the consumer.
- VRF policy enforcement is enabled. EPG preferred-group membership is excluded. **Intra-EPG traffic remains unenforced**; intra-EPG isolation is not modeled.
- This is a proposed logical policy tree, not a complete fabric deployment. Domains, VLAN pools, AEPs, interface policies, static/VMM bindings, L3Out, shared services, route leaking, IPv6 and service graphs are outside v0.1.
- No discovery, reconciliation, deletion of stale objects, rollback or APIC transport. Posting this tree to an existing tenant would not remove unrelated policy. Existing `vzAny`, contracts and other policies can alter effective access.
- The matrix is a filter-design view. An absent row does **not** prove traffic is denied; a present row does **not** prove connectivity.

## Verification and development

```sh
python -m pip install '.[dev]'
ruff check src tests scripts
ruff format --check src tests scripts
pytest -q
python scripts/check_examples.py --output reports/example-matrix
```

Tests inspect the generated graph and all relation targets, verify one pair per contract, check bidirectional port semantics, exercise malformed inputs and negative designs, compare deterministic output under input reordering, verify hashes and prove the CLI refuses to overwrite a prior run. CI runs on Python 3.11, 3.12 and 3.13.

Read the [validation record](docs/validation.md), [design and Cisco references](docs/design.md), [input specification](docs/input-spec.md) and [security notes](SECURITY.md).

## En español

Herramienta de diseño para traducir requisitos de comunicación en políticas ACI revisables. Ayuda a detectar inconsistencias antes de preparar un cambio y mantiene alineados el archivo de políticas, la matriz de comunicaciones y la documentación. Esta versión se prueba localmente y en CI; no se presenta como una implementación validada en APIC.

Created by **Carlos Alvarado**. MIT licensed; an independent project, not a Cisco product.

"""Deterministic ACI managed objects and a matching, explicit filter matrix."""

import csv
import io
from collections import Counter

from . import __version__
from .model import InputError, canonical, json_text, sha256
from .validation import validate


def mo(class_name, attributes, children=()):
    body = {"attributes": attributes}
    if children:
        body["children"] = list(children)
    return {class_name: body}


def walk(tree):
    for class_name, body in tree.items():
        yield class_name, body["attributes"]
        for child in body.get("children", []):
            yield from walk(child)


def compile_policy(data):
    """Return the desired policy tree; invalid designs never reach rendering."""
    result = validate(data)
    if not result["valid"]:
        raise InputError("Design has validation errors; no APIC payload was generated.")
    data = canonical(data)
    children = [mo("fvCtx", {"name": v["name"], "pcEnfPref": "enforced"}) for v in data["vrfs"]]
    for bd in data["bridge_domains"]:
        children.append(
            mo(
                "fvBD",
                {
                    "name": bd["name"],
                    "unicastRoute": "yes",
                    "arpFlood": "yes",
                    "unkMacUcastAct": "proxy",
                },
                [
                    mo("fvRsCtx", {"tnFvCtxName": bd["vrf"]}),
                    mo("fvSubnet", {"ip": bd["gateway"], "scope": "private"}),
                ],
            )
        )
    for flow in data["flows"]:
        fid = flow["id"]
        entries = []
        for i, port in enumerate(flow["destination_ports"], 1):
            entries.append(
                mo(
                    "vzEntry",
                    {
                        "name": f"entry_{i:02d}",
                        "etherT": "ip",
                        "prot": flow["protocol"],
                        "sFromPort": "unspecified",
                        "sToPort": "unspecified",
                        "dFromPort": str(port["from"]),
                        "dToPort": str(port["to"]),
                        "stateful": "no",
                        "tcpRules": "unspecified",
                        "applyToFrag": "no",
                    },
                )
            )
        children.append(mo("vzFilter", {"name": f"flt_{fid}"}, entries))
        children.append(
            mo(
                "vzBrCP",
                {"name": f"ct_{fid}", "scope": "context"},
                [
                    mo(
                        "vzSubj",
                        {"name": "traffic", "revFltPorts": "yes"},
                        [
                            mo(
                                "vzRsSubjFiltAtt",
                                {"tnVzFilterName": f"flt_{fid}", "action": "permit"},
                            )
                        ],
                    )
                ],
            )
        )
    for app in data["applications"]:
        app_children = []
        for epg in app["epgs"]:
            key = f"{app['name']}/{epg['name']}"
            relations = [mo("fvRsBd", {"tnFvBDName": epg["bridge_domain"]})]
            for flow in data["flows"]:
                if flow["consumer"] == key:
                    relations.append(mo("fvRsCons", {"tnVzBrCPName": f"ct_{flow['id']}"}))
                if flow["provider"] == key:
                    relations.append(mo("fvRsProv", {"tnVzBrCPName": f"ct_{flow['id']}"}))
            app_children.append(
                mo(
                    "fvAEPg",
                    {"name": epg["name"], "pcEnfPref": "unenforced", "prefGrMemb": "exclude"},
                    relations,
                )
            )
        children.append(mo("fvAp", {"name": app["name"]}, app_children))
    return mo("fvTenant", {"name": data["tenant"], "dn": f"uni/tn-{data['tenant']}"}, children)


def matrix(data):
    """Include reverse-port rules, never describe them as stateful return traffic."""
    rows = []
    for flow in canonical(data)["flows"]:
        for ports in flow["destination_ports"]:
            service = str(ports["from"])
            if ports["to"] != ports["from"]:
                service += f"-{ports['to']}"
            common = {
                "flow": flow["id"],
                "contract": f"ct_{flow['id']}",
                "protocol": flow["protocol"],
                "stateful": "no",
            }
            rows.append(
                dict(
                    common,
                    direction="consumer-to-provider",
                    source=flow["consumer"],
                    destination=flow["provider"],
                    source_ports="any",
                    destination_ports=service,
                )
            )
            rows.append(
                dict(
                    common,
                    direction="provider-to-consumer",
                    source=flow["provider"],
                    destination=flow["consumer"],
                    source_ports=service,
                    destination_ports="any",
                )
            )
    return rows


def matrix_csv(rows):
    output = io.StringIO(newline="")
    writer = csv.DictWriter(
        output,
        fieldnames=[
            "flow",
            "contract",
            "direction",
            "source",
            "destination",
            "protocol",
            "source_ports",
            "destination_ports",
            "stateful",
        ],
        lineterminator="\n",
    )
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()


def review_report(data, validation, counts=None, rows=None):
    valid = validation["valid"]
    lines = [
        "# ACI Policy Blueprint — design review",
        "",
        f"Result: **{'VALID MODEL' if valid else 'INVALID MODEL'}**",
        "",
        f"Tenant: `{data['tenant']}` · Compiler: `{__version__}`",
        "",
        "Validation scope: **offline model only; no APIC or fabric test**.",
        "",
        "## Findings",
        "",
    ]
    if not validation["findings"]:
        lines.append("No modeled errors or warnings.")
    for item in validation["findings"]:
        lines.append(
            f"- **{item['severity'].upper()} {item['code']}** · "
            f"`{item['location']}`: {item['message']}"
        )
    if not valid:
        lines += ["", "No APIC policy, canonical intent or communication matrix was generated.", ""]
        return "\n".join(lines)
    lines += ["", "## Generated objects", "", "| Class | Count |", "| --- | ---: |"]
    for key, count in sorted(counts.items()):
        lines.append(f"| {key} | {count} |")
    lines += [
        "",
        "## Modeled filter matrix",
        "",
        "Source/destination here are EPGs, not IP addresses. Every reverse-port rule is shown.",
        "",
        "| Flow | Direction | Source | Destination | Protocol | Source ports | Destination ports |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            "| "
            + " | ".join(
                row[key]
                for key in [
                    "flow",
                    "direction",
                    "source",
                    "destination",
                    "protocol",
                    "source_ports",
                    "destination_ports",
                ]
            )
            + " |"
        )
    lines += [
        "",
        "## Engineering decisions",
        "",
        "- One contract and filter per flow, with exactly one consumer and one provider.",
        "- VRF policy enforcement enabled; contract scope is context (VRF).",
        "- Subjects apply in both directions and reverse source/destination filter ports.",
        "- Filters are stateless. Reverse-port rules can match independently initiated traffic.",
        "- EPGs are excluded from the preferred group. Intra-EPG isolation is disabled.",
        "- IPv4 BD gateway subnets are private; no route leaking or L3Out is generated.",
        "",
        "## Before any deployment",
        "",
        "Review against the target APIC model and release in an isolated lab. This tool does "
        "not deploy, reconcile existing objects, delete stale objects or provide rollback.",
        "",
        "Domains, VLAN pools, AEPs, interfaces, static/VMM bindings, physical connectivity, "
        "endpoint learning, routing and operational state are outside this blueprint. "
        "Existing contracts, vzAny, preferred groups, route leaking and other policies can "
        "change effective access. Missing matrix rows are not proof of denied traffic.",
        "",
    ]
    return "\n".join(lines)


def artifacts(data, input_sha):
    data = canonical(data)
    validation = validate(data)
    files = {"validation.json": json_text(validation)}
    counts, rows = {}, []
    if validation["valid"]:
        tree = compile_policy(data)
        counts = dict(sorted(Counter(cls for cls, _ in walk(tree)).items()))
        rows = matrix(data)
        files.update(
            {
                "intent.json": json_text(data),
                "tenant.json": json_text(tree),
                "communications.csv": matrix_csv(rows),
            }
        )
    files["review.md"] = review_report(data, validation, counts, rows)
    manifest = {
        "schema_version": 1,
        "tool": "aci-policy-blueprint",
        "version": __version__,
        "result": "valid-model" if validation["valid"] else "invalid-model",
        "validation_scope": "offline-model-only",
        "apic_tested": False,
        "input_sha256": input_sha,
        "canonical_intent_sha256": sha256(json_text(data).encode()),
        "object_counts": counts,
        "files": {name: sha256(content.encode()) for name, content in sorted(files.items())},
    }
    files["manifest.json"] = json_text(manifest)
    return files, validation["valid"]

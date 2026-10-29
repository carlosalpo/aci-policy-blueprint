import copy
import csv
import io
import json

from aci_blueprint.compiler import artifacts, compile_policy, matrix, walk
from aci_blueprint.model import canonical, json_text, sha256


def children(tree, cls):
    return [
        body
        for name, body in [(k, v) for child in tree.get("children", []) for k, v in child.items()]
        if name == cls
    ]


def test_exact_three_tier_policy_graph(design):
    tree = compile_policy(design)["fvTenant"]
    assert tree["attributes"] == {"name": "BlueprintDemo", "dn": "uni/tn-BlueprintDemo"}
    assert children(tree, "fvCtx")[0]["attributes"]["pcEnfPref"] == "enforced"
    epgs = children(children(tree, "fvAp")[0], "fvAEPg")
    expected = {
        "Web": ({"ct_web_to_app"}, set()),
        "App": ({"ct_app_to_database"}, {"ct_web_to_app"}),
        "Database": (set(), {"ct_app_to_database"}),
    }
    for epg in epgs:
        consumed = {c["attributes"]["tnVzBrCPName"] for c in children(epg, "fvRsCons")}
        provided = {c["attributes"]["tnVzBrCPName"] for c in children(epg, "fvRsProv")}
        assert (consumed, provided) == expected[epg["attributes"]["name"]]
        assert epg["attributes"]["prefGrMemb"] == "exclude"
        assert epg["attributes"]["pcEnfPref"] == "unenforced"
    for contract in children(tree, "vzBrCP"):
        assert contract["attributes"]["scope"] == "context"
        subject = children(contract, "vzSubj")[0]
        assert subject["attributes"]["revFltPorts"] == "yes"
        assert children(subject, "vzRsSubjFiltAtt")[0]["attributes"]["action"] == "permit"
        assert not children(subject, "vzInTerm")
        assert not children(subject, "vzOutTerm")


def test_every_relation_resolves(design):
    tree = compile_policy(design)
    nodes = list(walk(tree))
    targets = {
        cls: {a["name"] for c, a in nodes if c == cls}
        for cls in ["fvCtx", "fvBD", "vzBrCP", "vzFilter"]
    }
    for cls, attr in nodes:
        for relation, target, attribute in [
            ("fvRsCtx", "fvCtx", "tnFvCtxName"),
            ("fvRsBd", "fvBD", "tnFvBDName"),
            ("fvRsCons", "vzBrCP", "tnVzBrCPName"),
            ("fvRsProv", "vzBrCP", "tnVzBrCPName"),
            ("vzRsSubjFiltAtt", "vzFilter", "tnVzFilterName"),
        ]:
            if cls == relation:
                assert attr[attribute] in targets[target]


def test_one_pair_per_contract_prevents_cartesian_expansion(design):
    flow = copy.deepcopy(design["flows"][0])
    flow.update(id="database_to_app", consumer="Store/Database")
    design["flows"].append(flow)
    tree = compile_policy(design)["fvTenant"]
    consumers, providers = {}, {}
    for app in children(tree, "fvAp"):
        for epg in children(app, "fvAEPg"):
            key = app["attributes"]["name"] + "/" + epg["attributes"]["name"]
            for cls, index in [("fvRsCons", consumers), ("fvRsProv", providers)]:
                for rel in children(epg, cls):
                    index.setdefault(rel["attributes"]["tnVzBrCPName"], []).append(key)
    actual = {(consumers[c][0], providers[c][0]) for c in consumers}
    assert actual == {(f["consumer"], f["provider"]) for f in design["flows"]}
    assert all(len(value) == 1 for value in [*consumers.values(), *providers.values()])


def test_filter_ports_and_reverse_matrix_agree(design):
    design["flows"][0]["destination_ports"] = [{"from": 8000, "to": 8010}]
    nodes = dict((a["name"], a) for cls, a in walk(compile_policy(design)) if cls == "vzFilter")
    assert set(nodes) == {"flt_app_to_database", "flt_web_to_app"}
    entries = [a for cls, a in walk(compile_policy(design)) if cls == "vzEntry"]
    assert {(a["dFromPort"], a["dToPort"]) for a in entries} == {("5432", "5432"), ("8000", "8010")}
    assert all(a["etherT"] == "ip" and a["stateful"] == "no" for a in entries)
    rows = [r for r in matrix(design) if r["flow"] == "web_to_app"]
    assert [(r["source_ports"], r["destination_ports"]) for r in rows] == [
        ("any", "8000-8010"),
        ("8000-8010", "any"),
    ]
    assert rows[0]["source"] == rows[1]["destination"]
    assert rows[0]["destination"] == rows[1]["source"]


def test_reordering_is_deterministic_and_does_not_mutate(design):
    original = copy.deepcopy(design)
    baseline, _ = artifacts(design, "same-source-hash")
    assert design == original
    for key in ("vrfs", "bridge_domains", "applications", "flows"):
        design[key].reverse()
    for app in design["applications"]:
        app["epgs"].reverse()
    assert artifacts(design, "same-source-hash")[0] == baseline


def test_manifest_hashes_all_artifacts(design):
    files, valid = artifacts(design, "original-bytes-hash")
    assert valid
    manifest = json.loads(files["manifest.json"])
    assert manifest["input_sha256"] == "original-bytes-hash"
    assert manifest["canonical_intent_sha256"] == sha256(json_text(canonical(design)).encode())
    assert manifest["apic_tested"] is False
    assert set(manifest["files"]) == set(files) - {"manifest.json"}
    for name, expected in manifest["files"].items():
        assert sha256(files[name].encode()) == expected
    assert manifest["object_counts"]["vzBrCP"] == 2
    assert len(list(csv.DictReader(io.StringIO(files["communications.csv"])))) == 4


def test_invalid_has_reports_only(design):
    design["flows"][0]["provider"] = "Store/Missing"
    files, valid = artifacts(design, "source")
    assert not valid
    assert set(files) == {"validation.json", "review.md", "manifest.json"}
    assert json.loads(files["manifest.json"])["result"] == "invalid-model"


def test_no_flows_emits_no_contracts(design):
    design["flows"] = []
    nodes = list(walk(compile_policy(design)))
    assert not {"vzBrCP", "vzFilter", "fvRsCons", "fvRsProv"}.intersection(c for c, _ in nodes)
    assert matrix(design) == []

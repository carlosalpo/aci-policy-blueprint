"""Strict input contract and canonical representation; no network operations."""

import hashlib
import json
import re
from pathlib import Path

MAX_BYTES = 1_000_000
NAME = re.compile(r"[A-Za-z][A-Za-z0-9_-]{0,47}\Z")


class InputError(ValueError):
    """Invalid input. Messages never interpolate unvalidated values."""


def json_text(value):
    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True) + "\n"


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def _object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise InputError("Duplicate JSON keys are not allowed.")
        result[key] = value
    return result


def _constant(_value):
    raise InputError("Non-finite JSON numbers are not allowed.")


def load(path: Path):
    with path.open("rb") as handle:
        raw = handle.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise InputError("Input exceeds 1,000,000 bytes.")
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=_object, parse_constant=_constant)
    except (UnicodeError, json.JSONDecodeError, RecursionError, ValueError) as exc:
        raise InputError("Input must be bounded UTF-8 JSON with unique keys.") from exc
    check_shape(value)
    return canonical(value), sha256(raw)


def fields(value, expected, path):
    if not isinstance(value, dict) or set(value) != set(expected.split()):
        raise InputError(f"{path}: required fields must match the input specification exactly.")


def items(value, path, minimum=0, maximum=64):
    if not isinstance(value, list) or not minimum <= len(value) <= maximum:
        raise InputError(f"{path}: expected a list with {minimum}..{maximum} items.")
    return value


def name(value, path):
    if not isinstance(value, str) or not NAME.fullmatch(value):
        raise InputError(f"{path}: expected a letter then up to 47 letters, digits, _ or -.")


def endpoint(value, path):
    if not isinstance(value, str) or len(value.split("/")) != 2:
        raise InputError(f"{path}: expected application/epg.")
    for part in value.split("/"):
        name(part, path)


def check_shape(data):
    fields(data, "schema_version tenant vrfs bridge_domains applications flows", "root")
    if type(data["schema_version"]) is not int or data["schema_version"] != 1:
        raise InputError("schema_version: only integer 1 is supported.")
    name(data["tenant"], "tenant")
    if data["tenant"].lower() in {"common", "infra", "mgmt"}:
        raise InputError("tenant: built-in tenants are outside the supported scope.")
    for vrf in items(data["vrfs"], "vrfs", 1):
        fields(vrf, "name", "vrfs[]")
        name(vrf["name"], "vrfs[].name")
    for bd in items(data["bridge_domains"], "bridge_domains", 1):
        fields(bd, "name vrf gateway", "bridge_domains[]")
        name(bd["name"], "bridge_domains[].name")
        name(bd["vrf"], "bridge_domains[].vrf")
        if not isinstance(bd["gateway"], str) or len(bd["gateway"]) > 32:
            raise InputError("bridge_domains[].gateway: expected an IPv4 interface string.")
    for app in items(data["applications"], "applications", 1):
        fields(app, "name epgs", "applications[]")
        name(app["name"], "applications[].name")
        for epg in items(app["epgs"], "applications[].epgs", 1):
            fields(epg, "name bridge_domain", "applications[].epgs[]")
            name(epg["name"], "applications[].epgs[].name")
            name(epg["bridge_domain"], "applications[].epgs[].bridge_domain")
    if sum(len(app["epgs"]) for app in data["applications"]) > 256:
        raise InputError("applications: at most 256 EPGs in total are supported.")
    for flow in items(data["flows"], "flows", maximum=256):
        fields(flow, "id consumer provider protocol destination_ports", "flows[]")
        name(flow["id"], "flows[].id")
        endpoint(flow["consumer"], "flows[].consumer")
        endpoint(flow["provider"], "flows[].provider")
        if flow["protocol"] not in ("tcp", "udp"):
            raise InputError("flows[].protocol: only tcp and udp are supported.")
        for port in items(flow["destination_ports"], "flows[].destination_ports", 1, 16):
            fields(port, "from to", "flows[].destination_ports[]")
            if any(type(port[key]) is not int or not 1 <= port[key] <= 65535 for key in port):
                raise InputError("flows[].destination_ports[]: ports must be integers 1..65535.")


def canonical(data):
    """Return a detached model, stable under input collection reordering."""
    result = json.loads(json_text(data))
    for key in ("vrfs", "bridge_domains", "applications"):
        result[key].sort(key=lambda item: item["name"])
    for app in result["applications"]:
        app["epgs"].sort(key=lambda item: item["name"])
    result["flows"].sort(key=lambda item: item["id"])
    for flow in result["flows"]:
        flow["destination_ports"].sort(key=lambda port: (port["from"], port["to"]))
    return result

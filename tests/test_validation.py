import copy

import pytest

from aci_blueprint.compiler import compile_policy
from aci_blueprint.model import InputError, check_shape
from aci_blueprint.validation import validate


def codes(design):
    return {item["code"] for item in validate(design)["findings"]}


def test_valid_three_tier(design):
    assert validate(design) == {
        "schema_version": 1,
        "valid": True,
        "validation_scope": "offline-model-only",
        "findings": [],
    }


@pytest.mark.parametrize("section", ["vrfs", "bridge_domains", "applications"])
def test_duplicate_names(design, section):
    design[section].append(copy.deepcopy(design[section][0]))
    assert "DUPLICATE_NAME" in codes(design)
    with pytest.raises(InputError):
        compile_policy(design)


def test_duplicate_epg(design):
    design["applications"][0]["epgs"].append(copy.deepcopy(design["applications"][0]["epgs"][0]))
    assert "DUPLICATE_NAME" in codes(design)


def test_unknown_vrf(design):
    design["bridge_domains"][0]["vrf"] = "Missing"
    assert "UNKNOWN_VRF" in codes(design)


def test_unknown_bd(design):
    design["applications"][0]["epgs"][0]["bridge_domain"] = "Missing"
    assert "UNKNOWN_BD" in codes(design)


@pytest.mark.parametrize("endpoint", ["consumer", "provider"])
def test_unknown_epg(design, endpoint):
    design["flows"][0][endpoint] = "Store/Missing"
    assert "UNKNOWN_EPG" in codes(design)


def test_cross_vrf(design):
    design["vrfs"].append({"name": "Other"})
    design["bridge_domains"][0]["vrf"] = "Other"
    assert "CROSS_VRF" in codes(design)


def test_same_epg(design):
    design["flows"][0]["provider"] = design["flows"][0]["consumer"]
    assert "SAME_EPG" in codes(design)


def test_subnet_overlap(design):
    design["bridge_domains"][1]["gateway"] = "192.0.2.2/25"
    assert "SUBNET_OVERLAP" in codes(design)


def test_overlap_across_vrfs_is_allowed(design):
    design["vrfs"].append({"name": "Other"})
    design["bridge_domains"].append({"name": "OtherBD", "vrf": "Other", "gateway": "192.0.2.2/26"})
    assert validate(design)["valid"]
    assert "UNUSED_BD" in codes(design)


@pytest.mark.parametrize(
    "gateway",
    [
        "192.0.2.0/26",
        "192.0.2.63/26",
        "192.0.2.1",
        "192.0.2.1/31",
        "192.0.2.1/32",
        "192.0.2.1/0",
        "::1/64",
        "127.0.0.1/24",
        "224.0.0.1/24",
        "0.0.0.0/24",
        "169.254.1.1/24",
        "240.0.0.1/24",
        "bad<secret>",
    ],
)
def test_invalid_gateway(design, gateway):
    design["bridge_domains"][0]["gateway"] = gateway
    assert "INVALID_GATEWAY" in codes(design)
    assert gateway not in str(validate(design)["findings"])


def test_duplicate_flow(design):
    design["flows"].append(copy.deepcopy(design["flows"][0]))
    assert {"DUPLICATE_FLOW_ID", "OVERLAPPING_FLOW"} <= codes(design)


@pytest.mark.parametrize(
    "ports,code",
    [
        ([{"from": 20, "to": 10}], "REVERSED_PORT_RANGE"),
        ([{"from": 1, "to": 65535}], "BROAD_PORT_RANGE"),
        ([{"from": 100, "to": 200}, {"from": 200, "to": 300}], "OVERLAPPING_FLOW"),
    ],
)
def test_port_semantics(design, ports, code):
    design["flows"][0]["destination_ports"] = ports
    assert code in codes(design)


def test_overlapping_separate_flows(design):
    flow = copy.deepcopy(design["flows"][0])
    flow["id"] = "another"
    design["flows"].append(flow)
    assert "OVERLAPPING_FLOW" in codes(design)


def test_disjoint_ports_and_different_protocols(design):
    flow = copy.deepcopy(design["flows"][0])
    flow["id"] = "udp_service"
    flow["protocol"] = "udp"
    design["flows"].append(flow)
    assert validate(design)["valid"]


def test_isolated_epgs_are_valid_with_warning(design):
    design["flows"] = []
    result = validate(design)
    assert result["valid"]
    assert len(result["findings"]) == 3
    assert codes(design) == {"NO_CONTRACT"}


@pytest.mark.parametrize(
    "name",
    [
        "common",
        "infra",
        "mgmt",
        "COMMON",
        "bad/name",
        "../evil",
        "bad\nname",
        "bad name",
        "<script>",
        "a" * 49,
        "1name",
        "",
        None,
    ],
)
def test_unsupported_tenant_names(design, name):
    design["tenant"] = name
    with pytest.raises(InputError):
        check_shape(design)


@pytest.mark.parametrize("version", [True, 1.0, 2, "1", None])
def test_schema_version_is_strict(design, version):
    design["schema_version"] = version
    with pytest.raises(InputError):
        check_shape(design)


@pytest.mark.parametrize("port", [True, 0, 65536, 1.0, "443", None])
def test_port_types(design, port):
    design["flows"][0]["destination_ports"][0]["from"] = port
    with pytest.raises(InputError):
        check_shape(design)


@pytest.mark.parametrize("protocol", ["any", "icmp", "TCP", None, [], {}])
def test_protocol_scope(design, protocol):
    design["flows"][0]["protocol"] = protocol
    with pytest.raises(InputError):
        check_shape(design)


def test_unknown_fields_rejected(design):
    design["apic_password"] = "PRIVATE_TEST_SENTINEL"
    with pytest.raises(InputError) as error:
        check_shape(design)
    assert "PRIVATE_TEST_SENTINEL" not in str(error.value)


def test_missing_fields_rejected(design):
    del design["flows"][0]["provider"]
    with pytest.raises(InputError):
        check_shape(design)


def test_limits(design):
    design["flows"] *= 129
    with pytest.raises(InputError):
        check_shape(design)

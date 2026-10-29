"""Validate a deliberately limited, single-tenant application policy model."""

from ipaddress import IPv4Interface

from .model import check_shape


def validate(data):
    check_shape(data)
    findings = []

    def finding(code, location, message, severity="error"):
        findings.append(dict(code=code, location=location, message=message, severity=severity))

    def index(values, location):
        result = {}
        for value in values:
            key = value["name"]
            if key in result:
                finding("DUPLICATE_NAME", location, f"Duplicate name: {key}.")
            result[key] = value
        return result

    vrfs = index(data["vrfs"], "vrfs")
    bds = index(data["bridge_domains"], "bridge_domains")
    apps = index(data["applications"], "applications")
    networks = {}
    for bd in bds.values():
        location = f"bridge_domains/{bd['name']}"
        if bd["vrf"] not in vrfs:
            finding("UNKNOWN_VRF", location, "Referenced VRF does not exist.")
        try:
            if "/" not in bd["gateway"]:
                raise ValueError
            address = IPv4Interface(bd["gateway"])
            if (
                address.network.prefixlen > 30
                or address.ip
                in (address.network.network_address, address.network.broadcast_address)
                or address.ip.is_multicast
                or address.ip.is_unspecified
                or address.ip.is_loopback
                or address.ip.is_link_local
                or address.ip.is_reserved
                or str(address) != bd["gateway"]
            ):
                raise ValueError
            networks[bd["name"]] = address.network
        except ValueError:
            finding(
                "INVALID_GATEWAY", location, "Use a canonical unicast IPv4 host/prefix, /1../30."
            )
            continue
        if address.network.prefixlen == 0:
            finding(
                "INVALID_GATEWAY", location, "Default-route-sized bridge domains are unsupported."
            )
        for other, network in networks.items():
            if (
                other != bd["name"]
                and bds[other]["vrf"] == bd["vrf"]
                and address.network.overlaps(network)
            ):
                finding(
                    "SUBNET_OVERLAP", location, f"Subnet overlaps bridge domain {other} in the VRF."
                )

    epgs = {}
    used_bds = set()
    for app in apps.values():
        for epg in index(app["epgs"], f"applications/{app['name']}/epgs").values():
            key = f"{app['name']}/{epg['name']}"
            epgs[key] = epg
            used_bds.add(epg["bridge_domain"])
            if epg["bridge_domain"] not in bds:
                finding("UNKNOWN_BD", f"epgs/{key}", "Referenced bridge domain does not exist.")

    ids = set()
    intervals = {}
    connected = set()
    for flow in data["flows"]:
        location = f"flows/{flow['id']}"
        if flow["id"] in ids:
            finding("DUPLICATE_FLOW_ID", location, "Flow IDs must be unique.")
        ids.add(flow["id"])
        consumer, provider = flow["consumer"], flow["provider"]
        connected.update((consumer, provider))
        if consumer == provider:
            finding("SAME_EPG", location, "Intra-EPG policy is not modeled by inter-EPG contracts.")
        if consumer not in epgs or provider not in epgs:
            finding("UNKNOWN_EPG", location, "Consumer or provider does not exist.")
        else:
            cb, pb = epgs[consumer]["bridge_domain"], epgs[provider]["bridge_domain"]
            if cb in bds and pb in bds and bds[cb]["vrf"] != bds[pb]["vrf"]:
                finding("CROSS_VRF", location, "Cross-VRF flows require a different design.")
        key = (consumer, provider, flow["protocol"])
        previous = intervals.setdefault(key, [])
        for ports in flow["destination_ports"]:
            start, end = ports["from"], ports["to"]
            if start > end:
                finding("REVERSED_PORT_RANGE", location, "Port range start exceeds its end.")
                continue
            if end - start + 1 > 1024:
                finding("BROAD_PORT_RANGE", location, "Each port range is limited to 1,024 ports.")
            if any(start <= old_end and end >= old_start for old_start, old_end in previous):
                finding("OVERLAPPING_FLOW", location, "Same endpoint/protocol port ranges overlap.")
            previous.append((start, end))

    for key in sorted(set(epgs) - connected):
        finding("NO_CONTRACT", f"epgs/{key}", "EPG has no modeled inter-EPG contract.", "warning")
    for key in sorted(set(bds) - used_bds):
        finding(
            "UNUSED_BD", f"bridge_domains/{key}", "Bridge domain has no modeled EPG.", "warning"
        )
    findings.sort(key=lambda item: (item["severity"], item["location"], item["code"]))
    return {
        "schema_version": 1,
        "valid": not any(item["severity"] == "error" for item in findings),
        "validation_scope": "offline-model-only",
        "findings": findings,
    }

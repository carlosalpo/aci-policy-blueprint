# Input specification — schema version 1

Input is a complete UTF-8 JSON document, at most 1,000,000 bytes. All fields below are required. Unknown fields, duplicate JSON keys, non-finite numbers and type coercion are rejected. A UTF-8 BOM is not accepted. Nothing is loaded from environment variables or remote locations.

Names begin with an ASCII letter, followed by up to 47 ASCII letters, digits, `_` or `-`. This deliberately conservative subset keeps names safe in ACI references and review artifacts. Names are case sensitive. Built-in tenants `common`, `infra` and `mgmt` are rejected case-insensitively. These are tool constraints, not a complete statement of APIC naming limits.

| Field | Type | Meaning |
| --- | --- | --- |
| `schema_version` | integer `1` | Input contract version; boolean `true` is not accepted |
| `tenant` | name | One user tenant |
| `vrfs` | array, 1–64 objects | Each object has only `name` |
| `bridge_domains` | array, 1–64 objects | Each has `name`, `vrf`, `gateway` |
| `applications` | array, 1–64 objects | Each has `name`, `epgs` |
| `flows` | array, 0–256 objects | Each flow specifies exactly one consumer and one provider |

## Bridge domains

`vrf` references a declared VRF. `gateway` is a canonical IPv4 host/prefix such as `192.0.2.1/26`, not a network address. Prefixes /1 through /30 are supported. Network/broadcast, multicast, unspecified, loopback, link-local and reserved gateway addresses are rejected. No DHCP, secondary subnet or IPv6 model is provided. Subnets on different BDs must not overlap within the same VRF; the same subnet in separate VRFs is allowed.

## Applications and EPGs

Each application's `epgs` is a 1–64 element array; total EPGs across the design are limited to 256. An EPG has only `name` and `bridge_domain`, which references a declared BD. EPG names must be unique within their application; the same name in different applications is allowed. A flow endpoint is always qualified as `application/epg`.

## Flows

```json
{
  "id": "web_to_app",
  "consumer": "Store/Web",
  "provider": "Store/App",
  "protocol": "tcp",
  "destination_ports": [{"from": 8443, "to": 8443}]
}
```

IDs are unique across the tenant. `protocol` is exactly `tcp` or `udp`. `destination_ports` contains 1–16 inclusive ranges, each with integer `from` and `to` between 1 and 65535. A range contains at most 1,024 ports; disjoint ranges are allowed. These limits make application intent explicit; they are not a least-privilege certification. The tool does not assess whether an individual requested service is appropriate.

Ranges may not overlap for the same ordered consumer/provider/protocol tuple, even in different flows. The opposite ordered tuple is a distinct requirement. Both endpoints must exist, be different EPGs and use BDs in the same VRF. Cross-application flows within that VRF are supported.

Each flow produces `ct_<id>` and `flt_<id>`. The filter has one entry per sorted destination range; source ports are unspecified. The contract subject attaches that filter in both directions with reversed ports. The CSV includes the explicit consumer-to-provider rows and corresponding provider-to-consumer rows.

## Stable findings

Errors: `DUPLICATE_NAME`, `UNKNOWN_VRF`, `INVALID_GATEWAY`, `SUBNET_OVERLAP`, `UNKNOWN_BD`, `DUPLICATE_FLOW_ID`, `SAME_EPG`, `UNKNOWN_EPG`, `CROSS_VRF`, `REVERSED_PORT_RANGE`, `BROAD_PORT_RANGE`, `OVERLAPPING_FLOW`.

Warnings: `NO_CONTRACT`, `UNUSED_BD`. Warnings do not change exit 0. A warning describes absence from this model, not a statement about live isolation or operational use.

Syntactically/schema-invalid input exits 2 and prints a bounded explanation. It does not emit semantic findings or a build directory. Semantically invalid input exits 1, and `build` emits reports without a policy payload.

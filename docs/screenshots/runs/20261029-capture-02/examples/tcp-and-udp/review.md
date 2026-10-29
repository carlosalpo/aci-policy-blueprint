# ACI Policy Blueprint — design review

Result: **VALID MODEL**

Tenant: `BlueprintDemo` · Compiler: `0.1.0`

Validation scope: **offline model only; no APIC or fabric test**.

## Findings

No modeled errors or warnings.

## Generated objects

| Class | Count |
| --- | ---: |
| fvAEPg | 3 |
| fvAp | 1 |
| fvBD | 3 |
| fvCtx | 1 |
| fvRsBd | 3 |
| fvRsCons | 3 |
| fvRsCtx | 3 |
| fvRsProv | 3 |
| fvSubnet | 3 |
| fvTenant | 1 |
| vzBrCP | 3 |
| vzEntry | 3 |
| vzFilter | 3 |
| vzRsSubjFiltAtt | 3 |
| vzSubj | 3 |

## Modeled filter matrix

Source/destination here are EPGs, not IP addresses. Every reverse-port rule is shown.

| Flow | Direction | Source | Destination | Protocol | Source ports | Destination ports |
| --- | --- | --- | --- | --- | --- | --- |
| app_dns | consumer-to-provider | Store/App | Store/Database | udp | any | 53 |
| app_dns | provider-to-consumer | Store/Database | Store/App | udp | 53 | any |
| app_to_database | consumer-to-provider | Store/App | Store/Database | tcp | any | 5432 |
| app_to_database | provider-to-consumer | Store/Database | Store/App | tcp | 5432 | any |
| web_to_app | consumer-to-provider | Store/Web | Store/App | tcp | any | 8443 |
| web_to_app | provider-to-consumer | Store/App | Store/Web | tcp | 8443 | any |

## Engineering decisions

- One contract and filter per flow, with exactly one consumer and one provider.
- VRF policy enforcement enabled; contract scope is context (VRF).
- Subjects apply in both directions and reverse source/destination filter ports.
- Filters are stateless. Reverse-port rules can match independently initiated traffic.
- EPGs are excluded from the preferred group. Intra-EPG isolation is disabled.
- IPv4 BD gateway subnets are private; no route leaking or L3Out is generated.

## Before any deployment

Review against the target APIC model and release in an isolated lab. This tool does not deploy, reconcile existing objects, delete stale objects or provide rollback.

Domains, VLAN pools, AEPs, interfaces, static/VMM bindings, physical connectivity, endpoint learning, routing and operational state are outside this blueprint. Existing contracts, vzAny, preferred groups, route leaking and other policies can change effective access. Missing matrix rows are not proof of denied traffic.

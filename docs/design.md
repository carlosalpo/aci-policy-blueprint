# Design decisions and model mapping

## Why compile requirements?

A hand-maintained application matrix and a separate policy payload can diverge. This compiler uses one explicit input for both. Validation resolves the graph before any payload is produced, and deterministic ordering makes generated files suitable for review in Git.

A contract shared by several consumers and providers can express more endpoint pairs than an application owner requested. v0.1 allocates one contract per explicit flow. This favors traceability over contract-count optimization; it does not estimate hardware scale or TCAM use.

## Mapping

| Intent | ACI managed object / relationship | Explicit choice |
| --- | --- | --- |
| Tenant | `fvTenant` | User tenant only |
| VRF | `fvCtx` | `pcEnfPref=enforced` |
| Bridge domain | `fvBD`, `fvRsCtx`, `fvSubnet` | Routing enabled, ARP flooding, unknown unicast proxy, private subnet |
| Application | `fvAp` | Contains named EPGs |
| EPG | `fvAEPg`, `fvRsBd` | Preferred-group exclusion; intra-EPG enforcement disabled |
| Flow | `vzBrCP`, `vzSubj` | Context scope, both directions, `revFltPorts=yes` |
| Service ranges | `vzFilter`, `vzEntry`, `vzRsSubjFiltAtt` | IPv4 (`etherT=ip`), TCP/UDP, permit, stateless |
| Consumer / provider | `fvRsCons` / `fvRsProv` | One of each per contract |

Bidirectional filters are attached directly beneath the subject with `vzRsSubjFiltAtt`; one-way `vzInTerm`/`vzOutTerm` objects are not generated. Reverse filter ports swap source and destination constraints. This is not connection tracking. TCP rules remain unspecified and `stateful=no`; the reverse rule may match an independently initiated packet with the modeled source port.

BD choices are a supported design baseline, not universal recommendations. The input cannot override these choices in v0.1; unsupported knobs are rejected rather than silently ignored.

## Reproducibility and publication

Collection ordering is canonicalized by names/IDs and port range. Equivalent reordered input produces identical policy, CSV, review and canonical intent. The manifest records both canonical intent and original input hashes; the original hash will differ if whitespace or order differs. There are no timestamps or machine-specific paths inside compiler outputs.

Output is written to a new directory with mode 0700 and files with mode 0600 on POSIX. The manifest is written last. This is not a transactional, crash-durable directory commit: on file-operation failure a partial directory can remain and must not be consumed. Manifests are integrity inventories, not signatures.

The runtime imports no networking client, reads no credentials and has no deployment command. A payload is a desired tree; it does not reconcile existing objects. Review in the target APIC release's model before any separately managed deployment. APIC compatibility is not certified by local graph tests.

## Primary references consulted

- [Cisco DevNet: Creating a Tenant, VRF, and Bridge Domain](https://developer.cisco.com/docs/apic-rest-api-configuration-guide/creating-a-tenant-vrf-and-bridge-domain/) — object hierarchy and reference names.
- [Cisco ACI Contract Guide](https://www.cisco.com/c/en/us/products/collateral/networking/cloud-networking/application-centric-infrastructure/contract-guide.html) — consumer/provider roles, contract scope and reverse filter semantics.
- [Cisco's Ansible ACI subject implementation](https://github.com/CiscoDevNet/ansible-aci/blob/master/plugins/modules/aci_contract_subject.py) — subject properties and one-way terminal distinction.
- [ACI filter entry module documentation](https://docs.ansible.com/projects/ansible/latest/collections/cisco/aci/aci_filter_entry_module.html) — protocol and port-range vocabulary.

References checked 2026-10-29. They guide this limited compiler; local tests do not substitute for an APIC schema check or a fabric test.

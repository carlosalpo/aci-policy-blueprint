# ACI Policy Blueprint — design review

Result: **INVALID MODEL**

Tenant: `BlueprintDemo` · Compiler: `0.1.0`

Validation scope: **offline model only; no APIC or fabric test**.

## Findings

- **ERROR SUBNET_OVERLAP** · `bridge_domains/WebBD`: Subnet overlaps bridge domain AppBD in the VRF.

No APIC policy, canonical intent or communication matrix was generated.

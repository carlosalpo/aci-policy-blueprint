# ACI Policy Blueprint — design review

Result: **INVALID MODEL**

Tenant: `BlueprintDemo` · Compiler: `0.1.0`

Validation scope: **offline model only; no APIC or fabric test**.

## Findings

- **ERROR CROSS_VRF** · `flows/app_to_database`: Cross-VRF flows require a different design.

No APIC policy, canonical intent or communication matrix was generated.

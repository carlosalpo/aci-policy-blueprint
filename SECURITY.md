# Security and private data

This tool is offline and accepts no APIC host, token, password or private key. The input schema rejects unknown fields and unsafe identifier syntax. It is not a sanitizer: accepted tenant names, EPG names, gateways and application intent appear in generated artifacts. Review outputs before publishing any real design.

The repository's examples use synthetic names and documentation addresses. Do not submit client configurations, credentials or sensitive designs in public issues. For a bug report, provide a minimal synthetic reproducer and the version.

Compilation is not authorization to deploy. This version neither evaluates effective fabric access nor enforces a security baseline across existing ACI configurations. Generated stateless filter rules and unenforced intra-EPG traffic must be understood before use. No live APIC compatibility or security certification is claimed.

Only consume output with a completed manifest, expected `result`, and matching artifact hashes. A manifest is not signed and can be modified alongside the files. Trust the source of a package separately from its internal hash consistency.

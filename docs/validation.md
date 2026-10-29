# Validation record

Scope: local compiler and CLI tests using synthetic requirements. **No APIC connection, deployment, fabric simulation or live packet test has been performed for this project.**

The test suite checks schema and bounds, malformed inputs, reference resolution, duplicate names, subnet semantics, cross-VRF rejection, contract endpoint cardinality, exact service ranges, reverse-port matrix entries, deterministic generation, hash integrity, output permissions and refusal to overwrite existing runs. It also disables socket creation during a build to verify offline execution.

The seven-case executable example matrix verifies exit codes, expected findings, payload presence/absence and every manifest artifact hash. CI repeats the suite and examples on Python 3.11, 3.12 and 3.13. The workflow's downloadable artifacts contain synthetic outputs only.

Interpretation: these tests demonstrate the implemented compiler behavior. They do not establish APIC schema acceptance, hardware support, fabric convergence, endpoint reachability, effective isolation or suitability for production.

Reproduce with the commands in the root README. Captures must identify their source commit and distinguish generated policy review from an APIC screenshot.

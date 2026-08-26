# Contributing to the Open Memory Protocol

Thanks for your interest in the Open Memory Protocol (OMP). This document is the entry point for anyone who wants to shape the specification, contribute to the reference implementation, run the conformance suite against their own memory system, or participate in the working group.

## Ways to contribute

- **Specification feedback.** Read [`spec/draft-v0.1.md`](../spec/draft-v0.1.md) and open an issue with feedback, questions, or proposed changes.
- **Reference implementation.** The Python reference lives in [`reference/`](../reference/). Bug reports, patches, and additional loader / validator implementations are welcome.
- **Conformance tests.** The [`conformance/`](../conformance/) directory holds an executable test suite. If your memory system implements OMP, run the suite and report results.
- **Working group participation.** Attend the monthly working-group call and the two annual technical convenings. Email [ompi@aidisclosures.org](mailto:ompi@aidisclosures.org) to be added.
- **Adopter case studies.** If you have implemented OMP in a production agent harness or memory-layer service, submit a short case study for the quarterly report.

## Proposing a protocol change (RFC)

Substantive changes to the protocol are proposed as RFCs. See [`GOVERNANCE.md`](../GOVERNANCE.md) for the full process. In brief:

1. Open an RFC issue in this repository using the RFC template.
2. Include: problem statement, proposed spec change, implementation sketch or link.
3. Public comment stays open for at least two weeks.
4. Protocol Editors decide (merge, revise, decline), with rationale.
5. Steering Committee reviews editor decisions quarterly.

## Reference-implementation development

- Install: `pip install -e reference/`
- Run tests: `pytest reference/tests/`
- Style: `ruff format` and `ruff check`

The reference implementation follows semantic versioning. Reference-implementation changes require two reviewer approvals and a passing test suite before merge.

## Code of conduct

The Initiative operates under the [Contributor Covenant v2.1](https://www.contributor-covenant.org/version/2/1/code_of_conduct/). Behavior violating the covenant should be reported to [conduct@aidisclosures.org](mailto:conduct@aidisclosures.org).

## Working-group meetings

- **Monthly working-group call.** Second Tuesday of each month, 10:00 ET, one hour. Notes published within one week.
- **September 9, 2026** — kickoff technical convening (online, two hours). Co-hosted by AI Disclosures Project, Mozilla, and IBM.
- **October 2026** — in-person session at the O'Reilly open-source unconference (Berkeley).

## Contact

- Working-group coordination: [ompi@aidisclosures.org](mailto:ompi@aidisclosures.org)
- Security: [security@aidisclosures.org](mailto:security@aidisclosures.org)
- Code of conduct: [conduct@aidisclosures.org](mailto:conduct@aidisclosures.org)

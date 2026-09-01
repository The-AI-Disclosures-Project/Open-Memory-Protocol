# Contributing to the Open Memory Protocol

Thanks for your interest in the Open Memory Protocol (OMPI). This document is the entry point for anyone who wants to shape the specification, contribute to the experimental code, run the conformance suite against their own memory system, or participate in the working group.

## Ways to contribute

- **Specification feedback.** Read [`spec/draft-v0.1.md`](../spec/draft-v0.1.md) and open an issue with feedback, questions, or proposed changes.
- **Experimental code.** The Python sketch lives in [`prototypes/python-loader-validator/`](../prototypes/python-loader-validator/). Bug reports, patches, and additional loader / validator experiments are welcome.
- **Conformance tests.** The [`conformance/`](../conformance/) directory holds an executable test suite. If your memory system implements OMPI, run the suite and report results.
- **Working group participation.** Attend the monthly working-group call and the two annual technical convenings. Email [ompi@aidisclosures.org](mailto:ompi@aidisclosures.org) to be added.
- **Adopter case studies.** If you have implemented OMPI in a production agent harness or memory-layer service, submit a short case study for the quarterly report.

## Proposing a protocol change

Substantive changes to the protocol move through open discussion, iteration, testing, implementation, and market experimentation. See [`GOVERNANCE.md`](../GOVERNANCE.md) for the full process. In brief:

1. Open an issue in this repository describing the problem and a proposed direction.
2. Include: problem statement, proposed change, implementation sketch or link, and (where possible) evidence from usage or adoption.
3. Public discussion stays open for at least two weeks so implementers and adopters can weigh in.
4. Protocol Editors decide (merge, revise, decline), with rationale.
5. Steering Committee reviews editor decisions quarterly.

## Experimental code development

- Install: `pip install -e prototypes/python-loader-validator/`
- Run tests: `pytest prototypes/python-loader-validator/tests/`
- Style: `ruff format` and `ruff check`

The experimental code follows semantic versioning. Changes require two reviewer approvals and a passing test suite before merge.

## Code of conduct

The Initiative operates under the [Contributor Covenant v2.1](https://www.contributor-covenant.org/version/2/1/code_of_conduct/). Behavior violating the covenant should be reported to [ompi@aidisclosures.org](mailto:ompi@aidisclosures.org).

## Working-group meetings

- **Monthly working-group call.** Second Tuesday of each month, 10:00 ET, one hour. Notes published within one week.
- **September 9, 2026** — first informal working-group discussion (online, two hours). Co-hosted by AI Disclosures Project, Mozilla, and IBM.
- **October 2026** — in-person session at the O'Reilly open-source unconference (Berkeley).

## Contact

All Initiative correspondence — working-group coordination, security disclosures, and code-of-conduct reports — goes to [ompi@aidisclosures.org](mailto:ompi@aidisclosures.org).

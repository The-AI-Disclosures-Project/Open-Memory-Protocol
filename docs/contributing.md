# Contributing to the Open Memory Protocol

How to shape the specification, contribute to the experimental code, or join the working group.

## Ways to contribute

- **Specification feedback.** Read the [editors' draft v0.5](../working-group/exchange-and-runtime/2026-11-06-working-spec-v0.5.md) and open an issue or pull request. Contributed proposals live in [`working-group/past-proposals/`](../working-group/past-proposals/); when you revise one, move the previous revision to [`working-group/past-proposals/archive/`](../working-group/past-proposals/archive/) so only the latest is listed.
- **Experimental code.** The Python sketch lives in [`prototypes/python-loader-validator/`](../prototypes/python-loader-validator/). Bug reports, patches, and additional loader / validator experiments are welcome.
- **Working group participation.** Attend the technical working meetings. Email [ompi@aidisclosures.org](mailto:ompi@aidisclosures.org) or apply on [Discord](https://discord.gg/B8Fhcech4) to be added.
- **Implementation reports.** If you prototype against the editors' draft, open an issue describing what mapped cleanly and what did not.

## Proposing a protocol change

Substantive changes to the protocol go through public discussion and implementation evidence. See [`GOVERNANCE.md`](../GOVERNANCE.md) for the full process. In brief:

1. Open an issue in this repository describing the problem and a proposed direction.
2. Include: problem statement, proposed change, implementation sketch or link, and (where possible) evidence from usage or adoption.
3. Maintainers decide by lazy consensus, with the rationale recorded on the issue.
4. Unresolved decisions go to a simple majority of the Technical Steering Group; breaking changes need a migration plan and a two-thirds TSG vote.

## Experimental code development

- Install: `pip install -e prototypes/python-loader-validator/`
- Run tests: `pytest prototypes/python-loader-validator/tests/`
- Style: `ruff format` and `ruff check`

Run the tests before opening a pull request; a maintainer reviews and merges.

## Code of conduct

The Initiative operates under the [Contributor Covenant v2.1](https://www.contributor-covenant.org/version/2/1/code_of_conduct/). Behavior violating the covenant should be reported to [ompi@aidisclosures.org](mailto:ompi@aidisclosures.org).

## Working-group meetings

Technical working meetings are announced on Discord. Decisions are folded into the editors' draft in [`working-group/`](../working-group/) (see its change log). Past convenings are listed in [`history.md`](history.md).

## Contact

Working-group coordination, security disclosures, and code-of-conduct reports: [ompi@aidisclosures.org](mailto:ompi@aidisclosures.org).

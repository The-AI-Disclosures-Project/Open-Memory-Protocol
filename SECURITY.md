# Security policy

This policy covers the experimental code in [`prototypes/`](prototypes/) and the protocol text itself: a flaw in the specification that would let a conforming implementation leak, forge or resurrect memory is a security issue, not only an editorial one.

## Reporting

Report vulnerabilities by email to [ompi@aidisclosures.org](mailto:ompi@aidisclosures.org). Do not open a public issue. Include what is affected, how to reproduce it, and the impact you expect.

You will get an acknowledgement within five working days. If the report concerns a third-party implementation rather than this repository, we will tell you and, where we can, help you reach its maintainers.

## Coordinated disclosure

Reports are handled through a time-limited private response: triage, a fix or a specification change, then a public advisory in this repository once a mitigation is available. Target timelines, as set in [`GOVERNANCE.md`](GOVERNANCE.md): fourteen days for high-severity issues, thirty for medium. If a fix needs longer, we will say so and agree a date with the reporter.

Reporters are credited in the advisory unless they ask not to be.

## Scope notes

- The prototypes are sketches with no release process; a fix lands on `main` and the advisory names the commit.
- Memory objects exchanged under this protocol may carry adversarial content. The threat model being drafted in [PR #17](https://github.com/The-AI-Disclosures-Project/Open-Memory-Protocol/pull/17) is the right place for design-level concerns; a concrete exploit of the current text goes through this policy.

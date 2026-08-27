# Governance

The Open Memory Protocol Initiative (OMPI) develops and maintains the Open Memory Protocol (OMP). This document describes how the Initiative is organized, how decisions are made, and how the governance trajectory is expected to mature over the first two years of active work.

## Hosting and legal structure

During the award period, OMPI is a named initiative housed at the AI Disclosures Project, a project of Code for Science & Society (CS&S), a registered 501(c)(3) public charity. **No new legal entity is created during the grant period.** CS&S / AI Disclosures Project retain fiduciary, employment, contracting, and grant-accountability responsibilities. Technical authority is delegated through public maintainer and steering processes described below.

## Governance trajectory

| Period | Structure | Decision rights and output |
|---|---|---|
| **Months 0–6: bootstrap** | AI Disclosures Project / OMPI project team plus an interim Technical Steering Group (TSG) of 5–7 active implementers and reviewers, with at least three seats held by external organizations. | Publish charter, DCO / contributor rules, security policy, release authority, maintainer ladder, initial roadmap, and RFC process. The AI Disclosures Project schedules work and administers funds; technical decisions follow published public rules. |
| **Months 6–12: distributed maintenance** | TSG of up to seven seats, no more than two from any one organization, selected from active maintainers and implementation representatives under published eligibility rules. | Approve stable protocol features, releases, maintainer additions, and roadmap. Breaking changes require two-thirds approval and a migration plan; ordinary decisions use consensus / majority rules described in the charter. |
| **Months 12–24: sustainability transition** | Broader maintainer council plus adopter and user representation, an external governance review, and an institutional-home assessment. | Reduce dependence on founders. Target maintainers drawn from at least five organizations. Continue within AI Disclosures Project / CS&S unless maintainers and adopters support affiliation or transition to the Agentic AI Foundation or another appropriate neutral steward under an open transition plan. |

## Decision rules

- Technical changes go through public issues and RFCs.
- Component maintainers may merge non-breaking implementation changes after required review.
- Changes to the core object model, exchange semantics, or conformance profile use lazy consensus among maintainers.
- Unresolved decisions may be decided by a simple majority of the Technical Steering Group.
- Breaking changes require a documented migration plan and a two-thirds TSG vote.
- Maintainer promotion is based on sustained contribution and review activity under published criteria.
- Security incidents may use a time-limited private response process, with public advisories after mitigation.
- Decisions, rationale, votes or consensus records, and conflicts of interest are documented.
- **No funder, sponsor, or founding organization receives a technical veto by virtue of financial support.**

## Licensing

Licensing is part of the product architecture.

- Reference code, schemas distributed as code, adapters maintained in the OMPI repository, and conformance tooling are released under **Apache License 2.0** (with its explicit patent grant).
- Human-readable specifications, implementation guidance, governance documents, and general documentation are released under **CC BY 4.0**.
- Contributions to the core repository use a **Developer Certificate of Origin (DCO) sign-off**, not copyright assignment, preserving contributor ownership while creating a clear chain of contribution.
- Dependencies must use compatible open-source licenses and are tracked through automated license and dependency scanning, with SBOMs where practical.
- Independent implementations keep their own copyright and compatible open-source licenses.
- The OMP / OMPI name and any conformance mark are stewarded by AI Disclosures Project / CS&S during the award under a neutral-use policy. Conformance claims depend on published tests, not organizational membership.
- If mature specification work moves to a formal standards body or an Agentic AI Foundation project, the transition agreement preserves open licensing and applies the receiving body's patent / IP policy prospectively.

## Long-term stewardship

Continued AI Disclosures Project / CS&S stewardship is the default beyond the initial award period. Affiliation with or transition to the **Agentic AI Foundation** is a candidate path that will be considered only if it improves neutral long-term maintenance and is supported by active maintainers and adopters. Alternative homes (W3C, an independent 501(c)(6), or another neutral steward) will be evaluated in the same review.

The Initiative also intends to submit the mature written specification to the IETF for formal ratification once implementation evidence supports it.

## Security policy

The Initiative maintains a public security policy in [`SECURITY.md`](SECURITY.md) (in development). Vulnerability reports in the experimental code or in the protocol itself are handled through coordinated disclosure at [ompi@aidisclosures.org](mailto:ompi@aidisclosures.org). Security patches to the experimental code follow the timelines documented in the security policy (typically 14 days for high-severity issues, 30 days for medium-severity).

## Transparency

- All RFCs, issues, pull requests, and meeting records are public.
- The TSG publishes a quarterly public report covering adoption metrics, RFC status, security advisories, and financial position.
- Working-group meeting notes are published within one week of each meeting.

## Amendments

This governance document may be amended by a two-thirds vote of the Technical Steering Group, subject to a two-week public comment period. Amendments are announced in the repository and in the quarterly public report.

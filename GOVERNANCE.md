# Governance

The Open Memory Protocol Initiative (OMPI) is a multi-stakeholder working group that develops and maintains the Open Memory Protocol (OMP). This document describes how the Initiative makes decisions, how changes to the protocol are proposed and adopted, and how the Initiative is organized during and after the initial two-year build-out (2026–2028).

## Hosting and legal structure

OMPI is hosted as an initiative within the AI Disclosures Project, a project of Code for Science & Society (CS&S), a registered 501(c)(3) public charity. CS&S is the applicant institution for grants that fund the Initiative and administers all financial and legal aspects of that funding. The AI Disclosures Project provides administrative, communications, and convening support.

The Initiative does not currently operate as a separate legal entity. During the two-year build-out, the Initiative operates as a named program within the AI Disclosures Project. Once the protocol reaches stable production adoption, long-term stewardship is planned to move to an appropriate standards-body home. The primary planned destination is the Agentic AI Foundation, whose scope covers agent-infrastructure standards; W3C and an independent 501(c)(6) formation are alternative candidates evaluated during the award period.

## Roles

**Steering Committee.** Sets Initiative direction, approves changes to governance, arbitrates disputes, and makes final decisions on scope. Members are drawn from the Initiative host organization and from formal in-kind partners.

- Ilan Strauss (AI Disclosures Project) — chair
- Sruly Rosenblat (AI Disclosures Project)
- Tim O'Reilly (AI Disclosures Project)
- Representative from Mozilla
- Representative from IBM

**Protocol Editors.** Maintain the specification document, integrate accepted RFC decisions into the spec text, and manage the versioning of published spec releases. The current editor is Charles Packer (Letta). The Initiative expects to add one or two co-editors during Year 1.

**Reference-Implementation Maintainers.** Own the Python reference implementation, review pull requests, and cut releases. Recruited and paid through award funding during 2026–2028.

**Working Group.** Any organization or individual actively contributing to specification review, implementation, adoption, or conformance testing. Working-group participants have a voice in the RFC process but no formal decision-making authority.

## Decision-making: the RFC process

Changes to the protocol are proposed through a public request-for-comment (RFC) process. The process is designed to keep the protocol single-track and grounded in implementation evidence.

1. **Proposal.** Anyone may open an RFC in the OMPI repository. An RFC has a defined problem statement, a proposed change to the specification, and (where possible) an implementation sketch or link to a working prototype.
2. **Public review.** RFCs remain open for a minimum public comment period of two weeks. Working-group participants and any interested implementer may comment.
3. **Implementation evidence.** Substantive protocol changes must be backed by implementation evidence: at least one working implementation, or a clear plan for one. Protocol changes are not accepted on the basis of specification argument alone.
4. **Editor decision.** The Protocol Editors evaluate the RFC and either merge it, request revisions, or decline it with a public rationale. Declined RFCs remain in the record.
5. **Steering-committee review.** The Steering Committee reviews decisions quarterly and may reverse an editor decision by a majority vote.

## Versioning and releases

The specification uses semantic versioning. Reference-implementation releases are tagged and cryptographically signed. Backwards-incompatible changes require a major-version bump and are announced at least one release cycle in advance.

## Licensing

- Specification and documentation are released under [CC BY 4.0](LICENSE-SPEC).
- Reference-implementation code and conformance-suite code are released under [Apache 2.0](LICENSE).
- Independent implementations may remain in their maintainers' repositories under any compatible open-source license, provided they can run the published conformance suite.

## Security policy

The Initiative maintains a public security policy in [`SECURITY.md`](SECURITY.md) (in development). Vulnerability reports in the reference implementation or in the protocol itself are handled through coordinated disclosure at [security@ai-disclosures.org](mailto:security@ai-disclosures.org). Security patches to the reference implementation follow the timelines documented in the security policy (typically 14 days for high-severity issues, 30 days for medium-severity).

## Transparency

- All RFCs, issues, pull requests, and meeting records are public.
- The Steering Committee publishes a quarterly public report covering adoption metrics, RFC status, security advisories, and financial position.
- Working-group meeting notes are published within one week of each meeting.

## Long-term stewardship

Once the protocol reaches stable production adoption, the Initiative expects to submit the specification to the IETF for formal ratification and to hand off long-term stewardship to a standards-body home. The choice of long-term home is decided by the Steering Committee based on adoption record, community fit, and licensing compatibility. That decision, when made, is announced publicly with a rationale document.

## Amendments

This governance document may be amended by a majority vote of the Steering Committee, subject to a two-week public comment period. Amendments are announced in the repository and in the quarterly public report.

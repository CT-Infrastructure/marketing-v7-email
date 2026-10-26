# Security boundary

All outputs are synthetic. No sockets, DNS resolution, SMTP client, mailbox login,
subprocess, provider SDK, credential reader or production enable switch exists.
Reject endpoint/URL/shell/path/credential keys. Accepted payload refs cannot fetch
files or URLs. Fixed protocol errors omit input values. No raw payload logging.
Only synthetic opaque refs and inert fixtures are supported; no actual DNS record
values or recommended site configuration are included.

SyntheticVerifier accepts only exact pre-registered original bytes. The trusted
harness owns that registration; callers cannot supply verified=true as proof.
This is explicitly not a vendor signature algorithm. Bind callback account,
tenant, destination, action and established native object, bound timestamps and
persist replay IDs in the synthetic snapshot. Production verifier support is
blocked on human security/provider review. Source contracts and dataclass types
are not authentication: real evidence must be verified upstream.

Serialization and in-memory mutation are a bounded single-caller model, not a
concurrent durable ledger. No E11 dispatch guard, E12 atomic quota controller or
full production restore/replay is implemented. Tests do not qualify actual Mautic,
SMTP, DNS, mailbox or PostgreSQL integrations. No privilege or resource enforcement
claims follow from metadata. Host import validation remains the controller's job.

Original local work is MIT under the repository license. Upstream and Python
licenses remain their own. inventory.json records exact supplied input hashes.
No vulnerability scanner, dependency advisory feed, CI or independent security
review was run. Report vulnerabilities privately through the configured security
owner; no invented reporting address. Preserve HOLD and human production gates.


## Review observation dispositions

F16 explicitly assigns max_age_seconds to caller-reviewed policy. CP146 preserves
that contract rather than invent a legal maximum. The unchanged independent
test_unbounded_privacy_age still fails its expected-denial assertion: this is a
documented policy observation, not an unresolved R1 clock bypass. The trusted
harness must approve the freshness policy as well as time and evidence sources.

Restore now restricts locally generated receipt metadata to synthetic-evidence,
synthetic-approval, synthetic-correlation and synthetic-proof, plus the bounded
synthetic provider-object reference form. This scope-compatible restriction
matches every value the mock itself generates; it does not change accepted F04.
A single receipt edit also disagrees with immutable history. The independent
non-synthetic evidence_ref observation now rejects. These checks cannot certify
provenance, recognize secrets encoded in allowed identifiers, or detect coordinated
fabrication of an otherwise valid backup. Callers must supply synthetic-only data
and authenticate backups; no general-purpose secret scanner/redactor is claimed.

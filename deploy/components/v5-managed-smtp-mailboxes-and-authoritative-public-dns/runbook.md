# CP146 offline contract 1.0.0

This package is an external contract and mock. There is no installation, service,
Quadlet, Containerfile, native worker or provider selection. No container rendering
is applicable. No live installation/restore qualification has been performed.
Use Python 3.14.3 stdlib only; no pip, credentials or provider configuration.
The root controller owns resource enforcement, independent review and integration.

## Offline use

From a clean public checkout, run these literal commands (Python 3.14.3 and Git required for assembly):

```powershell
git clone https://github.com/CT-Infrastructure/marketing-v7-control.git marketing-v7-public
python -B deploy/components/v5-managed-smtp-mailboxes-and-authoritative-public-dns/assemble.py --checkout marketing-v7-public
python -B -m unittest discover -s deploy/components/v5-managed-smtp-mailboxes-and-authoritative-public-dns/tests -v
python -B -O -m unittest discover -s deploy/components/v5-managed-smtp-mailboxes-and-authoritative-public-dns/tests -v
```

Run from the repository containing this component. Assembly reads exact Git blobs at
locked commits, including LICENSE/NOTICE for each revision, checks SHA256, and
publishes a complete content-addressed generation under this component's `.assembled/`.
It never edits accepted sources. Missing commits, corrupt bytes and unsafe paths fail
closed. Repeating assembly validates the existing generation without transport.
The two test commands are offline after assembly; they execute the original 26 tests
plus 8 assembly tests (34 total). No installs are required.

The Git adapter and clean public checkout qualification are NOT_RUN by this worker.
Observed assembly uses injected transport over supplied canonical public byte fixtures;
negative tests use synthetic bytes. The trusted root must qualify actual Git transport.
See `dependencies.lock.json` for every repository, accepted revision, source path,
local destination and digest, and `provenance.md` for notices and owner handoffs.

Do not import or run historical scripts. Copy held-config.json as an in-memory
object; unknown config fields and every live mode are rejected. Construct Mock
with an explicit SyntheticVerifier containing original-byte synthetic fixtures.
No fixture is a production signature, real permission or business approval.
Payload refs are bounded synthetic opaque identifiers and are never dereferenced.

## Ownership and adaptations

Mautic owns contact permissions, suppression and campaigns. F16 evaluate is
called directly for transport.submit with current caller-authenticated evidence.
OpenProject approval is represented by an exact scoped synthetic approval snapshot;
this does not authenticate real business authority. F16 requires provider and
jurisdiction reviews. Mailbox administration and DNS simulation require exact
operation-specific approval plus explicit provider review, independently of
recipient consent. Receipt intake needs verified original bytes, matching account,
action, tenant, destination and object; it does not require current recipient
consent and can retain suppression/revocation/deletion evidence. It grants no
send authority. These are synthetic references to native state, not a CRM.

F05 providers actions are reused and validated without changing the catalog.
Mailbox and DNS extensions are CP146-local fixture operations; shared F05 does not
list them or CP146. F05 errors are used directly. Zero retry budget is deliberate:
pre-submit transient/rate-limit errors remain held; authentication and permanent
errors reject; timeout/ambiguous acceptance reserves UNKNOWN. A 404 cannot prove
absence after possible submission. Duplicate intent returns the prior receipt
regardless of current eligibility, without another simulation or attempt.
Changed payload, account, destination, revision or operation under a key rejects.

F04 1.0 definitions are read directly by conformance.py, a bounded interpreter for
keywords used by these envelope/receipt definitions. Supplied fixtures and negative
mutations are exercised. The upstream jsonschema/referencing executor is NOT_RUN
because installs/third-party dependencies are forbidden. The F04 canonical action
key algorithm and exact identity fields are used. A reconciled OCCURRED receipt
uses F04 CONFIRMED to describe historical synthetic occurrence only; the mock and
component remain HOLD. This is not a production release flag.

## Recovery

Quiesce the bounded caller. Save Mock.dump() as a synthetic backup in approved
output; it contains reservations, dedupe fingerprints, receipts, replay IDs and
denial tombstones, never permission grants or enable flags. For rollback retain
the previous reviewed code and matching versioned synthetic state. Restore only
in isolation with Mock.restore; corrupt/version-mismatched state is rejected.
Serialization is not cryptographically authenticated: the trusted caller must
verify backup integrity/provenance. No untrusted snapshot may grant authority.

Restore retains UNKNOWN and dedupe. Reapply current native revocation, suppression
and deletion evidence using authenticated synthetic intake and fresh F16 lifecycle
snapshots. New submit simulations require restore replay evidence and a matching
F16 ReplayReceipt/generation in addition to current permission/reviews/approval.
There is no automatic resubmission. Definitive synthetic OCCURRED reuses the
action result with a new immutable reconciliation receipt; NOT_OCCURRED stays held awaiting a separately authorized new identity;
UNKNOWN remains reserved. Prior intent keys are never silently recycled.
External effects cannot be undone by rolling back a backup.

## Remaining gates

Provider/security owner must choose exact provider release/edition/account/region,
capabilities and native interfaces, qualify mailbox verification and DNS behavior,
select real UID/GID/network/credentials and database/cache facts, and perform live
installation/restore qualification in a separately authorized test scope. These
are HOLD/UNKNOWN, not missing facts to guess. The controller must supply lease
transport metadata and accepted input hash and obtain independent reviewer,
exact-head CI/Copilot clearance and merge receipts. No G02, acceptance ID, provider
qualification, code acceptance or production approval is claimed here.


## Scoped correction clock and receipt profile

The trusted harness supplies nonnegative integer seconds to simulate/intake.
The common UTC origin is 2026-10-25T11:58:20Z; default now=100 maps to
2026-10-25T12:00:00Z and preserves the original 15 test fixtures unchanged.
CP146 replaces privacy_request.now with that mapped time before calling F16.
Approval/callback ages and receipt times use the same seconds domain. Advancing
the clock with a refreshed approval cannot freeze privacy evidence in the past.
The harness authenticates time; this offline model cannot authenticate a wall clock.

Reconciliation copies the old receipt and appends a new snapshot. IDs are
synthetic- plus SHA256 of action_key + ':' + zero-based history index.
Duplicate intent returns the latest receipt; it does not append or resend.
Restore requires history and exact latest/history agreement, initial disposition
consistency, deterministic IDs, stable bindings and chronological one-attempt
UNKNOWN -> RECONCILED transitions. Legacy snapshots lacking history fail closed.
Reconciliation at the same instant is allowed; an earlier time is rejected before
state or replay IDs change. dump/restore is not a durable or authenticated ledger.

The accepted F04 transition function is exercised verbatim via its AST using the
local schema validator and F16 UTC parser. Full F04 jsonschema execution remains
NOT_RUN (third-party dependency unavailable; no installation authorized).

# Public source provenance

All 26 locked blobs come from https://github.com/CT-Infrastructure/marketing-v7-control.
The lock records canonical byte SHA256 values and destinations relative to the cache generation.

| Package | Accepted revision | Notices in assembled generation |
| --- | --- | --- |
| F04 | c06f435797142b77aa233fce9067e938942a0f5b | notices/F04/LICENSE; notices/F04/NOTICE.md |
| F05 | 30f56e90e1fc103eaf0491838b53ba07f9ab732c | notices/F05/LICENSE; notices/F05/NOTICE.md |
| F16 | e0185b6bc6ef46a22ccf2196ccdbad2a2c9d4b52 | notices/F16/LICENSE; notices/F16/NOTICE.md |

Each revision's matching LICENSE and NOTICE.md are locked and assembled unchanged.
No alternate contract or provider implementation is supplied. Runtime uses exact locked
F05/F16 code and F04 schemas/fixtures. Provider facts and G02 remain HOLD.

Shared CI is a separate owner handoff: add pinned dependency assembly and both test
commands from the runbook while preserving existing gates. This component task does
not edit shared CI. Independent review, actual Git transport qualification, exact-head
CI, actual GitHub Codex review requested with @codex review, and acceptance remain root-owned and unclaimed.
Clearance requires an exact-head full explicit favorable assessment (APPROVED preferred, or an authorized unambiguous COMMENTED assessment with no findings or contradictions). CI and native CODEOWNER, approval, last-push, discussion, base-compatibility and merge-eligibility gates remain unchanged. A reaction, header or "No open" alone is not clearance. Any new commit invalidates review. Historical Copilot receipts and original criteria remain unchanged.

#!/usr/bin/env bash
# CP146 scoped CI amendment; CODEOWNERS review and exact-candidate CI remain required.
set -euo pipefail
[[ "$#" == 1 && "$1" == cp146 ]] || { echo 'usage: validate-public-component.sh cp146' >&2; exit 2; }
component=deploy/components/v5-managed-smtp-mailboxes-and-authoritative-public-dns
# Discard inherited repository, config injection, alternates, transport and trace state.
for name in ${!GIT_@}; do unset "$name"; done
unset SSH_AUTH_SOCK SSH_AGENT_PID
export PYTHONDONTWRITEBYTECODE=1 GIT_TERMINAL_PROMPT=0
export GIT_CONFIG_NOSYSTEM=1 GIT_CONFIG_GLOBAL=/dev/null
export GIT_NO_REPLACE_OBJECTS=1 GIT_NO_LAZY_FETCH=1
export GIT_CONFIG_COUNT=5
export GIT_CONFIG_KEY_0=credential.helper GIT_CONFIG_VALUE_0=
export GIT_CONFIG_KEY_1=core.hooksPath GIT_CONFIG_VALUE_1=/dev/null
export GIT_CONFIG_KEY_2=init.templateDir GIT_CONFIG_VALUE_2=/dev/null
export GIT_CONFIG_KEY_3=protocol.allow GIT_CONFIG_VALUE_3=never
export GIT_CONFIG_KEY_4=protocol.https.allow GIT_CONFIG_VALUE_4=always
python3 -B -c 'import sys; sys.exit(0 if sys.version_info[:3] == (3,14,3) else "required Python 3.14.3 unavailable")'
test -f "$component/assemble.py"
test -f "$component/dependencies.lock.json"
test -d "$component/tests"
test ! -e "$component/.assembled"
test ! -L "$component/.assembled"
# Validate the transport allowlist before any fetch; assembly verifies every blob hash.
python3 -B - "$component/dependencies.lock.json" <<'PY'
import json, sys
pins = {'c06f435797142b77aa233fce9067e938942a0f5b',
        '30f56e90e1fc103eaf0491838b53ba07f9ab732c',
        'e0185b6bc6ef46a22ccf2196ccdbad2a2c9d4b52'}
with open(sys.argv[1], encoding='utf-8') as f:
    entries = json.load(f)
if not entries or {e['revision'] for e in entries} != pins or any(
    e['repository'] != 'CT-Infrastructure/marketing-v7-control' for e in entries
):
    sys.exit('unapproved dependency repository or revision')
PY
# Exclusive disposable scratch directory; the hosted runner owns its disposal.
scratch=$(mktemp -d "${RUNNER_TEMP:-/tmp}/public-component.XXXXXXXX")
control="$scratch/public-control-checkout"
git init --bare "$control"
git -C "$control" remote add origin https://github.com/CT-Infrastructure/marketing-v7-control.git
for pin in c06f435797142b77aa233fce9067e938942a0f5b 30f56e90e1fc103eaf0491838b53ba07f9ab732c e0185b6bc6ef46a22ccf2196ccdbad2a2c9d4b52; do
  git -C "$control" fetch --no-tags --no-recurse-submodules --depth=1 origin "$pin"
  test "$(git -C "$control" rev-parse --verify FETCH_HEAD)" = "$pin"
  test "$(git -C "$control" rev-parse --verify "$pin^{commit}")" = "$pin"
done
# No further transport is permitted by Git. Assembly reads local commit/blob objects.
export GIT_CONFIG_VALUE_4=never
python3 -B "$component/assemble.py" --checkout "$control"
# Run the unchanged component suite in both modes and report observed counts/skips.
failed=0
for mode in normal optimized; do
  options=()
  if [[ "$mode" == optimized ]]; then options=(-O); fi
  if ! python3 -B "${options[@]}" - "$component/tests" "$mode" <<'PY'
import sys, unittest
suite = unittest.defaultTestLoader.discover(sys.argv[1], pattern='test_*.py')
result = unittest.TextTestRunner(verbosity=2).run(suite)
print(f'CP146 {sys.argv[2]}: tests={result.testsRun} skips={len(result.skipped)} '
      f'failures={len(result.failures)} errors={len(result.errors)}', flush=True)
print('Coverage: CP146 stdlib contracts only; full upstream F04 jsonschema runtime NOT_RUN.', flush=True)
sys.exit(0 if result.wasSuccessful() and result.testsRun >= 34 else 1)
PY
  then failed=1; fi
done
exit "$failed"

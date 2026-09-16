#!/usr/bin/env bash
# Load .pgn files through the LIVE app's real parser (loadpuzzles.js -> cm-pgn ->
# chess.js) and report what the trainer gets. This is the only check that proves
# the moves are legal; an illegal move otherwise fails silently at load time.
#
#   .claude/skills/pgn-lines/parse_check.sh beginners/tactics1.pgn
#   .claude/skills/pgn-lines/parse_check.sh -v beginners/tactics1.pgn  # dump moves
#
# The runtime comes from the app we ship to, NOT from the folder this skill sits
# in -- authoring happens in "training pgns/", which has no app sources at all.
# Override with PGN_APP_ROOT when testing against a different checkout.
#
# Node cannot import the repo's modules in place: cm-pgn/package.json has no
# "type" field, so Node treats its .js files as CommonJS and the import fails.
# Staging a copy with two {"type":"module"} shims is enough to fix that.
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# The live app. Its parser differs from the older chessboxing/ one in two ways
# that matter to an author: promotions are supported, and one unparsable game is
# skipped rather than aborting every game after it.
root="${PGN_APP_ROOT:-/home/luis/Sync/projects/chessboxing-smoother}"
if [ ! -f "$root/loadpuzzles.js" ]; then
  echo "parse_check.sh: no app sources at $root" >&2
  echo "Set PGN_APP_ROOT to the app checkout to test against." >&2
  exit 2
fi
root="$(cd "$root" && pwd)"

work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT

cp -r "$root/cm-pgn" "$root/chess.js" "$root/puzzleTrainer.js" \
      "$root/loadpuzzles.js" "$here/check.js" "$work/"
printf '{"type":"module"}\n' > "$work/package.json"
printf '{"type":"module"}\n' > "$work/cm-pgn/package.json"

args=()
for a in "$@"; do
  if [ -f "$a" ]; then args+=("$(realpath "$a")"); else args+=("$a"); fi
done

node "$work/check.js" "${args[@]}"

---
name: pgn-lines
description: Write or change chess training PGN files for the chessboxing game — a new opening chapter, tactics lesson, endgame study, extra sidelines, spoken comments, playlist entries. Use whenever a .pgn under beginners/, intermediate/ or advanced/ is authored or edited, and when a puzzle fails to load, plays the wrong side, locks the board, or ends before the pawn queens or the mate lands.
---

# Writing a trainer line

**`PGNLINES.md` at the root of `training pgns/` is the authoring contract. Read it
before writing anything.** It is not guessable: the app reads a narrow subset of
PGN, and most mistakes fail *silently* — a game vanishes with a `console.warn`, a
comment is never spoken, an arrow is never drawn.

This file is a router. It holds no chess rules, because a second copy of a rule
is a rule that drifts. Everything normative lives in `PGNLINES.md`.

## Where things are

| Path | What it is |
|---|---|
| `training pgns/` | where files are authored — `beginners/`, `intermediate/`, `advanced/` |
| `training pgns/Lucas/` | frozen legacy corpus. Read it for shape; never edit it |
| `training pgns/downloaded/` | raw lichess exports. Source material, rule-breaking on purpose, never shipped |
| `chessboxing-smoother/` | the live app. The ship target, and the parser everything is checked against |
| `chessboxing/` | an older app checkout. Not the ship target |

Shipping: copy into `chessboxing-smoother/pgns/`, usually renamed to that repo's
`<topic>-<level>.pgn` convention, then add a `Display Name:filename.pgn:level`
line to its **root** `playlist.txt`. Never edit `www/playlist.txt` — `build-www.sh`
generates it.

## The order of operations

Each step names the section of `PGNLINES.md` that governs it. Follow the section,
not this list.

1. **Fix the file spec before writing a move** — A3. Domain, rating band, folder,
   game count, and the block plan.
2. **Choose the file's shape** — A4. An opening file is not shaped like a lesson
   file, and getting this wrong is the most expensive mistake available.
3. **For each game, fix its role and domain** — B6, B7, B8. These two choices
   decide the move, the comments, the arrows and the sidelines. Write the role
   down as `[Role "…"]` (C11). Read your one domain profile in B8; skip the
   other three.
4. **For a tactics block, download candidate positions** — B8.2. Do not compose
   them; composed positions fail the motif test. Ask lichess for three times what
   you will ship, at a low rating, then screen every one:

   ```
   node .claude/skills/pgn-lines/fetch_puzzles.mjs --theme fork --max-rating 1100 --count 24
   ```

5. **Build the line with the engine, never from memory** — D17. The `stockfish`
   plugin is loaded in every session: `describe_position`, `analyze_position`
   with `multipv: 5`, `analyze_move`, `play_moves`. Evaluations are always from
   White's point of view.
6. **Write the comments clear first, then for the ear** — C13.3, then C13.4.
   They are spoken once and never re-read.
7. **Cover the alternatives** — C15.2 plus your domain's mandatory set in B8.
   Anything not recorded locks the board.
8. **Continue each sideline to the point** — C15.3. It has a floor as well as a
   ceiling: stopping early is as much a defect as running long.
9. **Run the mainline to the payoff** — B7.6. Decide where the decisions end,
   put `[%tail]` on the last one, and let the tail show the queen, the mate or
   the draw. The last comment describes the board, not the future.
10. **Validate** — D18, and below.
11. **Ship and register** — A2, D19.

## The commands

Run from `training pgns/`:

```
node    .claude/skills/pgn-lines/fetch_puzzles.mjs --theme fork --max-rating 1100 --count 24
python3 .claude/skills/pgn-lines/validate.py beginners/yourfile.pgn
.claude/skills/pgn-lines/parse_check.sh     beginners/yourfile.pgn   # -v dumps moves
python3 .claude/skills/pgn-lines/tb_check.py beginners/yourfile.pgn  # endgames only
python3 .claude/skills/pgn-lines/openings.py beginners/yourfile.pgn  # openings only
```

- **`fetch_puzzles.mjs`** downloads themed lichess puzzles as drafts (B8.2).
  `--list-themes` lists the slugs. What it writes is raw material, not games.
- **`validate.py`** is the structural pass. ERROR means the file must not ship.
  Warnings are silent content loss. Below the warnings it prints a line-endings
  table and a set of file numbers that are **not** errors and that no tool can
  decide for you: coverage, stubs, silent sidelines, repeats, sideline lengths
  all alike, silent moves. Every `PROMISE` row and every repeat is read before
  the file is called done.
- **`parse_check.sh`** runs the **live app's** parser and is the only check that
  proves the moves are legal. `N of M games loaded` with `N < M` names each game
  that was dropped; the app skips it and keeps the rest, so the loss is local.
  Override the app checkout with `PGN_APP_ROOT`.
- **`tb_check.py`** is the endgame truth pass: it asks the lichess tablebase for
  the exact result of every position and move in every line. Needs
  `pip install chess` and network access. Run it on any file reaching 7 men or
  fewer.
- **`openings.py`** is the opening pass and needs no network: it reads a Polyglot
  book from `polyglot/` (default `codekiddy.bin`, the best-covering of the books
  there) and asks whether the replies you scripted for the opponent are moves humans
  play (B9), and whether a popular move at a player decision point goes unrecorded
  (C15.2). Findings are advisory — the book has no rating bands and cannot rank the
  beginner mistakes B8.1 cares about. `--fen "<FEN>"` looks up a single position.

Fix every ERROR. Read the warnings before dismissing them, and read the endings
table and the numbers before deciding the file is done.

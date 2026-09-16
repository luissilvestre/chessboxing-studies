# PGNLINES.md — how to write the trainer's PGN files

This is the authoring contract for the chess training files in this folder. They
look like ordinary PGN, and the oldest of them were exported from lichess
studies, but the app reads only a narrow subset of PGN and several of the rules
that make a file work are invisible — a game's opening comment is found with a
raw regex, adjacent comment blocks are merged with a literal string replace, and
nested variations parse cleanly and are then silently thrown away.

Everything mechanical below was verified by running the **live app's** own parser
(`chessboxing-smoother`: `loadpuzzles.js` → `cm-pgn` → `chess.js`), not inferred
from the PGN standard. Where the app diverges from standard PGN, the app wins.

**What a game is.** One `[Event]` block is one line the player reproduces while
the app plays the other side and the comments coach out loud. What changes from
game to game is *how much help the comments give*: a **teaching** game hands the
move over, a **review** game asks the player to recall it, an **exercise** game
asks them to find it. Rehearsal and puzzle are two ends of one dial, not two
different formats — which is why the rules below are organised by **domain** (what
kind of chess) and **role** (how much help), and why almost nothing here applies
to every game unconditionally.

## How to read this

| Part | What it covers | Read |
|---|---|---|
| **A** | the file: its shape, its games, where it ships | in full, before writing a move |
| **B** | the game: role, arrows, and one domain profile | roles in full; **only your one domain profile** |
| **C** | the format: layout, headers, grammar, comments, shapes, sidelines | in full |
| **D** | checking and shipping | in full |
| **Ap** | evidence — examples, measurements, source lines, phrase bank | when you need it |

Part C is invariant: it is the same for every file that has ever been written
here. Parts A and B are where the judgment lives, and where files go wrong.

---

# Part A — The file

## A1. Where things live

| Folder | What it is |
|---|---|
| `beginners/`, `intermediate/`, `advanced/` | **where you author.** New work goes here |
| `Lucas/` | the frozen legacy corpus, byte-identical to the old app's `pgns/`. Read it for shape; **never edit it**. Every measurement in Ap3 was taken here |
| `downloaded/` | raw lichess study exports. They break these rules on purpose — `[Result "*"]`, NAGs, nested variations, sidelines on the opponent's moves. **Source material for lines and ideas, never shipped** |
| `drafts/` | where `fetch_puzzles.mjs` (B8.2) drops downloaded puzzle candidates. Working material: screen it, harvest what survives into a real file, and do not ship or register anything from here |

`/home/luis/Sync/projects/chessboxing-smoother/` is the **live app** and the ship
target. `/home/luis/Sync/projects/chessboxing/` is an older checkout; it is not.

**The `playlist.txt` in this folder is real and load-bearing, not a mirror
kept for reference.** `chessboxing-smoother`'s `contentUpdater.js` syncs it
straight from this repo's GitHub copy — the same mechanism that syncs the
PGN files themselves and the two presets (`isSyncedPath('playlist.txt')`,
checked against `luissilvestre/chessboxing-studies` on `main`) — which is
how an installed copy of the app learns about a new or corrected study
without waiting for an app-store release. A file shipped through A2 whose
line never reaches this copy is invisible to that sync: correct in the
app repo, correct on the phone that gets a fresh app build, absent from
every phone that only ever pulls content updates. This document said the
opposite of this for months — "a stale authoring artefact... nothing
reads it" — and was wrong; do not trust that sentence if you find it
quoted anywhere older than 2026-09-16.

## A2. Shipping a file

1. Copy it into `chessboxing-smoother/pgns/`, at the **same path** it has
   here — `beginners/basic-tactics.pgn` in this repo is
   `chessboxing-smoother/pgns/beginners/basic-tactics.pgn` in that one, no
   renaming. (Older shipped files used a flat `<topic>-<level>.pgn`
   convention instead; that convention is retired, not a choice to make
   for a new file.)
2. Add a line to that repo's **root** `playlist.txt`:

   ```
   Display Name:filename.pgn:level
   ```

   Split on the **first** colon, so the display name may not contain one; the
   level comes off the **end**, anchored on `.pgn`, so the filename still may.
   Line order is play order. The name is optional — a line that is nothing but a
   filename ending in `.pgn` still loads, and the app derives a name from it
   (`london-system.pgn` becomes "London System"). Blank lines and `#` comments
   are skipped. **Copy the same line into this repo's own `playlist.txt`** (A1) —
   the two must match, or the GitHub sync serves a picker the shipped app
   build does not.
3. **The level is `beginner`, `intermediate` or `advanced`, and it must match the
   folder the file was authored in.** The format treats it as optional; practice
   does not. The opening screen offers a BEGINNER and an INTERMEDIATE preset,
   each built by filtering the playlist on this word, so **a study with no level
   is one no preset can ever hand a player** — it exists only for someone who
   goes the long way round through PICK MY OWN. There is deliberately no
   ADVANCED preset: advanced studies are badged in the picker and reached that
   way on purpose. A level the app does not recognise is reported with its line
   number and the study still loads, because a typo in a classification must not
   cost the player the lesson.
4. Run `node tools/sim/playlist.js` in the app repo. It fails if any shipped
   line lacks a level.
5. Never edit `chessboxing-smoother/www/playlist.txt` or `www/pgns/`.
   `build-www.sh` regenerates both — `cp playlist.txt www/` and
   `rsync -a pgns www/` — so hand edits there are overwritten, and a shipped
   file does not reach the web build until that script is run.

**A file is a *study* the player picks**, not a slot in a queue. The picker
lists the playlist with a BEG/INT/ADV chip per study, lets the player choose and
reorder, and shows solved/total per study; a preset run is simply that level's
studies in playlist order, followed by a block of ten random lichess puzzles. So
a file is a unit someone chooses and finishes — which is what makes A3's game
count and A4's ordering matter, and it is now **playlist order within a level**
that sets the teaching sequence.

Neither path validates the PGN. `validate.py` does check registration, but only
once the file is shipped: it matches on content, so it speaks up when a
byte-identical copy sits in the app's `pgns/` and no playlist line points at it,
when the line carries no level, or when the level contradicts the folder (D18).
**The app itself is no longer silent either** — a playlist line the parser cannot
use names itself in the console with its line number, and a study that ends up
with zero puzzles is drawn `⚠ not loaded` in the picker rather than an
easily-missed `0/0`.

## A3. Fix the file's specification before writing a move

Six things, settled before the engine is opened:

| | |
|---|---|
| **Domain** | opening · tactics · endgame · strategy (B8) |
| **Target rating** | the band the player is in. It sets what counts as a candidate move in C15.2, and what a "natural" mistake is |
| **Folder** | `beginners/`, `intermediate/`, `advanced/` — and, as the matching word, the level its playlist line must carry (A2) |
| **Game count** | how many `[Event]` blocks. A4 says how they divide |
| **Title sentence** | the one line the player hears when the file opens (C13.5) |
| **Block plan** | the table below, filled in |

`[Event]` names follow `"File topic: chapter name"` — `"Vienna: the gambit
accepted"`, `"Tactics school: the fork, lesson"`. It is the only human-readable
label in validator output and in the app's warning when a game is dropped, so
make it name the chapter, not the number.

The **block plan** is written before any moves:

| # | role | start | teaches |
|---|---|---|---|
| 1 | teaching | move 1 | the main line, every move shown |
| 2 | exercise | FEN after 4...Bc5 | he blocks with the bishop — punish it |
| 3 | review | FEN after 3...Nf6 | recall the d3 set-up |
| … | | | |

The role column is not only a plan: it goes into each game's `[Role]` tag
(C11), which is how the validator knows which rules to hold the game to.

If the plan cannot be filled in without repeating a row, the file is too long —
cut it (A5).

## A4. The shape of the file

Every file is a sequence of **blocks**, and a block is **one teaching game
followed by review and/or exercise games on the same material**. That is the
whole structure. A file that introduces one idea is one block; a file covering
five tactical motifs is five blocks.

Every block has its teaching game, **at every level**. An advanced file is not
exempt because its player is: `advanced/imbalanced-endgames.pgn` announces four
new themes ("A new theme: giving material away…") and never teaches one — the
concept is introduced and examined in the same breath, and the player is
praised for guessing it. Across a block the help fades (B7.3): the teaching game
hands the move over, the first exercise names the idea and asks for the move,
the last says nothing but the position.

### A4.1 Opening files — anchor each chapter where the player already is

An opening file teaches a repertoire: one line for our side, and an answer to
everything the opponent does. Its shape is fixed:

```
Game 1        from move 1     the main line, teaching role, moves shown
Game 2        FEN @ branch    "he checks on a5"
Game 3        FEN @ branch    "he kicks the knight"
Game 4        FEN @ branch    "he plays rook e8 first"
...                           one chapter per opponent deviation
Game n-2..n   FEN             exercises from positions the opening reaches
```

**The `FEN` may only contain moves the player has already made.** A chapter starts
at a position the player has *reached* — the standard start, or somewhere on the
mainline of an earlier chapter in this same file. Everything up to and including
the opponent's deviation may sit in the `FEN`; **the player's answer to it belongs
in the movetext.**

Get this wrong in either direction and the chapter fails, in opposite ways:

| Anchored | What the player gets |
|---|---|
| **too early** | moves they have already drilled, replayed again — padding, not rehearsal |
| **too late** | their own pieces on squares they never moved them to, and no way to account for the position |

The second is the easier mistake to make and the harder one to see, because the
file looks fine to its author, who knows how the pieces got there. The player
opens the chapter, finds their knight on e4 and their queen on h4, and has to
take the position on trust.

**The test is mechanical.** A chapter's `FEN` must appear on the mainline of an
earlier chapter, or be the standard start position. Walk the file once, keeping
every position each chapter passes through; every later `FEN` must already be in
that set. Nothing in the toolchain checks this — it is yours to run.

**Anchoring is not only about readability: a move baked into a `FEN` escapes every
other rule in this document.** It is never priced against the engine (B8.1), never
gets a sideline (C15.2), and never has to be a move the repertoire can defend. Move
the anchor back and the move becomes a decision the player makes, so it has to
survive the same scrutiny as every other. That is often where a chapter turns out
to rest on something the engine does not like — and better to find out than to ship
it invisibly.

Anchoring correctly also pays for itself in coverage. `advanced/vienna.pgn` was
written the other way — all 14 games from move 1 — and the arithmetic is brutal:
14 games × 4 White moves in the shared 8-ply prefix means **56 of its 94 decision
points (60%) are the same four moves, re-drilled fourteen times**. Each needed
sidelines, most did not get them, and the file's coverage is **51%** against 100%
for the tactics files. `advanced/london-system.pgn` has the same defect (12 games,
zero `FEN` tags, 62%). Anchoring does not merely stop the repetition — it *deletes*
those 56 decision points, which is what makes full coverage achievable.

`intermediate/stafford-gambit.pgn` is the worked example of both halves: nine
chapters, every one anchored on a position an earlier chapter reaches, and no
chapter replaying a move already drilled. `Lucas/benoni.pgn` gets the first half
right and the second half wrong — 7 of its 16 chapters start after moves the
player never made — so read it for its branch structure, not as a model of this
rule.

**A branch chapter is usually an exercise, not a review.** The opponent has just
deviated, and working out why it is bad is exactly the kind of thing a player can
do from the board. Give it the exercise role (B7.3): ask, do not show.

**Which deviations earn a chapter is decided by B8.1** — the moves a human at the
target rating actually plays, not the moves the engine ranks lowest.

### A4.2 Tactics files — one motif per block

```
Game 1     teaching   names the motif out loud, shows every move, draws the mechanism
Game 2..k  exercise   the same motif, new positions, hints fading to nothing
```

Then the next motif, and the next. A file covering forks, pins and skewers is
three blocks. Do not interleave motifs: the player is learning one word at a
time.

### A4.3 Endgame files — one technique per block

```
Game 1     teaching   the technique walked through from the critical position
Game 2..k  exercise   the same technique, different placements and colours
```

The teaching walk is where the technique gets its name — "the bridge", "the
opposition", "the short side defence". Ap3 has nothing to say about how long a
walk should be; B7.6 does: it runs to the new queen, or to the draw a beginner
can see.

### A4.4 Strategy files — one plan per block

Same shape. The teaching game names the plan — "the minority attack", "hanging
pawns", "the good knight against the bad bishop" — and the exercises ask the
player to find the move that serves it. **One plan per game.** A seven-ply game
carrying thirteen sidelines and five ideas (`intermediate/strategy-pieces.pgn`,
"the right trade, keep the outpost": the trade, holding c5, the b pawn push,
the fixed b2 pawn, knight against bad bishop) is two or three games, and the
player leaves it with none of them.

## A5. No two games may be the same puzzle

Two games are the same puzzle when the player is looking at the same position.
**Mirroring the board, flipping the ranks, or swapping the colours does not make
a new puzzle** — it is the same position shown twice, it teaches nothing, and a
file that does it reads as padding. Shifting the whole idea one file across is
the same offence.

Never ship two games where either of these is true:

- one position is the other reflected (files a↔h), rotated, or with the colours
  swapped;
- the combination runs on the same squares with the same geometry, and only the
  piece names or the spare material differ.

Teaching one motif across several games is the point of a block (A4), and
practising it from both sides is wanted — but each game must be its **own
position**, found or built independently, never the previous one turned around.

The check, before the file ships: write out the solution of every game in one
sentence **with its squares** — "knight to f6 checks and forks the queen on d7",
"rook takes e8 and the recapturing rook leaves the back rank". Repeated *motifs*
in that list are fine. Repeated *squares and geometry* are not: that pair is one
puzzle, and one of the two must be replaced.

If a motif cannot fill its practice slots with positions that are genuinely
different, it ships with fewer games. **The count gives way, not this rule.**

## A6. File sign-off

- [ ] the block plan (A3) is honoured, and no row repeats another
- [ ] no two games are the same puzzle (A5)
- [ ] game 1 opens with the file's title comment (C13.5)
- [ ] every game carries a `Site` or `ChapterURL`, and every `Site` matches its
      own `FEN` (C11)
- [ ] every game carries `[Role]`, and every endgame game `[IntendedResult]`
      (C11)
- [ ] every mainline ends with its payoff on the board, and its last comment
      describes the board rather than promising it (B7.6); no game is one ply
      unless that ply is the payoff
- [ ] an opening file anchors every chapter after the first at a `FEN`, and
      every one of those FENs appears on the mainline of an earlier chapter —
      no chapter starts after a move the player never made (A4.1)
- [ ] in an opening file, every tempting move the opponent declined is answered —
      by its own chapter, or by a sentence in the comment on the move he did
      play (B8.1)
- [ ] `validate.py` and `parse_check.sh` are clean, and the three numbers under
      the warnings have been read and judged (D18)
- [ ] shipped and registered (A2)

---

# Part B — The game

## B6. The two axes

Every game declares two things, and between them they settle every question this
document used to answer with an exception clause.

| | decides |
|---|---|
| **Domain** — opening · tactics · endgame · strategy | how the mainline move is chosen, what verifies it, where the line starts, where its decision points end (the line itself always runs to the payoff, B7.6), which sidelines are mandatory, how far each runs |
| **Role** — teaching · review · exercise | how much the comments give away, and whether the move is drawn on the board |

The two are independent. The combination that used to cause arguments is
**domain = opening, role = exercise**: an opening branch chapter (A4.1) picks its
move by repertoire, like every opening game, but behaves like a tactic in its
comments — because the opponent has just played a mistake and the player can
work out the punishment. There is no contradiction; the axes simply differ.

## B7. Role — how much help the player gets

### B7.1 Teaching

The worked example. The comment tells the player what to play and why **before**
it is asked for, and being told is the point — this game is not a test.

It opens by **naming the thing with its real name**, out loud, before a move is
played: "hanging pawns", "the fork", "the minority attack", "opposition", "the
Vienna". The player must leave with a word for it, not just a feeling. Say the
name straight and have the fun around it, never in place of it (C13.4).

```
{ We will now learn the knight fork. One move, two targets, and he can only save one. [%csl Rc8,Rg8] } 1. Ne7+ ...
```

**Naming is not defining.** The name comes with a one-sentence definition a
child can repeat, and the definition must be true of the example on the board.
"One move, two targets, and he can only save one" is a fork. "Neither can run"
was the shipped version, and the very next comment in that game says "The king
runs" — a definition the position contradicts teaches that words do not mean
much. **One new word per teaching game**; a second word waits for its own game.
`intermediate/pawn-endgames.pgn` introduces opposition, outflanking and the
queening square in three consecutive comments, and across the two book endgame
files "opposition" is spoken seventy-four times without once being defined. The
word is then said again in every game of the block — the exercises too, in the
set-up or the reward — because a word heard once is a noise (twelve of the
twenty games in `intermediate/intermediate-tactics.pgn` never speak their own
motif).

Then keep coaching all the way down. **Say why the move works, not what it
does**: "the knight eats the queen" narrates; "the knight can grab a defended
pawn, because he has to answer the check first" teaches. Every player move's
comment carries a why, and the last comment restates the lesson with its word:
"One knight, two targets: that is a fork." The line then runs to the payoff
(B7.6) — a teaching game about promotion ends with the queen on the board.

### B7.2 Review

The player has seen this material in a teaching game and now reproduces it from
memory. The comments set up and confirm; they do not supply the move. Getting it
back out of memory *is* the training, so handing it over would undo the exercise.

### B7.3 Exercise

Ask, do not show. The comment poses the question — "How do you remove the bishop
from g3?", "He has weakened the long diagonal. How do you use it?" — and the
answer arrives only in the reward comment, after the move.

**The set-up may not contain the answer.** It names neither the piece, the
square nor the plan, and it draws nothing that is the answer. "Remove it", "Can
the spare pawn step make his king move?", "Can giving up your rook stop his
passer?" leave the player nothing to find; so do three red circles on the light
squares under the question "which colour is weak around his king?"
(`intermediate/strategy-pieces.pgn`, "the weak colour, aim the queen"). A circle
on the material, a red mark on his threat: fine. A shape on the square the
answer lands on, in any colour: the exercise is over before it starts.

**The reward says why it worked**, with the squares, and names what was gained.
"Perfect." and "The key square." are cheers, not rewards; "Check! His king had
to step in front of your queen" is the last thing a player hears after giving a
rook for the queen, and it never says the queen was won.

**Hints fade across the block**, in every domain, not only tactics. The first
exercise after the lesson may name the idea in its set-up — "the opposition
again: find it" — and the last says nothing but the position.

Pose it as a dare rather than an exam question (C13.4), and let the reward
comment do the celebrating: the player has just worked something out for
themselves, which is the one moment in the file that has genuinely earned it.
And the line then runs on to the payoff (B7.6): finding the move is the test,
seeing what it wins is the lesson.

### B7.4 Arrows: one rule

| Role | Draw the move the player must play? |
|---|---|
| **Teaching** | **Yes** — a yellow arrow on the preceding ply, and say it in words too. **Except** where the player can plainly work the move out for themselves: a forced recapture, a move with only one good answer that is visible on the board. An arrow there is noise |
| **Review** | **No.** Reproducing from memory is the drill |
| **Exercise** | **No** on the answer — no yellow hint, no green arrow along the winning path, no circle on the landing square. Context that does not give the move away is fine: circles on the material, a red mark on the opponent's threat, a green arrow *after* the move showing why it worked |

The reason teaching games draw and exercises do not is that **an opening move has
no mechanism**. `2. Bf4` is not deducible from anything on the board: it is a
convention, one of twenty reasonable moves, and a player meeting the line for the
first time cannot reason their way to it. Withholding it does not test them, it
ends the puzzle, because an unrecorded move locks the board (C15.1 rule 4). A
tactic is the opposite — there *is* a mechanism, and an arrow pointing at it
steals the exercise.

That is also why the exception exists. A move the player can see for themselves —
the only recapture, the only square the knight has — has a mechanism too, and
drawing it wastes the one shape the eye is going to look at.

**Draw the whole mechanism, not the answer.** In a teaching game, show both
halves: the mover's target *and* the line that opens behind it. One arrow
pointing at the solution teaches less than two arrows showing why it works.

In the tail (B7.6) the puzzle is over and the app is playing: shapes there are
the plan — the road the pawn is walking — and they are drawn **green**, never
yellow. Yellow means a move the player must find, and there is nothing left to
find.

### B7.5 Where a hint can physically live

A comment is read **after** the move it follows (C13.1). So the hint for a
player's move sits on the **opponent's preceding ply**: that comment is spoken
once the move auto-plays, while the player is looking at the position.

The player's **first** move has no preceding ply, so it has exactly one possible
home — the **opening comment**:

```
{ Time to practise the reverse Sicilian. [%cal Gc2c4] } 1. c4 e5 2. Nc3 ...
```

That is also the best-behaved comment in the app. The opening comment is the
**only** one whose speech is awaited with the board locked — `lockBoard()` then
`saycomment(...).then(whoshouldmovefirst)` — so it is the one comment guaranteed
to be heard in full. A mid-line opponent comment is never awaited, and a fast
player can cut it off.

A game whose player moves first, and whose opening comment does not point at move
one, is asking for a move out of thin air.

Say the move in words as well as drawing it — "open with the queen pawn". The
prose is what a player hears when they are not looking at the board, and it is
what survives if the shape is ever dropped. (This is a rule, not a description of
the legacy corpus, which does the opposite — see Ap3.)

**Which moves carry a comment.** Every move in the mainline does, up to the
`[%tail]` move. Past it the app is playing, not the player, and there the rule
inverts: silence, except the reward (B7.6).

- **Every player move.** The comment confirms the move and says why it works.
  The *last* player move carries the reward, and it is the one comment in a
  line that is always heard in full (below). Six of the nine chapters in
  `intermediate/stafford-gambit.pgn` end on a silent player move — one of them
  `8... Bg4#`, a checkmate the player delivers and hears nothing about.
- **Every opponent move.** The comment says what he did and, in a teaching game,
  hints at the answer. This includes the set-up move (C11): it gets its own
  comment, so the opening comment describes the position in the `FEN` — or is
  the file's title (C13.5) — and never narrates a move that has not been
  played. `beginners/checkmate-patterns.pgn` "smothered in the corner" opens
  "His king has crawled into the corner with his own men around him. Mate in
  two" with his king still on b1: the set-up move is what puts it in the
  corner, and the comment is false at the moment it is spoken. All twenty games
  in `intermediate/intermediate-tactics.pgn` have a silent set-up move for this
  reason.
- **The role is a tag, never spoken.** `advanced/benoni.pgn` opens eleven
  chapters with "Review:" or "Exercise:", which the synthesiser reads out as
  "Review colon". Write `[Role "review"]` (C11) and let the comment talk chess.

**How the end of a line is heard.** The app awaits the comment on the player's
move in full before it plays the reply (`applyMove` → `saycomment(...).then`),
so a reward on the player's last move is always heard. A comment on the
opponent's move is never awaited: mid-line it is spoken while the player thinks,
and as the *final* move of a line it is held only while its shapes linger — with
no shape it is cut after about a second. So a line ends on the player's move,
the reward sits there, and a final opponent comment is a defect.

## B7.6 Where the line ends: the payoff on the board

A line ends when the thing the lesson promised is on the board, and the last
comment describes it. Not "the pawn walks home now": the new queen. Not "mate
next move": the mate. Not "b5 is coming": the pawn on b5 and the weak pawn it
left behind. The player reproduces a line to *get* something, and a line that
stops one move short hands them a promissory note and moves on. Every role runs
to the payoff — teaching, review and exercise alike — at every level. This
replaces the old advice to stop as soon as the position "wins itself"; that
test survives, with a smaller job, below.

**The test is the last comment.** Read it. If it is about the future — "will",
"next move", "is coming", "cannot be stopped", "walks home", "is next", "from
here" — the line stopped early. The reward names what is on the board and what
it is worth, with its squares: "A new queen on e8, and his king on b3 never got
near it."

| Domain | The payoff is on the board when |
|---|---|
| **opening, branch chapter** | the material is won and the recapture, if any, has been played — the piece is gone and nothing hangs. "His king is stuck in the open" is a threat, not a payoff |
| **opening, main line** | the position theory aims at is reached, and the comment describes it as a board — where your pieces stand, what his weakness is — not as a forecast or a list of moves to come |
| **tactics** | the material is counted: the fork cashed, the mate delivered, the queen taken and, if she must be, retaken |
| **endgame, a win** | the new queen is on the board, or the mate, or a position a beginner can name as won — his bare king against your queen |
| **endgame, a draw** | stalemate, bare kings, or the hold *shown*: his king tries to pass and fails, the pawn is blocked and his king cannot help — and the word "draw" is spoken |
| **strategy** | the plan's first concrete gain: the pawn on b5 and the weak c pawn it left, the knight on d5 that nothing can remove, the column that is now yours with a rook on it |

Shipped examples of stopping short, all real. `intermediate/pawn-endgames.pgn`
"the opposition" ends on 3. Kf7 with "The queening square is yours. The pawn
simply walks home now", the pawn still on e4. `intermediate/rook-endgames.pgn`
"the Lucena bridge" ends on the bridge move, and f8=Q is never played, so "the
bridge" is a word attached to one rook move. `advanced/strategy-pawns.pgn` "the
minority attack, lesson" promises "push b5 and his c pawn is weak for ever" and
ends on 18. a4 with "b5 is coming anyway". `intermediate/stafford-gambit.pgn`
"everyone falls for this one" ends on Qh2+ with "And it is mate next move on
h1". Across the four endgame files, about fifty-five of sixty-six games end
this way.

**Decision points, then the tail.** The multi-PV test of B8 — three of the top
five moves already winning; four or five preserving moves all demanding a
sideline — still tells you something, but not where to stop. It tells you where
the **decision points** end: the moves the player has to find, or recall, or be
taught. After the last decision point comes the **tail**: the moves that
collect. Put `[%tail]` in the comment of the last decision move (C14) and the
app plays the tail itself — both sides, every comment spoken, every shape drawn
— then awards the stars the player earned. The player never plays a tail move,
so the tail needs no sidelines and cannot lock the board.

The tail has its own rules, and the first is the opposite of what this
document said when the tail was introduced:

- **Silent by default.** The app plays a silent tail ply in 0.7 seconds and a
  commented one in however long the comment takes to say — about a second for
  every fifteen characters, plus 1.4 s if it draws a shape. Eight commented
  plies is close to a minute of locked board, sat through *after* the puzzle
  is solved; the same eight plies silent take six seconds and read as the
  pawn running home. This was measured, not guessed: the first tail-bearing
  corpus had 90 tails with every ply spoken, 22 of them over half a minute
  and the worst at 71 s, and the player who tested them found the pace the
  most annoying thing about the feature. So a tail ply carries **no comment**
  unless it says something the player could not see for themselves.
- **Two comments a tail always has, and at most one more.** The move that
  carries `[%tail]` keeps its comment — it is the player's move, and it is
  where to say "now watch". The last ply carries the reward: what is on the
  board, with its squares, and in a teaching game the lesson's word once
  more. Between the two, one comment at most, and only on the ply that needs
  explaining: the stalemate trick sidestepped, the check that has to be met
  one particular way, the underpromotion, the moment his last try fails. One
  sentence. If nothing in the tail needs explaining, nothing gets one.
- **The opponent's moves are his best** (B9), silent or not.
- **Length is measured in seconds, not plies.** Silent plies are cheap, so a
  tail the tablebase forces to twelve or fourteen plies is fine — about ten
  seconds. What is not fine is a tail that takes longer to watch than the
  puzzle took to solve: aim for well under twenty seconds all told. If a tail
  cannot get there, the lesson is anchored too far from its payoff — start it
  closer, or cut the position down.
- **Shapes only where there is a comment.** A silent ply clears the board of
  shapes, and a shapes-only comment still holds the board for 1.4 s. Put the
  reward's shape on the last ply, green (C14) — the road the pawn walked —
  and never yellow: yellow is a move the player must find, and there is
  nothing left to find.
- **No sidelines on tail moves.** They are unreachable (C15.1 rule 7), and the
  validator says so.

A game whose last decision move already puts the payoff on the board — a mate,
the capture that ends it — needs no tail: the reward sits on that move.

**The old symptom, read again.** When four alternatives on one player move all
end in "also good — a piece up", this document used to say the chapter had run
past its end and the ply should be deleted. The new reading is that you have
crossed into the tail: put `[%tail]` on the last move that was genuinely a
decision, drop the also-good sidelines from the moves after it, and keep the
plies.

**No one-ply games**, unless the single move *is* the payoff — a mate in one.
One move and "the rest wins itself" is a set-up with no lesson attached: ten of
the twenty games in `intermediate/capablanca-plans-intermediate.pgn` are one
ply, ending on lines like "You can follow with g3 and make a passed pawn".

*Check:* the last mover is the player · the last comment describes the board,
in the present tense, with squares · no promise anywhere in it · the tail is
silent except its last ply and at most one explaining comment, and plays in
well under twenty seconds · the validator's line-endings table shows no
PROMISE.

## B8. Domain profiles — read only the one you are writing

The four profiles answer the same six questions. Read yours; skip the rest.

| | **opening** | **tactics** | **endgame** | **strategy** |
|---|---|---|---|---|
| **the move is chosen by** | the repertoire | being the only move that wins | the technique | the plan the comment names |
| **verified with** | multi-PV, to *reject* not to pick | multi-PV: top clearly ahead, second not also winning | the **result** — tablebase at ≤7 men | multi-PV as a floor only |
| **the line starts** | move 1 (teaching) or a `FEN` at the branch point (everything else) | one ply before the point | the critical position | where the plan is available |
| **the decision points end** | when theory stops being the point — or when three of the top five moves already win | when the winning move has been found | at the technique's last unique move | when the plan's move has been found |
| **the payoff on the board (B7.6)** | branch chapter: the material captured, and recaptured if it must be, nothing hanging; main line: the position theory aims at, described as a board | the material collected, or the mate | the new queen, the mate, or the draw shown and said | the plan's first concrete gain |
| **mandatory sidelines** | comparable-or-better, and looks-right-at-a-glance | every serious candidate — they are all refutations | every result-preserving move | every equal-scoring move |
| **a sideline runs** | until the character of the game is clear | **until the tactic is fully resolved** | until the result is decided and visible | until the plan has plainly failed |

### B8.1 Opening

**No unique best move is required, and you must not manufacture one.** Most
opening positions have several playable moves. The mainline is the repertoire's
suggestion — usually the engine's move, but not always, because a move a human
can play and explain beats a move only an engine keeps (D17). Use the engine to
reject moves, not to pick them.

Alternatives are recorded and judged honestly: "perfectly playable, but we are
learning this line". Mandatory at every player decision point:

- **any move the engine scores comparable to or better than the mainline move**
  in the top-five list — within about a third of a pawn, or both winning;
- **the move that looks right at a glance** — the natural recapture, the obvious
  check, the developing move, the pattern from another chapter.

Review games (B7.2) need the **densest** cover of any domain, because the player
is recalling rather than reasoning and their wrong guesses are plausible moves.
A coverage figure below 80% in an opening file means the board will lock.

**The opponent's most natural move is covered before anything else.** The app
plays the opponent from your script, so a player wondering *why did he not just
take?* has no way to ask, and no way to find out. A sideline cannot answer it
either: a variation on an opponent move is parsed and then unreachable (C15.1
rule 1). The answer has exactly two possible homes.

| The opponent's tempting move is | Where the answer goes |
|---|---|
| **a mistake the player must know how to punish** — the greedy capture, the trap, the natural developing move that drops material | **a chapter of its own**, anchored at the position before it, with that move as the single auto-played set-up ply (A4.1, C11) |
| **merely worse, and the player only needs to know why he avoided it** | **one sentence in the comment on the move he did play** — "he would love to take on e5, but your queen to e2 would pin the knight" |

Rank the opponent's alternatives by **how likely a human at the target rating is to
play them**, not by how far the engine dislikes them. The capture, the check, the
recapture and the obvious developing move come first; a move only an engine would
consider comes nowhere. `openings.py` (D18) can rank the *popular* end of
that list for you, but not the end this rule is about: books carry no rating bands
and rarely contain a beginner's mistake at all, so where the book is silent the
ranking is still yours. A trap the *player* can fall into is already covered by
C15.2 — this rule is its mirror, for the trap the *opponent* falls into.

**The screen is mechanical; the decision is not.** As the last pass over a
finished opening file, walk every chapter's mainline and, at each of the
**opponent's** moves, list the captures and checks he declined and price them
against the move you scripted. Anything within about **two pawns** is a candidate.

Then judge the candidates by eye, because the number does not decide it. What
makes a player ask is a move that *looks* good — it wins material, or it solves
the opponent's problem, usually both. A sacrifice he declined needs nothing
however small the gap: nobody wonders why he refused to give a piece away.

`beginners/italian.pgn` was scanned this way, and its numbers show why the eye has
to finish the job. Its four chapters decline nine captures. Six are three pawns or
worse and nobody misses them. Two more sit between two and three pawns and still
need nothing: both are the opponent declining to throw a bishop at the king for a
single check, and no reader has ever asked about those. Exactly one comes in under
two pawns, and it is the one that matters — `4... Nxe4` in the fried-liver chapter
(1.9 pawns), which takes a loose pawn *and* answers the threat, so every player
wants to know why he did not. The comment on the move he plays instead now names
the check that refutes it.

The other row of the table is not a new shape: a mistake that earns its own chapter
is an opponent deviation like any other, anchored and roled exactly as A4.1 says.
What this rule adds is the trigger — you go looking for the deviation, instead of
waiting to notice it.

**Where the decisions end.** Theory stops being the point the moment the player
can no longer go wrong. The test is mechanical: run a top-five multi-PV at each
of the player's moves and read the evaluations White-POV (D17). When **three or
more of the top five are winning for the player** — above about +2.0, or below
about −2.0 in a Black chapter — that position is not a decision point. It is a
position where the player picks any sensible move and stays winning, so there is
nothing left to coach and nothing left to get wrong.

That is where the *decisions* end, not where the chapter ends (B7.6). Put
`[%tail]` on the player's move that reached it and let the tail put the payoff
on the board. In a **branch chapter** that means the material: the capture that
wins the piece, and the recapture if there is one, so that nothing hangs when
the line stops. `beginners/italian.pgn` "the fried liver" ends on 8. Nc3 with
"It hits the pinned knight, and his king is stuck in the open" — a knight down,
queen out, nothing yet won — and a beginner who was taught three chapters
earlier never to hand a bishop over for one pawn cannot see why this sacrifice
is different. Either the tail shows what the sacrifice buys, or the chapter is
cut back to one that can. In a **main-line chapter** nothing is won; the payoff
is the position theory aims at, and the reward describes it as a board — where
your pieces stand, what his weakness is — not as a forecast ("this knight now
travels to f1 and then g3") and not as a list of moves to come ("Now the plans:
c6 and queen c7, rook to e8, knight to f8 and g6"). The tail cap of B7.6, about
four moves each side, is what keeps an opening chapter from turning into a
middlegame demonstration.

The symptom in a finished file is a run of sidelines that all say the same
thing. When four alternatives on one move each end in "also good — a piece up",
you have crossed into the tail: those four recordings hang on a move the player
will never play. Move `[%tail]` back to the last move that was genuinely a
decision — the capture that won the piece, the only answer to the check — and
drop the sidelines after it.

*Ship check:* every chapter after the first starts at a `FEN` · coverage is high
enough that a plausible guess is recorded · no comment claims a move is bad when
the engine calls it playable · no decision point sits in a position where three
of the top five moves are already winning, and the line runs on to the material
(B7.6) · every tempting move the opponent declined is answered, by a chapter or
by a sentence.

### B8.2 Tactics

**Every player move in the line must have a single right answer.** The point of
the puzzle is that the player sees *the* move; if two moves both work, the player
who found the other one is told they were wrong, and the lesson lands as a guess.

Check with a top-five multi-PV at every player move: the top move must be clearly
ahead of the second — more than about a third of a pawn — and the second must not
also be winning (above 2.0 for the player, minding the White-POV sign). Mate in
three next to mate in five is still two solutions; so is a fork next to a quiet
move that also wins a piece. If the position has a second answer, do not paper
over it: **start the puzzle a move later, or choose another position.**

Because there is exactly one answer, every other candidate is a refutation, and
every one of them gets a continuation under C15.3.

**The line runs until the material is counted** (B7.6). A fork that has not yet
taken the piece is a threat; the puzzle ends when the piece is off the board and
the recapture, if there is one, has been played. `intermediate/intermediate-tactics.pgn`
"decoy, order matters" gives a rook to win the queen and ends on "Check! His
king had to step in front of your queen" — the queen is never taken and never
mentioned. The reward counts: "A queen for a rook. The check dragged his king
onto her line." And the motif's word — fork, pin, decoy, interference — is spoken
in every game of the block, not only in the lesson: twelve of the twenty games
in that file never say theirs.

**The position must need the motif.** A game names a motif — in its title, and
out loud in the teaching comment (B7.1). The position then has to make the player
use it: **the winning move must stop being winning if the motif is taken off the
board.** The test is mechanical and costs one engine run. Remove the motif's key
ingredient and ask again: for a discovered attack, delete the piece behind or
block its line; for a pin, move the king off the pin line; for interference,
remove the defender whose line you meant to cut. **If the move is still best and
still wins the same material, the position is not about that motif** — replace
it, do not re-label it.

Discovered attacks fail this test more than anything else. **If the moving piece
captures something big and undefended, there is no discovered attack** — the
player is just taking a hanging piece and the check is decoration. The motif is
real only when the moving piece does something it could not get away with alone:
it captures a **defended** piece, or lands where it can be taken, and survives
because the opponent must answer the piece behind first. The rear piece must also
aim at something worth more than what the mover grabs, or there was no reason to
uncover it. A muddled teaching game poisons every exercise after it.

#### Sourcing the exercise positions

Do not invent practice positions. A composed position tends to be the motif
drawn as a diagram rather than a position that *needs* it, and it fails the motif
test above more often than not.

**Draw them from lichess instead**, which has millions of puzzles tagged by theme
and rated:

```
node .claude/skills/pgn-lines/fetch_puzzles.mjs --theme fork --max-rating 1100 --count 24
```

- **Ask for a low rating.** A low-rated puzzle is one whose idea is *clean* —
  short, forcing, one point — which is exactly what a teaching block needs. Aim
  the window at or a little below the file's target band, not above it.
- **Ask for far more than you will ship.** Three times is a reasonable ratio.
  Most candidates will not survive screening, and a block that ships nine puzzles
  because nine were downloaded is a block that skipped the screening.
- **`--exclude-theme` keeps a block clean.** A fork puzzle also tagged `mateIn1`
  is a mate puzzle; the player will find the mate and never see the fork.
  `--max-themes` does the same job more bluntly: a puzzle carrying eight themes
  is a muddy position whatever its tags say.

The script writes a draft `.pgn` of candidates and a screening table. The drafts
are **not games**: they have a set-up move, a solution, a `FEN`, a `Site` and
nothing else. Every one of them still needs the whole of this document applied.

**Screen every candidate before it becomes a game.** A lichess theme tag is
crowd-derived and generous, and the script cannot judge chess:

1. **Run the motif test** (above) on each one. This is the check the tags do not
   do, and it is the one that matters. A puzzle tagged `fork` where the winning
   move simply takes a hanging piece is not a fork puzzle.
2. **Confirm the single answer** with a top-five multi-PV at every player move.
   Lichess accepts only its own solution, but it does not promise the position
   has just one good move.
3. **Check the set-up move.** Lichess hands you the game up to and including the
   opponent's last move, so the draft opens with it as the one auto-played ply
   (C11). That move is the blunder the puzzle is built on, and it is exempt from
   B9 — but read it anyway: if it is not a move a human would play, the position
   will look invented.
4. **Check against A5.** Two lichess puzzles on the same motif are quite often
   the same geometry. The script flags a position already used in this folder;
   it cannot flag two candidates that mirror each other.
5. **Then write the game**: title, comments, arrows per the role (B7.4), and the
   sidelines of C15.2 with continuations that run until the tactic resolves
   (C15.3). None of that comes from lichess.

*Ship check:* one answer at every player move, confirmed by multi-PV · the motif
test passes · no arrow points at the solution (B7.4) · every sideline is
continued until the tactic is resolved (C15.3) · the line runs until the
material is counted (B7.6) · the motif's word is spoken in every game · every
game has a `Site` (C11).

### B8.3 Endgame

**The eval bar is the wrong instrument.** A rook ending is a win, a draw or a
loss; the centipawn number attached to it is commentary (+4.3 and +6.8 are the
same fact), and in drawn positions half the legal moves hold while everything
hovers near zero. So an endgame chapter is checked against the **result**:

- **With 7 or fewer men, use a tablebase** — the answer is exact, for the
  position and for every legal move in it. `tb_check.py` (D18) asks the lichess
  tablebase for every position in a file. With more men, use a deep multi-PV
  (depth 24+) and read the result it implies, not the decimals.
- **Every mainline move preserves the result for the side that plays it** — the
  player's moves and the opponent's replies alike.
- **A mistake sideline must actually change the result** (win to draw, draw to
  loss); an "also good" sideline must actually preserve it. The words follow the
  tablebase, not your memory of the lesson: "he checks you forever" on a position
  that is still winning, or "you are lost" on a drawn one, is a false verdict.
  Say "also winning, but slower" when that is the truth.
- **Once a sideline's first move has set the new result, every further scripted
  ply keeps it.** Both sides of a continuation are authored text, and each ply is
  checked like a mainline move.
- **The final position of a demonstration must agree with its verdict** — run the
  engine on the last position too, not only on the moves that got there.

**Where the decisions end is decided by the technique, not by the eval.** In a
won rook ending nearly every sensible move keeps the win, so the multi-PV test
of B8.1 would say the decisions are over before the technique starts. The
decision points are the technique's unique moves — the freeing check, the
king's walk down the ladder, the bridge. After the last of them put `[%tail]`
and let the tail show the rest (B7.6): the pawn walking home, the new queen, the
draw held. "The pawn walks home now" was this document's model reward, and it
is why eleven of the seventeen games in `intermediate/pawn-endgames.pgn` end
with the pawn where it started, and why the Lucena lesson in
`intermediate/rook-endgames.pgn` never plays f8=Q. A tail that would be a king
marching down a check ladder and eight mop-up rook moves is the wrong starting
position, not a reason to stop early: start closer to the queen.

**A draw is shown, and said.** The payoff of a drawing technique is a position
the player can recognise: stalemate, bare kings, or the hold demonstrated — his
king tries to get round and is met, the pawn is blocked and he cannot help it —
with the word "draw" in the reward. `intermediate/rook-endgames.pgn` teaches
four draws under a `1-0` header and never says the word; "Frozen for ever"
sounds like a win.

**Pawns may promote** (C12). An endgame line runs to the new queen when queening
is the point.

**The mandatory set is result-preservation.** At every mainline player decision
point, classify **all** legal moves with the tablebase or a full-width multi-PV.
Every move that preserves the player's result must be the mainline, a recorded
sideline, or a move you can defend leaving out as plan-less at the target level —
a bare rook shuffle to an empty square, a wait with no idea behind it. Defend each
omission move by move; "I did not think of it" is how a player finds a winning
move and watches the board lock. Checks, captures, result-preserving retreats,
squares belonging to the plan being taught (the fourth rank in a bridge chapter,
the far rank in a frontal-defence chapter) and the twin of any move you did
record (the other corner, the adjacent waiting square) are **never** defensible
omissions.

When more than four or five preserving moves genuinely demand recording, the
position is not a decision point — it plays itself. Hand that ply to the
opponent, start the puzzle elsewhere, sharpen the position — or, if the
decision points are behind you, that ply is the tail: mark the move before it
and let the app play on. The Philidor shuffle is the honest exception: when
"any square along the row draws" *is* the lesson, record the family and let the
comments say they are equal.

*Ship check:* `tb_check.py` reports zero errors · every spoken verdict matches
the tablebase, including at the final position · the line ends with the payoff
on the board — the queen, the mate, or the draw shown and said (B7.6).

### B8.4 Strategy

The move to teach is the one that achieves a strategic goal — a good square for
the knight, a pawn break, a trade that leaves you the better minor piece — and
the engine may price it at a modest edge, a third of a pawn or less, with two or
three other moves scoring the same. **That is a fine exercise, and no unique best
move is required.** The move is right because of the plan the comment names, not
because the number is bigger.

The question here is "does the comment name why this move is the one to learn",
not "is it the only move that works". Never bend a strategic position to
manufacture a single answer.

Those equal-scoring moves are then **mandatory sidelines**: play each one out and
say in words what it fails to achieve. The motif test of B8.2 applies here too,
with the plan in place of the motif.

**The line runs to the plan's first concrete gain** (B7.6). "The plan is
visible" is not a payoff a beginner can see: the minority attack lesson in
`advanced/strategy-pawns.pgn` promises "push b5 and his c pawn is weak for
ever" and ends two moves before b5 is played. The tail shows the pawn on b5 and
the weak pawn it left, the knight arriving on the square nothing can take it
from, the rook on the column that was just opened. If the gain is more than
about six moves away, the position is the wrong one for a lesson. **One plan per
game** (A4.4): a seven-ply game with fifteen sidelines and five ideas is two or
three games.

*Ship check:* every mainline move's comment names the plan it serves · every
equal-scoring alternative is recorded and played out to its shortcoming · the
mainline runs to the plan's first concrete gain (B7.6).

## B9. The opponent's moves — every domain, every role

The app plays the opponent for you. Every move of the side the player is not on —
in the mainline and inside every sideline — is one **you** wrote, and it reaches
the player looking like a human choice. A reply nobody would make is spotted
instantly, and it makes the whole line look invented.

So **every opponent reply is taken from the engine, never composed by hand**: ask
for the position after your move and write the engine's first choice. Another
move is allowed only when it is within about a third of a pawn of the top move
*and* it tells the story better — a check that must be answered, a recapture that
keeps the position legible.

Recaptures are where this shows. `13. Bxc6+ bxc6` when `Nxc6` was available is
exactly what a player catches, and it turns a correct verdict into a line they do
not believe.

**The free-capture test, before any scripted move ships.** List the captures
available to the side about to move. If one of them wins material and the engine
(or the tablebase) says it preserves or improves that side's result, the scripted
move must be that capture — or the comment must say out loud why it is declined.
"The line still wins without it" is no defence: a rook left hanging while both
sides play around it is the fastest way to make a line look invented. The test
covers every scripted ply — opponent moves in the mainline, and **both** sides
inside a sideline continuation. Declining a capture that *loses* is fine and
often the lesson (the poisoned pawn, the trade that loses the pawn race); the
test is about captures the engine calls at least equal.

**The set-up move is not a reply.** The single opponent move that runs before the
player's first decision *is* the mistake the puzzle is built on: it is chosen to
be plausible, not best, and the engine will always prefer something else. This
rule governs every opponent move that comes **after** the player has started
moving.

**One exception, and it has to be spoken: the punishment line.** When the point of
the game is to show what happens if the opponent falls for it — he takes back the
piece his overloaded rook was guarding, he grabs the poisoned pawn — that losing
reply may go in the **mainline**, and the comment on it must say so out loud
**and name the move he should have played**: "he took the queen, and that was
the mistake — the d pawn should have taken the knight." A player watching the
app choose the losing capture has no way to ask why he did not simply take, and
a sideline cannot answer it (C15.1 rule 1); this sentence is the only place the
answer can live, and no shipped file gives it — `intermediate/stafford-gambit.pgn`
"oh no, my queen" rests entirely on 7. Bxd8 without a word about 7. dxe4. Never
in a sideline: a sideline demonstrates a refutation, so the opponent plays it at
his best.

**An opening book can check the reply for you.** `openings.py` (D18) reads a
Polyglot book offline and reports what it plays in a position, and auditing a file
with it flags any scripted opponent reply the book does not contain while humans
overwhelmingly play something else. Treat a flag as a question, not a verdict —
and know what the instrument cannot do:

- **it has no rating bands.** Book weights are the book author's preferences, and
  the natural beginner mistake that earns its own chapter under B8.1 is usually
  absent from the book altogether. The book cannot rank those; you still can.
- **a thin entry means nothing.** A position the book holds with one or two moves
  is a repertoire, not a survey, so a move missing from it is not evidence.
  `openings.py` only speaks up where the book has an opinion.
- **the two exemptions above still hold.** The set-up ply is never checked, and a
  punishment line whose comment names the move as a mistake drops to a note —
  which is the tool reading the same sentence this section demands.

---

# Part C — The format

Mechanics only. Nothing here depends on domain or role, and nothing here has
changed since the corpus began except where noted.

## C10. Physical layout

Whitespace is load-bearing. The layout is (`·` marks a line that must be empty):

```
[Event "..."]
[Result "0-1"]
...more tags...
·
{ optional opening comment }
1. e4 e5 2. Nf3 ...  0-1
```

Three hard rules:

1. **Exactly one blank line between the last tag and the movetext.** Zero blank
   lines is a hard parse error that kills the game. Two or more still parse, but
   the **opening comment is silently lost** (`Pgn.js` splits on `]\n\n`;
   `loadpuzzles.js` matches `]\n\n{`).
2. **The opening comment, if present, must start at the first character of the
   movetext** — the `{` immediately after that one blank line. It is found by
   regex, not by the PGN parser, and no other position works. It may be followed
   by a newline and then the moves, or the moves may continue on the same line;
   both shapes are used and both are fine.
3. **Keep the moves on one physical line.** cm-pgn folds newlines into spaces so
   multi-line movetext does parse, but the header/movetext split scans for
   `]\n\n`, so a shape code at the end of a line followed by a blank line would
   silently cut the game in half.

**Games are split on the literal text `[Event `.** Every game must have an
`[Event]` tag, and that exact string must never appear anywhere else — including
inside a comment, which corrupts the split and breaks the file.

Games are separated by two blank lines. CRLF is fine; it is stripped on load.

## C11. Headers

Only five tags are ever read. Everything else is decoration the app parses and
ignores — keep the lichess ones if you have them, they cost nothing.

| Tag | Effect |
|---|---|
| `Result` | **which side the player plays**, board orientation, who moves first |
| `FEN` | starting position |
| `SetUp` | gate that lets `FEN` reach the move parser |
| `ChapterURL` | URL behind the ⤴ Analysis button |
| `Site` | fallback for Analysis when there is no `ChapterURL` |

Ignored: `Event` (beyond splitting games), `Date`, `Annotator`, `Variant`, `ECO`,
`Opening`, `StudyName`, `ChapterName`, `UTCDate`, `UTCTime`, `White`, `Black`,
`Round`, `Termination`. Note that **`Variant` is ignored** — anything other than
standard chess is parsed as standard chess and blows up.

**Two more tags the app ignores and the tools read.** Every game carries
`[Role "teaching"]`, `[Role "review"]` or `[Role "exercise"]` (B7). It is what
lets `validate.py` hold a teaching game to its arrows and an exercise to its
silence, and it is never spoken (B7.5). An endgame game also carries
`[IntendedResult "win"]` or `[IntendedResult "draw"]` — the true result of the
position for the player — so the last comment can be checked against it (B8.3).
`[Domain]`, `[Block]` and `[ChapterId]`, which some files carry, are decoration.

Tag syntax must be `[Name "value"]`: the name is `\w+`, the value non-empty and
free of double quotes.

**Every game must carry a `Site` (or a `ChapterURL`).** The app puts it behind
the ⤴ Analysis button, which is how a player takes the position away and looks at
it properly — the one thing they can do when a puzzle beats them. With neither
tag the button is dead.

The default, and what every game should have unless it came from a lichess study,
is a **`Site` pointing at lichess analysis for the game's own initial FEN**:

```
[FEN "2q3k1/5ppp/8/p2N4/1n6/8/P4PPP/3Q2K1 w - - 0 1"]
[SetUp "1"]
[Site "https://lichess.org/analysis/2q3k1/5ppp/8/p2N4/1n6/8/P4PPP/3Q2K1_w_-_-_0_1"]
```

The URL is the six-field FEN with **every space replaced by an underscore**, and
nothing else. It must be *this game's* FEN: a copied `Site` from a neighbouring
game opens the wrong board, which is worse than no button at all. `validate.py`
checks both — a missing pair of tags, and a `Site` whose FEN disagrees with the
game's.

For a game that starts at move 1 and has no `FEN`, use the study chapter's
`ChapterURL` if it has one, or `https://lichess.org/analysis` for the start
position.

`ChapterURL` wins when both are present, so keep it for genuine lichess study
chapters and let `Site` carry the analysis link everywhere else.

**`Result` picks the player's side.**

```
[Result "1-0"]   -> the player is WHITE
[Result "0-1"]   -> the player is BLACK
```

It is not a game result, it is the side selector. It also sets the board
orientation and, with the position, decides who moves first. **Any other value
silently makes the player Black** — `*`, `1/2-1/2` and a missing `Result` all
fall through with no warning. Never leave a chapter on `*`. The result token at
the end of the movetext is optional and ignored; write it anyway to match the
corpus.

**`FEN` must be paired with `SetUp "1"`.**

```
[FEN "r1b1kb1r/p1ppqppp/1np5/4P3/2P5/8/PP2QPPP/RNB1KB1R w KQkq - 1 9"]
[SetUp "1"]
```

- The FEN must be a **complete six-field FEN**. `chess.js` rejects a bare
  placement string.
- Without `SetUp "1"` the movetext is parsed from the standard start position, so
  the moves are illegal and the app drops the game.
- The FEN's side-to-move field decides who plays the first move of the movetext.
  If that is not the player's side, the app auto-plays it — so it must be in the
  movetext. Use the `9...` ellipsis form when the movetext starts with Black.
- **Check `Result` and the FEN's side-to-move against each other.** They can
  disagree in a way that still parses: the player then watches the app play the
  move they were supposed to find. Aim for **at most one auto-played opponent
  move** before the player's first decision. One is often better than none — it
  shows why the position arose. That move carries its own comment, saying what
  he just did; the opening comment describes the position in the `FEN` and never
  narrates a move that has not been played yet (B7.5).

## C12. Movetext

Strict SAN — `sloppy` is off. The grammar accepts:

`e4` · `Nf3` · `Nbd2` · `exd5` · `R1e2` · `O-O` · `O-O-O` · `e8=Q` · `+` · `#` ·
move numbers with or without the dot · `9...` ellipses · `$1` / `!` / `?` NAGs ·
`{ comments }` · `( variations )`.

These are **hard parse errors**. The app skips the offending game with a
`console.warn` naming its `[Event]` and loads the rest of the file, so the loss
is local — but a game the app drops is a game the player never sees.

| Don't write | Why |
|---|---|
| `0-0`, `0-0-0` with zeros | the grammar only accepts the letter `O` |
| `}` inside comment prose | comments are `{` + `[^}]*` + `}` |
| `[Event ` inside comment prose | breaks the game splitter |
| `;` end-of-line comments | not in the grammar |
| `--` null moves | not in the grammar |
| a piece letter outside `RNBQKP` | e.g. localised notation |

**Promotions are supported**, in the mainline and inside sideline continuations.
Write them the standard way: `e8=Q`, `bxa8=N`, any piece. (They used to desync the
engine, and this document used to ban them; that ban is dead and endgame lines
run to the new queen, B7.6.)

One thing to know when authoring: **the player never picks the piece.** Dragging
the pawn to the last rank plays the *recorded* promotion — the mainline's piece,
or a matching sideline's — so an underpromotion puzzle is solved by the squares
alone. Say the piece in the move's comment when the choice is the lesson.

Castling and en passant are handled for you: the board relocates the rook itself,
and `boardMove()` removes the pawn taken en passant.

## C13. Comments

### C13.1 Placement

A comment is read **only if it sits after the move it describes** — the app reads
`commentAfter` and nothing else. `1. e4 { about e4 } e5` describes `e4`.

The prose is **spoken aloud** and printed under the board; `[%...]` blocks are
stripped from the spoken text and drawn on the board instead.

Lichess exports prose and shapes as two adjacent blocks:

```
7. Bd3 { Let us castle here. } { [%csl Gg8][%cal Ge8g8] } 7... O-O
```

The app keeps one comment per move, so it splices the separator out before
parsing — but it only recognises `"} { "` and `"}  {"` on the **same line**. If
the two blocks are separated by a newline, the second block and all its arrows
are **silently dropped**. When hand-authoring, use a **single block**, which
works identically:

```
7. Bd3 { Let us castle here. [%csl Gg8][%cal Ge8g8] } 7... O-O
```

Keep the two-block form only when round-tripping a lichess export.

### C13.2 Length — what it costs

Nothing is cut off. The app speaks a comment to its end and waits for it
(`puzzle-bridge.js` `speak()` awaits the utterance; the only race is a watchdog
of `min(30 s, 90 ms × characters + 3 s)` in `voices.js`, which no sane comment
reaches). This document used to say speech was chopped at 120 characters and
set a 90-character target, and that target is where "One given, two taken",
"Backwards." and "{ Lost. }" came from: comments squeezed until the subject and
the reason fell out. That rule is dead.

What length costs is **pacing**: the board is held while the comment is spoken,
about a second for every fifteen characters. So:

- **The target is two full sentences, about 150 characters.** A subject, a
  reason and a square fit in that. `validate.py` counts comments above it.
- **Above about 240 characters is a lecture** — fifteen seconds with the board
  locked. `validate.py` warns.
- A sentence is never shortened at the cost of its subject or its reason
  (C13.3). Cut the adverb, the second image, the third clause — never the
  chess.

End a line on the **player's** move. The comment on the player's move is
awaited in full; a comment on the opponent's final move is held only while its
shapes linger, and with no shape it is cut after about a second (B7.5).

### C13.3 Clarity — before the voice

A comment is spoken once, at a board the player is looking at, and then it is
replaced. They cannot re-read it, cannot ask what "it" meant, and cannot see
which of two queens "she" was. So every comment stands on its own, and a
comment that needs the previous one to make sense has failed. Clarity comes
before the voice: C13.4 is applied to a sentence that already passes these nine
points.

1. **Name the subject.** Which piece, on which square. Never a bare "it", "that
   one", "the idea", "the trick", "the same problem". "The knight on f6 blocks
   the check", not "it blocks". `intermediate/rook-endgames.pgn` "behind the
   passed pawn" has "Watch him park in front of it" — *him* is a rook, *it* is a
   pawn, and neither parks.
2. **A verdict carries its reason, in the same comment.** "Lost." tells a child
   nothing. One-word verdicts are banned — Lost, Drawn, Gone, Level, Playable,
   Fine, Backwards, Perfect — and so is a verdict whose reason lives in another
   comment. "Drawn: his king sits in front of the pawn, and you can never push
   it out." `intermediate/rook-endgames.pgn` closes thirty-four sidelines with
   the single word "Lost."
3. **Complete sentences.** A fragment may lean on the complete sentence beside
   it — "Mate! His own pawns kept him at home." — and never stands alone.
4. **Each comment stands alone.** No "as before", "the same idea", "again",
   "once more too early": say the idea again, with its squares. No comment in a
   file repeats another word for word (C15.4).
5. **One new word per teaching game**, defined the moment it is said, in a
   sentence a child can repeat and that is true of the example on the board:
   "Opposition: the two kings face each other with one square between them,
   and whoever has to move gives way." Then the word is used in every game of
   the block (B7.1). Exercises introduce no words.
6. **Pronouns are fixed.** *You* and *your* are the player. *He* and *his* are
   the opponent. *White* and *Black* only to say which side the player has, at
   the start of a game — never mid-comment for either side. A piece may be *she*
   or *it* only in the sentence right after it is named, and only when it is the
   only piece of its kind in that comment; two queens are two names.
7. **Directions are squares, columns, rows, wings, forwards and backwards.**
   Never left, right, top or bottom: the board is drawn from the player's side,
   and a Black player's left is a White player's right. Rows and columns are the
   ones in the square names, whoever the player is — the seventh row is the row
   of a7, for Black too. One vocabulary: *column* and *row*, not file and rank,
   except inside a pattern's name ("back rank mate", then "the last row");
   *centre*, *defence*. A pattern's name is said, then explained.
8. **Nobody else in the room.** No engine, machine, computer, book, author,
   grandmaster or eponym without a gloss in the same breath. "The engine likes
   it" appeals to an authority the child cannot hear — say the reason the engine
   found. "The Lucena" is fine once the same sentence has said "the bridge: your
   rook on the fourth row shields your king from his checks". And never the
   author's own doubts: "Be honest: the engine likes d5 better, but e4 sets the
   trap" is a note to self, spoken in a child's ear.
9. **Only what is on the board, and only what is true of it.** The comment on a
   move describes the position after that move — not the move he is about to
   play, not the mate that is coming. And every claim is checked against the
   board (D17): "his rook on h1 has nowhere to run" is false when rook to f1 is
   his best move, and a child who plays it out learns to distrust the file.
   Three shipped rewards claim material the board does not show — "The in
   between move won a whole rook" (the rooks were traded), "It was a bluff" (the
   fork was real), "A queen for a bishop" (two bishops still standing, a rook
   just lost on a8).

| Not this | This |
|---|---|
| "Backwards, and the win is gone." | "The king steps back to e5, and his king takes the opposition on e7. The win is gone." |
| "{ Lost. }" | "Lost. His king steps in front of your pawn on c5, and it never queens." |
| "The same idea, the same problem." | "Rook to b2 leaves the e pawn unguarded again, and his king takes it on e4." |
| "One given, two taken, and the g pawn is next." | "You gave one pawn and took two, and your king on f7 stands next to his g pawn." |
| "Give the guard something it cannot refuse." | "His knight on d7 guards the rook on b8. Check on f7 makes the knight take, and the rook on b8 is yours." |
| "His rook on h1 has nowhere to run." (false) | "His rook on h1 has one square, f1, and there your bishop takes it." |

The right-hand column is the shape, with squares to be replaced by the real
ones; none of it is over 150 characters. Clarity is not length. It is the
subject, the square and the reason being present.

### C13.4 Voice — playful on top of clear

Every comment is read out loud by the browser's speech synthesiser to a child
sitting at a board. So write for the ear, and write for someone who turned up
for a game rather than for a lesson. The sentence is already clear (C13.3);
this is what is done to it next.

- **Second person, coach voice.** "you" and "your". "Let us", spelled out —
  contractions read badly aloud.
- **Sound like a cool adult teaching chess to a child.** Playful, warm and a
  little bit fun — never stiff, never lecturing, never talking down. Short words,
  concrete pictures, a bit of mischief. Keep the chess exactly as correct as it
  would be in dry language: **the play is serious, the voice is not.**
- **Let the pieces have a life.** They are characters, and the squares are places
  they want to be: "the knight jumps in and makes a mess", "that bishop is
  staring right at f7", "the king hides in the corner and hopes nobody noticed",
  "grab some space before he wakes up". Say what a piece is *up to* and the
  geometry arrives with it — a player who pictures the bishop glaring down the
  diagonal has learned the diagonal.
- **Put a turn in it.** The best comments set something up and then flip it: "the
  queen looks safe. She is not." · "he defended the knight and forgot the rook
  behind it." · "a free pawn is nice. A free queen is nicer." The surprise is
  already sitting in the position; you are only timing it, and it is the part a
  player still has a week later.
- **Be encouraging.** The player should finish the line feeling good, so cheer
  the good moves on — "nice, that is the one", "well spotted", "you are right on
  track". When a move is hard, say so before blaming the player: "this one is
  tricky, take your time". Point at the mistake, never at the person — "that
  square is a trap" beats "you blundered". Praise stays honest: a bad move is
  still called bad (C15.4), just kindly, and a quiet move does not become
  thrilling because you called it thrilling.
- **Say squares, not SAN.** Write "the bishop to b5", not "Bb5". Write "queen
  side", "e column", "kings Indian".
- **Ask questions that make the player calculate**, and ask them like a dare
  rather than an exam paper — "Do you remember the best move here?", "How do you
  remove the bishop from g3?", "There is a fork hiding in this position. Can you
  find it?"
- **Judge the move in words** (C15.4). NAGs do nothing.

**Same chess, two voices.** Nothing in the right-hand column is longer, vaguer or
softer than its neighbour; it just has a picture in it. All four are shipped
lines, from `beginners/basic-tactics.pgn` and `beginners/checkmate-patterns.pgn`:

| Correct, and flat | Correct, and worth listening to |
|---|---|
| "The knight forks the king and the rook on h8." | "Check, and the rook in the corner is attacked too." |
| "Black has no time to move the queen." | "Check! He must answer the check, so his queen has no time to escape." |
| "Removing the defender wins a rook." | "A whole rook. Remove the defender, then collect." |
| "The king cannot escape the back rank." | "Mate! His own pawns kept him at home." |

**Playfulness is a register, not a licence.** It goes wrong in seven recognisable
ways, and every one of them costs more than writing plainly would have:

| Not this | Why |
|---|---|
| sarcasm — "congratulations genius, you have just blundered" | it is the one thing that makes a child stop playing. Point at the square, never at them |
| baby talk — "the little horsey hops away" | they are doing a grown-up thing on purpose, and being taken seriously is most of the fun |
| a joke standing in for the word — "the sneaky double poke" | the player must leave with **fork** (B7.1). Have the fun around the name, never instead of it |
| excitement on every single move | if every move is amazing, none of them is. Spend it on the move that earned it |
| a joke that needs a second sentence to land | the explanation is spoken while the player is trying to think, and the joke is now the longest thing in the comment |
| compression — "One given, two taken." | the ear cannot unpack a telegram. Say the sentence; the fun is in the picture, not in the missing words (C13.3) |
| an image standing in for the reason — "give the guard something it cannot refuse", "distance is what a rook lives on" | the idiom is a reason-shaped hole. Name the guard, the square and the check, then keep the image if there is room |

**Short is what makes it land — but nothing is chopped any more** (C13.2). The
cost of a long comment is the board held for it, about a second per fifteen
characters, and a joke that runs on is spoken while the player is trying to
think. One picture per comment, not three: cut the adverb, never the chess, and
never the subject or the reason (C13.3).

### C13.5 The file's first comment is its title

The opening comment of the **first game in a file** is the first thing the player
hears when the file comes up, so make it announce what is coming — a spoken title
for the whole file, not a note about that one puzzle:

```
{ Welcome to tactics school. Today we hunt forks. }
{ Time to practise the Scotch. Sharp, fast, and fun. }
{ Rook endings. Everybody reaches them, almost nobody knows them. }
{ Today we think like a general. Plans, not tricks. }
```

One or two short sentences, in the voice of C13.4. It is the most-listened-to
line in the file and the one that decides whether the player leans in or waits
it out, so make it the best sentence you write that day. In a file whose first game is a
teaching game — which is most of them (A4) — the concept sentence of B7.1 *is*
the title: write it once and let it do both jobs. If the first puzzle also needs
its own set-up, put it in the same block right after the title, and keep both
sentences short.

The title never lists moves: `advanced/benoni.pgn` opens with "One setup
answers it: d5, knight c3, e4, h3, knight f3, bishop d3. Queen pawn first" —
six items before a piece has moved. And no file opens straight into its first
motif: `beginners/basic-tactics.pgn` begins "We will now learn the fork" with
nothing to say what the file is.

Opening comments in the rest of the file's games stay what they are: a set-up for
that puzzle, and the only home for a hint on the player's first move (B7.5).

## C14. Arrows and circles

```
[%cal Ge8g8]                   arrow  e8 -> g8, green
[%csl Gg8]                     circle g8, green
[%csl Gf2,Rg3]                 two circles, comma-separated
[%csl Ye4][%cal Gf6e4,Gb4e1]   any number of blocks in one comment
```

- **The app picks arrow vs. circle from the code's length, not the tag name.** A
  3-character code is a circle, a 5-character code is an arrow, any other length
  is silently dropped. Use the right tag anyway — `csl` for circles, `cal` for
  arrows — so the file still makes sense in lichess.
- Colours are the first character: **`G` green, `R` red, `Y` yellow, `B` blue.**
  Anything else silently becomes green.
- Only `[%csl]`, `[%cal]` and `[%tail]` do anything. `[%clk]`, `[%eval]` and
  friends are stripped and discarded — and `[%eval]` in a shipped file means a
  lichess export was pasted in unedited (`advanced/benoni-white.pgn`).
- A `]` inside a `[%...]` block truncates it — don't.
- Shapes stay on screen until the next comment replaces them. A comment with
  shapes and no prose is legitimate on a sideline ply: it draws and says
  nothing. On a mainline move it counts as no comment (B7.5).
- An arrow from a square to itself draws nothing. `advanced/benoni-white.pgn`
  ships nineteen of them (`[%cal Gc3c3]`).
- **`[%tail]`** is the one block that is not a shape. In the comment of a
  player's mainline move it tells the app to play the rest of the line itself
  (B7.6). It is stripped from the spoken text like every other block, ignored on
  an opponent's move and inside a sideline, and `validate.py` checks where it
  sits.

The colour vocabulary:

| Colour | Used for |
|---|---|
| **G** green | the plan, the right idea, the threat you are creating — and, in the tail, the road the pawn is walking (B7.6) |
| **R** red | the danger, the move to avoid, the weakness |
| **B** blue | an idea for later, a playable alternative you are not choosing |
| **Y** yellow | a pointed hint at the move the player should find |

**Whether to draw at all is decided by role, in B7.4** — not here.

## C15. Sidelines

This is the heart of the format. A variation in parentheses records a move the
player might plausibly try instead of the mainline move. When they play it, the
app says what it is, **plays the rest of that line out on the board** with its own
comments and arrows, then rewinds to the puzzle position so they can find the
main move.

```
11. exf6 Qxf6 { [%cal Gf6f4,Gf6c3,Gb4c3] }
   (11... Nxf6 { This is ok. But taking with the queen is more aggressive. })
   (11... Rxf6 { This is not your best piece to capture. }
        12. Bg3 Bd6 { [%cal Gd6g3] } 13. Qe2 { [%cal Ge2e8] }
        13... Qf8 { The game is even. })
```

*(wrapped here for readability — in the file this is all one line, per C10.)*

### C15.1 The seven mechanical rules

1. **Attach sidelines to the player's moves only.** A variation on an opponent
   move is parsed and then unreachable — the app always plays the mainline for
   the opponent.
2. **A sideline must be a single unbranched line.** The app flattens each
   variation to a list and does not recurse, so a nested `( )` inside a variation
   parses cleanly and is then **silently discarded**. Sibling variations on the
   *same* move are fine and encouraged — up to seven are used in the corpus.
3. **Matching is by the from/to squares of the sideline's first move only.** Two
   siblings starting with the same from/to pair are indistinguishable; the first
   wins. Record one.
4. **Any move that is neither the mainline move nor a recorded sideline is a hard
   fail**: the board locks and the player must press Restart. A sideline is how
   you turn a wrong turn into a lesson instead of a dead end.
5. **Promotions inside a continuation work** (C12). The demo pushes moves
   straight to the board with no engine behind them, and `boardMove()` swaps the
   pawn for the recorded piece itself.
6. **A sideline whose first move carries no comment is narrated by the app
   instead of by you.** It falls back to *"That starts a sideline. Here is how it
   continues."* — about three seconds saying nothing the player cannot already
   see, in a flat register nobody else in the file uses — and it draws a **yellow
   arrow at the move the player just got wrong. Every sideline's first move must
   carry a comment (C15.4).**
7. **Sidelines on tail moves are unreachable** (B7.6). The app plays the tail,
   so the player never gets to deviate there: a variation on a tail move is
   parsed and never entered. `validate.py` lists them.

### C15.2 Which alternatives to record

Record the moves **a reasonable player at the target rating would logically play
in this position**. Not every legal move — but not just the first one that occurs
to you either. Any decision point with no sideline is a place where a sensible
move ends the puzzle instead of teaching something.

Go through the position and list the candidates such a player would consider:

- **the engine's other top moves** — its second and third choices are usually the
  ones a strong human finds too;
- **the natural human move** — the obvious recapture, the developing move, the
  move that completes the plan you have been coaching for three moves;
- **the tempting move** — a check, a capture, a pin, a free pawn;
- **the move from another chapter** — the pattern the player has just learned
  elsewhere and will try to apply here;
- **the transposition** — a move reaching a line the player already knows;
- **the mistake the position exists to punish.** If the lesson is that a natural
  move fails, that move has to be in the file.

Then filter: **keep the candidates you have to think about to reject.** If it
takes you a second to see why a move is bad, it belongs in the file. If it is bad
at a glance — a rook shuffling on the back rank, a piece hung for nothing, a move
only an engine would look at — leave it out.

**Your domain's mandatory set (B8) is a floor under this filter, not a
replacement for it.** Three or four siblings on one move is normal; the corpus
maximum is seven.

### C15.3 How far to continue — a floor and a ceiling

A sideline is not a verdict, it is a demonstration. It has **both** a minimum and
a maximum length, and today's files err on the short side.

**The floor: run the line until the point is settled.** Stop when the consequence
is on the board *and countable* — not when a ply budget is spent. In a tactic
that means the material balance has settled and nothing is still in the air: **if
the opponent still has a recapture, a check, a counter-fork or an in-between move
available, the line has not shown its point yet.** "The player can work out the
rest" is not a reason to stop; the player is watching a locked board precisely
because they did *not* work it out.

A good tactical continuation is usually **four to six plies**: the wrong move,
the punishing reply, and the move that collects. Two plies — the wrong move and
one reply — is enough only for "you hang a knight, he takes it". It cannot show a
counter-fork, a zwischenzug, a mate net, or the difference behind "also wins, but
slower", where the slower part *is* the verdict.

Beware of matching the file you are imitating: in `beginners/tactics1.pgn` 111 of
128 sidelines are exactly two plies, and in three other files every single
sideline is the same length. That is a formula, not a judgment. `validate.py`
now reports the share of a file's sidelines that are one length, and every
comment that repeats another verbatim.

**This ceiling governs sidelines only.** Where the mainline ends is B7.6, and
it runs to the payoff; a sideline is a demonstration of a wrong turn, and it
ends as soon as the turn is shown to be wrong.

**The ceiling: stop as soon as any of these is true.**

| Stop when | Because |
|---|---|
| the material or structural consequence is on the board | the player can see it; nothing after it teaches more |
| the position has visibly transposed into a line the player knows | name the line and stop |
| the move is simply also-good and its character is clear | one or two plies showing where it leads is the whole message |

In a sideline, do **not** play on to mate, to the end of the theory, or "for
completeness". The player is only watching: the board is locked for the whole
demonstration and then rewound, so every extra ply is dead time. A commented ply
costs its speech — about a second per fifteen characters — plus 1.4 s when it
draws a shape; a silent ply costs 0.7 s; and the final position is held 0.7 s
more. Ten commented plies is a lecture.

**End on a verdict comment.** The final comment of a continuation is spoken in
full — unlike the final comment of a mainline — so it is the safe place for the
judgement. But a verdict on the last ply does **not** discharge rule 6: the first
move needs a comment too, or the app talks over you before your demonstration
starts.

The verdict must also be **true of the position on the board** when the
demonstration stops: check the final position, not only the moves that got there.
A continuation ending "you are lost" in a drawn position — or a "punishment" that
has quietly handed the game back — teaches the player to distrust the whole file.

Give the last ply a shape as well, in the C14 colours: red on the punishment,
green on the idea the player is giving up.

**The one case that needs no continuation** is a move that loses on the spot,
where the prose and a single red arrow already say everything:

```
(2. Rd3 { Look again: the pawn takes your rook for free. [%cal Re4d3] })
```

This exemption is narrow: the *very next* move is a plain capture of a hanging
piece with nothing to follow. It is not a licence to skip the demonstration for
any move you personally find obvious. Everything else gets a continuation — good
alternatives as well as mistakes.

Inside a continuation the rest of the format still applies, and two rules bite
hard:

- **It is parsed strictly.** Variation moves go through the same `chess.js`
  validation as the mainline, so one impossible move in a continuation kills that
  game. Play the variation out through the engine first (D17).
- **No nested parentheses** (rule 2). A continuation is one straight line; if the
  opponent has two good answers, pick the one that makes the point.

### C15.4 Say whether the sideline is good or bad — in words

**Never leave the first move of a sideline without a comment.** The player has
just had the move taken out of their hands, so they already know they entered a
sideline; the app's stock sentence spends three seconds telling them so, in a
register nobody else in the file uses, while drawing a yellow arrow at the very
move they got wrong. In an exercise that arrow actively points at the error. The
first comment of a sideline is the one line the player is guaranteed to hear
about their move: name what it does, or what is wrong with it, in the voice of
C13.4. It is also the line where that voice matters most, because the player is
listening hardest right after getting something wrong — so the sentence is about
the move, never about them.

**Name what the move does wrong in this position**, with the square.
"Backwards.", "Sideways.", "Too slow.", "The same idea, the same problem." are
categories, not comments, and a bank of verdicts — "Playable" is used 393 times
across the shipped files, "Also fine" 247, "chooses a different task" 75 — is a
template, not a coach. Two sidelines in one game never share a sentence, and no
comment in a file repeats another word for word; the validator counts repeats.

NAGs (`!`, `?`, `!?`, `$1`) parse and are then ignored everywhere. The good/bad
judgement lives entirely in the prose. House phrasings worth copying are in Ap4
— for their shape, never pasted.

A one-move sideline carrying only a comment is the legacy shape of this corpus.
Unless the move loses on the spot (C15.3), show the continuation instead.

### C15.5 Stars — what actually costs the player

| Sidelines **entered** | Stars |
|---|---|
| 0 | ★★★ |
| 1 | ★★ |
| 2–5 | ★ |
| more than 5 | ☆ |

**Recording a sideline is free.** The counter increments only when the player
actually plays one, so a variation nobody enters costs nothing at all — not a
star, not a millisecond. There is no budget tension between the star table and
your domain's mandatory set in B8, and this document used to claim there was.

The real asymmetry is not padding versus omission, it is **free versus
catastrophic**. A move the player never tries costs you authoring time and
nothing else. A move they *do* try and you did not record costs them the whole
puzzle, because the board locks (C15.1 rule 4).

So record generously and precisely. What genuinely opposes dense coverage is not
stars but the tail (B7.6): a position where good moves multiply is a position
past the last decision point, and the app plays it — mark it, and record nothing
there. One small real cost:
entries are counted, not distinct sidelines, so a player who tries the same wrong
move twice pays twice.

## C16. Templates

```
[Event "Opening name: chapter name"]
[Result "0-1"]
[Role "teaching"]
[Variant "Standard"]
[ChapterURL "https://lichess.org/study/xxxxxxxx/yyyyyyyy"]

{ One or two sentences that are the file's title, in the voice of C13.4. }
1. e4 { He opens with the king pawn. Answer in the middle: pawn to e5. [%cal Ye7e5] } 1... e5 { Your pawn takes its share of the centre. } 2. Nf3 { His knight attacks your pawn on e5. Defend it with a knight of your own. [%cal Yb8c6] } 2... Nc6 { The knight guards e5 and comes out at the same time. } 3. Bc4 { The Italian. His bishop stares straight at f7, the one square only your king guards. Send your bishop to c5, to stare back at f2. [%csl Rf7][%cal Rc4f7,Yf8c5] } 3... Bc5 { Bishop for bishop: yours looks at f2 just as his looks at f7. [%csl Gf2] } (3... Nf6 { That is the two knights defence. It is playable, but we are practising the Italian. } 4. Ng5 { He jumps at f7 straight away. That is a different lesson. [%cal Rg5f7] }) 4. O-O { He castles. Bring the last knight out to f6. [%cal Yg8f6] } 4... Nf6 { Both knights out, both bishops out, and your king castles next. That is the Italian, and you are dead level. } 0-1
```

With a starting position other than the initial one — which is every game but the
first in an opening file (A4.1), and every game in a tactics, endgame or strategy
file — add both tags and start the movetext at the right move number:

```
[Event "Opening name: chapter name"]
[Result "1-0"]
[Role "exercise"]
[Variant "Standard"]
[FEN "r1bqkb1r/pppp1ppp/2n2n2/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 4 4"]
[SetUp "1"]
[Site "https://lichess.org/analysis/r1bqkb1r/pppp1ppp/2n2n2/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R_w_KQkq_-_4_4"]

{ He has played the two knights defence: knight to f6 instead of bishop to c5. Your bishop and knight both look at f7. Is there a way in? [%csl Rf6] }
4. Ng5 { The knight jumps at f7: bishop and knight both hit it, and only his king guards it. [%csl Rf7][%cal Gg5f7,Gc4f7] } 4... d5 { He blocks the bishop's line with the d pawn. What do you take with? } 5. exd5 { The pawn takes. Now his knight on f6 is attacked as well. [%cal Gd5c6] } (5. Bxd5 { The greedy recapture. But look at your knight on g5. [%csl Rg5] } 5... Nxd5 6. exd5 Qxg5 { A whole piece gone, and nothing to show for it: his queen took the knight on g5 for free. }) 5... Na5 { The main line. His knight goes straight after your bishop on c4. [%cal Ra5c4] } 6. Bb5+ { Check, and the bishop is safe. He has to block, and the pawn to c6 is his only good way. Watch how it ends. [%cal Gb5e8][%tail] } 6... c6 { The pawn blocks the check. } 7. dxc6 { Your pawn takes it, and now it threatens b7. [%csl Gb7] } 7... bxc6 { He takes back, and his queen side pawns are wrecked. [%csl Rc6,Ra7] } 8. Be2 { The bishop steps home. A pawn up, his pawns on a7 and c6 are weak, and his knight on a5 is out of play. That is what the two knights gives you. [%csl Ga7,Gc6,Ra5] } 1-0
```

---

# Part D — Checking and shipping

## D17. Checking a line with the engine

**Every line must be checked with Stockfish before the file ships.** Not the
mainline only — the mainline *and* every sideline, walked move by move, with each
verdict in the prose matching what the engine actually says. A line that has not
been through the engine does not go in the file. For each line: play the moves out
to confirm the line is legal and reaches the position you meant, ask for a
multi-PV analysis (top five) at each decision point, and have the engine price
the alternatives you judge in words (C15.4).

Ask at every **opponent** reply too, not only at the player's moves (B9). And run
your domain's own test — the motif test for tactics (B8.2), the tablebase pass
for endgames (B8.3).

This applies to **new** work. The files already in `Lucas/` are grandfathered — do
not re-run the engine over them unless you are changing a line.

Nothing in a `.pgn` has to be written from memory. **Use whatever Stockfish you
have** — a tool or plugin in the session, a local binary over UCI, a script
around a chess library, an online analysis board. This document names no tool; it
assumes only that the engine can answer these:

| While authoring | Ask the engine for |
|---|---|
| see the position instead of decoding the FEN by eye | the board drawn from the FEN |
| check that a move is playable at all | the legal moves in the position |
| walk a line forward and get the FEN at the end | the position after a list of moves — and which move failed, if one did |
| ask who is better, and for the top candidates | a **multi-PV** analysis, top five with evaluations |
| get the exact result of a small endgame, and of every move in it | a **tablebase** lookup, 7 men or fewer |
| ask how bad one specific alternative is | the evaluation of that one move |
| sanity-check a finished chapter | a pass over the whole mainline |

Four things worth knowing before you trust the output:

1. **Every evaluation is from White's point of view**, whoever is to move: `+1.2`
   is good for White, `#-3` is Black mating in three. The player's side comes from
   `Result` (C11), so in a Black chapter flip the sign in your head before you
   write "you are doing fine".
2. **Multi-PV is how you build the sideline list.** The top five moves with their
   evaluations give you the candidates C15.2 asks you to filter, and pricing each
   one makes the verdict in your comment the engine's rather than a guess.
3. **The best move is not always the move to teach.** The mainline should be a
   move a human can play and explain, and whose plan the comment can name, as
   long as the engine agrees it does not throw the position away. Use the engine
   to reject moves, not to pick them.
4. **Check legality the way the app does.** The app validates moves with
   `chess.js` in strict SAN, so a move walker built on `chess.js` accepts exactly
   what the app accepts; anything else may be more forgiving. Playing a variation
   out before pasting it in is the cheapest guard against the one error that kills
   a game, and it catches the line that is legal but does not reach the position
   you had in mind.

A whole-game pass reads the mainline only — variations and comments are ignored
by every engine — so sidelines still have to be checked one at a time. Checked
means every ply: a continuation is authored by you on both sides, and one
unexamined reply is where the hanging rook nobody takes comes from (B9).

Keep the numbers out of the file, and the engine itself (C13.3). The player
never sees an evaluation and never hears of a machine, so whatever the engine
tells you has to become the prose of C15.4 — the reason, not the authority.

## D18. The tools

Run from this folder:

```
node    .claude/skills/pgn-lines/fetch_puzzles.mjs --theme fork --max-rating 1100 --count 24
python3 .claude/skills/pgn-lines/validate.py  beginners/yourfile.pgn
.claude/skills/pgn-lines/parse_check.sh       beginners/yourfile.pgn   # -v dumps moves
python3 .claude/skills/pgn-lines/tb_check.py  beginners/yourfile.pgn   # endgames
python3 .claude/skills/pgn-lines/openings.py  beginners/yourfile.pgn   # openings
python3 .claude/skills/pgn-lines/openings.py  --fen "<FEN>"            # one position
```

**`fetch_puzzles.mjs`** downloads themed, rating-filtered puzzles from lichess as
draft candidates, for the tactics workflow in B8.2. It is an authoring tool, not
a check: what it writes is raw material that still needs screening, comments,
arrows and sidelines. `--list-themes` prints the theme slugs. It reuses the app's
own lichess client, so the API etiquette — sequential requests, a full minute
after a 429 — is honoured for you.

**`validate.py`** is the structural pass: layout, headers, grammar, shapes,
comment length, which moves carry sidelines — plus, for a file that has already
shipped, whether the app's playlist lists it and classifies it at the right level
(A2). It checks **everything in Part C that a script can check** — so if it is
clean, Part C is satisfied and you do not need a checklist for it. ERROR means
the file must not ship. Warnings are silent content loss or house style. It also
reads `[Role]` and `[IntendedResult]` (C11), knows where a `[%tail]` sits, and
prints a **line-endings table** — every game's last move, who played it, and its
last comment, flagged `PROMISE` when that comment is about the future — plus
notes on one-word verdicts, verbatim repeats, sideline lengths that are all the
same, silent moves, orientation words and mentions of the engine. Notes are
judgment prompts, not errors.

**`parse_check.sh`** loads the file through the **live app's** own parser and is
the only check that proves the moves are legal. `N of M games loaded` with
`N < M` names each game that was dropped. The app skips an unparsable game and
keeps the rest, so the loss is local — but a dropped game is a game the player
never sees. Set `PGN_APP_ROOT` to test against a different checkout.

**`tb_check.py`** is the endgame truth pass of B8.3 (needs `pip install chess`
and network access). It walks every line of every game, flags any scripted ply
that changes the result or ignores a result-improving capture as an ERROR, lists
the result-preserving moves left unrecorded at each decision point, and labels
each sideline mistake or also-good so the spoken verdicts can be read against the
truth. Skip it only for files with no positions of 7 men or fewer.

**`openings.py`** is the opening popularity pass, and the only tool here that
needs no network — it reads a Polyglot book from `polyglot/`, or from `--book` /
`$PGN_BOOK`. The default is `polyglot/codekiddy.bin`, picked by measuring the ten
readable books in that folder against the studies: it knows **336 of the 440**
mainline decision positions in the opening files (76%, next best 62%), its weights
behave like counts rather than preferences, and it is the only one that contains
the quiet sidelines those chapters actually meet. With `--fen` or `--moves` it prints what the book
plays in one position, most-played first. Given a PGN it walks the mainlines and
raises a **warn** where a scripted opponent reply is missing from a book that has
an opinion (B9), and a **note** where a popular book move at a player decision
point is recorded by no sideline (C15.2). Both are advisory: only the *player's*
unrecorded moves lock the board, and the book knows nothing about the target
rating band. It says so itself when the weights look like preferences rather than
counts, and it collapses the repeat findings that a file of unanchored chapters
produces (A4.1).

### What the tools do **not** decide

Below the warnings, `validate.py` prints the line-endings table and a set of
file numbers. None of them is an error, and none can be decided by a script —
they are judgment calls, and a clean bill of health printed next to a bad one is
not approval:

| Output | What to do with it |
|---|---|
| **line endings** | One row per game: last move, who played it, last comment. `PROMISE` means the comment is about the future and the line stopped before its payoff (B7.6); `OPP` means the reward is on the wrong move; `SILENT` means the player's last move says nothing (B7.5). Read every row |
| **sideline coverage %** | Over decision points only — the tail is not counted. Every uncovered decision point is a place a sensible move locks the board. Opening review games need the densest cover (B8.1). Shipped files today range from 100% down to 51% |
| **sidelines with no continuation** | Right only when the move loses on the spot (C15.3). More than a couple means the exemption is being stretched |
| **silent sidelines** | Sidelines whose first move says nothing, so the app narrates them itself (C15.1 rule 6). A verdict on the last ply does not fix this. **This should be zero** |
| **repeats, one-word verdicts** | A comment that appears twice is a template; a one-word verdict is a verdict with no reason (C13.3, C15.4). Both should be zero |
| **sideline lengths all alike** | Seven in ten sidelines the same length is a formula, not a judgment (C15.3) |
| **silent moves** | Mainline moves with no comment (B7.5). The set-up move and the player's last move are the two that matter most |

Little of Part A or Part B is checked. With `[Role]` the validator can see a
teaching game with no arrow, an exercise with one, and a set-up that draws the
answer; it cannot see the file's shape, the block plan, whether a chapter is
FEN-anchored, whether a comment's verdict is true, or whether a downloaded
puzzle really needs its motif. Those are yours.

Five checks are worth doing by hand on every file, because all five fail
silently and the author is the worst-placed person to catch them: you already
know the answer, and you already hear the joke in your own head:

- **Does any comment draw the move the player must find?** (B7.4) A shape in the
  comment *preceding* a player move, pointing at the square that move lands on,
  ends the exercise before it starts. Green counts as much as yellow — except in
  the tail (B7.6), where the app is playing and a green arrow is the plan.
- **Read the last comment of every game.** Is it about the board, or about the
  future? "The pawn walks home now" is a line that stopped early (B7.6). The
  validator's `PROMISE` flag catches the common wordings, not the idea.
- **Read every set-up comment against the `FEN`**, not against the position
  after the set-up move (B7.5). "Mate in two" with his king not yet in the corner
  is false at the moment it is spoken.
- **Does every chapter's `FEN` appear on an earlier chapter's mainline?** (A4.1)
  If not, the player opens it looking at their own pieces on squares they never
  moved them to.
- **Read the whole file out loud.** Speech is the product, and this is the only
  check on C13.4 there is: a comment that scans fine on the page can land flat,
  breathless or faintly sarcastic in the ear. Listen for the file's worst
  sentence rather than its best, for a run of comments that all sound the same,
  and for whether a child would still be enjoying this on game twelve.

**Registration is checked only for a file that has already shipped.**
`validate.py` matches on content, and once it finds the file's exact bytes in
the app's `pgns/` it warns if no playlist line points at it, if that line
carries no level (so no preset can serve it), or if the level contradicts the
folder. A file you have not shipped yet says nothing at all — and nothing here
checks the app's side of the list, which is what `node tools/sim/playlist.js`
is for (A2).

## D19. Shipping

See A2. Copy into `chessboxing-smoother/pgns/` under the app's naming
convention, add the `Display Name:filename.pgn:level` line to that repo's
**root** `playlist.txt` with the level that matches the folder, run
`node tools/sim/playlist.js`, and leave everything under `www/` to
`build-www.sh`.

---

# Appendices — evidence, not rules

## Ap1. Worked example

`Lucas/scotch.pgn`, the "Hemming" chapter — compact, and it uses nearly every
feature. Domain: opening. Role: review.

```
[Event "Scotch game: Hemming"]
[Result "0-1"]
[FEN "r1b1kb1r/p1ppqppp/1np5/4P3/2P5/8/PP2QPPP/RNB1KB1R w KQkq - 1 9"]
[SetUp "1"]
[ChapterURL "https://lichess.org/study/ns9Pwu95/bkw9qvPY"]

{ Once Hemming played b3 against you here. }
9. b3 Qe6 { This move prevents the Ba3 trick for white. } { [%cal Gc1a3,Ga3f8] } (9... a5 { You want to break the queen side pawns with your a pawn. But white has the Ba3 trick. } { [%cal Ga5a4] } 10. Ba3 Qe6 11. Bxf8 Rxf8 { The computer says you are doing fine. But are you happy with this? }) (9... g6 { That is a good plan as well. But what about the Ba3 trick? } 10. Ba3 { [%cal Ra3f8] }) (9... d5 { This is also completely reasonable. But the Ba3 trick is annoying. } 10. Ba3 { [%cal Ra3f8] }) 10. Bb2 { If you play d5 you transpose into the previous line. You can also push the a pawn to break the queen side. You will be fine either way. Play a5 to move on. } { [%csl Gd5,Ga5][%cal Gd7d5,Ga7a5] } 10... a5 (10... d5) 11. Nd2 { Keep pushing } { [%cal Ga5a4] } 11... a4 0-1
```

| Element | Effect |
|---|---|
| `Result "0-1"` | player is Black; board flips to Black's view |
| `FEN ... w ...` + `SetUp "1"` | position is set; **White** is to move, which is not the player, so… |
| `9. b3` | …the app auto-plays it after the opening comment |
| `{ Once Hemming played b3… }` | spoken before anything moves — found by the `]\n\n{` regex |
| `9... Qe6` | the first move the player must find |
| `{ This move prevents… } { [%cal Gc1a3,Ga3f8] }` | spoken, and two green arrows show the trick it prevents |
| `(9... a5 …)` | a *good* alternative. Player tries `a5` → prose plays, then `Ba3 Qe6 Bxf8 Rxf8` auto-plays with its comments → rewind. Costs a star |
| `(9... g6 …)`, `(9... d5 …)` | siblings on the same move, both two plies, both ending on a **red** arrow for the punishment |
| `10. Bb2` comment | the longest here — it tells the player what to play next, because two moves are equally fine and only one continues the line |
| `(10... d5)` | **a defect**, kept as an example of what not to write. With no comment the app speaks its own "That starts a sideline" line and draws a yellow arrow (C15.1 rule 6). Today it would carry a sentence naming the transposition and a ply or two showing it |
| `11... a4` | **a second defect.** The line ends on the player's move, which is right — but that move carries no comment at all, so the player's last move is silent and the chapter's last words are "Keep pushing", a promise. Today it would carry the reward and the chapter would run on to what the a pawn achieves (B7.5, B7.6) |

Note what is *not* here: no NAGs, no nested parentheses, no sideline on a White
move, and every comment is one or two spoken sentences. And note what would not
pass today: "Keep pushing" is a fragment with no subject (C13.3), "The computer
says you are doing fine. But are you happy with this?" names a machine and ends
on a question nobody answers (C13.3 rule 8), and the chapter has no `[Role]` tag
(C11).

## Ap2. Where the runtime facts come from

All in `/home/luis/Sync/projects/chessboxing-smoother/`.

| Fact | Source |
|---|---|
| games split on `[Event ` | `loadpuzzles.js` — `matchAll(/\[Event\s/g)` |
| one bad game is skipped, not cascaded | `loadpuzzles.js` — `try/catch` round `loadpuzzle()` |
| opening comment found by `]\n\n{` | `loadpuzzles.js` — `reComment` |
| `} { ` / `}  {` merged on the same line | `loadpuzzles.js` — two `replaceAll` calls |
| `Result` selects the side | `loadpuzzles.js` — `header.Result == "1-0"` |
| a file is a study | `loadpuzzles.js` `puzzle.study = file`; `puzzleTrainer.js` per-study counts; `studies.js` |
| promotions carried through | `loadpuzzles.js` `move.promotion`; `puzzleTrainer.addMove` fifth slot |
| the recorded line picks the promotion piece | `puzzle-bridge.js` — `promotionPieceFor()` |
| variations flattened one level | `loadpuzzles.js` — the `move.variations` loop does not recurse |
| shape code length decides circle vs arrow | `puzzle-bridge.js` — `c.length === 3` / `=== 5` |
| speech awaited to its end; watchdog `min(30000, 90 × chars + 3000)` ms | `voices.js` — `speechTimeoutFor()`, raced +3 s in `puzzle-bridge.js` `speak()` |
| a final comment on the player's move is awaited; on the opponent's move only its shapes hold it | `puzzle-bridge.js` — `applyMove()` awaits `saycomment`; `solvedPuzzle()` waits on `annotationHold`, which `saycomment()` sets only for shapes |
| `[%tail]` hands the rest of the line to the app | `loadpuzzles.js` — the sixth move slot; `puzzle-bridge.js` — `playTail()` |
| stars from sidelines **entered** | `puzzle-bridge.js` — `altCount` incremented in `handleAlternative()` |
| the stock "That starts a sideline" line | `puzzle-bridge.js` — the `else` branch of `playAlternative()` |
| board locks on an unrecorded move | `puzzle-bridge.js` — `backtrack()` |
| opening comment awaited with the board locked | `puzzle-bridge.js` — `lockBoard()` then `saycomment(...).then(whoshouldmovefirst)` |
| `playlist.txt` parsing, optional display name | `playlist.js` — `displayNameFor()` |
| the trailing `:level`, and the three level words | `playlist.js` — `splitLevel()`, `STUDY_LEVELS` |
| a level preset is that level's studies plus a lichess block | `puzzle-bridge.js` — `studiesAtLevel()`, `applyLevelPreset()` |
| BEGINNER and INTERMEDIATE presets, and no ADVANCED one | `levelpicker.js` |

## Ap3. The frozen baseline

**These are historical measurements, not targets and not current practice.** They
were taken over the **192-game snapshot** in `Lucas/` — every file except
`benko.pgn`, `benoni.pgn`, `endgame.pgn` and `eptest.pgn` — and every figure below
reproduces exactly on that set. The tree today holds far more than that, so do not
quote these as facts about "the corpus".

| Measured | Value |
|---|---|
| games | 192 |
| prose comments | 2669 |
| comment length | median 45, 90th percentile 89, longest 185 — about 1.4 sentences |
| "you"/"your" | ~1200 comments |
| "Let us" / "let's" | 138 / 4 |
| bare squares (`d5`, `f7`) | 480 comments |
| SAN piece notation | 9 of 2669 |
| green / red / blue / yellow shapes | 1971 / 746 / 555 / 114 |
| sidelines | 1774, of which 1398 (79%) are a single move with a comment |
| sidelines with a continuation | median 5 plies; 257 of 376 (68%) end on the opponent's move |
| opening comments | **101**, of which **56** carry shapes and **26** are shapes-only |
| NAGs | zero |

Two corrections to figures this document used to print. The opening-comment
counts above replace "147 of the corpus's 510", which reproduces on no snapshot —
192 games cannot hold 510 opening comments. And **all 26 shapes-only opening
comments carry no prose at all**, so B7.5's "say the move in words as well as
drawing it" is a rule this document is imposing, not a description of what the
corpus does.

`downloaded/` is excluded from every count and breaks most of these rules on
purpose: 274 games on `[Result "*"]`, 255 NAGs, 44 promotions, and hundreds of
sidelines on the opponent's moves.

## Ap4. Phrase bank

House phrasings grouped by the job they do; most are lines from shipped files.
Steal the shape, not the position — read them against C13.3 and C13.4 rather
than treating the list as the rule, and never paste one verbatim: a phrase that
appears twice in a file is a template (C15.4).

*Also good, but not our line:*
- "This is ok. But taking with the queen is more aggressive."
- "It is perfectly playable. But there is another idea on the other side of the board."
- "Also excellent, and the door into a whole different world."
- "That is the queens gambit. A fine opening, just not today."
- "A good move too. It reaches the same squares, only slower."
- "The same house by another door. Knights usually go first."
- "We prefer not to block our bishop."

*A mistake, pointed at the move and not at the player:*
- "A quiet move, and the whole idea evaporates."
- "A knight down, and the fork is gone too."
- "You take back. But the rook was not the prize here, the mate was."
- "You had mate in one. This only pokes at pawns."
- "The knight on h5 has no way back: every square it could reach belongs to a pawn."
- "Never step backwards in front of your own pawn."

*The verdict at the end of a continuation:*
- "The window is open, the mate is gone, and you are still losing."
- "He takes the opposition and your king can never get past. The win is gone."
- "A new queen on e8, and his king on b3 never got near it."
- "Also winning, but sideways is slow. Your king wants to go forwards."
- "You are in trouble: his rook reaches the seventh row and your king has no shelter."
- "Nothing gained. Go build the bridge: rook to d4."

*A verdict with its reason (C13.3):*
- "Drawn: his king sits in front of the pawn, and you can never push it out."
- "Lost. His king steps in front of your pawn on c5, and it never queens."
- "Also wins, but the king was faster: three moves for the pawn, two for your king to reach f7."

*The tail's comments (B7.6) — the send-off on the `[%tail]` move, at most one
explanation in the middle, the reward at the end, and silence everywhere else:*
- "Now watch the pawn go home."
- "Not b6: that is stalemate. The king steps to a6 and the pawn is still guarded."
- "A new queen on e8. That is the opposition: he had to move, so he had to let you past."

*Cheering, when it has been earned:*
- "Nice, that is the one." · "Well spotted." · "You are right on track."
- "A whole rook. The fork did all the work."
- "A free knight. The guard had to go first."
- "Mate! His own pawns kept him at home."
- "This one is tricky, take your time."

*Pieces behaving like characters (C13.4):*
- "A whole queen, collected from the far corner."
- "The little pawn shoos her away and slams the door on f7."
- "Never send the queen out early. She is big, and everyone chases her."
- "The knight ate your rook for free."
- "A free rook. The check bought you the time to take it."
- "Your queen parks in her own knight's doorway."

*Never — all three are real, and all three are in `Lucas/scotch.pgn`:*

| The line | What it costs | Say instead |
|---|---|---|
| "Congratulations genius, you have just blundered." | sarcasm aimed at a child, which is the fastest way to end the session | "That square is a trap. The knight walks in and does not walk out." |
| "This was a missed win. Think before you move." | the scolding lands on the player rather than the move | "That was the win, and it just walked past. Look again." |
| "This is a mistake. White prevents you to castle." | broken English is far more obvious in the ear than on the page | "This one is a mistake. Now he stops you castling." |

## Ap5. Counter-examples, with numbers

Measured with `validate.py` over the files as authored. Several of the names are
historical: `tactics1.pgn`, `tactics2.pgn` and `checkmates1.pgn` have since been
renamed, `rook-endgames.pgn` moved to `intermediate/`, and
`beginners/tactics-basics.pgn` was deleted in favour of the newer
`beginners/basic-tactics.pgn` (A5). The measurements are kept because what each
one demonstrates is not about the file.

| file | games | `FEN`-anchored | decision points | covered |
|---|---|---|---|---|
| `beginners/tactics1.pgn` | 30 | all | 62 | **100%** |
| `beginners/tactics-basics.pgn` | 18 | all | 26 | **100%** |
| `intermediate/tactics2.pgn` | 30 | all | 65 | **100%** |
| `beginners/checkmates1.pgn` | 24 | all | 37 | 86% |
| `advanced/rook-endgames.pgn` | 18 | all | 76 | 85% |
| `advanced/london-system.pgn` | 12 | **none** | 83 | **62%** |
| `advanced/vienna.pgn` | 14 | **none** | 94 | **51%** |

The two files that ignore A4.1 are the two worst covered, and it is arithmetic
rather than carelessness: 14 games sharing an 8-ply prefix means 56 of vienna's
94 decision points are the same four moves. Anchoring each chapter at its branch
point removes them.

Sideline continuation lengths, showing the two-ply formula of C15.3:

| file | sidelines | median plies | shape |
|---|---|---|---|
| `beginners/tactics1.pgn` | 128 | 2 | 111 at exactly 2 |
| `beginners/tactics-basics.pgn` | 44 | 2 | 39 at 2 |
| `beginners/checkmates1.pgn` | 73 | 2 | 64 at 2, plus 8 with no continuation |
| `intermediate/tactics2.pgn` | 120 | 2 | 93 at 2 |
| `advanced/vienna.pgn` | 65 | 4 | 46 at 4 |
| `advanced/london-system.pgn` | 109 | 4 | 100 at 4 |

And silent sidelines (C15.1 rule 6) — first move carrying no comment, so the app
narrates it itself:

| file | silent | of |
|---|---|---|
| `beginners/tactics-basics.pgn` | **44** | 44 |
| `advanced/london-system.pgn` | **109** | 109 |
| `advanced/vienna.pgn` | **65** | 65 |
| the other four files | 0 | — |

Those files put the verdict on the *last* ply of the continuation, which
reads correctly in a text editor and is wrong at run time: the player hears three
seconds of the app's flat stock sentence, and sees a yellow arrow drawn on the
move they just got wrong, before the demonstration starts.

Measured again in September 2026 over the twenty-five shipped files, before the
B7.6 and C13.3 rewrite:

| defect | count |
|---|---|
| endgame games whose last comment promises the payoff instead of showing it | about 55 of 66, across four files |
| games one ply long | 10 of 20 in `capablanca-plans-intermediate.pgn`; 4 in `rook-endgames.pgn`; 5 in `capablanca-endgames-intermediate.pgn` |
| chapters ending on a silent player move | 6 of 9 in `stafford-gambit.pgn`, one of them a mate |
| sidelines closing on the single word "Lost." | 34 in `rook-endgames.pgn`; "You are lost." 101 times in `imbalanced-endgames.pgn` |
| "Playable" / "Also fine" / "chooses a different task" / "takes a different route" | 393 / 247 / 75 / 109 |
| games that never speak their own motif | 12 of 20 in `intermediate-tactics.pgn` |
| uses of "opposition" / definitions of it | 74 / 0 |
| files where every game has the same number of plies | `basic-tactics.pgn` (14 × 4 plies, 3 sidelines each), `intermediate-tactics.pgn` (20 × 4 plies) |

Every one of those is a rule that was missing, not a rule that was broken.

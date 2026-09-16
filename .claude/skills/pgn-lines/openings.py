#!/usr/bin/env python3
"""Ask a Polyglot opening book what humans play, and audit a study against it.

Opening chapters script the opponent, so every reply is the author's choice, and
PGNLINES.md B9 asks that it look like a human choice. This tool puts a book behind
that judgement. It needs no network.

  python3 .claude/skills/pgn-lines/openings.py --fen "<FEN>"
  python3 .claude/skills/pgn-lines/openings.py --moves e4 e5 Nf3 Nc6 Bc4
  python3 .claude/skills/pgn-lines/openings.py beginners/italian.pgn [more.pgn ...]

Options:
  --book PATH     the Polyglot .bin to read.  Default: $PGN_BOOK, else
                  polyglot/codekiddy.bin under this folder, else
                  ~/.cache/pgn-openings-book.bin
  --max-ply N     stop auditing a game after N plies (default 24)
  --min-share P   a book move below P% of the position's weight is ignored when
                  looking for moves your sidelines do not record (default 10)
  --min-weight W  ignore a position whose total book weight is under W: the book
                  barely knows it, so its shares mean nothing (default 20)

WHAT THE BOOK CAN AND CANNOT SETTLE.  A book answers "do humans play this reply"
(B9).  It does NOT rank the moves a beginner plays: its weights are the book
author's preferences, it has no rating bands, and the natural mistakes that earn
their own chapter under B8.1 are usually absent from it entirely.  Every finding
here is advisory — judge it, do not apply it.

Exit status: 1 if any ERROR, 2 on a usage or environment problem, else 0.
"""
import os
import sys

try:
    import chess
    import chess.pgn
    import chess.polyglot
except ImportError:
    sys.exit("openings.py needs the python-chess package:  pip install chess")

# codekiddy.bin was picked by measurement over the ten readable books in
# polyglot/: it knows 336 of the 440 mainline decision positions in the opening
# studies (76%, next best 62%), its weights behave like counts rather than
# preferences, and it is the only one that contains the sidelines those studies
# actually meet.  Any Polyglot book works — point --book or $PGN_BOOK elsewhere.
BOOK_CANDIDATES = (
    "polyglot/codekiddy.bin",
    os.path.expanduser("~/.cache/pgn-openings-book.bin"),
)
FETCH_HINT = (
    "put a Polyglot .bin in polyglot/, or point --book / $PGN_BOOK at one"
)

errors = [0]
warns = [0]


def report(kind, gi, path, msg):
    if kind == "ERROR":
        errors[0] += 1
    elif kind == "warn":
        warns[0] += 1
    where = f"game {gi} | {path}" if path else f"game {gi}"
    print(f"{kind:6} {where}: {msg}")


def book_moves(reader, board):
    """[(san, move, weight, share_pct)] for this position, most-played first."""
    rows = []
    for entry in reader.find_all(board):
        mv = entry.move
        if mv not in board.legal_moves:
            continue
        rows.append([board.san(mv), mv, entry.weight])
    total = sum(r[2] for r in rows)
    if not total:
        return []
    rows.sort(key=lambda r: -r[2])
    return [(san, mv, w, 100.0 * w / total) for san, mv, w in rows]


MISTAKE_WORDS = ("mistake", "blunder", "greedy", "punish", "trap", "too early")


def names_a_mistake(comment):
    """B9's punishment line is allowed only when the comment says so out loud."""
    return any(w in (comment or "").lower() for w in MISTAKE_WORDS)


def fmt(rows, n=4):
    return ", ".join(f"{san} ({share:.0f}%)" for san, _, _, share in rows[:n])


# ---------------------------------------------------------------- lookup mode

def lookup(reader, board):
    rows = book_moves(reader, board)
    print(f"== {board.fen()}")
    if not rows:
        print("   not in the book")
        return 0
    total = sum(r[2] for r in rows)
    for san, _, weight, share in rows:
        print(f"   {san:8s} {share:5.1f}%   weight {weight}")
    print(f"   {len(rows)} move(s), total weight {total}")
    return 0


# ----------------------------------------------------------------- audit mode

def audit_game(reader, game, gi, max_ply, min_share, min_weight, said_before):
    player = chess.WHITE if game.headers.get("Result") == "1-0" else chess.BLACK
    seen = [0, 0]  # positions visited, positions found in the book

    def walk(node, board, depth, ply, path):
        children = node.variations
        if not children or ply > max_ply:
            return
        rows = book_moves(reader, board)
        if depth == 0:
            seen[0] += 1
            if rows:
                seen[1] += 1
        here_is_player = board.turn == player

        if rows and depth == 0 and sum(r[2] for r in rows) >= min_weight:
            top = rows[0]
            played = children[0].move
            played_row = next((r for r in rows if r[1] == played), None)

            # B9: the reply we scripted for the opponent.  Two moves are exempt.
            # The single auto-played ply before the player's first decision is the
            # set-up move, chosen to be plausible rather than best — "the set-up
            # move is not a reply".  And a losing reply may stand in the mainline
            # when the chapter exists to punish it, provided the comment says so
            # out loud; when it does, this drops to a note.
            if here_is_player:
                # C15.2: a popular try the player might make that nothing records.
                # Sidelines are matched by from/to only, the way the app does it.
                covered = {(c.move.from_square, c.move.to_square) for c in children}
                missing = [r for r in rows
                           if r[3] >= min_share
                           and (r[1].from_square, r[1].to_square) not in covered]
                if missing:
                    key = ("C15.2", board.board_fen(), fmt(missing))
                    if key in said_before:
                        said_before[key] += 1
                    else:
                        said_before[key] = 1
                        report("note", gi, path or "start",
                               f"book also plays {fmt(missing)} here, and no sideline "
                               f"records it  (PGNLINES.md C15.2)")
            elif ply > 0 and len(rows) >= 3:
                # A one- or two-move entry is a repertoire, not a survey: absence
                # from it says nothing.  Three or more means the book has an
                # opinion about the alternatives.
                said = names_a_mistake(children[0].comment)
                kind = "note" if said else "warn"
                excuse = "  (the comment calls it a mistake, so B9 allows it)" if said else ""
                msg = None
                if played_row is None and top[3] >= 50.0:
                    msg = (f"scripted reply {board.san(played)} is not in the book; "
                           f"humans play {fmt(rows)}{excuse}  (PGNLINES.md B9)")
                elif played_row is not None and played_row[3] < 2.0 and top[3] >= 50.0:
                    msg = (f"scripted reply {board.san(played)} is a {played_row[3]:.0f}% move; "
                           f"humans play {fmt(rows)}{excuse}  (PGNLINES.md B9)")
                if msg:
                    key = ("B9", board.board_fen(), board.san(played))
                    if key in said_before:
                        said_before[key] += 1
                    else:
                        said_before[key] = 1
                        report(kind, gi, path or "start", msg)

        for idx, child in enumerate(children):
            b2 = board.copy()
            b2.push(child.move)
            walk(child, b2,
                 depth if idx == 0 else depth + 1,
                 ply + 1,
                 f"{path} {board.san(child.move)}".strip())

    walk(game, game.board(), 0, 0, "")
    return seen


def audit(reader, path, max_ply, min_share, min_weight):
    try:
        text = open(path, encoding="utf-8").read()
    except OSError as exc:
        print(f"ERROR  {path}: {exc}")
        errors[0] += 1
        return
    import io
    stream = io.StringIO(text)
    gi = 0
    visited = found = 0
    said_before = {}
    before_e, before_w = errors[0], warns[0]
    while True:
        game = chess.pgn.read_game(stream)
        if game is None:
            break
        gi += 1
        v, f = audit_game(reader, game, gi, max_ply, min_share, min_weight, said_before)
        visited += v
        found += f
    print(f"== {path} — {gi} game(s), {errors[0] - before_e} error(s), "
          f"{warns[0] - before_w} warning(s)")
    repeats = sum(n - 1 for n in said_before.values() if n > 1)
    print(f"   {found} of {visited} mainline positions were in the book")
    if repeats:
        print(f"   {repeats} repeat finding(s) hidden — chapters that replay the same "
              f"prefix hit the same position again (PGNLINES.md A4.1)")
    if found == 0 and visited:
        print("   note  nothing to say about this file — the book does not reach it")


# ----------------------------------------------------------------------- main

def main(argv):
    args = argv[1:]
    if not args or args[0] in ("-h", "--help"):
        print(__doc__)
        return 2

    book_path = os.environ.get("PGN_BOOK")
    if not book_path:
        book_path = next((c for c in BOOK_CANDIDATES if os.path.exists(c)),
                         BOOK_CANDIDATES[0])
    fen = None
    moves = None
    max_ply = 24
    min_share = 10.0
    min_weight = 20.0
    paths = []

    i = 0
    while i < len(args):
        a = args[i]
        if a == "--book":
            i += 1
            book_path = args[i] if i < len(args) else None
        elif a == "--fen":
            i += 1
            fen = args[i] if i < len(args) else None
        elif a == "--moves":
            moves = args[i + 1:]
            i = len(args)
        elif a == "--max-ply":
            i += 1
            max_ply = int(args[i])
        elif a == "--min-share":
            i += 1
            min_share = float(args[i])
        elif a == "--min-weight":
            i += 1
            min_weight = float(args[i])
        elif a.startswith("-"):
            print(f"unknown option {a}\n")
            print(__doc__)
            return 2
        else:
            paths.append(a)
        i += 1

    if not book_path or not os.path.exists(book_path):
        print(f"no opening book at {book_path}", file=sys.stderr)
        print(f"  {FETCH_HINT}", file=sys.stderr)
        return 2

    try:
        reader = chess.polyglot.open_reader(book_path)
    except Exception as exc:
        print(f"{book_path} is not a readable Polyglot book: {exc}", file=sys.stderr)
        return 2

    with reader:
        start = book_moves(reader, chess.Board())
        start_weight = sum(r[2] for r in start)
        if start_weight and start_weight < 100:
            print(f"note   {os.path.basename(book_path)} weights look like preferences, "
                  f"not counts (total weight {start_weight} at the start position) — "
                  f"read the shares below as a ranking, not a frequency")

        if fen is not None or moves is not None:
            try:
                board = chess.Board(fen) if fen else chess.Board()
                for m in (moves or []):
                    board.push_san(m)
            except ValueError as exc:
                print(f"cannot read that position: {exc}", file=sys.stderr)
                return 2
            return lookup(reader, board)

        if not paths:
            print(__doc__)
            return 2
        for p in paths:
            audit(reader, p, max_ply, min_share, min_weight)

    return 1 if errors[0] else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

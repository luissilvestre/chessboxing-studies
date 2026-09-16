#!/usr/bin/env python3
"""Check a trainer PGN against exact endgame truth (PGNLINES.md B8.3, B9).

For every position with 7 men or fewer, asks the lichess tablebase for the
exact result of the position and of every legal move, then verifies:

  ERROR  a mainline move, or any move inside a sideline continuation, changes
         the result for the side playing it (a scripted blunder);
  ERROR  a scripted move ignores a capture that would strictly improve the
         mover's result (the hanging piece nobody takes);
  WARN   a winning or drawing side declines a free piece capture that keeps
         the same result — take it, or let the comment say why not;
  WARN   a mainline player decision point has result-preserving moves that
         are neither the mainline nor a sideline: the board locks on them
         (PGNLINES.md B8.3 — record them or defend leaving them out);
  note   each sideline's first move is labelled mistake / also-good, so the
         spoken verdict on it can be checked against the truth;
  note   a sideline hangs on a tail move, where the app is playing and the
         player can never enter it (PGNLINES.md B7.6, C15.1 rule 7).

The tail: a player's mainline move whose comment carries [%tail] is the last
decision point (PGNLINES.md B7.6). Every ply after it is played by the app, so
those plies are still checked for keeping the result (and for free captures,
since the player's tail moves are scripted too), but unrecorded alternatives
there do not lock the board and are not reported.

Needs:  pip install chess     and network access to tablebase.lichess.ovh
(cached in ~/.cache/pgn-tb-cache.json, so re-runs are mostly offline).
Positions with more than 7 men are reported and skipped — check those with a
deep multi-PV instead (PGNLINES.md D17).

  python3 .claude/skills/pgn-lines/tb_check.py advanced/yourfile.pgn

Exit status is 1 if any ERROR was found.
"""
import io, json, os, sys, time, urllib.parse, urllib.request

try:
    import chess, chess.pgn
except ImportError:
    sys.exit("tb_check.py needs the python-chess package:  pip install chess")

CACHE_FILE = os.path.expanduser("~/.cache/pgn-tb-cache.json")
try:
    cache = json.load(open(CACHE_FILE))
except Exception:
    cache = {}
_dirty = [0]

def tb(fen):
    key = " ".join(fen.split()[:5])
    if key in cache:
        return cache[key]
    url = "https://tablebase.lichess.ovh/standard?fen=" + urllib.parse.quote(fen)
    for attempt in range(6):
        try:
            with urllib.request.urlopen(url, timeout=20) as r:
                data = json.load(r)
            break
        except Exception:
            if attempt == 5:
                sys.exit(f"tablebase unreachable for {fen} — check the network")
            time.sleep(1.5 * (attempt + 1))
    time.sleep(0.1)
    cache[key] = data
    _dirty[0] += 1
    if _dirty[0] % 25 == 0:
        save_cache()
    return data

def save_cache():
    os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
    json.dump(cache, open(CACHE_FILE, "w"))

# Values are for the side to move in the queried position. Over the board the
# 50-move rule makes cursed wins and blessed losses draws.
CAT_VAL = {"win": 1, "maybe-win": 1, "cursed-win": 0, "draw": 0,
           "blessed-loss": 0, "maybe-loss": -1, "loss": -1, "unknown": None}
NAME = {1: "WIN", 0: "draw", -1: "LOSS", None: "?"}

def pos_val(board):
    if len(board.piece_map()) > 7:
        return None, None
    d = tb(board.fen())
    return CAT_VAL[d["category"]], d

def mover_val(board, move):
    b2 = board.copy(); b2.push(move)
    v, _ = pos_val(b2)
    return None if v is None else -v

errors = [0]
warns = [0]

def report(kind, game_i, path, msg):
    if kind == "ERROR":
        errors[0] += 1
    elif kind == "WARN":
        warns[0] += 1
    print(f"{kind:6} game {game_i} | {path}: {msg}")

def snippet(comment):
    c = " ".join((comment or "").split())
    return (c[:60] + "...") if len(c) > 63 else c

def check_game(game, gi):
    player = chess.WHITE if game.headers.get("Result") == "1-0" else chess.BLACK
    board = game.board()
    v0, _ = pos_val(board)
    if v0 is None:
        print(f"note   game {gi}: more than 7 men — tablebase skipped, use deep multi-PV")
        return

    def walk(node, board, depth, expect, path, tail=False):
        children = node.variations
        if not children:
            return
        mover_is_player = board.turn == player

        if depth == 0 and tail and len(children) > 1:
            print(f"note   game {gi} | {path or 'start'}: {len(children) - 1} sideline(s) on a "
                  f"tail move can never be reached — the app plays the tail (PGNLINES.md B7.6)")
            children = children[:1]

        if depth == 0 and mover_is_player and not tail:
            d = tb(board.fen())
            preserving, covered = [], set()
            for c in children:
                covered.add((c.move.from_square, c.move.to_square))
            missing = []
            for m in d["moves"]:
                mv = chess.Move.from_uci(m["uci"])
                v = mover_val(board, mv)
                if v is not None and v >= expect:
                    preserving.append(board.san(mv))
                    if (mv.from_square, mv.to_square) not in covered:
                        missing.append(board.san(mv))
            if missing:
                report("WARN", gi, path or "start",
                       f"{len(preserving)} moves preserve the result; not recorded: "
                       + ", ".join(missing) + "  (each of these locks the board)")

        for idx, child in enumerate(children):
            mv = child.move
            san = board.san(mv)
            here = f"{path} {san}".strip()
            vm = mover_val(board, mv)
            is_side_first = idx > 0
            in_continuation = depth > 0 and idx == 0

            if vm is not None and vm < expect:
                if is_side_first:
                    print(f"note   game {gi} | {here}: sideline mistake "
                          f"({NAME[expect]} -> {NAME[vm]}) — verdict: \"{snippet(child.comment)}\"")
                else:
                    where = "inside a continuation" if in_continuation else "MAINLINE"
                    report("ERROR", gi, here,
                           f"scripted move throws the result {where}: "
                           f"{NAME[expect]} -> {NAME[vm]} for the mover")
            elif is_side_first and vm is not None:
                print(f"note   game {gi} | {here}: sideline also-good "
                      f"(keeps {NAME[vm]}) — verdict: \"{snippet(child.comment)}\"")

            # free-capture test for every scripted (non-player-mainline) ply;
            # in the tail the player's moves are scripted too (PGNLINES.md B7.6)
            player_mainline_move = (depth == 0 and idx == 0 and mover_is_player
                                    and not tail)
            if vm is not None and not player_mainline_move and not board.is_capture(mv):
                for cap in board.legal_moves:
                    if not board.is_capture(cap):
                        continue
                    piece = board.piece_at(cap.to_square)
                    if piece is None or piece.piece_type == chess.PAWN:
                        continue
                    cv = mover_val(board, cap)
                    if cv is None:
                        continue
                    if cv > vm:
                        report("ERROR", gi, here,
                               f"ignores {board.san(cap)}, which improves the result "
                               f"({NAME[vm]} -> {NAME[cv]} for the mover)")
                    elif cv == vm and vm >= 0:
                        report("WARN", gi, here,
                               f"declines the free capture {board.san(cap)} "
                               f"(same result) — take it or say why not")
            b2 = board.copy(); b2.push(mv)
            child_tail = tail or (depth == 0 and idx == 0 and mover_is_player
                                  and "[%tail]" in (child.comment or ""))
            walk(child, b2, depth if idx == 0 else depth + 1,
                 None if vm is None else -vm, here, child_tail)

    walk(game, board, 0, v0, "")

def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    text = open(sys.argv[1], encoding="utf-8").read()
    stream = io.StringIO(text)
    gi = 0
    while True:
        game = chess.pgn.read_game(stream)
        if game is None:
            break
        gi += 1
        check_game(game, gi)
    save_cache()
    print(f"== {gi} game(s), {errors[0]} error(s), {warns[0]} warning(s)")
    sys.exit(1 if errors[0] else 0)

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Check a trainer PGN against the rules in PGNLINES.md.

ERROR = the game fails to load (the app skips it and keeps the rest), or
        breaks at play time. The file must not ship.
WARN  = the file loads, but content is silently dropped or the house style of
        the corpus is broken.
NOTE  = a judgement prompt, never an error: something the author has to read
        and decide at the board — a last comment that promises instead of
        describing, a one-word verdict, a comment repeated verbatim, a move
        that says nothing, a whole file of sidelines cut to the same length.

  python3 .claude/skills/pgn-lines/validate.py beginners/tactics1.pgn
  python3 .claude/skills/pgn-lines/validate.py advanced/*.pgn

Per file it prints every ERROR, warn and note, then the file numbers (decision
points and coverage, sidelines with no continuation, silent sidelines,
verbatim repeats, quantised lengths), then a line-endings table with one row
per game:

   ending  game 3   last=Kf7     by=player    PROMISE  "The pawn simply walks home now."

  PROMISE  the last comment talks about the future instead of the board (B7.6)
  SILENT   the last player move has no comment, so the reward is never heard
  OPP      the line ends on the opponent's move

This is a structural check: it never moves a piece. Whether the SAN is legal, and
whether a sideline attaches to the move you think it does, is what
parse_check.sh answers by running the app's own parser.

Exit status is 1 if any ERROR was found. Warns and notes never change it.
"""

import collections
import os
import re
import sys

# The app splits games on this exact regex (loadpuzzles.js:5).
RE_EVENT = re.compile(r"\[Event\s")
RE_TAG = re.compile(r'^\[(\w+)\s+"([^"]*)"\]\s*$')
RE_SAN = re.compile(
    r"O-O-O|O-O"
    r"|[KQRBN][a-h]?[1-8]?x?[a-h][1-8]"
    r"|[a-h]x[a-h][1-8](?:=[QRBN])?"
    r"|[a-h][1-8](?:=[QRBN])?"
)
RE_MOVENO = re.compile(r"\d+\.(?:\.\.)?")
RE_RESULT = re.compile(r"1-0|0-1|1/2-1/2|\*")
RE_NAG = re.compile(r"\$\d+")
RE_SHAPES = re.compile(r"\[%(csl|cal)\s+([^\]]+)\]")
RE_SQUARE = re.compile(r"^[a-h][1-8]$")
RE_BLOCK = re.compile(r"\[%[^\]]*\]")       # any [%...] block: shapes, tail, eval, clk
RE_TAIL = re.compile(r"\[%tail\]")
RE_EXPORT = re.compile(r"\[%(?:eval|clk)\b")
RE_WORD = re.compile(r"[A-Za-z']+")
RE_DEST = re.compile(r"([a-h][1-8])(?:=[QRBN])?[+#]?$")

# Nothing is cut any more. The app awaits every utterance; the only watchdog is
# voices.js speechTimeoutFor() = min(30000, 90 * chars + 3000) ms, raced with
# 3 s of grace in speak(). What a long comment costs is the board being held
# while it is spoken, roughly one second per 15 characters (PGNLINES.md C13.2).
STYLE_TARGET = 150   # two full sentences: counted, reported as a note
PACE_WARN = 240      # about 16 s of held board: warn, ask for a split
CHARS_PER_SECOND = 15
TAIL_MAX_SECONDS = 20  # a tail is watched after the puzzle is solved; B7.6 says well under this
SILENT_PLY_S = 0.7     # replayRest(): sleep(700) on a ply with no comment
SHAPE_LINGER_S = 1.4   # SHAPE_LINGER_MS: a comment that draws a shape holds the board this long
CHARS_PER_S = 15       # speech pace used throughout (C13.2)

# The last comment of a line is the reward. These words say the payoff is still
# to come, i.e. the line stopped early (PGNLINES.md B7.6).
RE_PROMISE = re.compile(
    r"\b(will|next move|walks? (home|in)|cannot be stopped|nothing (can )?stops?"
    r"|is coming|is next|from here|on its way|soon)\b", re.I)
# Directions that depend on which way the board is turned (C13.3 rule 7).
RE_ORIENTATION = re.compile(
    r"\b(top|bottom)\b"
    r"|\b(left|right)[ -](hand|side|edge|corner|flank|half)\b"
    r"|\b(to|on) the (left|right)\b"
    r"|\b(up|down) the board\b", re.I)
# Nobody else in the room (C13.3 rule 8).
RE_THIRD_PARTY = re.compile(r"\b(the (engine|machine|computer)|stockfish)\b", re.I)
# The role is a tag, never spoken (B7.5).
RE_ROLE_SPOKEN = re.compile(r"^\s*(Review|Exercise|Teaching|Lesson)\s*:")
RE_DRAW = re.compile(r"draw|drawn|stalemate", re.I)

ROLES = ("teaching", "review", "exercise")
INTENDED_RESULTS = ("win", "draw")


class Findings:
    def __init__(self):
        self.errors = []
        self.warns = []
        self.notes = []
        self.long_comments = 0  # over the style target; spoken in full, board held
        self.prose_seen = collections.Counter()  # every spoken comment in the file
        self.where = ""

    def error(self, msg):
        self.errors.append("%s%s" % (self.where, msg))

    def warn(self, msg):
        self.warns.append("%s%s" % (self.where, msg))

    def note(self, msg):
        self.notes.append("%s%s" % (self.where, msg))


def split_games(text):
    """Same split the app does: on the literal '[Event ' (loadpuzzles.js:5-13)."""
    starts = [m.start() for m in RE_EVENT.finditer(text)]
    games = []
    for i, start in enumerate(starts):
        end = starts[i + 1] if i + 1 < len(starts) else len(text)
        games.append((start, text[start:end].rstrip("\n")))
    return games


def split_header(raw, f):
    """Return (tags, blank_lines, movetext_lines). Reports layout errors."""
    lines = raw.split("\n")
    tags = {}
    i = 0
    while i < len(lines) and lines[i].startswith("["):
        m = RE_TAG.match(lines[i])
        if m:
            tags[m.group(1)] = m.group(2)
        else:
            f.error("tag line is not [Name \"value\"]: %s" % lines[i].strip())
        i += 1

    blanks = 0
    while i < len(lines) and lines[i].strip() == "":
        blanks += 1
        i += 1

    if blanks == 0:
        f.error("no blank line between the last tag and the movetext — the game "
                "will not parse (PGNLINES.md C10)")
    elif blanks > 1 and i < len(lines) and lines[i].lstrip().startswith("{"):
        f.warn("%d blank lines before the movetext — the opening comment is "
               "silently lost (PGNLINES.md C10)" % blanks)

    return tags, blanks, lines[i:]


def analysis_url(fen):
    """The lichess analysis URL for a FEN — spaces become underscores."""
    return "https://lichess.org/analysis/" + fen.replace(" ", "_")


def check_headers(tags, f):
    result = tags.get("Result")
    if result is None:
        f.error("no [Result] tag — the player silently becomes Black "
                "(PGNLINES.md C11)")
    elif result not in ("1-0", "0-1"):
        f.error('[Result "%s"] — only "1-0" (player is White) and "0-1" (player '
                "is Black) select a side; anything else silently makes the "
                "player Black (PGNLINES.md C11)" % result)

    fen = tags.get("FEN")
    if fen is not None:
        if tags.get("SetUp") != "1":
            f.error('[FEN] without [SetUp "1"] — the movetext is parsed from the '
                    "start position, so the moves are illegal and the app drops "
                    "this game (PGNLINES.md C11)")
        if len(fen.split()) != 6:
            f.error("[FEN] has %d fields, chess.js needs all six "
                    "(PGNLINES.md C11)" % len(fen.split()))
    elif tags.get("SetUp") == "1":
        f.warn('[SetUp "1"] without a [FEN] tag does nothing')

    # The Analysis button reads ChapterURL, then Site. With neither it is dead,
    # and the player cannot take the position away and look at it.
    if not tags.get("ChapterURL") and not tags.get("Site"):
        want = ("[Site \"%s\"]" % analysis_url(fen)) if fen else "[Site ...]"
        f.warn("no [ChapterURL] and no [Site] — the Analysis button does "
               "nothing for this game. Add %s (PGNLINES.md C11)" % want)
    elif fen and tags.get("Site") and not tags.get("ChapterURL"):
        expect = analysis_url(fen)
        if tags["Site"].startswith("https://lichess.org/analysis/") \
                and tags["Site"] != expect:
            f.warn("[Site] is a lichess analysis URL for a different position "
                   "than [FEN] — Analysis opens the wrong board. Expected %s "
                   "(PGNLINES.md C11)" % expect)

    return "white" if tags.get("Result") == "1-0" else "black"


def first_side(tags):
    """Who plays the first move of the movetext."""
    fen = tags.get("FEN")
    if fen and len(fen.split()) >= 2:
        return "white" if fen.split()[1] == "w" else "black"
    return "white"


def other(side):
    return "black" if side == "white" else "white"


def mover(i, opening):
    """Who plays mainline ply i when `opening` plays ply 0."""
    return opening if i % 2 == 0 else other(opening)


def prose(text):
    """What the app speaks: every [%...] block removed, braces dropped,
    whitespace collapsed (puzzle-bridge.js parseComment). Empty for a comment
    that only draws shapes."""
    text = RE_BLOCK.sub("", text)
    text = re.sub(r"[{}]", " ", text)
    return " ".join(text.split())


def shape_codes(text):
    """Every csl/cal code in a comment as (tag, code), blanks dropped."""
    out = []
    for tag, codes in RE_SHAPES.findall(text):
        for code in codes.split(","):
            code = code.strip()
            if code:
                out.append((tag, code))
    return out


def comments_on(comments, move):
    """The comment blocks attached to one move; None is the opening comment."""
    return [c for c in comments if c["move"] == move]


def prose_on(comments, move):
    """The spoken text of a move's comment(s), '' when it says nothing."""
    return " ".join(p for p in (prose(c["text"]) for c in comments_on(comments, move)) if p)


def destination(san):
    """The square a SAN move lands on; None for castling."""
    if san.startswith("O-O"):
        return None
    m = RE_DEST.search(san)
    return m.group(1) if m else None


def shorten(text, n=40):
    return text if len(text) <= n else text[:n - 1] + "…"


def scan_movetext(mt, f):
    """Walk the movetext once, reporting token-level errors.

    Returns (mainline, variations, comments):
      mainline   [{'san','pos'}]                     — one entry per ply
      variations [{'depth','parent','plies','pos'}]  — parent = mainline index
      comments   [{'text','start','end','move'}]     — 'move' is the ply it follows:
                 ("main", i) for mainline ply i, ("var", depth, j) inside a
                 sideline, None for the opening comment
    """
    mainline, variations, comments = [], [], []
    stack = []          # one entry per open '(' : {'depth','parent','plies','pos'}
    last_move = None    # the move a comment or '(' attaches to
    i, n = 0, len(mt)

    while i < n:
        c = mt[i]
        if c.isspace():
            i += 1
            continue

        if c == "{":
            end = mt.find("}", i)
            if end < 0:
                f.error("unterminated comment — a '{' is never closed")
                break
            text = mt[i + 1:end]
            if "[Event " in text:
                f.error("'[Event ' inside comment prose breaks the game splitter "
                        "(PGNLINES.md C10)")
            comments.append({"text": text, "start": i, "end": end, "move": last_move})
            i = end + 1
            continue

        if c == "(":
            entry = {"depth": len(stack) + 1, "parent": last_move, "plies": [], "pos": i}
            if entry["depth"] > 1:
                f.warn("nested '(' — a variation inside a variation parses and is "
                       "then silently discarded (PGNLINES.md C15.1 rule 2)")
            stack.append(entry)
            i += 1
            continue

        if c == ")":
            if not stack:
                f.error("stray ')' with no matching '('")
            else:
                entry = stack.pop()
                if entry["depth"] == 1:
                    entry["end"] = i
                    variations.append(entry)
                last_move = entry["parent"]
            i += 1
            continue

        m = RE_MOVENO.match(mt, i)
        if m and m.start() == i:
            i = m.end()
            continue

        m = RE_NAG.match(mt, i)
        if m:
            i = m.end()
            continue

        if c in "!?":
            i += 1
            continue

        m = RE_RESULT.match(mt, i)
        # A result token only ends the game; "1-0" can never start a move.
        if m and m.start() == i and not RE_SAN.match(mt, i):
            i = m.end()
            continue

        m = RE_SAN.match(mt, i)
        if m and m.start() == i:
            san = m.group(0)
            if i + len(san) < n and mt[i + len(san)] in "+#":
                san += mt[i + len(san)]
            if stack:
                stack[-1]["plies"].append({"san": san, "pos": i})
                last_move = ("var", len(stack) - 1, len(stack[-1]["plies"]) - 1)
            else:
                mainline.append({"san": san, "pos": i})
                last_move = ("main", len(mainline) - 1)
            i += len(san)
            continue

        # Nothing matched: name the usual suspects rather than a generic error,
        # and step over the whole token so one slip reports once.
        token = re.match(r"\S+", mt[i:]).group(0).rstrip(")}") or mt[i]
        if token.startswith("0-0"):
            f.error("castling written with zeros (%s) — the grammar only accepts "
                    "the letter O (PGNLINES.md C12)" % token)
        elif c == ";":
            f.error("';' end-of-line comment is not in the grammar (PGNLINES.md C12)")
        elif token.startswith("--"):
            f.error("'--' null move is not in the grammar (PGNLINES.md C12)")
        elif c == "}":
            f.error("stray '}' — a comment cannot contain the closing brace")
        else:
            f.error("cannot parse %r as a move (PGNLINES.md C12)" % token)
        i += len(token)

    if stack:
        f.error("unterminated variation — a '(' is never closed")
    return mainline, variations, comments


def check_comments(mt, comments, f):
    verdicts = collections.Counter()  # prose of one or two words, by frequency
    export = False
    for c in comments:
        text = c["text"]
        p = prose(text)
        if p:
            f.prose_seen[p] += 1

        if len(p) > PACE_WARN:
            f.warn("comment is %d characters — about %d seconds of held board; "
                   "nothing is cut, but split it (PGNLINES.md C13.2): %r"
                   % (len(p), round(len(p) / CHARS_PER_SECOND), p[:60]))
        elif len(p) > STYLE_TARGET:
            f.long_comments += 1

        # A verdict carries its reason (C13.3 rule 2). Shapes-only comments are
        # not verdicts; they are counted as silence elsewhere.
        if p and len(RE_WORD.findall(p)) <= 2:
            verdicts[p] += 1
        if RE_EXPORT.search(text):
            export = True
        for m in RE_ORIENTATION.finditer(p):
            f.note("'%s' — say the square, column, row or wing: the board is "
                   "turned for Black (PGNLINES.md C13.3): %r" % (m.group(0), p[:60]))
        for m in RE_THIRD_PARTY.finditer(p):
            f.note("'%s' — nobody else is in the room (PGNLINES.md C13.3): %r"
                   % (m.group(0), p[:60]))

        for tag, code in shape_codes(text):
            if len(code) not in (3, 5):
                f.warn("shape code %r is %d characters — only 3 (circle) and "
                       "5 (arrow) draw anything (PGNLINES.md C14)"
                       % (code, len(code)))
                continue
            if code[0] not in "GRYB":
                f.warn("shape colour %r is not G/R/Y/B — it silently becomes "
                       "green (PGNLINES.md C14)" % code[0])
            for sq in (code[1:3], code[3:5]):
                if sq and not RE_SQUARE.match(sq):
                    f.warn("shape code %r contains %r, which is not a square"
                           % (code, sq))
            if len(code) == 5 and code[1:3] == code[3:5]:
                f.warn("arrow %r goes from a square to itself and draws nothing "
                       "(PGNLINES.md C14)" % code)
            if tag == "csl" and len(code) == 5:
                f.warn("[%%csl %s] is 5 characters, so it draws an arrow — "
                       "use [%%cal] (PGNLINES.md C14)" % code)
            if tag == "cal" and len(code) == 3:
                f.warn("[%%cal %s] is 3 characters, so it draws a circle — "
                       "use [%%csl] (PGNLINES.md C14)" % code)

    if export:
        f.warn("raw lichess export blocks ([%eval] / [%clk]) — the comments were "
               "never rewritten after the export (PGNLINES.md C14)")
    if verdicts:
        examples = ", ".join("'%s'" % t for t, _ in verdicts.most_common(3))
        f.note("%d one- or two-word comment(s) with no reason, e.g. %s "
               "(PGNLINES.md C13.3)" % (sum(verdicts.values()), examples))

    # Two adjacent comment blocks are merged by a literal replace of "} { " or
    # "}  {" (loadpuzzles.js:15). Any other spacing drops the second block.
    for a, b in zip(comments, comments[1:]):
        gap = mt[a["end"] + 1:b["start"]]
        if gap.strip():
            continue
        merged = (gap == " " and b["start"] + 1 < len(mt) and mt[b["start"] + 1] == " ") or gap == "  "
        if not merged:
            f.warn("two comment blocks separated by %r — only '} { ' and '}  {' "
                   "are merged, so the second block and its arrows are silently "
                   "dropped (PGNLINES.md C13.1)" % gap)


def find_tail(comments):
    """Where [%tail] sits: the mainline indices carrying it, and whether it also
    appears where the app ignores it (a sideline, the opening comment)."""
    on_main, in_var, in_opening = [], False, False
    for c in comments:
        if not RE_TAIL.search(c["text"]):
            continue
        move = c["move"]
        if move is None:
            in_opening = True
        elif move[0] == "main":
            on_main.append(move[1])
        else:
            in_var = True
    return on_main, in_var, in_opening


def check_tail(mainline, variations, comments, side, opening, f):
    """[%tail] in the comment of a player's mainline move makes the app play
    the rest of the line itself (PGNLINES.md B7.6, C14). The plies after it are
    the tail: not decision points, and sidelines on them are unreachable.

    Returns the index of the move that starts the tail, or None.
    """
    on_main, in_var, in_opening = find_tail(comments)
    if in_var:
        f.warn("[%tail] inside a sideline comment does nothing — the app honours "
               "it only on a player's mainline move (PGNLINES.md C14)")
    if in_opening:
        f.warn("[%tail] in the opening comment does nothing — put it on the "
               "player's last decision move (PGNLINES.md C14)")

    tail_at = None
    for idx in sorted(on_main):
        if mover(idx, opening) != side:
            f.warn("[%%tail] sits on the opponent's move %s, where the app "
                   "ignores it — put it on the player's last decision move "
                   "(PGNLINES.md C14)" % mainline[idx]["san"])
        elif tail_at is None:
            tail_at = idx
        else:
            f.note("a second [%%tail] on %s is never reached — the tail already "
                   "starts at %s" % (mainline[idx]["san"], mainline[tail_at]["san"]))
    if tail_at is None:
        return None

    last = len(mainline) - 1
    if tail_at == last:
        f.note("[%%tail] sits on the last move %s, so no tail follows "
               "(PGNLINES.md B7.6)" % mainline[last]["san"])
        return tail_at

    tail = range(tail_at + 1, last + 1)
    # B7.6: the tail is silent except its last ply (the reward) and at most one
    # explaining comment. Every spoken ply costs its speech; a silent one 0.7 s.
    seconds = 0.0
    spoken_mid = []
    for i in tail:
        raw = " ".join(c["text"] for c in comments if c.get("move") == ("main", i))
        prose = prose_on(comments, ("main", i))
        shapes = bool(RE_SHAPES.search(raw))
        if prose:
            seconds += len(prose) / CHARS_PER_S + (SHAPE_LINGER_S if shapes else 0)
            if i != last:
                spoken_mid.append(mainline[i]["san"])
        elif shapes:
            seconds += SHAPE_LINGER_S
        else:
            seconds += SILENT_PLY_S
    if not prose_on(comments, ("main", last)):
        f.note("the tail's last move %s has no comment — that ply is the reward "
               "(PGNLINES.md B7.6)" % mainline[last]["san"])
    if len(spoken_mid) > 1:
        f.note("%d tail plies speak before the reward (%s) — a tail is silent "
               "except its last ply and at most one explaining comment "
               "(PGNLINES.md B7.6)" % (len(spoken_mid), ", ".join(spoken_mid)))
    if seconds > TAIL_MAX_SECONDS:
        f.note("the tail takes about %.0f s to watch (%d plies) — aim for well "
               "under %d; make the plies silent, or start the lesson closer to "
               "its payoff (PGNLINES.md B7.6)" % (seconds, len(tail), TAIL_MAX_SECONDS))
    unreachable = sum(1 for v in variations
                      if v["parent"] and v["parent"][0] == "main"
                      and v["parent"][1] > tail_at)
    if unreachable:
        f.note("%d sideline(s) on tail moves can never be reached — the app "
               "plays the tail itself (PGNLINES.md C15.1 rule 7)" % unreachable)
    return tail_at


def check_variations(variations, mainline, side, opening_side, comments, tail_at, f):
    """Sidelines must hang off the player's moves, speak, and show a continuation.

    Two different faults get counted here, and they are not the same thing:

      no continuation - the sideline is a single ply. Allowed only when the move
                        loses on the spot (PGNLINES.md C15.3), so this is a count
                        for the author to read, not a warning.
      SILENT          - the sideline's first move carries no comment at all. The
                        app then narrates it itself, in a flat register nobody
                        else in the file uses, and draws a yellow arrow at the
                        move the player just got wrong. Always a defect
                        (PGNLINES.md C15.1 rule 6, C15.4).

    Sidelines on tail moves (index > tail_at) are unreachable, so they are
    counted by check_tail and skipped here.

    Returns (stub, silent, lengths) — lengths is one ply count per sideline,
    for the quantisation note in main().
    """
    stub = silent = 0
    lengths = []
    for v in variations:
        parent = v["parent"]
        if parent is None or parent[0] != "main":
            f.warn("a sideline is not attached to a mainline move")
            continue
        idx = parent[1]
        if v["plies"]:
            lengths.append(len(v["plies"]))
        if tail_at is not None and idx > tail_at:
            continue
        if mover(idx, opening_side) != side:
            f.warn("sideline on the opponent's move %s is parsed and then "
                   "unreachable — the app always plays the mainline for the "
                   "opponent (PGNLINES.md C15.1 rule 1)" % mainline[idx]["san"])
        if not v["plies"]:
            continue
        if len(v["plies"]) <= 1:
            stub += 1

        # A comment for the first ply sits between that ply and the next one --
        # or the closing ')' when the sideline is a single move.
        first = v["plies"][0]
        limit = v["plies"][1]["pos"] if len(v["plies"]) > 1 else v.get("end", len(mainline))
        if not any(first["pos"] < c["start"] < limit for c in comments):
            silent += 1
            f.warn("sideline %s is silent on its first move: the app speaks its "
                   "own stock line and draws a yellow arrow at the move the "
                   "player just got wrong. A verdict on the LAST ply does not "
                   "fix this (PGNLINES.md C15.4)" % first["san"])

    # Two siblings on the same move whose first plies share a from/to square pair
    # are indistinguishable, but from/to needs a board — parse_check.sh does that.
    by_parent = {}
    for v in variations:
        by_parent.setdefault(v["parent"], []).append(v)
    for parent, group in by_parent.items():
        firsts = [v["plies"][0]["san"] for v in group if v["plies"]]
        dupes = set(s for s in firsts if firsts.count(s) > 1)
        for san in dupes:
            f.warn("two sidelines on the same move both start with %s — only the "
                   "first is reachable (PGNLINES.md C15.1 rule 3)" % san)
    return stub, silent, lengths


def check_ending(mainline, comments, side, opening, tail_at, f):
    """Where the line ends and what is heard there (PGNLINES.md B7.6).

    The last comment is the reward: it must be the player's, it must exist, and
    it must describe the board rather than promise what comes next. Along the
    way, every other move should speak too (B7.5); tail plies are check_tail's.

    Returns the row for the endings table, or None when there is no mainline.
    """
    if not mainline:
        return None
    last = len(mainline) - 1
    last_by = "player" if mover(last, opening) == side else "opponent"
    last_comments = comments_on(comments, ("main", last))
    last_prose = prose_on(comments, ("main", last))
    flags = []

    if last_by == "opponent":
        msg = ("the line ends on the opponent's move %s, so the reward belongs "
               "on the player's last move (PGNLINES.md B7.6)" % mainline[last]["san"])
        if not any("[%" in c["text"] for c in last_comments):
            msg += " — and with no shape it is cut off after about a second"
        f.warn(msg)
        flags.append("OPP")

    m = RE_PROMISE.search(last_prose)
    if m:
        f.note("the last comment promises the future ('%s') instead of describing "
               "the board — run the line to the payoff (PGNLINES.md B7.6): %r"
               % (m.group(0), last_prose[:60]))
        flags.append("PROMISE")

    player_plies = [i for i in range(len(mainline)) if mover(i, opening) == side]
    if player_plies:
        i = player_plies[-1]
        if not prose_on(comments, ("main", i)):
            f.warn("the last player move %s has no comment, so the reward is "
                   "never heard (PGNLINES.md B7.6)" % mainline[i]["san"])
            flags.append("SILENT")
        if len(player_plies) == 1 and not mainline[i]["san"].endswith("#"):
            f.note("a one-ply game, and %s is not a mate — the line should run "
                   "until the payoff is on the board (PGNLINES.md B7.6)"
                   % mainline[i]["san"])

    stop = last if tail_at is None else tail_at
    silent_player = [mainline[i]["san"] for i in player_plies
                     if i <= stop and i != player_plies[-1]
                     and not prose_on(comments, ("main", i))]
    silent_opp = [mainline[i]["san"] for i in range(stop + 1)
                  if mover(i, opening) != side
                  and not prose_on(comments, ("main", i))]
    if silent_player:
        f.note("%d player move(s) with no comment (%s) — every player move says "
               "why (PGNLINES.md B7.5)"
               % (len(silent_player), ", ".join(silent_player[:6])))
    if silent_opp:
        f.note("%d opponent move(s) with no comment (%s) — every opponent move "
               "says what he did, the set-up move included (PGNLINES.md B7.5)"
               % (len(silent_opp), ", ".join(silent_opp[:6])))

    return {"last_san": mainline[last]["san"], "last_by": last_by,
            "last_prose": last_prose, "flags": flags}


def check_role(tags, mainline, comments, side, opening, tail_at, f):
    """[Role] and [IntendedResult] are read by the tools, not the app (C11).
    The role says what the hints and the ending must look like (B7.3, B7.4)."""
    role = tags.get("Role")
    if role is None:
        f.warn("no [Role] tag (PGNLINES.md C11)")
    elif role not in ROLES:
        f.warn('[Role "%s"] — only teaching, review and exercise '
               "(PGNLINES.md C11)" % role)
    intended = tags.get("IntendedResult")
    if intended is not None and intended not in INTENDED_RESULTS:
        f.warn('[IntendedResult "%s"] — only win and draw (PGNLINES.md C11)' % intended)

    opening_comments = comments_on(comments, None)
    opening_prose = prose_on(comments, None)
    if RE_ROLE_SPOKEN.match(opening_prose):
        f.warn("the role is spoken aloud (%r) — it is a tag, never a word in "
               "the comment (PGNLINES.md B7.5)" % opening_prose[:40])

    stop = len(mainline) - 1 if tail_at is None else tail_at
    points = [i for i in range(stop + 1) if mover(i, opening) == side]

    def before(i):
        """The comment(s) on the board while the player decides ply i."""
        return opening_comments if i == 0 else comments_on(comments, ("main", i - 1))

    yellow = [i for i in points
              if any(code[0] == "Y" for c in before(i)
                     for _, code in shape_codes(c["text"]))]
    if role == "teaching" and points and not yellow:
        f.note("a teaching game with no yellow arrow before any player move "
               "(PGNLINES.md B7.4)")
    if role == "exercise":
        if yellow:
            f.warn("an exercise draws a yellow hint at a player move (%s) "
                   "(PGNLINES.md B7.4)"
                   % ", ".join(mainline[i]["san"] for i in yellow[:4]))
        if points:
            first = points[0]
            san = mainline[first]["san"]
            dest = destination(san)
            setup = list(opening_comments)
            if first > 0:
                setup += comments_on(comments, ("main", 0))
            hits = [code for c in setup for _, code in shape_codes(c["text"])
                    if len(code) in (3, 5) and code[-2:] == dest]
            if dest and hits:
                f.warn("the set-up draws the answer: %s marks %s, where the first "
                       "player move %s lands (PGNLINES.md B7.3)"
                       % (", ".join(hits), dest, san))

    if intended == "draw":
        main_comments = [c for c in comments if c["move"] and c["move"][0] == "main"]
        last_prose = prose(main_comments[-1]["text"]) if main_comments else ""
        if not RE_DRAW.search(last_prose):
            f.note('[IntendedResult "draw"] but the last comment never says draw, '
                   "drawn or stalemate — the word is spoken (PGNLINES.md B7.6)")


def check_layout(movetext_lines, f):
    """The moves must stay on one physical line; the opening comment may have
    its own line above them (PGNLINES.md C10 rule 2)."""
    filled = [i for i, ln in enumerate(movetext_lines) if ln.strip()]
    if not filled:
        f.error("the game has no movetext")
        return ""
    if any(not movetext_lines[i].strip() for i in range(filled[0], filled[-1] + 1)):
        f.error("a blank line inside the movetext cuts the game in half at the "
                "']\\n\\n' header split (PGNLINES.md C10)")

    body = [movetext_lines[i] for i in filled]
    moves = body[1:] if (len(body) > 1 and body[0].lstrip().startswith("{")
                         and "}" in body[0]) else body
    if len(moves) > 1:
        f.warn("the moves span %d lines — keep them on one physical line "
               "(PGNLINES.md C10 rule 3)" % len(moves))
    return " ".join(body)


def check_opening_comment(raw, movetext, f):
    """The opening comment is found by the regex ']\\n\\n{' (loadpuzzles.js:46)."""
    if not movetext.lstrip().startswith("{"):
        return
    if not re.search(r"\]\n\n\{", raw):
        f.warn("the opening comment does not sit at the first character after the "
               "one blank line, so it is never spoken (PGNLINES.md C10 rule 2)")


APP_ROOT = os.environ.get("PGN_APP_ROOT",
                          "/home/luis/Sync/projects/chessboxing-smoother")


STUDY_LEVELS = ("beginner", "intermediate", "advanced")

# beginners/ intermediate/ advanced/ -> the playlist word for that level.
FOLDER_LEVEL = {"beginners": "beginner",
                "intermediate": "intermediate",
                "advanced": "advanced"}


def parse_playlist(text):
    """The app's playlist format: `Display Name:file.pgn:level` (playlist.js).

    Split on the FIRST colon, so the name may not contain one; the level comes
    off the END and is anchored on `.pgn`, so the filename may. The level is
    optional in the format, and a line with no colon at all is the filename.
    Blank lines and `#` comments are skipped.

    Returns {filename: level or None}.
    """
    listed = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        rest = line.split(":", 1)[1].strip() if ":" in line else line
        level = None
        m = re.match(r"^(.*\.pgn)\s*:\s*([A-Za-z]+)$", rest, re.I)
        if m:
            rest = m.group(1).strip()
            if m.group(2).lower() in STUDY_LEVELS:
                level = m.group(2).lower()
        if rest.lower().endswith(".pgn"):
            listed[rest] = level
    return listed


def playlist_entry(path):
    """Has this file been shipped, is it listed, and is it classified?

    Authoring happens in beginners/ intermediate/ advanced/; shipping copies the
    file into the app's pgns/, usually under a different name
    (beginners/tactics1.pgn -> tactics-beginner.pgn). So a basename match is not
    enough -- match on content, which is what "shipped" actually means.

    Returns None when there is nothing to say (not shipped, or no app checkout),
    else (listed, level, expected_level): `listed` False means the file never
    plays; `level` is the playlist's classification, or None when the line
    carries none -- which keeps the study out of every level preset (A2).
    """
    shipped_dir = os.path.join(APP_ROOT, "pgns")
    playlist = os.path.join(APP_ROOT, "playlist.txt")
    if not os.path.isdir(shipped_dir) or not os.path.exists(playlist):
        return None
    try:
        with open(path, "rb") as fh:
            mine = fh.read()
    except OSError:
        return None

    shipped_as = None
    for name in os.listdir(shipped_dir):
        if not name.endswith(".pgn"):
            continue
        try:
            with open(os.path.join(shipped_dir, name), "rb") as fh:
                if fh.read() == mine:
                    shipped_as = name
                    break
        except OSError:
            continue
    if shipped_as is None:
        return None

    with open(playlist, encoding="utf-8") as fh:
        listed = parse_playlist(fh.read())
    folder = os.path.basename(os.path.dirname(os.path.abspath(path)))
    return (shipped_as in listed, listed.get(shipped_as), FOLDER_LEVEL.get(folder))


def validate_file(path):
    f = Findings()
    with open(path, encoding="utf-8") as fh:
        text = fh.read().replace("\r", "")

    games = split_games(text)
    if not games:
        f.error("no [Event ] tag: the app loads zero puzzles from this file")
        return f, []

    stats = []
    for number, (_, raw) in enumerate(games, 1):
        f.where = "game %d: " % number
        tags, _, movetext_lines = split_header(raw, f)
        label = tags.get("Event", "no Event tag")
        chapter = tags.get("ChapterName")
        if chapter and chapter not in label:
            label = "%s / %s" % (label, chapter)
        f.where = "game %d (%s): " % (number, label)
        side = check_headers(tags, f)
        movetext = check_layout(movetext_lines, f)
        check_opening_comment(raw, movetext, f)

        mainline, variations, comments = scan_movetext(movetext, f)
        opening = first_side(tags)
        check_comments(movetext, comments, f)
        tail_at = check_tail(mainline, variations, comments, side, opening, f)
        stub, silent, lengths = check_variations(variations, mainline, side,
                                                 opening, comments, tail_at, f)
        ending = check_ending(mainline, comments, side, opening, tail_at, f)
        check_role(tags, mainline, comments, side, opening, tail_at, f)

        # Decision points stop where the tail starts: after [%tail] the app
        # plays the line itself, and a sideline there is never reached.
        stop = len(mainline) - 1 if tail_at is None else tail_at
        points = [i for i in range(stop + 1) if mover(i, opening) == side]
        covered = set(v["parent"][1] for v in variations
                      if v["parent"] and v["parent"][0] == "main")
        stats.append({
            "event": tags.get("Event", "?"),
            "plies": len(mainline),
            "points": len(points),
            "covered": len([p for p in points if p in covered]),
            "sidelines": len(variations),
            "stub": stub,
            "silent": silent,
            "lengths": lengths,
            "tail": tail_at,
            "ending": ending,
        })
    f.where = ""
    return f, stats


def main(argv):
    paths = argv[1:]
    if not paths:
        print(__doc__)
        return 2

    failed = False
    for path in paths:
        f, stats = validate_file(path)
        print("== %s — %d game(s), %d error(s), %d warning(s), %d note(s)"
              % (path, len(stats), len(f.errors), len(f.warns), len(f.notes)))
        for e in f.errors:
            print("   ERROR %s" % e)
        for w in f.warns:
            print("   warn  %s" % w)
        for n in f.notes:
            print("   note  %s" % n)
        entry = playlist_entry(path)
        if entry is not None:
            listed, level, expected = entry
            if not listed:
                print("   warn  no playlist.txt line points at this file, so it "
                      "never plays (PGNLINES.md A2)")
            elif level is None:
                print("   warn  its playlist line carries no level, so no level "
                      "preset can ever serve it (PGNLINES.md A2)")
            elif expected and level != expected:
                print("   warn  its playlist line says %s but the file is "
                      "authored in %s/ (PGNLINES.md A2)"
                      % (level, [k for k, v in FOLDER_LEVEL.items()
                                 if v == expected][0]))
        if f.long_comments:
            print("   note  %d comment(s) above the style target of %d — two full "
                  "sentences; the board is held while they are spoken "
                  "(PGNLINES.md C13.2)" % (f.long_comments, STYLE_TARGET))
        if stats:
            points = sum(s["points"] for s in stats)
            covered = sum(s["covered"] for s in stats)
            sidelines = sum(s["sidelines"] for s in stats)
            stub = sum(s["stub"] for s in stats)
            silent = sum(s["silent"] for s in stats)
            tails = sum(1 for s in stats if s["tail"] is not None)
            pct = (100 * covered // points) if points else 0
            print("   %d player decision points, %d with a sideline (%d%%); "
                  "%d sidelines, %d with no continuation; %d game(s) with a "
                  "[%%tail] (PGNLINES.md B8, C15)"
                  % (points, covered, pct, sidelines, stub, tails))
            # None of what follows is an error -- each is a judgement call the
            # author has to make looking at the position. Say so, because a
            # clean bill of health next to 51% coverage reads as approval
            # (PGNLINES.md D18).
            if points and pct < 80:
                print("   note  coverage under 80%%: at %d decision point(s) a "
                      "sensible move locks the board. Openings reviewed from "
                      "memory need the densest cover (PGNLINES.md B8)"
                      % (points - covered))
            if silent:
                print("   note  %d of %d sidelines say nothing when the player "
                      "enters them (PGNLINES.md C15.4)" % (silent, sidelines))
            if stub and sidelines:
                print("   note  %d sideline(s) stop after one ply — right only "
                      "when the move loses on the spot; a tactic usually needs "
                      "the punishing reply AND the move that collects "
                      "(PGNLINES.md C15.3)" % stub)

            # Verbatim repeats: no two comments in a file identical (C13.3 rule 4).
            repeats = [(t, k) for t, k in f.prose_seen.most_common() if k > 1]
            if repeats:
                top = ", ".join("'%s' ×%d" % (shorten(t), k) for t, k in repeats[:3])
                print("   note  %d comment(s) repeat another verbatim (top: %s) "
                      "(PGNLINES.md C13.3)"
                      % (sum(k - 1 for _, k in repeats), top))

            # Quantisation: lengths decided by the file being imitated, not by
            # the line (C15.3 "beware of matching the file you are imitating").
            lengths = [n for s in stats for n in s["lengths"]]
            if len(lengths) >= 10:
                k, count = collections.Counter(lengths).most_common(1)[0]
                if count * 100 >= 70 * len(lengths):
                    print("   note  %d%% of the %d sidelines are exactly %d "
                          "plies — decide each length by the line "
                          "(PGNLINES.md C15.3)"
                          % (100 * count // len(lengths), len(lengths), k))
            if len(stats) >= 6:
                k, count = collections.Counter(
                    s["points"] for s in stats).most_common(1)[0]
                if count * 100 >= 70 * len(stats):
                    print("   note  %d%% of the %d games have exactly %d "
                          "decision points — decide where the decisions end "
                          "by the position, not by the games beside it "
                          "(PGNLINES.md B8.1, C15.3)"
                          % (100 * count // len(stats), len(stats), k))

            # The endings table: read every row. PROMISE means the line
            # stopped before the payoff (B7.6); the check line there is that
            # the table shows none.
            for number, s in enumerate(stats, 1):
                e = s["ending"]
                if e is None:
                    continue
                print('   ending  game %-2d  last=%-7s  by=%-8s  %-18s  "%s"'
                      % (number, e["last_san"], e["last_by"],
                         " ".join(e["flags"]) or "-", e["last_prose"][:70]))
        if f.errors:
            failed = True
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

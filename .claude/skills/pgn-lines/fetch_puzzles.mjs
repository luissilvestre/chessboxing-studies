#!/usr/bin/env node
// Download themed tactical puzzles from lichess as DRAFT candidates.
//
//   node .claude/skills/pgn-lines/fetch_puzzles.mjs --theme fork --max-rating 1100 --count 24
//
// Why this exists (PGNLINES.md B8.2): a tactics block needs exercise positions
// that genuinely turn on one motif, and inventing them by hand is how you end up
// with positions that fail the motif test. Lichess has millions, tagged by theme
// and rated, so draw from there -- and draw MORE than you need, because most
// candidates will not survive screening.
//
// This script does the mechanical half only. It fetches, replays each game to
// the puzzle position, converts the solution to SAN, and writes a draft .pgn you
// can edit. It CANNOT tell you whether a puzzle is really about the motif: a
// lichess theme tag is crowd-derived and often generous. The motif test in
// B8.2 -- take the key piece or line off the board and check the winning move
// stops working -- is still yours to run, on every candidate you keep.
//
// The API knowledge lives in the app's lichessPuzzles.js and is reused here
// rather than copied: difficulty is relative to the requester (1500 anonymous)
// with no absolute rating filter, so a rating window is honoured by rejection
// sampling; requests go out sequentially; a 429 means wait a full minute.

import fs from "node:fs";
import os from "node:os";
import path from "node:path";

const APP_ROOT = process.env.PGN_APP_ROOT
  || "/home/luis/Sync/projects/chessboxing-smoother";

// ---------------------------------------------------------------------------

function usage(msg) {
  if (msg) console.error("fetch_puzzles: " + msg + "\n");
  console.error(`Download themed lichess puzzles as draft trainer games.

  node fetch_puzzles.mjs --theme <slug> [options]

  --theme <slug>        lichess theme, e.g. fork pin skewer discoveredAttack
                        backRankMate deflection interference (required)
  --count <n>           candidates to fetch (default 20). Ask for 3x what you
                        intend to ship -- screening rejects most of them
  --min-rating <n>      inclusive (default none)
  --max-rating <n>      inclusive (default 1200; low ratings are simpler ideas)
  --out <file.pgn>      where to write the draft (default drafts/<theme>.pgn)
  --exclude-theme <s>   reject candidates carrying this theme; repeatable.
                        Use it to keep a fork block free of mateIn1, etc.
  --max-themes <n>      reject candidates tagged with more than n themes
                        (default 6). A puzzle with many themes is a muddy one
  --delay <ms>          pause between requests (default 300). Raise it if
                        lichess starts answering 429
  --rate-waits <n>      how many 429 waits to sit out before giving up
                        (default 1; each wait is a full minute)
  --no-dedupe           skip the check against positions already in this folder
  --list-themes         print the themes the app knows about and exit
`);
  process.exit(msg ? 2 : 0);
}

function parseArgs(argv) {
  const o = { count: 20, maxRating: 1200, minRating: null, out: null,
              theme: null, excludeThemes: [], maxThemes: 6, dedupe: true,
              delayMs: 300, rateWaits: 1 };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    const next = () => {
      if (i + 1 >= argv.length) usage(`${a} needs a value`);
      return argv[++i];
    };
    if (a === "--theme") o.theme = next();
    else if (a === "--count") o.count = parseInt(next(), 10);
    else if (a === "--min-rating") o.minRating = parseInt(next(), 10);
    else if (a === "--max-rating") o.maxRating = parseInt(next(), 10);
    else if (a === "--out") o.out = next();
    else if (a === "--exclude-theme") o.excludeThemes.push(next());
    else if (a === "--max-themes") o.maxThemes = parseInt(next(), 10);
    else if (a === "--delay") o.delayMs = parseInt(next(), 10);
    else if (a === "--rate-waits") o.rateWaits = parseInt(next(), 10);
    else if (a === "--no-dedupe") o.dedupe = false;
    else if (a === "--list-themes") o.listThemes = true;
    else if (a === "-h" || a === "--help") usage();
    else usage(`unknown option ${a}`);
  }
  return o;
}

/** Stage the app's ES modules where Node will load them as modules. */
async function loadAppModules() {
  for (const f of ["chess.js", "lichessPuzzles.js"]) {
    if (!fs.existsSync(path.join(APP_ROOT, f))) {
      console.error(`fetch_puzzles: no ${f} at ${APP_ROOT}`);
      console.error("Set PGN_APP_ROOT to the app checkout.");
      process.exit(2);
    }
  }
  const work = fs.mkdtempSync(path.join(os.tmpdir(), "pgnfetch-"));
  process.on("exit", () => fs.rmSync(work, { recursive: true, force: true }));
  for (const f of ["chess.js", "lichessPuzzles.js"]) {
    fs.copyFileSync(path.join(APP_ROOT, f), path.join(work, f));
  }
  fs.writeFileSync(path.join(work, "package.json"), '{"type":"module"}\n');
  const chess = await import(path.join(work, "chess.js"));
  const puzzles = await import(path.join(work, "lichessPuzzles.js"));
  return { Chess: chess.Chess, lp: puzzles, work };
}

/** Placement fields of every FEN already used under this folder. */
function usedPlacements(root) {
  const seen = new Map();
  const walk = (dir) => {
    for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
      if (e.name.startsWith(".")) continue;
      const p = path.join(dir, e.name);
      if (e.isDirectory()) walk(p);
      else if (e.name.endsWith(".pgn")) {
        const text = fs.readFileSync(p, "utf8");
        for (const m of text.matchAll(/\[FEN "([^"]+)"\]/g)) {
          seen.set(m[1].split(" ")[0], path.relative(root, p));
        }
      }
    }
  };
  walk(root);
  return seen;
}

const analysisUrl = (fen) =>
  "https://lichess.org/analysis/" + fen.replace(/ /g, "_");

/**
 * Turn one normalised lichess puzzle into the pieces of a trainer game.
 *
 * Lichess hands us the game up to and including the opponent's last move, after
 * which the solver is to move. That last move is exactly the "one auto-played
 * opponent move" PGNLINES.md C11 asks for: it shows why the position arose and
 * gives the set-up comment somewhere to live. So the [FEN] we emit is the
 * position BEFORE it, and the movetext opens with it.
 */
function toDraft(p, Chess) {
  const sans = p.gameSan;
  const board = new Chess();
  for (let i = 0; i < sans.length - 1; i++) {
    if (!board.move(sans[i])) throw new Error(`replay failed at ${sans[i]}`);
  }
  const setupFen = board.fen();
  const setupSan = sans[sans.length - 1];
  if (!board.move(setupSan)) throw new Error(`set-up move ${setupSan} illegal`);

  const solutionSan = [];
  for (const mv of p.solution) {
    const played = board.move({ from: mv.from, to: mv.to,
                                promotion: mv.promotion || undefined });
    if (!played) throw new Error(`solution move ${mv.from}${mv.to} illegal`);
    solutionSan.push(played.san);
  }
  return { setupFen, setupSan, solutionSan, finalFen: board.fen() };
}

/** Movetext with correct numbering, opening on the set-up move. */
function movetext(setupFen, setupSan, solutionSan) {
  const [, stm, , , , fullStr] = setupFen.split(" ");
  let no = parseInt(fullStr, 10);
  let white = stm === "w";
  const out = [];
  for (const san of [setupSan, ...solutionSan]) {
    if (white) out.push(`${no}. ${san}`);
    else { out.push(out.length === 0 ? `${no}... ${san}` : san); no++; }
    white = !white;
  }
  return out.join(" ");
}

// ---------------------------------------------------------------------------

const opts = parseArgs(process.argv.slice(2));
const { Chess, lp } = await loadAppModules();

if (opts.listThemes) {
  console.log(lp.KNOWN_THEMES.join("\n"));
  process.exit(0);
}
if (!opts.theme) usage("--theme is required");
if (!lp.KNOWN_THEMES.includes(opts.theme)) {
  console.error(`fetch_puzzles: "${opts.theme}" is not a theme the app knows.`);
  console.error("Run with --list-themes to see them. Continuing anyway.\n");
}

const root = process.cwd();
const used = opts.dedupe ? usedPlacements(root) : new Map();
const outPath = opts.out || path.join("drafts", `${opts.theme}.pgn`);

console.error(`Asking lichess for ${opts.count} "${opts.theme}" puzzles`
  + ` rated ${opts.minRating ?? "-"}..${opts.maxRating ?? "-"}`
  + ` (difficulty bucket: ${lp.difficultyFor(opts.minRating, opts.maxRating)})`);
console.error("Requests go out one at a time, as lichess asks. This takes a while.\n");

const res = await lp.fetchRandomPuzzles({
  count: opts.count,
  theme: opts.theme,
  minRating: opts.minRating,
  maxRating: opts.maxRating,
  delayMs: opts.delayMs,
  maxRateLimitWaits: opts.rateWaits,
  onProgress: ({ found, wanted, attempts }) => {
    process.stderr.write(`\r  ${found}/${wanted} kept, ${attempts} requests`);
  },
});
process.stderr.write("\n\n");

for (const p of res.problems || []) console.error(`  note: ${p.why} — ${p.detail}`);
if (!res.complete) {
  console.error(`  only ${res.puzzles.length} of ${opts.count} found`
    + ` (rejected: ${JSON.stringify(res.rejected)})\n`);
}

const rows = [];
const games = [];
for (const p of res.puzzles) {
  let d;
  try { d = toDraft(p, Chess); }
  catch (e) { rows.push({ p, flags: [`REPLAY FAILED: ${e.message}`] }); continue; }

  const flags = [];
  if (!p.themes.includes(opts.theme)) flags.push(`missing "${opts.theme}"`);
  for (const x of opts.excludeThemes) {
    if (p.themes.includes(x)) flags.push(`has "${x}"`);
  }
  if (p.themes.length > opts.maxThemes) flags.push(`${p.themes.length} themes`);
  const dupe = used.get(d.setupFen.split(" ")[0]);
  if (dupe) flags.push(`position already in ${dupe}`);
  if (d.solutionSan.length === 1) flags.push("one move only");

  rows.push({ p, d, flags });
  if (flags.length) continue;

  const side = p.side === "white" ? "1-0" : "0-1";
  games.push(
`[Event "TODO ${opts.theme}: ${p.id}"]
[Result "${side}"]
[Variant "Standard"]
[FEN "${d.setupFen}"]
[SetUp "1"]
[Site "${analysisUrl(d.setupFen)}"]

{ TODO set-up comment. Lichess ${p.id}, rated ${p.rating}, themes: ${p.themes.join(" ")} }
${movetext(d.setupFen, d.setupSan, d.solutionSan)} ${side}`);
}

// The screening table. Everything below is for a human to read.
const w = (s, n) => String(s).padEnd(n).slice(0, n);
console.log(`${w("id", 8)} ${w("rating", 6)} ${w("plies", 5)} ${w("themes", 46)} verdict`);
console.log("-".repeat(100));
for (const r of rows) {
  console.log(`${w(r.p.id, 8)} ${w(r.p.rating, 6)} `
    + `${w(r.d ? r.d.solutionSan.length : "-", 5)} `
    + `${w(r.p.themes.join(" "), 46)} `
    + (r.flags.length ? "SCREEN OUT: " + r.flags.join("; ") : "candidate"));
}

fs.mkdirSync(path.dirname(outPath), { recursive: true });
fs.writeFileSync(outPath, games.join("\n\n\n") + (games.length ? "\n" : ""));

console.log(`\n${games.length} candidate(s) written to ${outPath}`
  + `, ${rows.length - games.length} screened out.`);
console.log(`
These are DRAFTS, not games. Before any of them ships:
  - run the motif test on each one (PGNLINES.md B8.2). A lichess theme tag is
    not evidence the position needs the motif.
  - confirm one good move at every player move with a top-five multi-PV (B8.2).
  - check no two survivors are the same puzzle (A5).
  - replace every TODO comment, and add the sidelines a player would try
    (C15.2) with continuations that run until the tactic resolves (C15.3).
  - validate: validate.py, then parse_check.sh.`);

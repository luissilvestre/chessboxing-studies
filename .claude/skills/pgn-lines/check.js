// Load .pgn files through the app's own parser and report what the trainer
// would actually get. Run it via parse_check.sh, which stages the ES modules
// where Node can import them.
//
//   node check.js [-v] file.pgn [file.pgn ...]
//
// Exits 1 if a file loads fewer puzzles than it has [Event ] tags. The live app
// wraps each game in try/catch, so one unparsable game is skipped and the rest
// still load -- the loss is local, not a cascade. It is still a hard failure
// here: a game the app silently drops is a game the player never sees, and its
// [Event] name is printed so it can be found.
import fs from 'fs';
import path from 'path';
import { PuzzleTrainer } from './puzzleTrainer.js';
import { loadpgn } from './loadpuzzles.js';

const out = console.log;
const args = process.argv.slice(2);
const verbose = args.includes('-v');
const files = args.filter((a) => a !== '-v');
let failed = false;

const other = (s) => (s === 'white' ? 'black' : 'white');

for (const file of files) {
  const text = fs.readFileSync(file, 'utf8');
  const expected = (text.match(/\[Event\s/g) || []).length;
  const trainer = new PuzzleTrainer();
  trainer.collection = [];

  let error = null;
  // loadpgn() narrates every game to console.log, and names each game it had to
  // skip on console.warn. Swallow the first, keep the second -- it is the only
  // place the dropped game's [Event] appears.
  const skipped = [];
  const warn = console.warn;
  console.log = () => {};
  console.warn = (...a) => skipped.push(a.map(String).join(' '));
  try {
    loadpgn(trainer, text);
  } catch (e) {
    error = e;
  } finally {
    console.log = out;
    console.warn = warn;
  }

  const puzzles = trainer.collection;
  out(`== ${path.basename(file)} — ${puzzles.length} of ${expected} game(s) loaded`);
  if (error) {
    out(`   ERROR ${error.message || error}`);
    failed = true;
  }
  // Name the games that did not survive. loadpgn() skips an unparsable game and
  // keeps going, so the survivors' [Event] tags minus the file's [Event] tags is
  // exactly the list of casualties.
  if (puzzles.length !== expected) {
    out(`   ERROR ${expected - puzzles.length} game(s) failed to load and were `
      + `skipped; the rest still play`);
    skipped.forEach((msg) => out(`      ${msg}`));
    failed = true;
  }

  puzzles.forEach((p, n) => {
    const fen = p.initialPosition || '';
    const opening = fen && fen.split(' ')[1] === 'b' ? 'black' : 'white';
    const moverOf = (i) => (i % 2 === 0 ? opening : other(opening));
    const problems = [];

    p.moves.forEach((m, i) => {
      const alts = m[3] || [];
      if (alts.length && moverOf(i) !== p.side) {
        problems.push(`move ${i + 1} (${m[0]}${m[1]}) is the opponent's, so its `
          + `${alts.length} sideline(s) can never be reached`);
      }
      const seen = new Map();
      alts.forEach((alt) => {
        const key = alt[0][0] + alt[0][1];
        if (seen.has(key)) {
          problems.push(`move ${i + 1} has two sidelines starting ${key} — only `
            + `the first is reachable`);
        }
        seen.set(key, true);
        if (alt.length === 1) return;
      });
    });

    const sidelines = p.moves.reduce((a, m) => a + (m[3] ? m[3].length : 0), 0);
    // "no continuation" is a single-ply sideline; "silent" is one whose FIRST
    // ply carries no comment, which is what makes the app narrate it itself.
    // They are different faults and used to share the word "bare".
    const stub = p.moves.reduce(
      (a, m) => a + (m[3] || []).filter((alt) => alt.length === 1).length, 0);
    const silent = p.moves.reduce(
      (a, m) => a + (m[3] || []).filter((alt) => !(alt[0] && alt[0][2])).length, 0);
    out(`   puzzle ${n + 1}: player ${p.side}, ${p.moves.length} plies, `
      + `${sidelines} sideline(s) (${stub} with no continuation, ${silent} silent)`
      + (p.initialComment ? '' : ', no opening comment'));
    problems.forEach((msg) => {
      out(`      warn ${msg}`);
    });

    if (verbose) {
      p.moves.forEach((m, i) => {
        out(`      ${i + 1}. ${moverOf(i) === p.side ? '*' : ' '} ${m[0]}${m[1]}`
          + (m[2] ? `  "${m[2].replace(/\s+/g, ' ').trim().slice(0, 50)}"` : ''));
        (m[3] || []).forEach((alt) => {
          out(`           sideline: ${alt.map((v) => v[0] + v[1]).join(' ')}`);
        });
      });
    }
  });
}

process.exit(failed ? 1 : 0);

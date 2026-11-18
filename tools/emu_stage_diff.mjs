#!/usr/bin/env node
// Run the whole picture-processing stage list in om-emu, per picture mode,
// and compare the output blocks. Answers three questions about the stage 1
// patch:
//
//   1. How does the carrier mode (5) differ from Natural (2) on stock firmware?
//   2. What does the PEN-F change for COLOR (11) compared with Natural (2)?
//   3. Does the patch change exactly that on the E-M5 II, and nothing else?
//
//   node tools/emu_stage_diff.mjs
//
// Needs node 26, om-emu with E118 and E122 unpacked, and
// generated/stage1/main.bin. The job is this script's, not a camera's (see
// emu_color_check.mjs): these are the stages' answers to that job.
import { spawnSync } from 'node:child_process';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const EMU = path.join(ROOT, 'om-emu/emu');
const MAIN = path.join(ROOT, 'generated/stage1/main.bin');
const lab = (a) => (a - 0x10021020) >>> 0;

const STAGES = { E122: lab(0x604f8543), E118: lab(0x604e02c6) };
const COLOR_TABLE = { E122: 0x60622d74, E118: 0x60620f14 };
const C = 0, R = 0x1000, G = 0x2000, O = 0x5000;
const CHROMA = [76, 80];                        // chroma control word
const HSL = [[676, 966], [5172, 5212]];         // records + control, then LUT pointers
const LUT_POINTERS = 5172;

const le = (v, n) => Array.from({ length: n }, (_, i) => ((v >>> (8 * i)) & 0xff).toString(16).padStart(2, '0')).join('');
const sc = (o) => `scratch+${o}`;

async function child({ model, main, keys }) {
  const { openSession } = await import(path.join(EMU, 'host/session.mjs'));
  const s = await openSession({ model, say: () => {}, ...(main ? { main, loaded: 'off' } : {}) });
  const out = {};
  try {
    if (!s.first.ok) throw new Error(`session did not open: ${s.first.error}`);
    for (const key of keys) {
      const mem = [[sc(C + 4), `=${sc(R)}`], [sc(C + 8), `=${sc(G)}`], [sc(C + 12), `=${sc(O)}`],
        [sc(C + 48), le(key, 4)], [sc(C + 56), 'ffffffff'], [sc(R + 8), `0000${le(key, 2)}`],
        [sc(R + 996), le(5184, 2) + le(3888, 2) + le(5184, 2) + le(3888, 2)]];
      const r = s.input({ type: 'debug', op: 'call', fn: STAGES[model], regs: { a0: sc(C) }, scratch: 0x9000,
        restore: true, limit: 20000000, mem, read: [[sc(O), 0x2000], [sc(G), 0x3000]] });
      const d = r.debug ?? r;
      if (!d.ok || d.end !== 'return') throw new Error(`mode ${key}: ${JSON.stringify(d.error ?? d.end)}`);
      out[key] = { O: d.reads[0].hex, G: d.reads[1].hex, stubs: d.stubs.length };
    }
    console.log(JSON.stringify(out));
  } finally { s.close(); }
}

function run(q) {
  const r = spawnSync(process.execPath, [fileURLToPath(import.meta.url), '--child', JSON.stringify(q)], { encoding: 'utf8', maxBuffer: 1 << 28 });
  const line = r.stdout.trim().split('\n').filter((l) => l.startsWith('{')).at(-1);
  if (r.status !== 0 || !line) throw new Error(`${q.model}: ${(r.stderr || r.stdout).trim().split('\n').slice(-3).join(' | ')}`);
  return JSON.parse(line);
}

// Offsets at which two hex strings differ.
function differing(a, b) {
  const x = Buffer.from(a, 'hex'), y = Buffer.from(b, 'hex'), out = [];
  for (let i = 0; i < x.length; i++) if (x[i] !== y[i]) out.push(i);
  return out;
}
const within = (offsets, ranges) => offsets.every((o) => ranges.some(([lo, hi]) => o >= lo && o < hi));
const span = (offsets) => (offsets.length ? `${offsets.length} bytes, ${offsets[0]}..${offsets.at(-1)}` : 'none');
const pointers = (hex, table) => {
  const b = Buffer.from(hex, 'hex');
  return Array.from({ length: 10 }, (_, i) => b.readUInt32LE(LUT_POINTERS + 4 * i) - table);
};

function parent() {
  const penf = run({ model: 'E122', keys: [2, 11] });
  const stock = run({ model: 'E118', keys: [2, 5] });
  const patched = run({ model: 'E118', main: MAIN, keys: [2, 5] });
  let ok = true;
  const check = (text, cond) => { ok &&= cond; console.log(cond ? 'ok  ' : 'FAIL', text); };

  const d52 = differing(stock[5].O, stock[2].O);
  console.log('stock E-M5 II, mode 5 vs 2, output block:', span(d52));
  check('stock E-M5 II: mode 5 differs from mode 2 only in the chroma word', d52.length > 0 && within(d52, [CHROMA]) && stock[5].G === stock[2].G);

  const dPenf = differing(penf[11].O, penf[2].O);
  console.log('PEN-F, mode 11 vs 2, output block:', span(dPenf));
  check('PEN-F: COLOR differs from Natural only in the HSL records and LUT pointers', dPenf.length > 0 && within(dPenf, HSL) && penf[11].G === penf[2].G);

  const dPatch = differing(patched[5].O, stock[5].O);
  console.log('E-M5 II mode 5, patched vs stock, output block:', span(dPatch));
  check('patch: mode 5 changes only in the HSL records and LUT pointers', dPatch.length > 0 && within(dPatch, HSL) && patched[5].G === stock[5].G);
  check('patch: mode 2 output is identical to stock', patched[2].O === stock[2].O && patched[2].G === stock[2].G);

  const a = pointers(penf[11].O, COLOR_TABLE.E122), b = pointers(patched[5].O, COLOR_TABLE.E118);
  console.log('LUT pointers, offset from the COLOR table:', b.join(' '));
  check('patch: the ten LUT pointers sit at the PEN-F offsets inside the COLOR table',
    JSON.stringify(a) === JSON.stringify(b) && b.every((v) => v >= 336 && v < 3028));
  check('no lab hook answered in any call', [penf[2], penf[11], stock[2], stock[5], patched[2], patched[5]].every((x) => x.stubs === 0));
  process.exit(ok ? 0 : 1);
}

const i = process.argv.indexOf('--child');
if (i >= 0) await child(JSON.parse(process.argv[i + 1])); else parent();

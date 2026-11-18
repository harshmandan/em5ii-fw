#!/usr/bin/env node
// Call the picture-mode selector in om-emu on a job this script writes, and
// compare what the stage 1 patch produces with what the PEN-F produces.
//
//   node tools/emu_color_check.mjs
//
// Needs node 26, an om-emu checkout next to this repository's README with the
// E118 and E122 firmware unpacked, and generated/stage1/main.bin from
// tools/build_stage1.py.
//
// The job is this script's, not a camera's: zero except for the block
// pointers, the mode key, a flags word of all ones and the saturation steps.
// A real job holds more. So this shows that the ported builder computes the
// same records as the PEN-F for the same inputs, and that other modes take
// the stock path unchanged. It does not show what a camera's picture looks
// like, and it does not exercise the image processor.
import { spawnSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const EMU = path.join(ROOT, 'om-emu/emu');
const BUILD = path.join(ROOT, 'generated/stage1');

// The lab numbers the main block from 0x50000000; analysis addresses start at 0x60021020.
const lab = (a) => (a - 0x10021020) >>> 0;
const SELECTOR = { E122: lab(0x604f747f), E118: lab(0x604df257) };

// Job blocks inside the call's scratch, as om-emu's own stage tests lay them out.
const SIZE = 0x9000;
const C = 0, R = 0x1000, G = 0x2000, O = 0x5000, O_LEN = 0x2000;
const RECORDS = 676, RECORD_BYTES = 12 * 24, CONTROL = 964, DIRTY = 100;
const PENF_SAT = 1076;

const le = (v, n) => Array.from({ length: n }, (_, i) => ((v >>> (8 * i)) & 0xff).toString(16).padStart(2, '0')).join('');
const sc = (o) => `scratch+${o}`;
const sha = (hex) => createHash('sha256').update(Buffer.from(hex, 'hex')).digest('hex').slice(0, 16);

// ---- child: one model, one call ------------------------------------------
async function child({ model, main, key, sat }) {
  const { openSession } = await import(path.join(EMU, 'host/session.mjs'));
  const s = await openSession({ model, say: () => {}, ...(main ? { main, loaded: 'off' } : {}) });
  try {
    if (!s.first.ok) throw new Error(`session did not open: ${s.first.error}`);
    const mem = [
      [sc(C + 4), `=${sc(R)}`], [sc(C + 8), `=${sc(G)}`], [sc(C + 12), `=${sc(O)}`],
      [sc(C + 48), le(key, 4)], [sc(C + 56), 'ffffffff'], [sc(R + 8), `0000${le(key, 2)}`],
    ];
    if (sat) mem.push([sc(R + PENF_SAT), sat.map((v) => le(v & 0xff, 1)).join('')]);
    const r = s.input({ type: 'debug', op: 'call', fn: SELECTOR[model], regs: { a0: sc(C) }, scratch: SIZE,
      restore: true, limit: 2000000, mem,
      read: [[sc(O + RECORDS), RECORD_BYTES], [sc(O + CONTROL), 4], [sc(C + DIRTY), 4], [sc(O), O_LEN]] });
    const d = r.debug ?? r;
    if (!d.ok || d.end !== 'return') throw new Error(`call failed: ${JSON.stringify(d.error ?? d.end)}`);
    const [records, control, dirty, whole] = d.reads.map((x) => x.hex);
    console.log(JSON.stringify({ model, key, steps: d.steps, stubs: d.stubs.length, records, control, dirty, output: sha(whole) }));
  } finally { s.close(); }
}

// ---- parent ---------------------------------------------------------------
function run(q) {
  const r = spawnSync(process.execPath, [fileURLToPath(import.meta.url), '--child', JSON.stringify(q)],
    { encoding: 'utf8', maxBuffer: 1 << 26 });
  const line = r.stdout.trim().split('\n').filter((l) => l.startsWith('{')).at(-1);
  if (r.status !== 0 || !line) throw new Error(`${q.model} key ${q.key}: ${(r.stderr || r.stdout).trim().split('\n').slice(-3).join(' | ')}`);
  return JSON.parse(line);
}

function parent() {
  const build = JSON.parse(fs.readFileSync(path.join(BUILD, 'build.json'), 'utf8'));
  const main = path.join(BUILD, 'main.bin');
  const carrier = build.carrier_mode, sat = build.saturation;
  const other = carrier === 2 ? 3 : 2;
  let ok = true;
  const check = (text, cond) => { ok &&= cond; console.log(cond ? 'ok  ' : 'FAIL', text); };

  const penf = run({ model: 'E122', key: 11, sat });
  const penfZero = run({ model: 'E122', key: 11, sat: new Array(12).fill(0) });
  const patched = run({ model: 'E118', main, key: carrier });
  const stockCarrier = run({ model: 'E118', key: carrier });
  const patchedOther = run({ model: 'E118', main, key: other });
  const stockOther = run({ model: 'E118', key: other });

  console.log(`look ${build.look}: ${sat.join(' ')}; carrier mode ${carrier}`);
  check('PEN-F: the look changes the records (the input is live)', penf.records !== penfZero.records);
  check('patched E-M5 II, carrier mode: records equal the PEN-F COLOR records', patched.records === penf.records);
  check('patched E-M5 II, carrier mode: control word equals the PEN-F one', patched.control === penf.control);
  check('patched E-M5 II, carrier mode: dirty mask equals the PEN-F one', patched.dirty === penf.dirty);
  check('stock E-M5 II, carrier mode: records differ from the patched ones (the patch is live)', stockCarrier.records !== patched.records);
  check(`patched E-M5 II, mode ${other}: whole output block equals stock`, patchedOther.output === stockOther.output);
  check(`patched E-M5 II, mode ${other}: dirty mask equals stock`, patchedOther.dirty === stockOther.dirty);
  check('no lab hook answered in any call', [penf, patched, stockCarrier, patchedOther, stockOther].every((x) => x.stubs === 0));
  console.log(`instructions: PEN-F ${penf.steps}, patched carrier ${patched.steps}, stock carrier ${stockCarrier.steps}`);
  process.exit(ok ? 0 : 1);
}

const i = process.argv.indexOf('--child');
if (i >= 0) await child(JSON.parse(process.argv[i + 1])); else parent();

#!/usr/bin/env node
// Name the E-M5 II picture mode numbers by what the six-axis colour builder
// produces for each, compared with the PEN-F.
//
//   node tools/emu_mode_names.mjs
//
// Needs node 26 and om-emu with the E118 and E122 firmware unpacked.
//
// The PEN-F presets for Vivid, Muted and Portrait are published in
// oly_fw_analysis (docs/color/MODES.md). If a mode number gives one of those
// sets on the PEN-F, and the E-M5 II gives the same set for the same number
// apart from one fixed offset, the number carries that name on both.
//
// The job is this script's, not a camera's (see emu_color_check.mjs).
import { spawnSync } from 'node:child_process';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const EMU = path.join(ROOT, 'om-emu/emu');
const lab = (a) => (a - 0x10021020) >>> 0;

// Six-axis builder: the call at the same position in each body's stage list.
const BUILDER = { E122: lab(0x604f55de), E118: lab(0x604dd528) };
const KEYS = { E122: [1, 2, 3, 4, 5, 8, 10, 11], E118: [1, 2, 3, 4, 5, 8, 10] };
const OUT = 108;  // six saturation then six hue halfwords in the output block

// oly_fw_analysis docs/color/MODES.md: [saturation x6, hue x6]
const PUBLISHED = {
  Vivid: [18, 4, 24, 0, 8, 8, 0, 2, 4, -1, -6, 0],
  Muted: [-22, 4, -16, 0, 4, -8, 3, 0, -3, 9, 8, 10],
  Portrait: [14, 0, 0, 5, 0, 0, -1, 0, 2, -2, 0, 0],
  Natural: new Array(12).fill(0),
};

const le = (v, n) => Array.from({ length: n }, (_, i) => ((v >>> (8 * i)) & 0xff).toString(16).padStart(2, '0')).join('');
const sc = (o) => `scratch+${o}`;
const same = (a, b) => JSON.stringify(a) === JSON.stringify(b);

async function child(model) {
  const { openSession } = await import(path.join(EMU, 'host/session.mjs'));
  const s = await openSession({ model, say: () => {} });
  const C = 0, R = 0x1000, G = 0x2000, O = 0x5000, out = {};
  try {
    if (!s.first.ok) throw new Error(`session did not open: ${s.first.error}`);
    for (const key of KEYS[model]) {
      const mem = [[sc(C + 4), `=${sc(R)}`], [sc(C + 8), `=${sc(G)}`], [sc(C + 12), `=${sc(O)}`],
        [sc(C + 48), le(key, 4)], [sc(C + 56), 'ffffffff'], [sc(R + 8), `0000${le(key, 2)}`]];
      const r = s.input({ type: 'debug', op: 'call', fn: BUILDER[model], regs: { a0: sc(C) }, scratch: 0x9000,
        restore: true, limit: 2000000, mem, read: [[sc(O + OUT), 24]] });
      const d = r.debug ?? r;
      if (!d.ok || d.end !== 'return') throw new Error(`mode ${key}: ${JSON.stringify(d.error ?? d.end)}`);
      const b = Buffer.from(d.reads[0].hex, 'hex');
      out[key] = Array.from({ length: 12 }, (_, i) => b.readInt16LE(2 * i));
    }
    console.log(JSON.stringify(out));
  } finally { s.close(); }
}

function run(model) {
  const r = spawnSync(process.execPath, [fileURLToPath(import.meta.url), '--child', model], { encoding: 'utf8', maxBuffer: 1 << 26 });
  const line = r.stdout.trim().split('\n').filter((l) => l.startsWith('{')).at(-1);
  if (r.status !== 0 || !line) throw new Error(`${model}: ${(r.stderr || r.stdout).trim().split('\n').slice(-3).join(' | ')}`);
  return JSON.parse(line);
}

function parent() {
  const penf = run('E122'), em5 = run('E118');
  let ok = true;
  const check = (text, cond) => { ok &&= cond; console.log(cond ? 'ok  ' : 'FAIL', text); };
  const fmt = (v) => `sat ${v.slice(0, 6).join(',')} | hue ${v.slice(6).join(',')}`;

  console.log('mode  PEN-F                                        E-M5 II');
  for (const k of KEYS.E122) console.log(String(k).padEnd(5), fmt(penf[k]).padEnd(44), em5[k] ? fmt(em5[k]) : '-');

  const named = { 1: 'Vivid', 2: 'Natural', 3: 'Muted', 4: 'Portrait' };
  for (const [k, name] of Object.entries(named)) check(`PEN-F mode ${k} gives the published ${name} set`, same(penf[k], PUBLISHED[name]));

  // The E-M5 II sets equal the PEN-F sets plus one fixed offset.
  const offset = em5[2].map((v, i) => v - penf[2][i]);
  console.log('E-M5 II offset over the PEN-F:', fmt(offset));
  for (const k of [1, 2, 3, 4, 5, 8]) check(`E-M5 II mode ${k} = PEN-F mode ${k} + offset`, same(em5[k], penf[k].map((v, i) => v + offset[i])));
  check('E-M5 II mode 5 gives the same set as mode 2', same(em5[5], em5[2]));
  check('E-M5 II mode 8 gives the same set as mode 4', same(em5[8], em5[4]));
  check('PEN-F mode 11 (COLOR) gives the neutral set, as mode 2 does', same(penf[11], penf[2]));
  process.exit(ok ? 0 : 1);
}

const i = process.argv.indexOf('--child');
if (i >= 0) await child(process.argv[i + 1]); else parent();

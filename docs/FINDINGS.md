# Findings

All addresses are CPU analysis addresses in the decoded main block, base
`0x60021020`. E-M5 II means firmware 4.1, build 4100. PEN-F means 3.1, build
3101. Exact file hashes are in the [README](../README.md).

## Evidence levels

| Tag | Meaning |
| --- | --- |
| **B** | Byte comparison of stock files. Reproduced by a script in `tools/`. |
| **D** | Read from an objdump listing of the stock file. |
| **R** | Read from upstream documentation. Not re-checked here. |
| **I** | Inference from B and R. Not yet confirmed by disassembly. |

Nothing below was run in an emulator or on a camera.

## 1. Feasibility check (2026-11-18)

Question: does the E-M5 II have the 12-sector colour pipeline that the PEN-F
uses for COLOR profiles, or must it be built from nothing?

Answer: the data and the hardware path are there. The code that turns twelve
saturation values into a profile is not. The editor screen is mostly not.

### 1.1 The COLOR table is present and unused

`tools/find_color_table.py`

- The 3,028-byte COLOR table is at `0x60620f14`. It is byte-identical to the
  table on PEN-F (`0x60622d74`), E-P7 and OM-3. (B)
- It occurs once, in the main block only. (B)
- It sits in a run of tables of the same size. The five tables before it are
  each referenced from a pointer array at `0x6062de60`, stride `0x34`. The
  table after it is referenced from code at `0x604df314`. (B)
- No 32-bit pointer anywhere in the main block refers to the COLOR table. (B)
- The table after COLOR is identical on both bodies. (B)

| Slot | Address | Referenced from |
| ---: | --- | --- |
| −5 | `0x6061d3f0` | `0x6062de60`, `0x6062de94` |
| −4 | `0x6061dfc4` | `0x6062dec8` |
| −3 | `0x6061eb98` | `0x6062defc` |
| −2 | `0x6061f76c` | `0x6062df30` |
| −1 | `0x60620340` | `0x6062df64` |
| 0 | `0x60620f14` | nothing (COLOR) |
| +1 | `0x60621ae8` | `0x604df314` |

On the PEN-F the table before COLOR is Bleach Bypass II. (R) Slot −1 is then
likely the same art filter here. (I)

The PEN-F selector loads the COLOR table with an immediate at `0x604f7502`. (B)
The E-M5 II has no such load, so its selector has no COLOR case. (I)

### 1.2 The hardware path is the same

`tools/match_penf_code.py`

The PEN-F routine that writes the twelve records and LUTs to the image
processor has a near-exact twin at `0x6049d252`: 459 of 462 ten-byte windows
match at one displacement. (B)

The art filters use tables of this same layout. (B, by the pointer array above)
So the 12-sector hardware is exercised by stock firmware on this body. (I)

### 1.3 The profile builder is missing

| PEN-F piece | PEN-F address | Windows matched | Reading |
| --- | --- | ---: | --- |
| ISP writer | `0x604b5006` | 459 / 462 | Twin at `0x6049d252` |
| Table selector | `0x604f747f` | 79 / 233 | Partial twin near `0x604df20f` |
| COLOR builder | `0x604f7272` | 15 / 494 | No close twin |
| Saturation gain data | via `0x6062fef8` | absent | 40 bytes, not found |

The builder is about 500 bytes on the PEN-F. It scales twelve saturation
values by per-sector gains and fills the table records. (R) It and its gain
data must be added. (I)

### 1.4 The editor is mostly missing

| PEN-F piece | PEN-F address | Windows matched |
| --- | --- | ---: |
| Editor local handler | `0x60cefd3d` | 105 / 758 |
| Editor state entry | `0x60cefa1d` | 56 / 758 |
| GUI setter | `0x607363b3` | 65 / 502 |
| Settings manager | `0x6075fbed` | 28 / 502 |
| COLOR up/down | `0x60cb0684` | 41 / 1014 |
| Wheel viewer constructor | `0x60c84664` | 26 / 659 |
| Wheel viewer update | `0x60c84901` | 4 / 758 |
| Wheel draw command | `0x6081b780` | 5 / 758 |
| `Draw_C3d_Async` | `0x60300b3d` | 0 / 502 |
| C3d value conversion | `0x602fc370` | 0 / 502 |

The generic property editor has partial twins. The wheel drawing code has
none. (B) The E-M5 II does have a Color Creator wheel, so it draws a wheel some
other way. Where is not yet known.

Spans for the editor rows are fixed lengths from the entry point, not measured
function sizes. Low scores mean "no close twin", not "no equivalent code".

### 1.5 Modified 4.1 firmware has been built before

- A published stock/hack pair for E-M5 II 4100 changes 6 decoded main bytes:
  two video duration operands at offsets `534866` and `53486c`, and a focus
  stacking allowlist branch at `3f2ad5` (`0x60413af5`). Repairing the additive
  checksum reproduces the distributed file. (R, oly_fw_analysis
  `docs/features/HISTORICAL_HACKS.md`)
- azqeurio/om-c-firmware lists an aperture-ring patch for E-M5 II 4.1 with 13
  patch records and 2,616 changed bytes. (R, oly_fw_analysis
  `provenance/azqeurio-release.json`)

We have not found a first-hand report of the second one running on an E-M5 II.

### 1.6 Emulator support

om-emu runs E-M5 II 4.1 (code E118) through its PEN-F port: start, S1, S2 and
playback on the TFT and EVF, with the card file system native. (R) It does not
model the image processor, so it cannot show colour output. (R)

## 2. The selector and the hook site (2026-11-18)

`tools/selector_twins.py`, plus objdump listings (GNU binutils 2.45,
`mn10300-elf`). New tag: **D** means read from disassembly.

### 2.1 The E-M5 II selector is the PEN-F one without the COLOR branch

| Role | PEN-F | E-M5 II | Bytes differing |
| --- | --- | --- | ---: |
| Selector | `0x604f747f` | `0x604df257` | structure matches (D) |
| Custom-table applier | `0x604f6d67` | `0x604ded37` | 0 of 427 (B) |
| Generic applier | `0x604f6f12` | `0x604deee2` | 17 of 864 (B) |
| `0xF00D` case | `0x604f746a` | `0x604df242` | 0 of 21 (B) |
| Mode-to-table lookup | `0x604f6a2e` | `0x604de9fe` | differs, same shape (D) |
| COLOR builder | `0x604f7272` | none | |

Both selectors take a context in `a0`, load the request from `(4,a0)` and use
the same offsets: 960, 12, 56, 52, 100 and 5620. (D) Both appliers write their
records at context offset 676 and the control word at 964. (D)

The PEN-F places the builder between the generic applier and the `0xF00D`
case. That gap is exactly 504 bytes shorter on the E-M5 II, the length of the
builder. (B) So the builder was left out of this build and nothing else in that
stretch moved.

### 2.2 What the PEN-F does for COLOR

After the `0xF00D` test the PEN-F reads the picture mode from request bytes
8..11 and compares it with 11. (D) On a match it calls the builder with:

| Register | Value |
| --- | --- |
| `a0` | COLOR table, `0x60622d74` |
| `a1` | request + 1076, the twelve saturation values |
| `d0` | halfword at table + 3024 |
| `d1` | `(12,a2)`, the output context |

The E-M5 II goes straight from the `0xF00D` test to the generic path. (D)

### 2.3 Mode 11 is free on the E-M5 II

The lookup hashes the mode into a 64-slot table at `0x6062eae0`. It holds 59
modes. Those below `0x100` are 1, 2, 3, 4, 5, 8 and 10. Mode 11 is absent. (B)

Which picture mode each number means on this body is not yet known.

### 2.4 The PEN-F builder can be moved as it is

- It makes no calls. (D)
- It has one absolute reference: the gain pointer table at `0x6062fef8`. (B)
- It writes through the context offsets that the E-M5 II appliers also use. (D)

A port is the 504 builder bytes, twelve gain pointers and 40 bytes of gain
data, with that one reference repointed. (I)

### 2.5 Hook site

```text
604df2b6:  f8 02 38              mov   (56,a2),d0
604df2b9:  fc ec 2e 20 64 00     btst  0x64202e,d0
604df2bf:  c8 36                 beq   0x604df2f5
```

`0x604df2b6` is where the not-`0xF00D` path starts. It is the same point where
the PEN-F tests for mode 11. A 5-byte `jmp` over the first two instructions
(9 bytes) can reach new code that tests the mode, calls the builder for COLOR,
and otherwise replays the two instructions and returns to `0x604df2bf`. (I)

Register use differs slightly: the E-M5 II selector saves `d2, a2, a3` and
keeps request + 12 in `d2`. The PEN-F saves `d3` too and uses it for that. (D)
New code must follow the E-M5 II convention.

## 3. Stage 1 groundwork (2026-11-18)

### 3.1 The mode number and the lookup

The mode is composed from the request as `byte 8 << 24 | byte 9 << 16 |
halfword 10`. (D) Byte 8 is 0 for the plain picture modes, 1 and 2 for the two
larger groups. The lookup at `0x604de9fe` hashes it into the table at
`0x6062eae0` and jumps to a handler. Modes that share a handler get the same
table descriptor. (D)

| Modes | Handler |
| --- | --- |
| 1 | `0x604dec00` |
| 2, 5 | `0x604dec14` |
| 3 | `0x604dec46` |
| 4, 8 | `0x604dec5c` |
| 10 | `0x604dec72` |
| `0x7d0` | `0x604dec88` |

Each handler picks one of two descriptors by request byte 1063. Request bytes
1071 and 1072 can then replace the choice. (D) What those three bytes mean is
not known.

Names are a guess. If the numbering follows the menu order, 1 to 5 would be
Vivid, Natural, Muted, Portrait and i-Enhance. That would make Natural and
i-Enhance share a handler. (I, unconfirmed)

### 3.2 What the builder takes as input

The builder reads twelve signed bytes through `a1`, at index `2 * inner +
outer` for record `6 * outer + inner`. (D) That is the wheel order in
oly_fw_analysis `HSL_TABLES.md`. Each byte is the slider step, -5 to 5. A
negative step selects the second gain of the pair. The scaled product is
divided by 5. (D)

So a fixed look is twelve small integers. The PEN-F reads them from request +
1076. Stage 1 points `a1` at twelve bytes inside the patch, so the size of the
E-M5 II request does not matter yet.

### 3.3 Loaded sections and free space

`tools/section_tails.py`

The section table is at `0x60026d24`. The loaded end of each section comes
from a switch at `0x600420cf`, not from the next section's start. (D, B) The
flat file address equals the runtime address in every section. (B)

| Section | Loaded range | Free tail | From |
| ---: | --- | ---: | --- |
| 0 | `0x60130000..0x601d7000` | 940 | `0x601d6c54` |
| 1 | `0x60218000..0x603f8800` | 1,752 | `0x603f8128` |
| 2 | `0x60411000..0x6068f800` | 112 | `0x6068f790` |
| 3 | `0x606c6000..0x60a5f800` | 1,120 | `0x60a5f3a0` |
| 4 | `0x60aaa000..0x60fe2800` | 1,536 | `0x60fe2200` |
| 5 | `0x61042000..0x61124000` | 352 | `0x61123ea0` |

The file has far longer FF runs after each of these, up to 3.4 MB. They are
past the loaded end and are not usable as they stand.

The selector and the COLOR table are in section 2, which has only 112 free
bytes. The stage 1 patch needs 695. It goes in the section 1 tail. Total
loaded free space is about 5.8 KB. That is enough for stages 1 and 2. It is
not enough for an editor screen, which will need a section's loaded end
extended. (I)

Not yet checked: that nothing writes into these tails at run time, and that
section 1 is always loaded before the selector runs.

### 3.4 The stage 1 patch

`tools/build_stage1.py`, source in `patches/stage1/`

| Part | Address | Bytes | Origin |
| --- | --- | ---: | --- |
| Hook | `0x604df2b6` | 9 | `jmp` to the stub, four `nop` |
| Saturation steps | `0x603f8140` | 12 | `patches/stage1/look.json` |
| Gain pointers | `0x603f8150` | 48 | rebuilt for the new address |
| Gain data | `0x603f8180` | 40 | read from the PEN-F file at build time |
| COLOR builder | `0x603f81a8` | 504 | read from the PEN-F file at build time, one address repointed |
| Stub | `0x603f83a0` | 87 | `patches/stage1/stub.s` |

The stub composes the mode. For the carrier mode it calls the builder with the
COLOR table and the baked steps, then leaves through the stock exits at
`0x604df2a6` or `0x604df2f5`, as the PEN-F does. For any other mode it replays
the two displaced instructions and returns to `0x604df2bf`.

The build writes a patched main block for the emulator only. It does not
write a file a camera can install.

Status: builds, and the disassembly of the result reads as intended. Not yet
run in om-emu. Never run on a camera.

## Open questions

1. Which picture mode is which number? Needed to choose the carrier mode.
2. What do request bytes 1063, 1071 and 1072 select?
3. Does anything write into the section tails at run time?
4. The carrier mode keeps its own matrix, gamma and tone. Is that base close
   enough to the PEN-F COLOR base, or must those be redirected too?
5. Where are Color Creator's wheel and settings on this body?

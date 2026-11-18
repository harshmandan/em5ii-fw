# Roadmap

## Goal

A new colour UI on the E-M5 II, modelled on what OM System ships on the OM-3
and PEN-F: COLOR profiles, an on-camera editor, and film looks. The OM-3
screens cannot be copied over, because they are built on a newer GUI that this
body does not have. So the same feature is rebuilt on the E-M5 II's own GUI.
The stages below get there in steps that can each be tested.

Each stage ends with something that can be checked. No stage is flashed before
it passes in om-emu and the patch is reviewed byte by byte.

## Stage 0: tooling

- [x] Build GNU binutils for `mn10300-elf` (assembler, linker, objdump).
- [x] Disassemble the selector and name the hook site
  ([findings, section 2](FINDINGS.md#2-the-selector-and-the-hook-site-2026-11-18)).
- [x] Bring up E-M5 II 4.1 in om-emu (model `E118`).

Done when: the selector's table choice is understood well enough to name the
hook site, and the stock firmware runs in om-emu.

## Stage 1: one fixed film look

No new screen. Twelve saturation values are baked into the patch.

- [x] Find how the mode number is composed.
- [x] Port the PEN-F COLOR builder and its gain data (taken from the PEN-F
  file at build time, not stored here).
- [x] Hook the selector at `0x604df2b6` and add the COLOR case.
- [x] Find loaded free space for the patch.
- [x] Name picture modes 1 to 4; 5 and 8 by elimination.
- [ ] Confirm the carrier (mode 5) on a camera or by a further trace.
- [x] Run the patched main block in om-emu through S2.
- [x] Call the selector directly in om-emu and match the PEN-F records.
- [x] Check that nothing found reads or writes the section tail used.
- [x] Check that the patch changes only what COLOR changes on the PEN-F.
- [x] Read the four mode readers outside the stage list.
- [x] Pack update files and a stock restore file; prove the stock round trip.
- [x] Compare the E-M5 II SD update client and updater with the PEN-F.
- [ ] Find how the SD client is started on this body. Not known in code on any body.
- [ ] First camera test. Owner's decision, with the restore file on a second card.

Done when: the overlay runs clean in om-emu and the first camera test shows the
look in a JPEG while every other picture mode is unchanged.

## Stage 2: looks from the SD card

Design and options: [STAGE2.md](STAGE2.md).

- Read a small file of looks at start-up, as Caduceus does with `LOOKS.BIN`.
- Select a look through an existing menu item.
- Write the look name to EXIF.

## Stage 3: on-camera editor

- Find the Color Creator wheel and reuse what it offers.
- Add storage for the twelve values per profile.
- Add the editor screen.

This is the largest stage. The wheel drawing code of the PEN-F has no twin on
this body, so most of the screen is new work. It also needs more room than the
loaded section tails offer, so a section's loaded end must be extended first.

## Not planned

- Monochrome profiles.
- Any body other than the E-M5 II on firmware 4.1.

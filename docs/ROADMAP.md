# Roadmap

Each stage ends with something that can be checked. No stage is flashed before
it passes in om-emu and the patch is reviewed byte by byte.

## Stage 0: tooling

- Build GNU binutils for `mn10300-elf` (assembler, linker, objdump).
- Bring up E-M5 II 4.1 in om-emu (`--model E118`).
- Disassemble the selector near `0x604df20f` and the ISP writer at `0x6049d252`.

Done when: the selector's table choice is understood well enough to name the
hook site.

## Stage 1: one fixed film look

No new screen. Twelve saturation values are baked into the patch.

- Port the PEN-F COLOR builder and its gain data.
- Add a COLOR case to the selector, tied to one picture mode.
- Qualify the code space used.
- Build a patch overlay and run it in om-emu through S2.
- Build the update file and a matching stock restore file.

Done when: the overlay runs clean in om-emu and the first camera test shows the
look in a JPEG while every other picture mode is unchanged.

## Stage 2: looks from the SD card

- Read a small file of looks at start-up, as Caduceus does with `LOOKS.BIN`.
- Select a look through an existing menu item.
- Write the look name to EXIF.

## Stage 3: on-camera editor

- Find the Color Creator wheel and reuse what it offers.
- Add storage for the twelve values per profile.
- Add the editor screen.

This is the largest stage. The wheel drawing code of the PEN-F has no twin on
this body, so most of the screen is new work.

## Not planned

- Monochrome profiles.
- Any body other than the E-M5 II on firmware 4.1.

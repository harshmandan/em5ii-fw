# Stage 2 design: more than one look

Stage 1 gives one look, fixed when the firmware file is built. Stage 2 is
about choosing between looks without rebuilding. Three ways to get there,
smallest first. Evidence is in [FINDINGS.md](FINDINGS.md) sections 6 and 9.

Nothing here has run on a camera. Stage 1 itself is untested on hardware, so
every option below stacks on an untested base.

## Option A: change the look by rebuilding

Edit `patches/stage1/look.json`, rebuild, reinstall.

- New camera code: none. Works today in the build.
- Cost: an install for every change. Each install is a firmware write.
- Looks at once: one.

## Option B: several baked looks, picked by something the camera already has

The patch holds a small table of looks. The stub picks a row from a value
that is already in the picture job.

Two ways to pick:

| Selector | Looks | Cost to the user |
| --- | ---: | --- |
| The picture mode itself: mode 5 is look 1, mode 8 is look 2 | 2 | i-Enhance and e-Portrait, if those names are right |
| A slider inside the carrier mode, read from the request | 3 to 5 | that slider keeps its own effect as well |

For the slider route, request byte 1066 moves only the chroma word and is
probably the saturation slider. Bytes 1059 and 1060 pick the tone curve. No
byte was found that reaches these stages and does nothing else.

- New camera code: about 40 bytes in the stub plus 12 bytes per look. Fits
  the 1,033 bytes left in the section 1 tail many times over.
- No new memory, no file access, no new screen.
- Looks at once: 2 to 5, still fixed at build time.

## Option C: looks loaded from the SD card

A file on the card holds the looks. The camera reads it and keeps them.

Needs, none of which has been read on this body:

1. The file open, read and close calls, and which tasks may call them. The
   SD update client uses such calls and is a twin of the PEN-F's.
2. Memory that is writable, unused and kept. Caduceus uses an unused tail of
   a settings store that the camera saves by itself.
3. A moment to load. Caduceus hooks the half-press handler and loads once.
4. A way to choose a look. Option B's selector, or a menu item.
5. Room. Likely more than the section tails hold, so a section's loaded end
   must be raised.

- New camera code: several hundred bytes, in more than one task context.
- Risk: file calls from the wrong task, or a write to memory that is in use,
  can hang or corrupt settings. This is where Caduceus reports most of its
  own crashes.
- Looks at once: many, changed by copying a file.

## Recommendation

Do B before C, and test stage 1 on a camera before either. B reuses the
tested stub and adds no new kind of risk. C adds three: file access, memory
ownership and a second hook. It makes sense once stage 1 is known to work on
hardware, because every C failure would otherwise be hard to tell apart from
a stage 1 failure.

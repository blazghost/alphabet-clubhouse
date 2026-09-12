# Alphabet Clubhouse

A phonics and trackpad-skills app for a kindergartener, built to run in a browser
tab on a school Chromebook with nothing to install.

Open `index.html` in any browser, or use the published link.

## Why it is built this way

- **Nothing requires reading.** Every prompt is spoken with the Web Speech API and
  can be replayed with the speaker button. A five-year-old learning letters cannot
  read the instructions telling her to learn letters.
- **Andika for every letterform.** SIL's literacy typeface: single-story `a` and
  `g`, distinct `l`/`I`/`1` - the manuscript print taught in kindergarten. A
  double-story `a` actively confuses a new reader.
- **Sounds, not just names.** The voice gives the phoneme. Continuants (f, l, m,
  n, r, s, v, z) are held; stops get the shortest possible schwa.
- **Every drag also works as two taps.** Tap the letter, then tap where it goes,
  so a child who cannot yet hold a drag is never locked out of the phonics.
- **No losing.** A wrong answer never costs a star or ends a round.

## The ten activities

Letters & sounds: Alphabet Board, Find the Letter (letter name -> letter),
Letter Sounds (phoneme -> letter), Beginning Sounds (picture -> first letter),
Build a Word (CVC blending).

Trackpad practice: Bubble Pop (pointer control + click), Big and Little (drag),
Knock Knock (double-click), Scroll and Find (two-finger scroll),
Trace a Letter (press-and-hold drag along correct letter formation strokes).

## Notes

Single file, no build step, no dependencies beyond Google Fonts. Progress is kept
in `localStorage`, so each device keeps its own stars. Settings cover letter case
(capitals / lower case / mixed), voice on-off and voice speed.

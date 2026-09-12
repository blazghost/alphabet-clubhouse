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
- **Phrases are spoken as whole sentences.** A synthesiser carries its
  intonation across an utterance, so "B says buh, like ball!" is sent as one
  line. Chopping it into fragments restarts the prosody flat on each piece with
  a gap between, which is what makes synthetic speech sound like a robot. Voices
  are ranked (Natural / Neural / Online / Enhanced win; eSpeak, Festival, Pico
  and the legacy SAPI "Desktop" voices lose) and Settings has a picker with a
  preview, because what is installed differs on every machine.
- **Every drag also works as two taps.** Tap the letter, then tap where it goes,
  so a child who cannot yet hold a drag is never locked out of the phonics.
- **No losing.** A wrong answer never costs a star or ends a round, and the
  reply is always gentle: "That's okay. Let's try again together."
- **Pip does the talking.** Giving the voice a face is what makes it read as
  someone caring rather than a machine reading words aloud. He reacts to every
  answer, and tapping him repeats the question.
- **Teacher delivery.** Modelled on how the toddler-teaching videos on
  YouTube work, because that style is what she already responds to: slow and
  sing-song (parentese — pitched up, rate down), the target sound said three
  times, and then a real pause that waits for her to say it back, with a
  *Your turn!* badge on screen so the silence reads as an invitation rather
  than a bug. Producing the sound aloud is what builds the phoneme, not
  recognising it. Switchable to "Simple" in Settings.
- **Her name.** Optional, set in Settings, and woven into about half the praise
  so it is her being congratulated, not a generic player.

## The reading path

Letters are introduced in phonics order, not alphabetical order: **s a t p i n**
first, because those six make more real words than any other six in English
(sat, pit, tap, nip, pan, tin). Going A, B, C means a child cannot read a single
word until she is most of the way through the alphabet.

Four steps, each unlocking the next. A step is a short guided lesson in four
phases: meet three sounds (with a *Your turn!* pause on each), find them among
other letters, build two words and hear them blended, then read a real sentence
made only of sounds she has already met. Every word and sentence in the path is
checked to be decodable from the letters taught up to that point.

Blending is continuous: each letter lifts and lights as its sound is held, a
swoop is drawn underneath joining them, and then the whole word is said. That
join is the actual reading skill — three separate sounds are not a word until
they are run together.

Each phase carries a line for the adult, because at this age the app is a script
for the grown-up sitting next to her as much as it is a game.

## The ten activities

Stars fly to the counter as she earns them, five stars wins a sticker for the
sticker book, and the sound effects are soft sine tones rather than beeps.

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

## Getting a human-sounding voice

The browser supplies the voice, not the app. A Chromebook has good ones built
in (more under Settings -> Accessibility -> Text-to-speech). A bare Arch install
has *none*, so the app is silent until speech-dispatcher is present:

    sudo pacman -S speech-dispatcher rhvoice rhvoice-language-english rhvoice-voice-slt

Then restart the browser and choose the voice in Settings. RHVoice sounds far
more human than espeak-ng, which is the one that sounds like a robot.

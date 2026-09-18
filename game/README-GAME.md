# Can You Hear It?

Bonus listening game for **BME 576 · Sensory Prostheses Engineering**.

Gianluigi D'Antonio · Gabriele Colò · Yelizaveta Semikina

## Run

From the repository root, run `python run_game.py`, then open
`http://127.0.0.1:8765/web/`. The server uses Python's standard library.
Playback and interface logic run in the browser. No additional runtime
packages are needed when the prepared WAV files are available.

## Rules

Enter a username and complete five sentences in a fixed order. Each sentence
starts at Legend. A wrong answer or the More channels button advances one
level. There are at most two playback starts and one submitted answer per
level. An empty answer or an answer submitted before listening costs nothing.
Playback failures are refunded; files never fall back silently to original audio.

| Level | Channels | Points when correct |
|---|---:|---:|
| Legend | 1 | 100 |
| Champion | 2 | 90 |
| Pro | 4 | 80 |
| Skilled | 8 | 70 |
| Beginner | 16 | 60 |
| Rookie | 32 | 50 |

Matching ignores case, punctuation and repeated spaces. Words must match:
spelling mistakes and synonyms are not automatically accepted. A correct
answer shows the coin, confetti and reward, then waits for Next sentence.
Failing or skipping Rookie awards zero points and unlocks Listen to original.
The original is for comparison only and adds no points. Maximum round score: 500.

## Files and audio mapping

`web/model.js` defines sentences and scoring. `web/app.js` manages screens,
media events, asset checks and storage. `web/index.html`, `web/style.css` and
`web/coin.svg` provide the page, appearance and coin. `web/audio_check.html`
offers a separate comparison page, linked from the home screen.

At Play, the app checks all 35 audio URLs using HEAD requests. A missing or
unavailable file blocks the start and offers a retry. Media errors during a
round leave the current attempt available. Navigation cancels pending checks
and playback so late media events cannot alter another round.

| ID | Expected sentence |
|---|---|
| 01 | The small dog is sleeping on the bed. |
| 02 | Please put the red book on the table. |
| 03 | My sister drinks coffee every morning. |
| 04 | We can walk to the park together. |
| 05 | There is a blue car outside the house. |

Each ID uses six files `assets/processed/sentence_01_ch_1.wav` through
`sentence_01_ch_32.wav` for channel counts 1, 2, 4, 8, 16, 32.
The comparison reference is `assets/processed/sentence_01_original.wav`.
Replace `01` with the corresponding two-digit ID for the other sentences.
`sentence_01_metadata.json` records generation parameters and checks.

The original references are resampled, preprocessed and globally level-matched;
they are not untouched MP3 copies. Each sentence's seven versions have matched
RMS, with a shared attenuation if required to avoid clipping. Equal RMS does
not guarantee equal perceived loudness. The target RMS is 0.08, but sentences
requiring attenuation have a lower final RMS.

## Sampling choices

The prepared files use the existing Python pipeline: filterbank, envelope,
log compression, CIS pulses, pulse decoding and noise-vocoder reconstruction.
Audio output is mono PCM16 at 22050 Hz. The stimulation grid is **320000 Hz**,
with **1000 pulses/s per channel**, **12.5 microseconds per phase**, and no
interphase gap. At 32 channels each slot has 10 samples and the two phases
occupy 8 samples, so they fit without overlap. The same timing settings are
used for every game level. These are numerical-model choices, not a claim
about a universal clinical setting; the base assignment's defaults are unchanged.

Bands cover 200–8000 Hz. Four channels retain the original edges
`[200, 500, 1250, 3150, 8000]`; fewer channels merge bands and higher counts
subdivide them logarithmically. The envelope cutoff is 400 Hz, compression
alpha is 1000, filter order is 4 and noise seed is 42. To regenerate, use
`python prepare_game_audio.py` at the repository root with the project's
processing dependencies and the original MP3 files present.

## Results

Completed rounds use localStorage key `listening-game-cis-320k-v1` and include
per-sentence results and the audio version. Demo results stored under
`listening-game-demo-v1` remain separate. Equal totals share a rank; each
completed round is a separate entry. The leaderboard is local to the browser
and origin, not a shared online database. Clearing site data removes results.
An unfinished round is not saved.

This is an educational demonstration. Familiarity with the five sentences
and repeated listening influence performance, so the scores are not a
controlled measure of hearing ability. Transcripts and scores are client-side;
the game is intended for a classroom activity rather than secure competition.

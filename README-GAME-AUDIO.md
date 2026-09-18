# Listening game: prepare and compare the six audio levels

This package adds the audio preparation step to the existing `game` branch.
It includes the first sentence already processed at all six channel counts.
It does not change the existing game screens or connect their playback yet.

## Copy the files

| File or folder | Destination in the existing project |
|---|---|
| `prepare_game_audio.py` | Repository root, beside `run_game.py` |
| `game/web/audio_check.html` | Existing `game/web/` folder |
| `game/assets/processed/` | Inside `game/assets/`, beside `audio/` |
| `tests/test_game_audio.py` | Existing `tests/` folder |
| `README-GAME-AUDIO.md` | Repository root |

Merge folder contents. Keep the other project files. The original MP3 files
remain in `game/assets/audio/sentence_01.mp3` through `sentence_05.mp3`.
The script uses the filenames and IDs already defined in `game/sentences.py`.

First integrate `part3-reconstruction` into your local `game` branch so that
`src/cis.py` and `src/reconstruction.py` are available. The remote part 3
version checked for compatibility is `392157d3111607d04d928e54455e16f31996cc7d`.
All processing dependencies are already in the project `requirements.txt`.

## Check the first sentence

The included seven WAV files are ready to compare. Start the existing server:

```bash
python run_game.py
```

Then open <http://127.0.0.1:8765/web/audio_check.html>.
The default is Sentence 1. Listen to the six channel counts before the original.
You can also open `game/web/audio_check.html` directly in a browser.

To reproduce the files from the original MP3, use the project environment:

```bash
python prepare_game_audio.py --sentence 1
```

To generate all five sentences, use:

```bash
python prepare_game_audio.py
```

Or select several IDs, for example `--sentence 2 3`. Existing outputs for the
selected sentences are replaced. Files for other sentences are retained.
The check page's other sentence selections become available as their files
are generated. Missing files show a message and never fall back to an original.

## Outputs

Each sentence produces six reconstructed WAV files and one original reference:

- `sentence_01_ch_1.wav`, `sentence_01_ch_2.wav`, `sentence_01_ch_4.wav`
- `sentence_01_ch_8.wav`, `sentence_01_ch_16.wav`, `sentence_01_ch_32.wav`
- `sentence_01_original.wav`
- `sentence_01_metadata.json`

All WAVs are mono PCM16 at 22050 Hz. The original reference is resampled,
preprocessed and level-matched. It is not an untouched copy of the MP3.
The metadata records the input hash, signal length, band edges, stimulation
timing, seed, output gains, and pulse decoding checks.

## Fixed settings across levels

| Setting | Value |
|---|---|
| Audio sampling frequency | 22050 Hz |
| Stimulation sampling frequency | 320000 Hz |
| Pulse rate per channel | 1000 pulses/s |
| Phase duration / interphase gap | 12.5 / 0 microseconds |
| Envelope low-pass cutoff | 400 Hz |
| Compression alpha | 1000 |
| Butterworth order | 4 |
| Noise seed | 42 |

At 32 channels, one millisecond has 320 stimulation samples. Each channel slot
has 10 samples and a biphasic pulse occupies 8. The settings therefore fit on
the sampling grid without overlap. They are chosen for this numerical model,
not asserted to be a clinical standard. The assignment's encoder defaults are
unchanged because this script passes the game settings explicitly.

For 1 and 2 channels, the original four bands are merged. Four channels use
exactly `[200, 500, 1250, 3150, 8000]`. For 8, 16 and 32, each original band is
subdivided logarithmically, retaining the original boundaries.

Each input is preprocessed once. The pulse decoder reads the actual positive
phases, reverses compression, and interpolates at the channel's pulse times.
It then uses the existing noise vocoder. Encoder amplitudes are consulted only
afterward for verification. No extra normalization is applied to the envelopes.

For listening, every complete waveform is scaled to a target RMS of 0.08,
then all seven versions of that sentence receive one shared attenuation if
needed to keep peaks at or below 0.95. Equal RMS is not equal perceived
loudness. The gains do not change relative channel amplitudes within a version.

Only one dense CIS pulse matrix is processed at a time. The 32-channel case
uses a few hundred MB for a short sentence. Do not run multiple preparations
in parallel. Pulse matrices are not written to disk.

## Checks and next integration step

From the repository root:

```bash
python -m unittest discover -s tests -p test_game_audio.py -v
```

The added tests cover nested frequency bands, RMS and peak handling, and all
six channel counts through encoding and reconstruction. The first sentence
has also been processed using the supplied recording. Browser playback still
needs to be checked locally.

Once all 30 reconstructed files are generated and reviewed, connect the main
game's `audioPath(sentence, channels)` to these paths. Keep demo labels until
then. Use a new leaderboard storage key for real processed-audio scores, and
use the level-matched original for the post-Rookie comparison.

This is a listening demonstration, not a clinical assessment. A higher channel
count does not guarantee that each individual attempt becomes easier, and
repeated listening to a known sentence introduces learning.

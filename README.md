# From Sound to Stimulation and Back

A cochlear implant simulation and listening game for **BME 576, Sensory
Prostheses Engineering**, UIC, Fall 2026.

**Gabriele Colò · Yelizaveta Semikina · Gianluigi D’Antonio**

We process speech and music through a four-channel filter bank, encode the
compressed envelopes as continuous interleaved sampling (CIS) pulses, and
reconstruct an acoustic signal with a noise vocoder. The game uses the same
pipeline at six channel counts to explore how spectral detail affects sentence
recognition.

[Open the online game](https://sensory-prostheses-auditory-project.onrender.com)

## Setup

Use Python 3.12. From the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

On Windows, create the environment with `py -3.12 -m venv .venv` and activate it
with `.venv\Scripts\Activate.ps1` in PowerShell. In PyCharm, select this
virtual environment as the project interpreter.

`requirements.txt` covers the whole project. Its sections group audio
processing, notebooks, the server and tests; installation includes all sections.
NumPy 2 or later is needed for the band-power integration in `src/visualization.py`.

## Run the project

| Task | Entry point |
| --- | --- |
| Run Parts 1–3: filtering, CIS pulses and acoustic reconstruction | `cochlear_implant_assignment.ipynb` |
| Generate and check four-channel CIS pulses | `python part2_cis.py` |
| Run the standalone Part 3 walkthrough | `part3_reconstruction.ipynb` |
| Preview the game recordings and processed levels | `game_preview.ipynb` |
| Start the multiplayer game locally | `python run_multiplayer.py` |
| Regenerate the game audio | `python prepare_game_audio.py` |
| Run the tests | `python -m pytest tests -q` |

Start with `cochlear_implant_assignment.ipynb`, the unified notebook for Parts
1, 2 and 3. Open it from the repository root using `jupyter notebook` or PyCharm
and run all cells in order. It calls the shared modules in `src/`.
`part3_reconstruction.ipynb` remains an optional standalone walkthrough; it runs
the preceding stages itself. Neither notebook requires the other to run first.
The speech and music examples come from librosa and are downloaded on first use.

The CIS script writes pulse arrays and timing metadata to `results/`. Add
`--no-plots` to skip the timing figures. The reconstruction notebook writes
comparison figures, four listening WAV files and a settings/checks JSON to
`results/part3/`. Generated results are excluded from Git.

The older commands `python combined_part_1_and_2.py` and `python run_game.py`
remain aliases for `part2_cis.py` and `run_multiplayer.py`, respectively.

## Signal processing

1. Remove the input's DC offset and peak-normalize it once.
2. Split it into Butterworth bands and extract each envelope by full-wave
   rectification and low-pass filtering.
3. Apply logarithmic compression, then sample the envelopes to set the
   amplitudes of sequential, balanced biphasic pulses.
4. Read the positive pulse phases, invert the compression, and interpolate
   the recovered samples using each channel's actual pulse times.
5. Modulate band-limited noise with the recovered envelopes and sum the channels.

| Setting | Four-channel assignment | Listening game |
| --- | --- | --- |
| Channels | 4 | 1, 2, 4, 8, 16, 32 |
| Audio sampling rate | 22,050 Hz | 22,050 Hz |
| Frequency boundaries | 200, 500, 1,250, 3,150, 8,000 Hz | Merge or subdivide the same four bands |
| Butterworth design parameter `N` | 4 | 4 |
| Nominal single-pass envelope cutoff | 400 Hz | 400 Hz |
| Compression parameter | α = 1,000 | α = 1,000 |
| Pulse rate | 1,000 pulses/s/channel | 1,000 pulses/s/channel |
| Stimulation sampling rate | 100,000 Hz | 320,000 Hz |
| Phase duration | 50 µs | 12.5 µs |
| Interphase gap | 0 µs | 0 µs |
| Noise seed | 42 | 42 |

The band-pass design uses `butter(N=4, btype="bandpass")`, producing an
eighth-order filter with four second-order sections per band. Filters are
applied forward and backward with `sosfiltfilt`. This squares the single-pass
magnitude response: the envelope filter has approximately −6.02 dB gain at
400 Hz and its final half-power point is about 358.35 Hz at 22,050 Hz sampling.
Negative envelope undershoot from filtering is clipped to zero before compression.

In the four-channel model, each 1 ms frame contains four 250 µs slots.
Channel onsets are 0, 250, 500 and 750 µs, in low-to-high frequency order.
Each pulse lasts 100 µs and uses the same amplitude in its two opposite phases,
leaving 150 µs idle in each slot. Only complete frames are emitted.
The 1,000 Hz envelope sampling rate is above twice the nominal 400 Hz cutoff,
but the filter does not completely remove all higher-frequency content.

The shorter game pulses fit all 32 channels into a 1 ms frame. Pulse amplitudes
are normalized values, not calibrated currents. Inverse compression restores
the envelope scale chosen for acoustic synthesis; it does not represent a
biological decoding step. The decoder reads the pulse matrix, not the encoder's
cached amplitudes.

The vocoder preserves envelope information but replaces temporal fine structure
with new noise carriers. It is an offline listening demonstration, not a model
of an individual implant user's perception. Repeated exposure to the same
sentence also affects recognition, so game scores are not clinical measures.

### Pulse output and reuse

`python part2_cis.py` saves speech and music `.npz` files in `results/`.
Each archive contains `pulses` with shape `(channels, stimulation samples)`,
`stimulation_fs`, `pulse_rate`, `phase_samples`, `gap_samples`, `onset_samples`,
`audio_fs` and `input_samples`. Channel indices are zero-based. The timing fields
identify where to read each pulse when recovering the envelope samples.

To encode existing compressed envelopes in Python:

```python
from src.cis import encode_cis, plot_cis

result = encode_cis(compressed_envelopes, audio_fs)
plot_cis(result, start=0.5, duration=0.0033)
```

`result.amplitudes` is available for encoder checks. Reconstruction reads
`result.pulses` instead, so it includes the pulse-demodulation step. Simulation
amplitudes do not include patient thresholds or electrode impedances and must
not be used to drive stimulation hardware.

## Classroom game

Open the online link, or run `python run_multiplayer.py` and visit
[http://127.0.0.1:8000](http://127.0.0.1:8000).

1. Choose **Host a game**, create a room and project its QR code.
2. Players scan it and enter unique nicknames. Everyone joins before the host
   starts the game.
3. Press **Start game**, then **Play audio**. Sound comes from the host's
   speakers. Players submit answers on their phones after playback ends.
4. Use **Next level** to increase the channel count. Each player gets one answer
   per level. A correct answer earns points once and locks that player until
   the next sentence. Each level permits two shared listens.
5. At the final level, or once everyone has solved the sentence, choose
   **Reveal sentence**. The original recording can then be played.
6. Continue through the five sentences and download the final scores as CSV.

| Channels | 1 | 2 | 4 | 8 | 16 | 32 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Points | 100 | 90 | 80 | 70 | 60 | 50 |

An unsolved sentence earns zero; the maximum total is 500. Answers ignore case,
punctuation and extra spaces, but the words and their order must match. There
is no speed bonus, and tied totals receive the same rank.

Keep the host tab open. A refresh restores the session while the server is still
running. If playback was interrupted, use **Retry interrupted playback**.
Rooms and scores are stored in memory and disappear after a server restart or
deploy. Rooms also expire six hours after creation. Export the CSV to keep results.

For a local phone test, use `python run_multiplayer.py --host 0.0.0.0` and open
the host page through the computer's LAN IP, for example
`http://192.168.1.20:8000/host`. Phones must be on a network that allows access
to that computer. The online Render version works across different networks.

## Audio files

The five source recordings are in `game/assets/audio/`. The game plays the
35 WAV files already included in `game/assets/processed/`; no signal processing
runs during a live session. Transcripts are defined in `game/sentences.py` and
shared by the preparation script and server.

To regenerate one sentence:

```bash
python prepare_game_audio.py --sentence 1
```

Omit `--sentence` to regenerate all five. Each produces six reconstructions,
one original reference and a JSON record of parameters, source hash, gains and
pulse checks. The WAVs are mono PCM16 at 22,050 Hz. The original reference is
preprocessed and level-matched, not an unchanged copy of the source MP3.

Within each sentence, the seven waveforms are matched to a target RMS of 0.08,
then share any attenuation needed to keep peaks below 0.95. This matches energy,
not perceived loudness. Preparation processes one channel count at a time;
the 32-channel pulse array can require several hundred MB. Generate audio
locally and commit the WAVs before deployment.

## Render deployment

The service uses these settings:

| Field | Value |
| --- | --- |
| Service | Web Service, Python 3 |
| Branch | `feature/multiplayer` |
| Root Directory | Leave empty |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `uvicorn multiplayer.server:app --host 0.0.0.0 --port $PORT --workers 1` |
| Health Check Path | `/healthz` |
| Environment | `PYTHON_VERSION=3.12.10` |
| Instance Type | Free |

During integration, keep the deployed branch at `feature/multiplayer`. After
the pull request is merged and verified, select `main` in the Render dashboard
for subsequent deployments. Confirm the deployed commit before a classroom session.

For an existing service configured through the Render dashboard, update its
**Build Command** to the value above before deploying this revision. Adding
`render.yaml` alone does not update a manually configured service. The YAML
provides the same settings for a Blueprint deployment.

Use one worker and one instance because room state belongs to one process.
Avoid redeploying during a game. Open the site a few minutes before presenting:
the free instance may need to wake up after inactivity.

`/healthz` checks the server. `/api/readiness` lists missing or invalid WAV files.
If a room disappears after a restart, create a new one. If the QR points to
localhost, open the host page through the public URL or the computer's LAN IP.

## Files and tests

| Location | Contents |
| --- | --- |
| `src/` | Audio loading, preprocessing, filtering, envelopes, compression, CIS, reconstruction and plots |
| `game/sentences.py` | Recording filenames, transcripts and source-audio loader |
| `game/assets/` | Source MP3s, prepared WAVs and processing metadata |
| `game/web/` | Landing page, host/player screens, styles, JavaScript and coin graphic |
| `multiplayer/` | Game rules, room state, HTTP/WebSocket routes, QR codes and CSV export |
| `tests/` | Signal-processing and multiplayer regression tests |
| `render.yaml` | Deployment settings |

The tests check pulse timing and balance, reconstruction from actual pulse
samples, channel bands, playback gains, scoring, permissions, reconnects and
room isolation. They use synthetic signals and temporary files. A rehearsal
on the presentation computer and phones checks the actual speakers and browser.

## References

- Wilson et al. (1993). *Design and evaluation of a continuous interleaved
  sampling (CIS) processing strategy for multichannel cochlear implants*,
  pp. 110–116.
- Shannon et al. (1995). *Speech Recognition with Primarily Temporal Cues*.
  [doi:10.1126/science.270.5234.303](https://doi.org/10.1126/science.270.5234.303).
- López-Poveda et al. (2025). *Binaural audio frontend processing for cochlear
  implants inspired by the medial olivocochlear reflex*.
  [doi:10.3389/fnins.2025.1678288](https://doi.org/10.3389/fnins.2025.1678288).
  The α = 1,000 value is adapted from its reference FS4 strategy, not a universal
  CIS setting.
- BME 576 course material, *3.1 & 3.2*, auditory processing and CIS assignment.
- [Render FastAPI deployment](https://render.com/docs/deploy-fastapi).

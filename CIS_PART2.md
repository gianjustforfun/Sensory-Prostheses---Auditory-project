# Part 2: continuous interleaved sampling

This educational encoder uses the compressed envelopes produced by Part 1.
It produces four **trains** of electrical-style biphasic pulses, not just four
individual pulses. No patient thresholds, electrode impedances or physical
current units are modeled. Do not use these outputs to drive hardware.

## Parameter choices

The course slides specify a fixed-rate biphasic carrier, temporal interleaving,
and typically more than 800 pulses/s/channel; they do not prescribe exact timing.
Wilson et al. (1993), *Design and evaluation of a continuous interleaved sampling
(CIS) processing strategy for multichannel cochlear implants*, pp. 110–116,
describe balanced, non-overlapping pulses with envelope-derived amplitudes.
Table 1 reports several parameter sets, not one universal standard.

Our configurable defaults are design choices, not copied clinical settings:

| Parameter | Default |
| --- | --- |
| Envelope/audio sample rate | 22,050 Hz from Part 1 |
| Stimulation sample rate | 100,000 Hz (10 µs/sample) |
| Pulse rate | 1,000 pulses/s/channel |
| Phase duration | 50 µs (5 samples) |
| Interphase gap | 0 µs |
| Channel order | CH1, CH2, CH3, CH4 (low to high frequency) |
| Amplitude | compressed envelope, normalized 0–1 |

Each 1 ms frame has four 250 µs slots. Channel onsets are 0, 250, 500,
and 750 µs; each pulse occupies 100 µs, leaving 150 µs idle in each slot.
Both phases use the **same** sampled amplitude, so their signed areas cancel.
The 1,000 Hz envelope sampling rate exceeds twice the nominal 400 Hz cutoff.
The Butterworth lowpass is not an ideal brick-wall filter, so this is not a
claim that all out-of-band envelope content is eliminated.

## Run the Python files

Run `python part2_cis.py` from the repository root. It uses Part 1's Python
modules and the same speech/music examples, then generates and checks the pulses.
Outputs are saved in `results/`. Use `--no-plots` to export pulses without figures.
No notebook is needed. If Part 1 already supplies compressed envelopes, call:
The optional `combined_part_1_and_2.py` includes the same processing and encoding
functions in one standalone file. Run `python combined_part_1_and_2.py` for that version.
Keep the separate modules as the main version; update the combined copy if
their implementations change. Reconstruction is not included yet.

```python
from src.cis import encode_cis, plot_cis
import numpy as np
import matplotlib.pyplot as plt

speech_cis = encode_cis(speech_compressed_envelopes, fs_speech)
music_cis = encode_cis(music_compressed_envelopes, fs_music)

for name, result in [("Speech", speech_cis), ("Music", music_cis)]:
    assert np.all(np.count_nonzero(result.pulses, axis=0) <= 1)
    assert np.allclose(result.pulses.sum(axis=1), 0, atol=1e-10)
    print(name, result.pulses.shape, result.pulse_rate, "pps/channel")
    plot_cis(result, start=0.5, duration=0.0033, title=name + " CIS")
plt.show()
```

Part 3 can use `result.pulses` (channels × stimulation samples) and
`result.stimulation_fs`. Timing metadata (`onset_samples`, `phase_samples`,
`gap_samples`, `pulse_rate`) describes how to sample/demodulate the trains.
`amplitudes` contains the sampled envelopes for verification; reconstructing
from it directly bypasses pulse demodulation. Channel indices are zero-based.
Only complete frames are emitted; any trailing fraction of a frame is silent.

To export the pulse trains and metadata for your teammate:

```python
for name, result in [("speech", speech_cis), ("music", music_cis)]:
    np.savez_compressed(
        name + "_cis.npz", pulses=result.pulses,
        stimulation_fs=result.stimulation_fs, pulse_rate=result.pulse_rate,
        phase_samples=result.phase_samples, gap_samples=result.gap_samples,
        onset_samples=result.onset_samples, audio_fs=result.audio_fs,
        input_samples=result.input_samples,
    )
```

Run tests from the repository root:

```sh
python -m unittest discover -s tests -v
```

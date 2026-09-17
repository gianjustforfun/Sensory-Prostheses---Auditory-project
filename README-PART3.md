# Part 3: acoustic reconstruction

These files extend the existing auditory project on `part3-reconstruction`.

## Run

1. Open the project on `part3-reconstruction` and use its existing Python
   environment. The packages already listed in `requirements.txt` are enough.
   If that environment has not been set up, run
   `python -m pip install -r requirements.txt` from the repository root.
2. Open `part3_reconstruction.ipynb` in PyCharm or Jupyter. Use the repository
   root as the notebook working directory.
3. Select **Restart Kernel and Run All**. The notebook calls parts 1 and 2
   itself. There is no need to run the original notebook beforehand.
4. Listen to the original/reconstructed pairs and review the envelope plots.

The first use of the librosa examples may require an internet connection.
No new `requirements_game.txt` or other requirements file is needed.
The delivered notebook has cleared outputs so your results come from your run.

## Notebook contents

1. Shared parameters matching parts 1 and 2.
2. Speech (`libri1`, first 8 s) and music (`brahms`, 8 s from offset 15 s).
3. CIS generation and pulse plots using Liz's encoder.
4. Positive-phase amplitude extraction and numerical verification.
5. Inverse log compression with the same alpha, then interpolation using
   each channel's actual pulse times.
6. Noise-vocoder synthesis using the original four analysis bands.
7. RMS-matched listening pairs, waveform plots and comparable spectrograms.
8. WAV export and a JSON record of parameters, gains and numerical checks.

All generated results go into `results/part3/`. Rerunning replaces the files
with the same names there. The four WAV files are `speech_original.wav`,
`speech_reconstructed.wav`, `music_original.wav`, and
`music_reconstructed.wav`. The original files here are preprocessed input
references with the documented playback gain, not untouched source files.

## Reuse from Python

```python
from src.reconstruction import reconstruct_audio

decoded = reconstruct_audio(
    cis_result,
    band_edges=[200, 500, 1250, 3150, 8000],
    alpha=1000.0,
    seed=42,
)

audio = decoded["audio"]
envelopes = decoded["envelopes"]
```

`audio` is the raw channel sum and may exceed the playback range. Apply one
global output gain before playback/export, as demonstrated in the notebook.
The wrapper needs the `CISResult` object, frequency boundaries, and matching
alpha. It does not use original audio, reference envelopes, or the encoder's
cached `amplitudes` field.

## Checks

From the repository root:

```bash
python -m unittest discover -s tests -v
```

Seven added tests cover the log inverse, actual pulse decoding without cached
amplitudes, nonzero gaps/reversed channel order, staggered interpolation,
boundary holds, silence, incomplete frames, reproducible synthesis, relative
channel gain preservation, the wrapper, and invalid parameters.

## Interpretation and integration

This reconstruction illustrates the envelope information retained by the
simplified CIS model. It does not recover the original fine structure or model
an individual patient's hearing. References and modeling assumptions are
included in the code and notebook. Add your own listening observations to the
report after running it.

For the final combined notebook, keep the part 3 decoding and comparison
sections and connect them to the CIS objects already produced by its part 2
section. Remove the temporary bridge once the earlier sections provide those
inputs.

The current pulse timings support the four-channel assignment. Before using
8, 16 or 32 channels in the game, agree on pulse durations and a stimulation
clock that fit every channel slot. The reconstruction module can use other
channel counts when its inputs and band edges match, but does not alter the
encoder's timing rules.

# Sensory Prostheses - Auditory Project

This project models the main signal-processing steps of a four-channel
cochlear implant using the continuous interleaved sampling (CIS) strategy.
It processes one speech recording and one music recording.

## Unified notebook: Parts 1, 2 and 3

`cochlear_implant_assignment.ipynb` is the main entry point for the complete
project. Run it from top to bottom to process the example audio, encode the
four CIS pulse trains, recover the transmitted envelopes and synthesize the
acoustic reconstructions. The notebook uses the implementations in `src/`
rather than duplicating them.

## Parts 1 and 2

Part 1:

- loads and normalizes the audio
- separates it into four frequency bands
- extracts the envelope of each band
- applies logarithmic compression

Part 2:

- samples the four compressed envelopes
- generates balanced biphasic pulse trains
- offsets the channels in time so their pulses do not overlap
- checks the pulse rate, amplitudes, charge balance, and channel timing

The default simulation uses 1,000 pulses per second on each channel,
50 microseconds per phase, no interphase gap, and a 100,000 Hz stimulation
clock. Pulse amplitudes are normalized values, not real electrical currents.

## Files

- `src/` contains the separate processing modules
- `src/cis.py` contains the part 2 pulse encoder and plotting function
- `src/reconstruction.py` contains the part 3 decoder and noise vocoder
- `cochlear_implant_assignment.ipynb` is the unified main for all three parts
- `part2_cis.py` connects the separate part 1 and part 2 modules
- `combined_part_1_and_2.py` contains parts 1 and 2 in one Python file
- `part3_reconstruction.ipynb` retains the standalone part 3 development notebook
- `tests/test_cis.py` checks pulse timing, balance, interleaving, and integration
- `CIS_PART2.md` explains the part 2 parameters and output format

## Setup

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

Start Jupyter and open `cochlear_implant_assignment.ipynb`, then choose
**Run All**. This is the recommended way to run the complete project.

The individual command-line entry points remain available for development and
testing.

Run the combined file:

```sh
python combined_part_1_and_2.py
```

Or run the same pipeline using the separate modules:

```sh
python part2_cis.py
```

Both commands save the pulse data and timing plots in `results/`.

Run the tests with:

```sh
python -m unittest discover -s tests -v
```

## Output for part 3

The `.npz` files contain four pulse trains and the timing information needed
for reconstruction. The pulse array shape is `(channels, stimulation samples)`.
Part 3 should recover the envelope values from these pulses before rebuilding
the audio signal.

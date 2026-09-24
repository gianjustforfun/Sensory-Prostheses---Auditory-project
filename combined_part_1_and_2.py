"""Compatibility entry point for the parts 1 and 2 pipeline.

The implementation is shared with src/ and part2_cis.py so both commands
use the same processing settings and functions.
"""

from src.audio import load_example_audio, load_audio_file
from src.preprocessing import preprocess_audio
from src.filterbank import bandpass_filter, apply_filterbank
from src.envelope import full_wave_rectify, lowpass_filter, extract_envelope, extract_envelopes
from src.compression import logarithmic_compression, compress_envelopes
from src.cis import CISResult, encode_cis, plot_cis
from part2_cis import process_audio, check_pulses, main


if __name__ == "__main__":
    main()

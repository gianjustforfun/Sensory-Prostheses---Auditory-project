"""Prepare the six listening-game levels using the existing CIS pipeline."""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import soundfile as sf

from game.sentences import AUDIO_DIR, SENTENCES
from src.audio import load_audio_file
from src.preprocessing import preprocess_audio
from src.filterbank import apply_filterbank
from src.envelope import extract_envelopes
from src.compression import compress_envelopes
from src.cis import encode_cis
from src.reconstruction import reconstruct_audio


PROJECT_ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = PROJECT_ROOT / "game" / "assets" / "processed"
CHANNEL_COUNTS = (1, 2, 4, 8, 16, 32)
BASE_EDGES = np.array([200, 500, 1250, 3150, 8000], dtype=float)
AUDIO_FS = 22050
FILTER_ORDER = 4
ENVELOPE_CUTOFF = 400
ALPHA = 1000.0
NOISE_SEED = 42
TARGET_RMS = 0.08
PEAK_LIMIT = 0.95

# Use the same timing at all six levels. At 1000 pulses/s/channel,
# one frame is 1 ms = 320 samples. With 32 channels each slot contains
# 10 samples. A biphasic pulse occupies 4 + 4 = 8 samples and fits.
# This is a numerical configuration for our simplified acoustic model,
# not a clinical stimulation prescription. The encoder defaults stay intact.
STIMULATION_FS = 320000
PULSE_RATE = 1000
PHASE_DURATION_US = 12.5
INTERPHASE_GAP_US = 0


def make_band_edges(channel_count):
    """Merge or subdivide the four original bands, retaining their boundaries."""
    if channel_count not in CHANNEL_COUNTS:
        raise ValueError(f"channel_count must be one of {CHANNEL_COUNTS}.")
    if channel_count == 1:
        return BASE_EDGES[[0, -1]].copy()
    if channel_count == 2:
        return BASE_EDGES[[0, 2, 4]].copy()
    if channel_count == 4:
        return BASE_EDGES.copy()

    subdivisions = channel_count // 4
    edges = []
    for low, high in zip(BASE_EDGES[:-1], BASE_EDGES[1:]):
        # Drop each segment's last boundary to avoid duplicating shared edges.
        edges.extend(np.geomspace(low, high, subdivisions + 1)[:-1])
    return np.r_[edges, BASE_EDGES[-1]]


def synthesize_level(audio, fs, channel_count):
    """Encode a preprocessed input and reconstruct it from the actual pulses."""
    edges = make_band_edges(channel_count)
    bands = apply_filterbank(audio, fs, edges, order=FILTER_ORDER)
    envelopes = extract_envelopes(
        bands, fs, cutoff=ENVELOPE_CUTOFF, order=FILTER_ORDER
    )
    envelope_peak = float(np.max(envelopes))
    if envelope_peak > 1:
        raise ValueError(
            f"{channel_count} channels: envelope peak {envelope_peak:.4f} exceeds 1. "
            "Review input gain for this recording before compression."
        )
    compressed = compress_envelopes(envelopes, alpha=ALPHA)
    cis = encode_cis(
        compressed, fs,
        stimulation_fs=STIMULATION_FS,
        pulse_rate=PULSE_RATE,
        phase_duration_us=PHASE_DURATION_US,
        interphase_gap_us=INTERPHASE_GAP_US,
    )

    # Check exact timing, phase balance, and the absence of slot overlap.
    frame_samples = STIMULATION_FS // PULSE_RATE
    if frame_samples % channel_count:
        raise ValueError("The frame must divide into whole channel slots.")
    slot_samples = frame_samples // channel_count
    if 2 * cis.phase_samples + cis.gap_samples > slot_samples:
        raise ValueError("The pulse does not fit in its channel slot.")
    if cis.onset_samples.shape[1] == 0:
        raise ValueError("The recording is too short to transmit a complete frame.")
    offsets = np.arange(cis.phase_samples)
    frames = np.arange(cis.onset_samples.shape[1]) * frame_samples
    for channel, onsets in enumerate(cis.onset_samples):
        np.testing.assert_array_equal(onsets, frames + channel * slot_samples)
        negative = cis.pulses[channel, onsets[:, None] + offsets]
        positive = cis.pulses[
            channel, onsets[:, None] + cis.phase_samples + cis.gap_samples + offsets
        ]
        np.testing.assert_allclose(negative + positive, 0, rtol=0, atol=1e-12)

    decoded = reconstruct_audio(
        cis, edges, alpha=ALPHA, order=FILTER_ORDER, seed=NOISE_SEED
    )
    reconstructed = decoded["audio"]
    if reconstructed.shape != audio.shape or not np.all(np.isfinite(reconstructed)):
        raise ValueError("Reconstructed audio must be finite and preserve input length.")

    # Cached amplitudes are used ONLY for verification, never as decoder input.
    pulse_error = float(np.max(np.abs(decoded["sampled_compressed"] - cis.amplitudes)))
    np.testing.assert_allclose(
        decoded["sampled_compressed"], cis.amplitudes, rtol=0, atol=1e-12
    )
    info = {
        "channels": channel_count,
        "band_edges_hz": edges.tolist(),
        "slot_samples": slot_samples,
        "phase_samples": cis.phase_samples,
        "frames": cis.onset_samples.shape[1],
        "envelope_peak": envelope_peak,
        "pulse_decoding_max_error": pulse_error,
    }
    # Only the waveform and small metadata leave this function. The large
    # pulse matrix can be released before the next channel count is processed.
    return reconstructed, info


def match_playback_levels(signals):
    """RMS-match complete waveforms, then apply one shared peak attenuation."""
    matched = {}
    gains = {}
    for name, signal in signals.items():
        signal = np.asarray(signal, dtype=float)
        rms = float(np.sqrt(np.mean(signal ** 2)))
        if not np.isfinite(rms) or rms <= 0:
            raise ValueError(f"{name}: cannot level-match an empty, silent or invalid signal.")
        gains[name] = TARGET_RMS / rms
        matched[name] = signal * gains[name]

    largest_peak = max(float(np.max(np.abs(x))) for x in matched.values())
    common_gain = min(1.0, PEAK_LIMIT / largest_peak)
    for name in matched:
        matched[name] *= common_gain
        gains[name] *= common_gain
    return matched, gains, common_gain


def prepare_sentence(sentence, output_dir=OUTPUT_DIR):
    """Generate all six levels and a level-matched original for one sentence."""
    source_path = AUDIO_DIR / sentence["filename"]
    if not source_path.is_file():
        raise FileNotFoundError(f"Original recording not found: {source_path}")
    audio, fs = load_audio_file(str(source_path), sr=AUDIO_FS)
    if audio.size == 0 or not np.all(np.isfinite(audio)):
        raise ValueError(f"Invalid or empty input: {source_path.name}")
    audio = preprocess_audio(audio)
    if not np.any(audio):
        raise ValueError(f"Silent input: {source_path.name}")

    sentence_id = sentence["id"]
    prefix = f"sentence_{sentence_id:02d}"
    signals = {"original": audio}
    level_info = []
    for channel_count in CHANNEL_COUNTS:
        print(f"Sentence {sentence_id}: processing {channel_count} channels...", flush=True)
        reconstructed, info = synthesize_level(audio, fs, channel_count)
        signals[f"ch_{channel_count}"] = reconstructed
        level_info.append(info)

    matched, gains, common_gain = match_playback_levels(signals)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    files = {}
    for name, signal in matched.items():
        if np.max(np.abs(signal)) > PEAK_LIMIT + 1e-12:
            raise ValueError("Export peak limit was exceeded.")
        filename = f"{prefix}_{name}.wav"
        path = output_dir / filename
        sf.write(path, signal, fs, subtype="PCM_16")
        saved = sf.info(path)
        if saved.frames != len(audio) or saved.samplerate != fs or saved.channels != 1:
            raise ValueError(f"Unexpected WAV metadata: {path}")
        files[name] = {
            "filename": filename, "global_gain": gains[name],
            "rms_before_pcm": float(np.sqrt(np.mean(signal ** 2))),
            "peak_before_pcm": float(np.max(np.abs(signal))),
        }

    metadata = {
        "schema_version": 1,
        "sentence_id": sentence_id,
        "source_filename": source_path.name,
        "source_sha256": hashlib.sha256(source_path.read_bytes()).hexdigest(),
        "audio_fs": fs, "input_samples": len(audio), "duration_s": len(audio) / fs,
        "stimulation_fs": STIMULATION_FS, "pulse_rate_per_channel": PULSE_RATE,
        "phase_duration_us": PHASE_DURATION_US, "interphase_gap_us": INTERPHASE_GAP_US,
        "envelope_cutoff_hz": ENVELOPE_CUTOFF, "filter_order": FILTER_ORDER,
        "alpha": ALPHA, "noise_seed": NOISE_SEED,
        "target_rms": TARGET_RMS, "shared_peak_attenuation": common_gain,
        "peak_limit": PEAK_LIMIT, "wav_subtype": "PCM_16",
        "levels": level_info, "files": files,
    }
    (output_dir / f"{prefix}_metadata.json").write_text(
        json.dumps(metadata, indent=2), encoding="utf-8"
    )
    print(f"Sentence {sentence_id}: saved 6 levels + original in {output_dir}", flush=True)
    return metadata


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--sentence", nargs="+", type=int, choices=[s["id"] for s in SENTENCES],
        help="Sentence IDs to prepare, e.g. --sentence 1. Default: all five."
    )
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    args = parser.parse_args()
    selected = set(args.sentence) if args.sentence else {s["id"] for s in SENTENCES}
    for sentence in SENTENCES:
        if sentence["id"] in selected:
            prepare_sentence(sentence, args.output_dir)
    print("Done. Open game/web/audio_check.html to compare the levels.")


if __name__ == "__main__":
    main()

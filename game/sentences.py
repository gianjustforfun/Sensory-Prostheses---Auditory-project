from pathlib import Path

from src.audio import load_audio_file
from src.preprocessing import preprocess_audio


# Resolve the audio folder relative to this file.
AUDIO_DIR = Path(__file__).resolve().parent / "assets" / "audio"

# Expected transcripts, based on the text used to generate each file.
SENTENCES = [
    {
        "id": 1,
        "filename": "sentence_01.mp3",
        "text": "The small dog is sleeping on the bed."
    },
    {
        "id": 2,
        "filename": "sentence_02.mp3",
        "text": "Please put the red book on the table."
    },
    {
        "id": 3,
        "filename": "sentence_03.mp3",
        "text": "My sister drinks coffee every morning."
    },
    {
        "id": 4,
        "filename": "sentence_04.mp3",
        "text": "We can walk to the park together."
    },
    {
        "id": 5,
        "filename": "sentence_05.mp3",
        "text": "There is a blue car outside the house."
    }
]


def load_sentences(sr=22050):
    """
    Load and preprocess the five game sentences.

    Parameters
    ----------
    sr : int
        Target sampling frequency in Hz.

    Returns
    -------
    sentences : list
        Dictionaries containing the sentence ID, filename,
        expected text, processed audio and sampling frequency.
    """

    sentences = []

    for sentence in SENTENCES:
        filepath = AUDIO_DIR / sentence["filename"]

        if not filepath.is_file():
            raise FileNotFoundError(f"Audio file not found: {filepath}")

        audio, fs = load_audio_file(str(filepath), sr=sr)
        audio = preprocess_audio(audio)

        sentences.append({
            **sentence,
            "audio": audio,
            "fs": fs
        })

    return sentences
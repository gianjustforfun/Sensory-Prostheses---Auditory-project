"""Game rules shared by all players, evaluated only on the server."""

import re
from dataclasses import dataclass, field


# Keep this order aligned with game/assets/processed/sentence_XX_*.wav.
# These are the existing recordings, not newly synthesized audio.
SENTENCES = (
    "The small dog is sleeping on the bed.",
    "Please put the red book on the table.",
    "My sister drinks coffee every morning.",
    "We can walk to the park together.",
    "There is a blue car outside the house.",
)
LEVELS = (
    {"name": "Legend", "channels": 1, "points": 100, "color": "#ddd4f4"},
    {"name": "Champion", "channels": 2, "points": 90, "color": "#cddff6"},
    {"name": "Pro", "channels": 4, "points": 80, "color": "#cce7dd"},
    {"name": "Skilled", "channels": 8, "points": 70, "color": "#f4e7b9"},
    {"name": "Beginner", "channels": 16, "points": 60, "color": "#f4d5c3"},
    {"name": "Rookie", "channels": 32, "points": 50, "color": "#edcddd"},
)
MAX_PLAYS = 2


def normalize(text):
    """Match the solo game's case/punctuation/whitespace normalization."""
    return " ".join(re.sub(r"[^a-z0-9\s]", "", text.lower()).split())


@dataclass
class Player:
    nickname: str
    token: str
    points: list = field(default_factory=lambda: [0] * len(SENTENCES))
    solved: set = field(default_factory=set)
    attempts: dict = field(default_factory=dict)

    @property
    def score(self):
        return sum(self.points)


class RuleError(ValueError):
    """An action is not allowed in the current round."""


@dataclass
class Round:
    phase: str = "lobby"
    sentence: int = 0
    level: int = 0
    plays: int = 0
    play_id: str = ""
    return_phase: str = "ready"

    @property
    def turn(self):
        return self.sentence * len(LEVELS) + self.level

    def control(self, action, turn, players, play_id=""):
        """Advance the shared round. No player can change the shared level."""
        if turn != self.turn:
            raise RuleError("The level changed. Please try again.")
        if action == "start" and self.phase == "lobby":
            if not players:
                raise RuleError("Wait for at least one player to join.")
            self.phase = "ready"
        elif action == "play" and self.phase in ("ready", "answering"):
            if self.plays >= MAX_PLAYS:
                raise RuleError("Both listens have been used at this level.")
            self.return_phase = self.phase
            self.plays += 1
            self.play_id = play_id
            self.phase = "listening"
        elif action in ("audio_end", "audio_error") and self.phase == "listening":
            if play_id != self.play_id:
                raise RuleError("That playback is no longer current.")
            if action == "audio_error":
                self.plays -= 1
                self.phase = self.return_phase
            else:
                self.phase = "answering"
        elif action == "next_level" and self.phase == "answering":
            if self.level == len(LEVELS) - 1:
                raise RuleError("Reveal this sentence before continuing.")
            self.level += 1
            self.plays = 0
            self.phase = "ready"
        elif action == "reveal" and self.phase == "answering":
            all_solved = players and all(self.sentence in p.solved for p in players)
            if self.level != len(LEVELS) - 1 and not all_solved:
                raise RuleError("Continue to Rookie, or wait until everyone has solved it.")
            self.phase = "reveal"
        elif action == "next_sentence" and self.phase == "reveal":
            if self.sentence == len(SENTENCES) - 1:
                self.phase = "finished"
            else:
                self.sentence += 1
                self.level = 0
                self.plays = 0
                self.phase = "ready"
        else:
            raise RuleError("This action is not available right now.")

    def answer(self, player, text, turn):
        """One nonempty answer per level, one score per sentence."""
        if turn != self.turn or self.phase != "answering":
            raise RuleError("Answers are not open for that level.")
        if self.sentence in player.solved:
            raise RuleError("You already solved this sentence.")
        if self.turn in player.attempts:
            raise RuleError("You already answered. Wait for the next level.")
        if not normalize(text):
            raise RuleError("Please type the words you heard.")
        correct = normalize(text) == normalize(SENTENCES[self.sentence])
        player.attempts[self.turn] = correct
        if correct:
            player.solved.add(self.sentence)
            player.points[self.sentence] = LEVELS[self.level]["points"]
        return correct

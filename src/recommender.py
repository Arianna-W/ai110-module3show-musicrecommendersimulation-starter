import csv
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, asdict

# Max points per feature (total 7.0). Genre and mood are all-or-nothing;
# the rest give partial credit by closeness to the user's target.
BASE_WEIGHTS = {
    "genre": 2.0,
    "mood": 1.0,
    "energy": 2.0,
    "valence": 0.5,
    "acousticness": 0.5,
    "tempo_bpm": 0.5,
    "danceability": 0.5,
}
# Tempo gaps are scaled by this many BPM, so a gap this big earns zero points.
TEMPO_SPAN = 120.0
# Features that only count when the user states a target for them.
OPTIONAL_FEATURES = ("tempo_bpm", "danceability")
# Experiment: mood counts double genre instead of the reverse.
MOOD_FIRST_WEIGHTS = {**BASE_WEIGHTS, "genre": 1.0, "mood": 2.0}

@dataclass
class Song:
    """
    Represents a song and its attributes.
    Required by tests/test_recommender.py
    """
    id: int
    title: str
    artist: str
    genre: str
    mood: str
    energy: float
    tempo_bpm: float
    valence: float
    danceability: float
    acousticness: float

@dataclass
class UserProfile:
    """
    Represents a user's taste preferences.
    Required by tests/test_recommender.py
    """
    favorite_genre: str
    favorite_mood: str
    target_energy: float
    likes_acoustic: bool
    target_valence: float = 0.5
    target_tempo_bpm: Optional[float] = None
    target_danceability: Optional[float] = None

class Recommender:
    """
    OOP implementation of the recommendation logic.
    Required by tests/test_recommender.py
    """
    def __init__(self, songs: List[Song]):
        self.songs = songs

    @staticmethod
    def _prefs(user: UserProfile) -> Dict:
        """Convert a UserProfile into the prefs dict that score_song expects."""
        prefs = {
            "genre": user.favorite_genre,
            "mood": user.favorite_mood,
            "energy": user.target_energy,
            "acousticness": 0.8 if user.likes_acoustic else 0.2,
            "valence": user.target_valence,
        }
        if user.target_tempo_bpm is not None:
            prefs["tempo_bpm"] = user.target_tempo_bpm
        if user.target_danceability is not None:
            prefs["danceability"] = user.target_danceability
        return prefs

    def recommend(self, user: UserProfile, k: int = 5) -> List[Song]:
        """Return the top k songs for the user, best score first, ties broken by title."""
        prefs = self._prefs(user)
        ranked = sorted(
            self.songs,
            key=lambda song: (-score_song(prefs, asdict(song))[0], song.title),
        )
        return ranked[:k]

    def explain_recommendation(self, user: UserProfile, song: Song) -> str:
        """Return a comma-separated list of the scoring reasons for this song."""
        _, reasons = score_song(self._prefs(user), asdict(song))
        return ", ".join(reasons)

def load_songs(csv_path: str) -> List[Dict]:
    """
    Loads songs from a CSV file.
    Required by src/main.py
    """
    int_fields = ("id",)
    float_fields = ("energy", "tempo_bpm", "valence", "danceability", "acousticness")
    songs = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            for field in int_fields:
                row[field] = int(row[field])
            for field in float_fields:
                row[field] = float(row[field])
            songs.append(row)
    return songs

def score_song(
    user_prefs: Dict, song: Dict, weights: Optional[Dict[str, float]] = None
) -> Tuple[float, List[str]]:
    """
    Scores a single song against user preferences.
    Required by recommend_songs() and src/main.py
    Returns (score, reasons).
    """
    w = weights or BASE_WEIGHTS
    score = 0.0
    reasons = []

    for feature in ("genre", "mood"):
        if song[feature] == user_prefs[feature]:
            score += w[feature]
            reasons.append(f"{feature} match (+{w[feature]:.2f})")

    for feature in ("energy", "valence", "acousticness"):
        points = w[feature] * (1 - abs(song[feature] - user_prefs[feature]))
        score += points
        reasons.append(f"{feature} closeness (+{points:.2f})")

    for feature in OPTIONAL_FEATURES:
        if feature not in user_prefs:
            continue
        gap = abs(song[feature] - user_prefs[feature])
        if feature == "tempo_bpm":
            gap = min(gap / TEMPO_SPAN, 1.0)
        points = w[feature] * (1 - gap)
        score += points
        reasons.append(f"{feature} closeness (+{points:.2f})")

    return score, reasons

def recommend_songs(
    user_prefs: Dict,
    songs: List[Dict],
    k: int = 5,
    weights: Optional[Dict[str, float]] = None,
) -> List[Tuple[Dict, float, str]]:
    """
    Functional implementation of the recommendation logic.
    Required by src/main.py
    Returns (song_dict, score, explanation), best first, ties broken by title.
    """
    scored = [(song, *score_song(user_prefs, song, weights)) for song in songs]
    ranked = sorted(scored, key=lambda item: (-item[1], item[0]["title"]))
    return [(song, score, ", ".join(reasons)) for song, score, reasons in ranked[:k]]

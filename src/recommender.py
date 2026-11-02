import csv
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, asdict, field

# Max points per feature (core features total 7.0; the optional ones add up to 3.5 more). Genre and mood are all-or-nothing;
# the rest give partial credit by closeness to the user's target.
BASE_WEIGHTS = {
    "genre": 2.0,
    "mood": 1.0,
    "energy": 2.0,
    "valence": 0.5,
    "acousticness": 0.5,
    "tempo_bpm": 0.5,
    "danceability": 0.5,
    "popularity": 0.5,
    "release_decade": 0.5,
    "mood_tags": 1.0,
    "instrumentalness": 0.5,
    "explicit": 0.25,
    "duration_sec": 0.25,
}
# Tempo gaps are scaled by this many BPM, so a gap this big earns zero points.
TEMPO_SPAN = 120.0
# Same idea for the newer numeric features: a gap this big earns zero points.
POPULARITY_SPAN = 100.0
DECADE_SPAN = 50.0
DURATION_SPAN = 180.0
# Features that only count when the user states a target for them.
OPTIONAL_FEATURES = (
    "tempo_bpm", "danceability", "popularity", "release_decade",
    "instrumentalness", "duration_sec",
)
# Gap divisor per optional feature; features not listed use the raw 0-1 gap.
GAP_SPANS = {
    "tempo_bpm": TEMPO_SPAN,
    "popularity": POPULARITY_SPAN,
    "release_decade": DECADE_SPAN,
    "duration_sec": DURATION_SPAN,
}
# Diversity penalty: points subtracted from a candidate for each song by the same
# artist (or in the same genre) already picked for the top-k list.
ARTIST_PENALTY = 1.0
GENRE_PENALTY = 0.5


@dataclass(frozen=True)
class RankingStrategy:
    """A named set of feature weights. Swapping strategies changes the ranking
    without touching the scoring code (Strategy pattern)."""
    name: str
    description: str
    weights: Dict[str, float]


STRATEGIES: Dict[str, RankingStrategy] = {
    s.name: s
    for s in (
        RankingStrategy("balanced", "Default blend of all features", BASE_WEIGHTS),
        RankingStrategy(
            "genre-first", "Genre counts most; mood is a minor bonus",
            {**BASE_WEIGHTS, "genre": 4.0, "mood": 0.5},
        ),
        RankingStrategy(
            "mood-first", "Mood and mood tags count most, genre is secondary",
            {**BASE_WEIGHTS, "genre": 1.0, "mood": 2.0, "mood_tags": 2.0},
        ),
        RankingStrategy(
            "energy-focused", "Energy, tempo and danceability dominate",
            {**BASE_WEIGHTS, "genre": 0.5, "mood": 0.5, "energy": 4.0,
             "tempo_bpm": 1.5, "danceability": 1.5},
        ),
    )
}


def get_strategy(strategy) -> RankingStrategy:
    """Accept a RankingStrategy or its name; raise ValueError for unknown names."""
    if isinstance(strategy, RankingStrategy):
        return strategy
    try:
        return STRATEGIES[strategy]
    except KeyError:
        raise ValueError(
            f"Unknown strategy {strategy!r}; choose from {sorted(STRATEGIES)}"
        ) from None

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
    popularity: int = 50
    release_decade: int = 2000
    mood_tags: List[str] = field(default_factory=list)
    instrumentalness: float = 0.0
    explicit: int = 0
    duration_sec: int = 210

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
    target_popularity: Optional[int] = None
    target_decade: Optional[int] = None
    favorite_mood_tags: Optional[List[str]] = None
    target_instrumentalness: Optional[float] = None
    allow_explicit: Optional[bool] = None
    target_duration_sec: Optional[int] = None

class Recommender:
    """
    OOP implementation of the recommendation logic.
    Required by tests/test_recommender.py
    """
    def __init__(
        self,
        songs: List[Song],
        strategy="balanced",
        artist_penalty: float = ARTIST_PENALTY,
        genre_penalty: float = GENRE_PENALTY,
    ):
        self.songs = songs
        self.strategy = get_strategy(strategy)
        self.artist_penalty = artist_penalty
        self.genre_penalty = genre_penalty

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
        optional = {
            "popularity": user.target_popularity,
            "release_decade": user.target_decade,
            "mood_tags": user.favorite_mood_tags,
            "instrumentalness": user.target_instrumentalness,
            "explicit": user.allow_explicit,
            "duration_sec": user.target_duration_sec,
        }
        prefs.update({k: v for k, v in optional.items() if v is not None})
        return prefs

    def recommend(self, user: UserProfile, k: int = 5) -> List[Song]:
        """Return the top k songs for the user, best score first, ties broken by title."""
        by_id = {song.id: song for song in self.songs}
        results = recommend_songs(
            self._prefs(user), [asdict(s) for s in self.songs], k=k,
            strategy=self.strategy,
            artist_penalty=self.artist_penalty, genre_penalty=self.genre_penalty,
        )
        return [by_id[song["id"]] for song, _, _ in results]

    def explain_recommendation(self, user: UserProfile, song: Song) -> str:
        """Return a comma-separated list of the scoring reasons for this song."""
        _, reasons = score_song(
            self._prefs(user), asdict(song), self.strategy.weights
        )
        return ", ".join(reasons)

def load_songs(csv_path: str) -> List[Dict]:
    """
    Loads songs from a CSV file.
    Required by src/main.py
    """
    int_fields = ("id", "popularity", "release_decade", "explicit", "duration_sec")
    float_fields = (
        "energy", "tempo_bpm", "valence", "danceability", "acousticness",
        "instrumentalness",
    )
    songs = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            for name in int_fields:
                row[name] = int(row[name])
            for name in float_fields:
                row[name] = float(row[name])
            row["mood_tags"] = [t for t in row["mood_tags"].split("|") if t]
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
        gap = min(gap / GAP_SPANS.get(feature, 1.0), 1.0)
        points = w[feature] * (1 - gap)
        score += points
        reasons.append(f"{feature} closeness (+{points:.2f})")

    wanted_tags = user_prefs.get("mood_tags")
    if wanted_tags:
        overlap = set(wanted_tags) & set(song["mood_tags"])
        if overlap:
            points = w["mood_tags"] * len(overlap) / len(set(wanted_tags))
            score += points
            reasons.append(f"mood tags {'/'.join(sorted(overlap))} (+{points:.2f})")

    if user_prefs.get("explicit") is not None:
        if song["explicit"] and not user_prefs["explicit"]:
            reasons.append("explicit lyrics unwanted (+0.00)")
        else:
            score += w["explicit"]
            reasons.append(f"explicit preference ok (+{w['explicit']:.2f})")

    return score, reasons

def recommend_songs(
    user_prefs: Dict,
    songs: List[Dict],
    k: int = 5,
    weights: Optional[Dict[str, float]] = None,
    strategy="balanced",
    artist_penalty: float = ARTIST_PENALTY,
    genre_penalty: float = GENRE_PENALTY,
) -> List[Tuple[Dict, float, str]]:
    """
    Functional implementation of the recommendation logic.
    Required by src/main.py
    Ranks with `strategy` (name or RankingStrategy) unless explicit `weights` are given.
    Picks greedily: each next song is the best remaining one after subtracting
    `artist_penalty` per already-picked song by its artist and `genre_penalty` per
    already-picked song in its genre (pass 0 for both to disable).
    Returns (song_dict, score, explanation), best first, ties broken by title.
    """
    weights = weights or get_strategy(strategy).weights
    pool = [(song, *score_song(user_prefs, song, weights)) for song in songs]
    picked: List[Tuple[Dict, float, str]] = []
    artists: Dict[str, int] = {}
    genres: Dict[str, int] = {}

    while pool and len(picked) < k:
        def adjusted(item):
            song, score, _ = item
            return (
                score
                - artist_penalty * artists.get(song["artist"], 0)
                - genre_penalty * genres.get(song["genre"], 0)
            )

        best = min(pool, key=lambda item: (-adjusted(item), item[0]["title"]))
        pool.remove(best)
        song, score, reasons = best
        reasons = list(reasons)
        cost = artist_penalty * artists.get(song["artist"], 0)
        if cost:
            reasons.append(f"repeat artist penalty (-{cost:.2f})")
        cost = genre_penalty * genres.get(song["genre"], 0)
        if cost:
            reasons.append(f"repeat genre penalty (-{cost:.2f})")
        picked.append((song, adjusted(best), ", ".join(reasons)))
        artists[song["artist"]] = artists.get(song["artist"], 0) + 1
        genres[song["genre"]] = genres.get(song["genre"], 0) + 1
    return picked

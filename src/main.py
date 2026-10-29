"""
Command line runner for the Music Recommender Simulation.

This file helps you quickly run and test your recommender.

You will implement the functions in recommender.py:
- load_songs
- score_song
- recommend_songs
"""

try:
    from .recommender import load_songs, recommend_songs
except ImportError:  # run directly as `python src/main.py`
    from recommender import load_songs, recommend_songs


WIDTH = 60

# Distinct taste profiles, one target value per scored feature
PROFILES = {
    "High-Energy Pop": {
        "genre": "pop",
        "mood": "happy",
        "energy": 0.90,
        "acousticness": 0.10,
        "valence": 0.85,
        "tempo_bpm": 128,
        "danceability": 0.85,
    },
    "Chill Lofi": {
        "genre": "lofi",
        "mood": "chill",
        "energy": 0.40,
        "acousticness": 0.80,
        "valence": 0.60,
        "tempo_bpm": 78,
        "danceability": 0.60,
    },
    "Deep Intense Rock": {
        "genre": "rock",
        "mood": "intense",
        "energy": 0.92,
        "acousticness": 0.10,
        "valence": 0.35,
        "tempo_bpm": 150,
        "danceability": 0.45,
    },
}

# Adversarial / edge-case profiles meant to stress the scoring logic
EDGE_PROFILES = {
    "Sad but Hyper": {
        "genre": "pop", "mood": "sad", "energy": 0.90,
        "acousticness": 0.20, "valence": 0.20,
    },
    "Unknown Genre": {
        "genre": "k-pop", "mood": "happy", "energy": 0.80,
        "acousticness": 0.20, "valence": 0.80,
    },
    "Near-Miss Genre": {
        "genre": "indie", "mood": "happy", "energy": 0.70,
        "acousticness": 0.40, "valence": 0.75,
    },
    "Out-of-Range Numbers": {
        "genre": "pop", "mood": "happy", "energy": 1.5,
        "acousticness": -0.5, "valence": 0.5, "tempo_bpm": 300,
    },
    "Dead Center": {
        "genre": "jazz", "mood": "relaxed", "energy": 0.5,
        "acousticness": 0.5, "valence": 0.5, "tempo_bpm": 100,
        "danceability": 0.5,
    },
    "Extremist": {
        "genre": "classical", "mood": "melancholic", "energy": 0.0,
        "acousticness": 1.0, "valence": 0.0,
    },
    "Missing Keys": {
        "energy": 0.5, "acousticness": 0.5, "valence": 0.5,
    },
    "Genre-Only Loyalist": {
        "genre": "lofi", "mood": "angry", "energy": 0.95,
        "acousticness": 0.10, "valence": 0.30,
    },
}


def format_recommendations(recommendations) -> str:
    """Render (song, score, explanation) tuples as a readable terminal table."""
    lines = ["=" * WIDTH, "TOP RECOMMENDATIONS".center(WIDTH), "=" * WIDTH]
    for rank, (song, score, explanation) in enumerate(recommendations, start=1):
        lines.append(f"#{rank}  {song['title']}")
        lines.append(f"    {song['artist']}  |  Score: {score:.2f}")
        lines.append("    Reasons:")
        for reason in explanation.split(", "):
            lines.append(f"      - {reason}")
        lines.append("-" * WIDTH)
    return "\n".join(lines)


def main() -> None:
    songs = load_songs("data/songs.csv")
    print(f"Loaded songs: {len(songs)}")

    for name, user_prefs in {**PROFILES, **EDGE_PROFILES}.items():
        print(f"\nProfile: {name}")
        try:
            recommendations = recommend_songs(user_prefs, songs, k=5)
        except KeyError as err:
            print(f"ERROR: recommender crashed, missing preference {err}")
            continue
        print(format_recommendations(recommendations))


if __name__ == "__main__":
    main()

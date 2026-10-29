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

    # Taste profile: "Late-night study session" listener
    # One target value per scored feature
    user_prefs = {
        "genre": "lofi",
        "mood": "chill",
        "energy": 0.40,
        "acousticness": 0.80,
        "valence": 0.60,
        "tempo_bpm": 78,
        "danceability": 0.60,
    }

    recommendations = recommend_songs(user_prefs, songs, k=5)

    print(format_recommendations(recommendations))


if __name__ == "__main__":
    main()

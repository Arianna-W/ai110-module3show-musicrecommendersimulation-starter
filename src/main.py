"""
Command line runner for the Music Recommender Simulation.

This file helps you quickly run and test your recommender.

You will implement the functions in recommender.py:
- load_songs
- score_song
- recommend_songs
"""

import argparse
import textwrap

try:
    from .recommender import STRATEGIES, load_songs, recommend_songs
except ImportError:  # run directly as `python src/main.py`
    from recommender import STRATEGIES, load_songs, recommend_songs


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
    "Nostalgic Throwback": {
        "genre": "synthwave",
        "mood": "moody",
        "energy": 0.65,
        "acousticness": 0.30,
        "valence": 0.50,
        "popularity": 60,
        "release_decade": 1980,
        "mood_tags": ["nostalgic", "dark", "driving"],
        "instrumentalness": 0.70,
        "explicit": False,
        "duration_sec": 230,
    },
    "Aggressive Underground": {
        "genre": "metal",
        "mood": "angry",
        "energy": 0.95,
        "acousticness": 0.05,
        "valence": 0.25,
        "popularity": 30,
        "release_decade": 2010,
        "mood_tags": ["aggressive", "rebellious"],
        "instrumentalness": 0.10,
        "explicit": True,
        "duration_sec": 270,
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


def _wrap(text: str, width: int) -> list:
    return textwrap.wrap(text, width) or [""]


def format_recommendations(recommendations) -> str:
    """Render (song, score, explanation) tuples as an ASCII table with reasons."""
    headers = ("#", "Song / Artist", "Score", "Reasons")
    widths = (2, 26, 5, 50)
    rule = "+" + "+".join("-" * (w + 2) for w in widths) + "+"

    def row(cells) -> str:
        return "| " + " | ".join(c.ljust(w) for c, w in zip(cells, widths)) + " |"

    lines = [rule, row(headers), rule.replace("-", "=")]
    for rank, (song, score, explanation) in enumerate(recommendations, start=1):
        song_lines = _wrap(song["title"], widths[1]) + _wrap(
            f"by {song['artist']}", widths[1]
        )
        reason_lines = []
        for reason in explanation.split(", "):
            wrapped = _wrap(reason, widths[3] - 2)
            reason_lines.append("- " + wrapped[0])
            reason_lines.extend("  " + w for w in wrapped[1:])
        for i in range(max(len(song_lines), len(reason_lines))):
            lines.append(row((
                str(rank) if i == 0 else "",
                song_lines[i] if i < len(song_lines) else "",
                f"{score:.2f}" if i == 0 else "",
                reason_lines[i] if i < len(reason_lines) else "",
            )))
        lines.append(rule)
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Music Recommender Simulation")
    parser.add_argument(
        "--mode", default="balanced", choices=sorted(STRATEGIES),
        help="ranking strategy: "
        + "; ".join(f"{s.name} = {s.description}" for s in STRATEGIES.values()),
    )
    parser.add_argument(
        "--no-diversity", action="store_true",
        help="turn off the repeat artist/genre penalty",
    )
    args = parser.parse_args()
    penalties = (
        {"artist_penalty": 0.0, "genre_penalty": 0.0} if args.no_diversity else {}
    )

    songs = load_songs("data/songs.csv")
    print(f"Loaded songs: {len(songs)}  |  Ranking mode: {args.mode}")

    for name, user_prefs in {**PROFILES, **EDGE_PROFILES}.items():
        print(f"\nProfile: {name}")
        try:
            recommendations = recommend_songs(
                user_prefs, songs, k=5, strategy=args.mode, **penalties
            )
        except KeyError as err:
            print(f"ERROR: recommender crashed, missing preference {err}")
            continue
        print(format_recommendations(recommendations))


if __name__ == "__main__":
    main()

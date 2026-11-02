from src.recommender import Song, UserProfile, Recommender

def make_small_recommender() -> Recommender:
    songs = [
        Song(
            id=1,
            title="Test Pop Track",
            artist="Test Artist",
            genre="pop",
            mood="happy",
            energy=0.8,
            tempo_bpm=120,
            valence=0.9,
            danceability=0.8,
            acousticness=0.2,
        ),
        Song(
            id=2,
            title="Chill Lofi Loop",
            artist="Test Artist",
            genre="lofi",
            mood="chill",
            energy=0.4,
            tempo_bpm=80,
            valence=0.6,
            danceability=0.5,
            acousticness=0.9,
        ),
    ]
    return Recommender(songs)


def test_recommend_returns_songs_sorted_by_score():
    user = UserProfile(
        favorite_genre="pop",
        favorite_mood="happy",
        target_energy=0.8,
        likes_acoustic=False,
    )
    rec = make_small_recommender()
    results = rec.recommend(user, k=2)

    assert len(results) == 2
    # Starter expectation: the pop, happy, high energy song should score higher
    assert results[0].genre == "pop"
    assert results[0].mood == "happy"


def test_explain_recommendation_returns_non_empty_string():
    user = UserProfile(
        favorite_genre="pop",
        favorite_mood="happy",
        target_energy=0.8,
        likes_acoustic=False,
    )
    rec = make_small_recommender()
    song = rec.songs[0]

    explanation = rec.explain_recommendation(user, song)
    assert isinstance(explanation, str)
    assert explanation.strip() != ""


# --- new attributes, ranking strategies and diversity penalty ---

import pytest
from src.recommender import STRATEGIES, get_strategy, load_songs, recommend_songs, score_song


def _song(**overrides):
    song = {
        "id": 1, "title": "A", "artist": "X", "genre": "pop", "mood": "happy",
        "energy": 0.8, "tempo_bpm": 120, "valence": 0.8, "danceability": 0.8,
        "acousticness": 0.2, "popularity": 80, "release_decade": 2010,
        "mood_tags": ["euphoric", "bright"], "instrumentalness": 0.1,
        "explicit": 0, "duration_sec": 200,
    }
    song.update(overrides)
    return song


BASE_PREFS = {"genre": "pop", "mood": "happy", "energy": 0.8,
              "acousticness": 0.2, "valence": 0.8}


def test_load_songs_parses_new_attributes():
    songs = load_songs("data/songs.csv")
    assert len(songs[0]) >= 16
    assert isinstance(songs[0]["mood_tags"], list) and songs[0]["mood_tags"]
    assert 0 <= songs[0]["popularity"] <= 100


def test_new_attributes_are_optional():
    _, reasons = score_song(BASE_PREFS, _song())
    assert not any("popularity" in r or "tags" in r for r in reasons)


def test_mood_tags_partial_credit():
    prefs = {**BASE_PREFS, "mood_tags": ["euphoric", "dark"]}
    none = score_song(BASE_PREFS, _song())[0]
    assert score_song(prefs, _song())[0] == pytest.approx(none + 0.5)


def test_popularity_and_decade_closeness():
    prefs = {**BASE_PREFS, "popularity": 80, "release_decade": 2010}
    far = _song(popularity=0, release_decade=1950)
    assert score_song(prefs, _song())[0] > score_song(prefs, far)[0]


def test_explicit_opt_out_loses_points():
    prefs = {**BASE_PREFS, "explicit": False}
    assert score_song(prefs, _song())[0] > score_song(prefs, _song(explicit=1))[0]


def test_strategies_change_ranking():
    songs = [
        _song(id=1, title="GenreMatch", genre="pop", mood="sad", artist="A"),
        _song(id=2, title="MoodMatch", genre="rock", mood="happy", artist="B"),
    ]
    first = recommend_songs(BASE_PREFS, songs, k=1, strategy="genre-first")
    second = recommend_songs(BASE_PREFS, songs, k=1, strategy="mood-first")
    assert first[0][0]["title"] == "GenreMatch"
    assert second[0][0]["title"] == "MoodMatch"


def test_unknown_strategy_raises():
    with pytest.raises(ValueError):
        get_strategy("nope")
    assert {"balanced", "genre-first", "mood-first", "energy-focused"} <= set(STRATEGIES)


def test_diversity_penalty_demotes_repeat_artist():
    songs = [
        _song(id=1, title="A1", artist="Same"),
        _song(id=2, title="A2", artist="Same", genre="rock"),
        _song(id=3, title="B1", artist="Other", genre="jazz"),
    ]
    plain = recommend_songs(BASE_PREFS, songs, k=2, artist_penalty=0, genre_penalty=0)
    diverse = recommend_songs(BASE_PREFS, songs, k=2)
    assert [s["title"] for s, _, _ in plain] == ["A1", "A2"]
    assert [s["title"] for s, _, _ in diverse] == ["A1", "B1"]
    assert "repeat" not in plain[1][2]

# 🎵 Music Recommender Simulation

## Project Summary

**LofiMatch** is a small, command-line music recommender. It reads an 18-song catalog from `data/songs.csv`, compares each song to a user's taste profile, and prints the top five matches along with the reasons each one was picked.

- **Taste profile:** a favorite genre and mood, a target energy level, an acoustic preference and a target positivity (valence), plus an optional target tempo and danceability.
- **Scoring:** every song earns up to 7 points. Genre and mood are all-or-nothing matches, and the numeric features earn partial credit the closer they are to the user's target.
- **Output:** a ranked list where each song shows a point-by-point breakdown, such as "genre match (+2.00)" or "energy closeness (+1.96)".
- **Focus:** the demo profile is a late-night study session, so the system is tuned to surface calm, low-energy, acoustic-leaning lofi tracks.

It is a content-based system that works only from the profile the user states. It has no listening history and can't learn from behavior, which is the main way it differs from real recommenders. The sections below explain the scoring in detail, show sample output, and cover the experiments and biases I found.

---

## How The System Works

This is a **content-based** recommender. It compares a user's taste profile to the attributes of each song, scores every song, and returns the best matches.

### Concept sketch

```
 UserProfile                         Song catalog (data/songs.csv)
 ───────────                         ─────────────────────────────
 favorite_genre ──────────────┐      ┌──── genre
 favorite_mood  ──────────────┤      ├──── mood
 target_energy  ──────────────┤      ├──── energy
 likes_acoustic ──────────────┼─────►├──── acousticness
 target_valence ──────────────┤      ├──── valence
 target_tempo_bpm (optional) ─┤      ├──── tempo_bpm
 target_danceability (opt.) ──┘      └──── danceability
                                  │
                      Scoring Rule (one song at a time)
                                  │
                         score between 0 and 7
                                  │
                      Ranking Rule (all songs)
                    sort high to low, return top k
                                  │
                   Top k songs + a reason for each
```

### Song features

| Feature | Used in score? | Role |
|---|---|---|
| `genre` | Yes | Exact match with the user's favorite genre |
| `mood` | Yes | Exact match with the user's favorite mood |
| `energy` | Yes | Closeness to the user's target energy |
| `acousticness` | Yes | Closeness to the user's acoustic preference |
| `valence` | Yes | Closeness to the user's target valence (how positive the song sounds) |
| `tempo_bpm` | Yes, if the user sets a target | Closeness to the user's target tempo (a gap of 120 BPM or more earns nothing) |
| `danceability` | Yes, if the user sets a target | Closeness to the user's target danceability |
| `id`, `title`, `artist` | No | Display only |

### UserProfile

- `favorite_genre`: the genre the user prefers
- `favorite_mood`: the mood the user prefers
- `target_energy`: the energy level they want, from 0 to 1
- `likes_acoustic`: whether they prefer acoustic songs (target acousticness 0.8) or not (0.2)
- `target_valence`: how positive they want songs to sound, from 0 to 1 (optional, defaults to 0.5)
- `target_tempo_bpm`: the tempo they want in beats per minute (optional; if left out, tempo is not scored)
- `target_danceability`: how danceable they want songs to be, from 0 to 1 (optional; if left out, danceability is not scored)

The scoring functions take the same profile as a dictionary of target values (see "Taste profile used for comparison" below). `likes_acoustic` becomes the numeric `acousticness` target (0.8 or 0.2), `target_energy` becomes `energy`, `target_valence` becomes `valence`, `target_tempo_bpm` becomes `tempo_bpm` and `target_danceability` becomes `danceability`. The original `UserProfile` fields are unchanged.

### Taste profile used for comparison

The recommender is run against one concrete profile, a "late-night study session" listener (defined in `src/main.py`). It is a dictionary with one target value for each feature in the score:

```python
user_prefs = {
    "genre": "lofi",         # compared by exact match
    "mood": "chill",         # compared by exact match
    "energy": 0.40,          # compared by closeness
    "acousticness": 0.80,    # compared by closeness
    "valence": 0.60,         # compared by closeness
    "tempo_bpm": 78,         # compared by closeness (optional)
    "danceability": 0.60,    # compared by closeness (optional)
}
```

- **Genre `lofi` and mood `chill`:** the user wants calm background music, and both match several songs in the catalog.
- **Energy 0.40:** low but not silent. Closeness scoring ranks mid-low songs (such as *Midnight Coding*, 0.42) above both very quiet ambient tracks and high-energy ones.
- **Acoustic preference:** favors warm, acoustic-sounding songs over electronic ones.
- **Valence 0.60:** a calm, neutral-to-pleasant feel. It keeps sad songs such as *Blue Highway Blues* (0.30) from ranking high just because they are quiet and acoustic.

- **Tempo 78 BPM and danceability 0.60:** a slow, steady groove. This is the pace of the lofi tracks in the catalog (72 to 80 BPM).

The profile separates close matches from near misses. *Library Rain* and *Midnight Coding* should rank at the top. *Coffee Shop Stories* (jazz, relaxed) and *Spacewalk Thoughts* (ambient, chill) should rank in the middle. *Iron Hymn* and *Bass Cathedral* should rank at the bottom.

### Scoring Rule (one song)

```
score = 2.0 * genre_match
      + 1.0 * mood_match
      + 2.0 * energy_closeness
      + 0.5 * valence_closeness
      + 0.5 * acousticness_closeness
      + 0.5 * tempo_closeness             (only if the user sets a tempo target)
      + 0.5 * danceability_closeness      (only if the user sets a danceability target)
                                          (max score 7.0)

closeness(song_value, target) = 1 - abs(song_value - target)
tempo_closeness = 1 - min(abs(song_bpm - target_bpm) / 120, 1)
match = 1 if equal, else 0
```

Genre and mood are all-or-nothing, so their weights set how much a match can swing the ranking. Closeness rewards songs near the user's target, not songs with a higher or lower value. Energy gets the largest numeric weight because it separates calm songs from intense ones most reliably, and it always contributes, which avoids ties. Valence, acousticness, tempo and danceability (0.5 each) refine the ranking, mostly by separating songs that already match on the bigger features. The weights are named constants (`BASE_WEIGHTS`, `MOOD_FIRST_WEIGHTS`) in `src/recommender.py`.

Sanity check (without tempo and danceability targets): a song matching genre and mood with energy off by 0.6 scores about 3.8. A song matching neither categorical feature but fitting the numbers perfectly scores about 3.0. Taste matches win, but a badly wrong energy can still pull a song down.

### Ranking Rule (all songs)

1. Score every song in the catalog.
2. Sort from highest to lowest score, breaking ties by title.
3. Return the top `k` songs, each with the reasons it scored well.

### Algorithm Recipe (final)

1. **Input:** a user profile with a target for each scored feature, plus the song catalog loaded from `data/songs.csv`.
2. **Score each song** (max 7.0 points):
   - +2.0 if the genre matches
   - +1.0 if the mood matches
   - up to +2.0 for energy closeness
   - up to +0.5 for valence closeness
   - up to +0.5 for acousticness closeness
   - up to +0.5 for tempo closeness (only if the user sets a tempo target)
   - up to +0.5 for danceability closeness (only if the user sets a danceability target)
3. **Rank** by score, highest first, with ties broken by title.
4. **Output** the top `k` songs, each with the point-by-point reasons behind its score.

### Expected biases

- **Genre over-prioritized.** Genre is worth twice mood, so a song in the user's genre can outrank a better-fitting song in another genre. In the swap experiment, *Focus Flow* (lofi, focused) ranked above *Spacewalk Thoughts* (ambient, chill) for a lofi/chill listener.
- **Exact-match labels are too rigid.** "chill" and "relaxed" get no credit for being similar, and "indie pop" does not match "pop". A near-identical song gets zero points for a different label.
- **Energy dominates among numeric features.** At 2.0 points it can outweigh a genre or mood match, so a song with the right energy but the wrong feel can still rank well.
- **Small catalog.** Most genres have one song, so a genre match often decides the #1 result, and the rest of the top 5 is filled by numeric closeness alone.
- **Echo chamber.** The system only rewards similarity to the stated profile. It can't surface songs unlike what the user already described.
- **Small tempo and danceability weights.** At 0.5 points each they mostly break ties. They can't rescue a song that misses on genre, mood and energy. They also only count if the user sets a target, so a profile without them ignores those features.

### How real recommenders do it at scale

Platforms like Spotify and YouTube combine two kinds of signals:

- **Collaborative filtering** uses behavior from millions of users (plays, skips, saves, playlist adds, watch time) to find "people like you liked this."
- **Content-based filtering** uses the attributes of the item (audio features, genre, mood, text) to find "this is similar to what you liked." This is what this project simulates.

At scale this runs as a pipeline: a fast model narrows millions of items to hundreds of candidates, a heavier model ranks them using history and context (time of day, device), and a final step adjusts for diversity and freshness. Real systems depend mostly on **implicit feedback** such as skips and replays, because few users rate anything. This simulation has no behavior data, so it can't learn from users and can't recommend songs that are unlike what the profile already describes.

---

## Getting Started

### Setup

1. Create a virtual environment (optional but recommended):

   ```bash
   python -m venv .venv
   source .venv/bin/activate      # Mac or Linux
   .venv\Scripts\activate         # Windows
   ```

2. Install dependencies

```bash
pip install -r requirements.txt
```

3. Run the app:

```bash
python -m src.main
```

### Running Tests

Run the starter tests with:

```bash
pytest
```

You can add more tests in `tests/test_recommender.py`.

---

## Sample Recommendation Output

Output of `python src/main.py` for the late-night study profile (genre=lofi, mood=chill, energy=0.40, acousticness=0.80, valence=0.60, tempo=78 BPM, danceability=0.60):

```
============================================================
                    TOP RECOMMENDATIONS
============================================================
#1  Midnight Coding
    LoRoom  |  Score: 6.89
    Reasons:
      - genre match (+2.00)
      - mood match (+1.00)
      - energy closeness (+1.96)
      - valence closeness (+0.48)
      - acousticness closeness (+0.45)
      - tempo_bpm closeness (+0.50)
      - danceability closeness (+0.49)
------------------------------------------------------------
#2  Library Rain
    Paper Lanterns  |  Score: 6.83
    Reasons:
      - genre match (+2.00)
      - mood match (+1.00)
      - energy closeness (+1.90)
      - valence closeness (+0.50)
      - acousticness closeness (+0.47)
      - tempo_bpm closeness (+0.47)
      - danceability closeness (+0.49)
------------------------------------------------------------
#3  Focus Flow
    LoRoom  |  Score: 5.98
    Reasons:
      - genre match (+2.00)
      - energy closeness (+2.00)
      - valence closeness (+0.49)
      - acousticness closeness (+0.49)
      - tempo_bpm closeness (+0.49)
      - danceability closeness (+0.50)
------------------------------------------------------------
#4  Spacewalk Thoughts
    Orbit Bloom  |  Score: 4.50
    Reasons:
      - mood match (+1.00)
      - energy closeness (+1.76)
      - valence closeness (+0.47)
      - acousticness closeness (+0.44)
      - tempo_bpm closeness (+0.42)
      - danceability closeness (+0.41)
------------------------------------------------------------
#5  Coffee Shop Stories
    Slow Stereo  |  Score: 3.76
    Reasons:
      - energy closeness (+1.94)
      - valence closeness (+0.45)
      - acousticness closeness (+0.46)
      - tempo_bpm closeness (+0.45)
      - danceability closeness (+0.47)
------------------------------------------------------------
```

**Screenshot or video** *(optional)*: <!-- Insert a screenshot or demo video link here -->

---

## Experiments You Tried

### Swapping the genre and mood weights

Baseline: genre 2.0, mood 1.0. Experiment: genre 1.0, mood 2.0. Everything else unchanged. These runs happened before tempo and danceability were scored, so the profiles have no tempo or danceability targets and the scores below are out of 6.0. Each profile is a dictionary like the one in "Taste profile used for comparison"; the gym, sad acoustic and contradictory profiles are extra profiles used only for this test.

| Profile | Baseline top 5 | Swapped top 5 | What changed |
|---|---|---|---|
| Late-night study (lofi/chill) | Midnight Coding, Library Rain, **Focus Flow**, **Spacewalk Thoughts**, Coffee Shop Stories | Midnight Coding, Library Rain, **Spacewalk Thoughts**, **Focus Flow**, Coffee Shop Stories | Spacewalk Thoughts (ambient, chill) moves above Focus Flow (lofi, focused): 4.67 vs 3.99 |
| Gym (pop/intense) | Gym Hero, **Sunrise City**, **Storm Runner**, Bass Cathedral, Concrete Psalms | Gym Hero, **Storm Runner**, **Sunrise City**, Bass Cathedral, Concrete Psalms | Storm Runner (rock, intense) overtakes Sunrise City (pop, happy) |
| Sad acoustic (blues/sad) | Blue Highway Blues, then four close numeric fits | Same | No change. One song matches both, and the rest have no categorical match |
| Contradictory (metal/sad) | Iron Hymn (4.96), Storm Runner, Gym Hero, ... | Iron Hymn (3.96), **Blue Highway Blues (3.45)**, Storm Runner, ... | The sad song enters at #2, because a mood match now earns 2.0 points while a genre match earns only 1.0 |

**Takeaways**

- The #1 result never changed in any of the four profiles. The swap only reorders or replaces songs in lower positions, because one song already matches both genre and mood.
- With genre weighted higher, the system is stricter. It keeps same-genre songs ahead even when the feel is wrong (Focus Flow before Spacewalk Thoughts).
- With mood weighted higher, results are more varied and follow the listening context. The cost: the mood word becomes a single point of failure, so a song with a near-identical feel but a different mood label gets no credit.
- The contradictory profile shows the difference most clearly. Neither weighting is right, because the profile asks for something the catalog doesn't contain (loud and sad).
- Because the catalog has roughly one song per genre, a genre match works almost like picking the single #1 song. That is why I'd lean toward mood-first for a larger catalog, and I kept genre-first as the default only because it matches the common starting recipe.

---

## Limitations and Risks

Summarize some limitations of your recommender.

Examples:

- It only works on a tiny catalog
- It does not understand lyrics or language
- It might over favor one genre or mood

You will go deeper on this in your model card.

---

## Reflection

Read and complete `model_card.md`:

[**Model Card**](model_card.md)

Write 1 to 2 paragraphs here about what you learned:

- about how recommenders turn data into predictions
- about where bias or unfairness could show up in systems like this




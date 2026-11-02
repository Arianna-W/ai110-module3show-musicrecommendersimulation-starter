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
| `popularity` (0-100) | Yes, if the user sets a target | Closeness to the target popularity |
| `release_decade` | Yes, if the user sets a target | Closeness to the target decade (a 50-year gap earns nothing) |
| `mood_tags` | Yes, if the user lists tags | Share of the user's wanted tags the song has (e.g. `nostalgic\|dark\|driving`) |
| `instrumentalness` | Yes, if the user sets a target | Closeness to the target instrumentalness |
| `explicit` | Yes, if the user states a preference | Earns points unless the user opted out of explicit songs |
| `duration_sec` | Yes, if the user sets a target | Closeness to the target length (a 180-second gap earns nothing) |
| `id`, `title`, `artist` | No | Display only (`artist` also drives the diversity penalty) |

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
      + optional extras, each only if the user sets a target: popularity 0.5, release decade 0.5,
        mood tags 1.0, instrumentalness 0.5, explicit 0.25, duration 0.25
                                          (max 7.0 with these seven; up to 10.5 with every optional attribute)

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
2. **Score each song** (max 7.0 points from the core features):
   - +2.0 if the genre matches
   - +1.0 if the mood matches
   - up to +2.0 for energy closeness
   - up to +0.5 for valence closeness
   - up to +0.5 for acousticness closeness
   - up to +0.5 for tempo closeness (only if the user sets a tempo target)
   - up to +0.5 for danceability closeness (only if the user sets a danceability target)
   - optional extras, each only if the user sets a target: popularity (0.5), release decade (0.5), mood tags (1.0), instrumentalness (0.5), explicit (0.25), duration (0.25), for a theoretical max of 10.5
3. **Rank** by score (using the chosen `--mode` weights), highest first, ties broken by title. Each pick subtracts a diversity penalty for artists and genres already picked.
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

## Ranking Modes, Diversity and Output

**Ranking modes.** Each mode is a named weight set (a Strategy pattern, `RankingStrategy` in `src/recommender.py`). Pick one with `--mode`:

| Mode | Emphasis |
|---|---|
| `balanced` (default) | The default weights |
| `genre-first` | Genre counts most, mood is a minor bonus |
| `mood-first` | Mood and mood tags count most, genre is secondary |
| `energy-focused` | Energy, tempo and danceability dominate |

**Diversity penalty.** Songs are picked one at a time. Each candidate loses 1.0 point per already-picked song by the same artist and 0.5 per already-picked song in the same genre, so the top 5 doesn't fill up with one artist. Turn it off with `--no-diversity`.

**Output.** Recommendations print as an ASCII table with a Reasons column, including any penalty lines.

```bash
python src/main.py                      # balanced, with diversity penalty
python src/main.py --mode mood-first
python src/main.py --no-diversity
```

The saved sample outputs below were captured before the new attributes, modes, diversity penalty and table format, so rerun the script to see current output.

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

`tests/test_recommender.py` covers the recommender, the new attribute scoring, the ranking modes and the diversity penalty.

---

## Sample Recommendation Output

Output of `python src/main.py` for the late-night study profile (genre=lofi, mood=chill, energy=0.40, acousticness=0.80, valence=0.60, tempo=78 BPM, danceability=0.60):

```
+----+----------------------------+-------+----------------------------------------------------+
| #  | Song / Artist              | Score | Reasons                                            |
+====+============================+=======+====================================================+
| 1  | Midnight Coding            | 6.89  | - genre match (+2.00)                              |
|    | by LoRoom                  |       | - mood match (+1.00)                               |
|    |                            |       | - energy closeness (+1.96)                         |
|    |                            |       | - valence closeness (+0.48)                        |
|    |                            |       | - acousticness closeness (+0.45)                   |
|    |                            |       | - tempo_bpm closeness (+0.50)                      |
|    |                            |       | - danceability closeness (+0.49)                   |
+----+----------------------------+-------+----------------------------------------------------+
| 2  | Library Rain               | 6.33  | - genre match (+2.00)                              |
|    | by Paper Lanterns          |       | - mood match (+1.00)                               |
|    |                            |       | - energy closeness (+1.90)                         |
|    |                            |       | - valence closeness (+0.50)                        |
|    |                            |       | - acousticness closeness (+0.47)                   |
|    |                            |       | - tempo_bpm closeness (+0.47)                      |
|    |                            |       | - danceability closeness (+0.49)                   |
|    |                            |       | - repeat genre penalty (-0.50)                     |
+----+----------------------------+-------+----------------------------------------------------+
| 3  | Spacewalk Thoughts         | 4.50  | - mood match (+1.00)                               |
|    | by Orbit Bloom             |       | - energy closeness (+1.76)                         |
|    |                            |       | - valence closeness (+0.47)                        |
|    |                            |       | - acousticness closeness (+0.44)                   |
|    |                            |       | - tempo_bpm closeness (+0.42)                      |
|    |                            |       | - danceability closeness (+0.41)                   |
+----+----------------------------+-------+----------------------------------------------------+
| 4  | Focus Flow                 | 3.98  | - genre match (+2.00)                              |
|    | by LoRoom                  |       | - energy closeness (+2.00)                         |
|    |                            |       | - valence closeness (+0.49)                        |
|    |                            |       | - acousticness closeness (+0.49)                   |
|    |                            |       | - tempo_bpm closeness (+0.49)                      |
|    |                            |       | - danceability closeness (+0.50)                   |
|    |                            |       | - repeat artist penalty (-1.00)                    |
|    |                            |       | - repeat genre penalty (-1.00)                     |
+----+----------------------------+-------+----------------------------------------------------+
| 5  | Coffee Shop Stories        | 3.76  | - energy closeness (+1.94)                         |
|    | by Slow Stereo             |       | - valence closeness (+0.45)                        |
|    |                            |       | - acousticness closeness (+0.46)                   |
|    |                            |       | - tempo_bpm closeness (+0.45)                      |
|    |                            |       | - danceability closeness (+0.47)                   |
+----+----------------------------+-------+----------------------------------------------------+
```

**Screenshot or video** *(optional)*: <!-- Insert a screenshot or demo video link here -->

---

## Profile Test Results (Standard and Edge Cases)

Output of `python src/main.py` for every profile in `PROFILES` and `EDGE_PROFILES` (top 5 each, k=5).

### High-Energy Pop

Clean win: Sunrise City matches genre and mood.

```
+----+----------------------------+-------+----------------------------------------------------+
| #  | Song / Artist              | Score | Reasons                                            |
+====+============================+=======+====================================================+
| 1  | Sunrise City               | 6.72  | - genre match (+2.00)                              |
|    | by Neon Echo               |       | - mood match (+1.00)                               |
|    |                            |       | - energy closeness (+1.84)                         |
|    |                            |       | - valence closeness (+0.49)                        |
|    |                            |       | - acousticness closeness (+0.46)                   |
|    |                            |       | - tempo_bpm closeness (+0.46)                      |
|    |                            |       | - danceability closeness (+0.47)                   |
+----+----------------------------+-------+----------------------------------------------------+
| 2  | Gym Hero                   | 5.34  | - genre match (+2.00)                              |
|    | by Max Pulse               |       | - energy closeness (+1.94)                         |
|    |                            |       | - valence closeness (+0.46)                        |
|    |                            |       | - acousticness closeness (+0.47)                   |
|    |                            |       | - tempo_bpm closeness (+0.48)                      |
|    |                            |       | - danceability closeness (+0.48)                   |
|    |                            |       | - repeat genre penalty (-0.50)                     |
+----+----------------------------+-------+----------------------------------------------------+
| 3  | Rooftop Lights             | 4.54  | - mood match (+1.00)                               |
|    | by Indigo Parade           |       | - energy closeness (+1.72)                         |
|    |                            |       | - valence closeness (+0.48)                        |
|    |                            |       | - acousticness closeness (+0.38)                   |
|    |                            |       | - tempo_bpm closeness (+0.48)                      |
|    |                            |       | - danceability closeness (+0.48)                   |
+----+----------------------------+-------+----------------------------------------------------+
| 4  | Bass Cathedral             | 3.82  | - energy closeness (+1.90)                         |
|    | by Kilo Verse              |       | - valence closeness (+0.48)                        |
|    |                            |       | - acousticness closeness (+0.46)                   |
|    |                            |       | - tempo_bpm closeness (+0.50)                      |
|    |                            |       | - danceability closeness (+0.47)                   |
+----+----------------------------+-------+----------------------------------------------------+
| 5  | Storm Runner               | 3.60  | - energy closeness (+1.98)                         |
|    | by Voltline                |       | - valence closeness (+0.32)                        |
|    |                            |       | - acousticness closeness (+0.50)                   |
|    |                            |       | - tempo_bpm closeness (+0.40)                      |
|    |                            |       | - danceability closeness (+0.41)                   |
+----+----------------------------+-------+----------------------------------------------------+
```

### Chill Lofi

Same as the sample output above. The diversity penalty moves Focus Flow (a second LoRoom song and a third lofi song) from #3 to #4, below Spacewalk Thoughts.

```
+----+----------------------------+-------+----------------------------------------------------+
| #  | Song / Artist              | Score | Reasons                                            |
+====+============================+=======+====================================================+
| 1  | Midnight Coding            | 6.89  | - genre match (+2.00)                              |
|    | by LoRoom                  |       | - mood match (+1.00)                               |
|    |                            |       | - energy closeness (+1.96)                         |
|    |                            |       | - valence closeness (+0.48)                        |
|    |                            |       | - acousticness closeness (+0.45)                   |
|    |                            |       | - tempo_bpm closeness (+0.50)                      |
|    |                            |       | - danceability closeness (+0.49)                   |
+----+----------------------------+-------+----------------------------------------------------+
| 2  | Library Rain               | 6.33  | - genre match (+2.00)                              |
|    | by Paper Lanterns          |       | - mood match (+1.00)                               |
|    |                            |       | - energy closeness (+1.90)                         |
|    |                            |       | - valence closeness (+0.50)                        |
|    |                            |       | - acousticness closeness (+0.47)                   |
|    |                            |       | - tempo_bpm closeness (+0.47)                      |
|    |                            |       | - danceability closeness (+0.49)                   |
|    |                            |       | - repeat genre penalty (-0.50)                     |
+----+----------------------------+-------+----------------------------------------------------+
| 3  | Spacewalk Thoughts         | 4.50  | - mood match (+1.00)                               |
|    | by Orbit Bloom             |       | - energy closeness (+1.76)                         |
|    |                            |       | - valence closeness (+0.47)                        |
|    |                            |       | - acousticness closeness (+0.44)                   |
|    |                            |       | - tempo_bpm closeness (+0.42)                      |
|    |                            |       | - danceability closeness (+0.41)                   |
+----+----------------------------+-------+----------------------------------------------------+
| 4  | Focus Flow                 | 3.98  | - genre match (+2.00)                              |
|    | by LoRoom                  |       | - energy closeness (+2.00)                         |
|    |                            |       | - valence closeness (+0.49)                        |
|    |                            |       | - acousticness closeness (+0.49)                   |
|    |                            |       | - tempo_bpm closeness (+0.49)                      |
|    |                            |       | - danceability closeness (+0.50)                   |
|    |                            |       | - repeat artist penalty (-1.00)                    |
|    |                            |       | - repeat genre penalty (-1.00)                     |
+----+----------------------------+-------+----------------------------------------------------+
| 5  | Coffee Shop Stories        | 3.76  | - energy closeness (+1.94)                         |
|    | by Slow Stereo             |       | - valence closeness (+0.45)                        |
|    |                            |       | - acousticness closeness (+0.46)                   |
|    |                            |       | - tempo_bpm closeness (+0.45)                      |
|    |                            |       | - danceability closeness (+0.47)                   |
+----+----------------------------+-------+----------------------------------------------------+
```

### Deep Intense Rock

Only one rock song exists, so #2 onward is energy-driven (a pop song takes #2 on mood).

```
+----+----------------------------+-------+----------------------------------------------------+
| #  | Song / Artist              | Score | Reasons                                            |
+====+============================+=======+====================================================+
| 1  | Storm Runner               | 6.80  | - genre match (+2.00)                              |
|    | by Voltline                |       | - mood match (+1.00)                               |
|    |                            |       | - energy closeness (+1.98)                         |
|    |                            |       | - valence closeness (+0.43)                        |
|    |                            |       | - acousticness closeness (+0.50)                   |
|    |                            |       | - tempo_bpm closeness (+0.49)                      |
|    |                            |       | - danceability closeness (+0.40)                   |
+----+----------------------------+-------+----------------------------------------------------+
| 2  | Gym Hero                   | 4.46  | - mood match (+1.00)                               |
|    | by Max Pulse               |       | - energy closeness (+1.98)                         |
|    |                            |       | - valence closeness (+0.29)                        |
|    |                            |       | - acousticness closeness (+0.47)                   |
|    |                            |       | - tempo_bpm closeness (+0.42)                      |
|    |                            |       | - danceability closeness (+0.29)                   |
+----+----------------------------+-------+----------------------------------------------------+
| 3  | Iron Hymn                  | 3.75  | - energy closeness (+1.90)                         |
|    | by Black Ritual            |       | - valence closeness (+0.45)                        |
|    |                            |       | - acousticness closeness (+0.47)                   |
|    |                            |       | - tempo_bpm closeness (+0.42)                      |
|    |                            |       | - danceability closeness (+0.50)                   |
+----+----------------------------+-------+----------------------------------------------------+
| 4  | Bass Cathedral             | 3.32  | - energy closeness (+1.94)                         |
|    | by Kilo Verse              |       | - valence closeness (+0.23)                        |
|    |                            |       | - acousticness closeness (+0.46)                   |
|    |                            |       | - tempo_bpm closeness (+0.41)                      |
|    |                            |       | - danceability closeness (+0.27)                   |
+----+----------------------------+-------+----------------------------------------------------+
| 5  | Night Drive Loop           | 3.22  | - energy closeness (+1.66)                         |
|    | by Neon Echo               |       | - valence closeness (+0.43)                        |
|    |                            |       | - acousticness closeness (+0.44)                   |
|    |                            |       | - tempo_bpm closeness (+0.33)                      |
|    |                            |       | - danceability closeness (+0.36)                   |
+----+----------------------------+-------+----------------------------------------------------+
```

### Nostalgic Throwback

Uses the newer attributes (decade 1980, popularity 60, mood tags nostalgic/dark/driving, instrumentalness 0.7, no explicit lyrics, about 230 seconds). Night Drive Loop wins by matching genre, mood and all three tags.

```
+----+----------------------------+-------+----------------------------------------------------+
| #  | Song / Artist              | Score | Reasons                                            |
+====+============================+=======+====================================================+
| 1  | Night Drive Loop           | 8.71  | - genre match (+2.00)                              |
|    | by Neon Echo               |       | - mood match (+1.00)                               |
|    |                            |       | - energy closeness (+1.80)                         |
|    |                            |       | - valence closeness (+0.49)                        |
|    |                            |       | - acousticness closeness (+0.46)                   |
|    |                            |       | - popularity closeness (+0.46)                     |
|    |                            |       | - release_decade closeness (+0.50)                 |
|    |                            |       | - instrumentalness closeness (+0.50)               |
|    |                            |       | - duration_sec closeness (+0.24)                   |
|    |                            |       | - mood tags dark/driving/nostalgic (+1.00)         |
|    |                            |       | - explicit preference ok (+0.25)                   |
+----+----------------------------+-------+----------------------------------------------------+
| 2  | Dust Road Home             | 4.34  | - energy closeness (+1.74)                         |
|    | by Hollow Pines            |       | - valence closeness (+0.41)                        |
|    |                            |       | - acousticness closeness (+0.28)                   |
|    |                            |       | - popularity closeness (+0.49)                     |
|    |                            |       | - release_decade closeness (+0.40)                 |
|    |                            |       | - instrumentalness closeness (+0.19)               |
|    |                            |       | - duration_sec closeness (+0.24)                   |
|    |                            |       | - mood tags nostalgic (+0.33)                      |
|    |                            |       | - explicit preference ok (+0.25)                   |
+----+----------------------------+-------+----------------------------------------------------+
| 3  | Island Clock               | 4.11  | - energy closeness (+1.80)                         |
|    | by Sol Tide                |       | - valence closeness (+0.35)                        |
|    |                            |       | - acousticness closeness (+0.42)                   |
|    |                            |       | - popularity closeness (+0.46)                     |
|    |                            |       | - release_decade closeness (+0.40)                 |
|    |                            |       | - instrumentalness closeness (+0.18)               |
|    |                            |       | - duration_sec closeness (+0.25)                   |
|    |                            |       | - explicit preference ok (+0.25)                   |
+----+----------------------------+-------+----------------------------------------------------+
| 4  | Storm Runner               | 4.10  | - energy closeness (+1.48)                         |
|    | by Voltline                |       | - valence closeness (+0.49)                        |
|    |                            |       | - acousticness closeness (+0.40)                   |
|    |                            |       | - popularity closeness (+0.44)                     |
|    |                            |       | - release_decade closeness (+0.30)                 |
|    |                            |       | - instrumentalness closeness (+0.18)               |
|    |                            |       | - duration_sec closeness (+0.23)                   |
|    |                            |       | - mood tags driving (+0.33)                        |
|    |                            |       | - explicit preference ok (+0.25)                   |
+----+----------------------------+-------+----------------------------------------------------+
| 5  | Coffee Shop Stories        | 4.03  | - energy closeness (+1.44)                         |
|    | by Slow Stereo             |       | - valence closeness (+0.40)                        |
|    |                            |       | - acousticness closeness (+0.20)                   |
|    |                            |       | - popularity closeness (+0.46)                     |
|    |                            |       | - release_decade closeness (+0.30)                 |
|    |                            |       | - instrumentalness closeness (+0.45)               |
|    |                            |       | - duration_sec closeness (+0.20)                   |
|    |                            |       | - mood tags nostalgic (+0.33)                      |
|    |                            |       | - explicit preference ok (+0.25)                   |
+----+----------------------------+-------+----------------------------------------------------+
```

### Aggressive Underground

Uses the newer attributes (decade 2010, popularity 30, mood tags aggressive/rebellious, explicit lyrics allowed, about 270 seconds). Iron Hymn wins on genre, mood and energy.

```
+----+----------------------------+-------+----------------------------------------------------+
| #  | Song / Artist              | Score | Reasons                                            |
+====+============================+=======+====================================================+
| 1  | Iron Hymn                  | 8.52  | - genre match (+2.00)                              |
|    | by Black Ritual            |       | - mood match (+1.00)                               |
|    |                            |       | - energy closeness (+1.96)                         |
|    |                            |       | - valence closeness (+0.50)                        |
|    |                            |       | - acousticness closeness (+0.49)                   |
|    |                            |       | - popularity closeness (+0.38)                     |
|    |                            |       | - release_decade closeness (+0.20)                 |
|    |                            |       | - instrumentalness closeness (+0.50)               |
|    |                            |       | - duration_sec closeness (+0.24)                   |
|    |                            |       | - mood tags aggressive/rebellious (+1.00)          |
|    |                            |       | - explicit preference ok (+0.25)                   |
+----+----------------------------+-------+----------------------------------------------------+
| 2  | Storm Runner               | 5.41  | - energy closeness (+1.92)                         |
|    | by Voltline                |       | - valence closeness (+0.39)                        |
|    |                            |       | - acousticness closeness (+0.47)                   |
|    |                            |       | - popularity closeness (+0.29)                     |
|    |                            |       | - release_decade closeness (+0.40)                 |
|    |                            |       | - instrumentalness closeness (+0.47)               |
|    |                            |       | - duration_sec closeness (+0.21)                   |
|    |                            |       | - mood tags aggressive/rebellious (+1.00)          |
|    |                            |       | - explicit preference ok (+0.25)                   |
+----+----------------------------+-------+----------------------------------------------------+
| 3  | Concrete Psalms            | 4.89  | - energy closeness (+1.66)                         |
|    | by Dre Maddox              |       | - valence closeness (+0.34)                        |
|    |                            |       | - acousticness closeness (+0.47)                   |
|    |                            |       | - popularity closeness (+0.24)                     |
|    |                            |       | - release_decade closeness (+0.30)                 |
|    |                            |       | - instrumentalness closeness (+0.46)               |
|    |                            |       | - duration_sec closeness (+0.18)                   |
|    |                            |       | - mood tags aggressive/rebellious (+1.00)          |
|    |                            |       | - explicit preference ok (+0.25)                   |
+----+----------------------------+-------+----------------------------------------------------+
| 4  | Gym Hero                   | 4.73  | - energy closeness (+1.96)                         |
|    | by Max Pulse               |       | - valence closeness (+0.24)                        |
|    |                            |       | - acousticness closeness (+0.50)                   |
|    |                            |       | - popularity closeness (+0.18)                     |
|    |                            |       | - release_decade closeness (+0.50)                 |
|    |                            |       | - instrumentalness closeness (+0.46)               |
|    |                            |       | - duration_sec closeness (+0.14)                   |
|    |                            |       | - mood tags aggressive (+0.50)                     |
|    |                            |       | - explicit preference ok (+0.25)                   |
+----+----------------------------+-------+----------------------------------------------------+
| 5  | Bass Cathedral             | 4.64  | - energy closeness (+2.00)                         |
|    | by Kilo Verse              |       | - valence closeness (+0.18)                        |
|    |                            |       | - acousticness closeness (+0.49)                   |
|    |                            |       | - popularity closeness (+0.23)                     |
|    |                            |       | - release_decade closeness (+0.50)                 |
|    |                            |       | - instrumentalness closeness (+0.27)               |
|    |                            |       | - duration_sec closeness (+0.21)                   |
|    |                            |       | - mood tags aggressive (+0.50)                     |
|    |                            |       | - explicit preference ok (+0.25)                   |
+----+----------------------------+-------+----------------------------------------------------+
```

### Sad but Hyper

The only `sad` song (Blue Highway Blues) lands at #5. Genre + energy (4.0 max) overpower mood (1.0), so the "sad" listener gets upbeat pop.

```
+----+----------------------------+-------+----------------------------------------------------+
| #  | Song / Artist              | Score | Reasons                                            |
+====+============================+=======+====================================================+
| 1  | Gym Hero                   | 4.58  | - genre match (+2.00)                              |
|    | by Max Pulse               |       | - energy closeness (+1.94)                         |
|    |                            |       | - valence closeness (+0.21)                        |
|    |                            |       | - acousticness closeness (+0.42)                   |
+----+----------------------------+-------+----------------------------------------------------+
| 2  | Sunrise City               | 4.01  | - genre match (+2.00)                              |
|    | by Neon Echo               |       | - energy closeness (+1.84)                         |
|    |                            |       | - valence closeness (+0.18)                        |
|    |                            |       | - acousticness closeness (+0.49)                   |
|    |                            |       | - repeat genre penalty (-0.50)                     |
+----+----------------------------+-------+----------------------------------------------------+
| 3  | Storm Runner               | 2.79  | - energy closeness (+1.98)                         |
|    | by Voltline                |       | - valence closeness (+0.36)                        |
|    |                            |       | - acousticness closeness (+0.45)                   |
+----+----------------------------+-------+----------------------------------------------------+
| 4  | Iron Hymn                  | 2.75  | - energy closeness (+1.86)                         |
|    | by Black Ritual            |       | - valence closeness (+0.47)                        |
|    |                            |       | - acousticness closeness (+0.42)                   |
+----+----------------------------+-------+----------------------------------------------------+
| 5  | Blue Highway Blues         | 2.60  | - mood match (+1.00)                               |
|    | by Otis Marlow             |       | - energy closeness (+0.96)                         |
|    |                            |       | - valence closeness (+0.45)                        |
|    |                            |       | - acousticness closeness (+0.19)                   |
+----+----------------------------+-------+----------------------------------------------------+
```

### Unknown Genre

No song can earn the 2.0 genre points, so the max score drops to ~5.0 and mood + energy decide the ranking.

```
+----+----------------------------+-------+----------------------------------------------------+
| #  | Song / Artist              | Score | Reasons                                            |
+====+============================+=======+====================================================+
| 1  | Sunrise City               | 3.93  | - mood match (+1.00)                               |
|    | by Neon Echo               |       | - energy closeness (+1.96)                         |
|    |                            |       | - valence closeness (+0.48)                        |
|    |                            |       | - acousticness closeness (+0.49)                   |
+----+----------------------------+-------+----------------------------------------------------+
| 2  | Rooftop Lights             | 3.84  | - mood match (+1.00)                               |
|    | by Indigo Parade           |       | - energy closeness (+1.92)                         |
|    |                            |       | - valence closeness (+0.49)                        |
|    |                            |       | - acousticness closeness (+0.43)                   |
+----+----------------------------+-------+----------------------------------------------------+
| 3  | Concrete Psalms            | 2.81  | - energy closeness (+1.96)                         |
|    | by Dre Maddox              |       | - valence closeness (+0.39)                        |
|    |                            |       | - acousticness closeness (+0.46)                   |
+----+----------------------------+-------+----------------------------------------------------+
| 4  | Bass Cathedral             | 2.58  | - energy closeness (+1.70)                         |
|    | by Kilo Verse              |       | - valence closeness (+0.46)                        |
|    |                            |       | - acousticness closeness (+0.41)                   |
+----+----------------------------+-------+----------------------------------------------------+
| 5  | Storm Runner               | 2.57  | - energy closeness (+1.78)                         |
|    | by Voltline                |       | - valence closeness (+0.34)                        |
|    |                            |       | - acousticness closeness (+0.45)                   |
+----+----------------------------+-------+----------------------------------------------------+
```

### Near-Miss Genre

`indie` earns nothing against `indie pop` (exact string match); the indie pop song only ranks via mood.

```
+----+----------------------------+-------+----------------------------------------------------+
| #  | Song / Artist              | Score | Reasons                                            |
+====+============================+=======+====================================================+
| 1  | Rooftop Lights             | 3.82  | - mood match (+1.00)                               |
|    | by Indigo Parade           |       | - energy closeness (+1.88)                         |
|    |                            |       | - valence closeness (+0.47)                        |
|    |                            |       | - acousticness closeness (+0.47)                   |
+----+----------------------------+-------+----------------------------------------------------+
| 2  | Sunrise City               | 3.60  | - mood match (+1.00)                               |
|    | by Neon Echo               |       | - energy closeness (+1.76)                         |
|    |                            |       | - valence closeness (+0.46)                        |
|    |                            |       | - acousticness closeness (+0.39)                   |
+----+----------------------------+-------+----------------------------------------------------+
| 3  | Island Clock               | 2.65  | - energy closeness (+1.70)                         |
|    | by Sol Tide                |       | - valence closeness (+0.47)                        |
|    |                            |       | - acousticness closeness (+0.47)                   |
+----+----------------------------+-------+----------------------------------------------------+
| 4  | Concrete Psalms            | 2.61  | - energy closeness (+1.84)                         |
|    | by Dre Maddox              |       | - valence closeness (+0.41)                        |
|    |                            |       | - acousticness closeness (+0.36)                   |
+----+----------------------------+-------+----------------------------------------------------+
| 5  | Velvet Hours               | 2.54  | - energy closeness (+1.56)                         |
|    | by Marisol Vega            |       | - valence closeness (+0.48)                        |
|    |                            |       | - acousticness closeness (+0.50)                   |
+----+----------------------------+-------+----------------------------------------------------+
```

### Out-of-Range Numbers

No crash and no negative scores in the top 5, but out-of-range targets are accepted silently and tempo 300 earns 0 from every song.

```
+----+----------------------------+-------+----------------------------------------------------+
| #  | Song / Artist              | Score | Reasons                                            |
+====+============================+=======+====================================================+
| 1  | Sunrise City               | 4.13  | - genre match (+2.00)                              |
|    | by Neon Echo               |       | - mood match (+1.00)                               |
|    |                            |       | - energy closeness (+0.64)                         |
|    |                            |       | - valence closeness (+0.33)                        |
|    |                            |       | - acousticness closeness (+0.16)                   |
|    |                            |       | - tempo_bpm closeness (+0.00)                      |
+----+----------------------------+-------+----------------------------------------------------+
| 2  | Gym Hero                   | 2.95  | - genre match (+2.00)                              |
|    | by Max Pulse               |       | - energy closeness (+0.86)                         |
|    |                            |       | - valence closeness (+0.36)                        |
|    |                            |       | - acousticness closeness (+0.22)                   |
|    |                            |       | - tempo_bpm closeness (+0.00)                      |
|    |                            |       | - repeat genre penalty (-0.50)                     |
+----+----------------------------+-------+----------------------------------------------------+
| 3  | Rooftop Lights             | 1.94  | - mood match (+1.00)                               |
|    | by Indigo Parade           |       | - energy closeness (+0.52)                         |
|    |                            |       | - valence closeness (+0.34)                        |
|    |                            |       | - acousticness closeness (+0.08)                   |
|    |                            |       | - tempo_bpm closeness (+0.00)                      |
+----+----------------------------+-------+----------------------------------------------------+
| 4  | Iron Hymn                  | 1.54  | - energy closeness (+0.94)                         |
|    | by Black Ritual            |       | - valence closeness (+0.38)                        |
|    |                            |       | - acousticness closeness (+0.23)                   |
|    |                            |       | - tempo_bpm closeness (+0.00)                      |
+----+----------------------------+-------+----------------------------------------------------+
| 5  | Storm Runner               | 1.51  | - energy closeness (+0.82)                         |
|    | by Voltline                |       | - valence closeness (+0.49)                        |
|    |                            |       | - acousticness closeness (+0.20)                   |
|    |                            |       | - tempo_bpm closeness (+0.00)                      |
+----+----------------------------+-------+----------------------------------------------------+
```

### Dead Center

Only the single jazz/relaxed song gets a big lead; the rest are near-ties separated by hundredths.

```
+----+----------------------------+-------+----------------------------------------------------+
| #  | Song / Artist              | Score | Reasons                                            |
+====+============================+=======+====================================================+
| 1  | Coffee Shop Stories        | 6.38  | - genre match (+2.00)                              |
|    | by Slow Stereo             |       | - mood match (+1.00)                               |
|    |                            |       | - energy closeness (+1.74)                         |
|    |                            |       | - valence closeness (+0.40)                        |
|    |                            |       | - acousticness closeness (+0.30)                   |
|    |                            |       | - tempo_bpm closeness (+0.46)                      |
|    |                            |       | - danceability closeness (+0.48)                   |
+----+----------------------------+-------+----------------------------------------------------+
| 2  | Dust Road Home             | 3.71  | - energy closeness (+1.96)                         |
|    | by Hollow Pines            |       | - valence closeness (+0.41)                        |
|    |                            |       | - acousticness closeness (+0.38)                   |
|    |                            |       | - tempo_bpm closeness (+0.49)                      |
|    |                            |       | - danceability closeness (+0.47)                   |
+----+----------------------------+-------+----------------------------------------------------+
| 3  | Velvet Hours               | 3.64  | - energy closeness (+1.96)                         |
|    | by Marisol Vega            |       | - valence closeness (+0.39)                        |
|    |                            |       | - acousticness closeness (+0.45)                   |
|    |                            |       | - tempo_bpm closeness (+0.43)                      |
|    |                            |       | - danceability closeness (+0.41)                   |
+----+----------------------------+-------+----------------------------------------------------+
| 4  | Midnight Coding            | 3.55  | - energy closeness (+1.84)                         |
|    | by LoRoom                  |       | - valence closeness (+0.47)                        |
|    |                            |       | - acousticness closeness (+0.40)                   |
|    |                            |       | - tempo_bpm closeness (+0.41)                      |
|    |                            |       | - danceability closeness (+0.44)                   |
+----+----------------------------+-------+----------------------------------------------------+
| 5  | Island Clock               | 3.48  | - energy closeness (+1.90)                         |
|    | by Sol Tide                |       | - valence closeness (+0.35)                        |
|    |                            |       | - acousticness closeness (+0.47)                   |
|    |                            |       | - tempo_bpm closeness (+0.40)                      |
|    |                            |       | - danceability closeness (+0.36)                   |
+----+----------------------------+-------+----------------------------------------------------+
```

### Extremist

The lone classical song wins easily (5.44 vs 2.08), then scores fall off a cliff.

```
+----+----------------------------+-------+----------------------------------------------------+
| #  | Song / Artist              | Score | Reasons                                            |
+====+============================+=======+====================================================+
| 1  | Ashes on the Strings       | 5.44  | - genre match (+2.00)                              |
|    | by Ember Quartet           |       | - mood match (+1.00)                               |
|    |                            |       | - energy closeness (+1.56)                         |
|    |                            |       | - valence closeness (+0.40)                        |
|    |                            |       | - acousticness closeness (+0.48)                   |
+----+----------------------------+-------+----------------------------------------------------+
| 2  | Spacewalk Thoughts         | 2.08  | - energy closeness (+1.44)                         |
|    | by Orbit Bloom             |       | - valence closeness (+0.17)                        |
|    |                            |       | - acousticness closeness (+0.46)                   |
+----+----------------------------+-------+----------------------------------------------------+
| 3  | Blue Highway Blues         | 2.00  | - energy closeness (+1.24)                         |
|    | by Otis Marlow             |       | - valence closeness (+0.35)                        |
|    |                            |       | - acousticness closeness (+0.41)                   |
+----+----------------------------+-------+----------------------------------------------------+
| 4  | Library Rain               | 1.93  | - energy closeness (+1.30)                         |
|    | by Paper Lanterns          |       | - valence closeness (+0.20)                        |
|    |                            |       | - acousticness closeness (+0.43)                   |
+----+----------------------------+-------+----------------------------------------------------+
| 5  | Coffee Shop Stories        | 1.85  | - energy closeness (+1.26)                         |
|    | by Slow Stereo             |       | - valence closeness (+0.15)                        |
|    |                            |       | - acousticness closeness (+0.45)                   |
+----+----------------------------+-------+----------------------------------------------------+
```

### Missing Keys

Crash: `score_song` indexes `user_prefs["genre"]` directly. `main.py` catches the `KeyError` so the run continues.

```
ERROR: recommender crashed, missing preference 'genre'
```

### Genre-Only Loyalist

Mood match + energy (angry/Iron Hymn) beats every lofi song; lofi songs follow because genre still adds 2.0 despite poor energy fit. Focus Flow is pushed out of the top 5 by the diversity penalty (a second LoRoom song and a third lofi song).

```
+----+----------------------------+-------+----------------------------------------------------+
| #  | Song / Artist              | Score | Reasons                                            |
+====+============================+=======+====================================================+
| 1  | Iron Hymn                  | 3.91  | - mood match (+1.00)                               |
|    | by Black Ritual            |       | - energy closeness (+1.96)                         |
|    |                            |       | - valence closeness (+0.47)                        |
|    |                            |       | - acousticness closeness (+0.47)                   |
+----+----------------------------+-------+----------------------------------------------------+
| 2  | Midnight Coding            | 3.50  | - genre match (+2.00)                              |
|    | by LoRoom                  |       | - energy closeness (+0.94)                         |
|    |                            |       | - valence closeness (+0.37)                        |
|    |                            |       | - acousticness closeness (+0.20)                   |
+----+----------------------------+-------+----------------------------------------------------+
| 3  | Storm Runner               | 2.83  | - energy closeness (+1.92)                         |
|    | by Voltline                |       | - valence closeness (+0.41)                        |
|    |                            |       | - acousticness closeness (+0.50)                   |
+----+----------------------------+-------+----------------------------------------------------+
| 4  | Library Rain               | 2.77  | - genre match (+2.00)                              |
|    | by Paper Lanterns          |       | - energy closeness (+0.80)                         |
|    |                            |       | - valence closeness (+0.35)                        |
|    |                            |       | - acousticness closeness (+0.12)                   |
|    |                            |       | - repeat genre penalty (-0.50)                     |
+----+----------------------------+-------+----------------------------------------------------+
| 5  | Gym Hero                   | 2.70  | - energy closeness (+1.96)                         |
|    | by Max Pulse               |       | - valence closeness (+0.27)                        |
|    |                            |       | - acousticness closeness (+0.47)                   |
+----+----------------------------+-------+----------------------------------------------------+
```

---

## Experiments You Tried

### Swapping the genre and mood weights

Baseline: genre 2.0, mood 1.0. Experiment: genre 1.0, mood 2.0 (this later became the basis of the `mood-first` mode). Everything else unchanged. These runs happened before tempo and danceability were scored, so the profiles have no tempo or danceability targets and the scores below are out of 6.0. Each profile is a dictionary like the one in "Taste profile used for comparison"; the gym, sad acoustic and contradictory profiles are extra profiles used only for this test.

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

- **Tiny catalog.** It only has 18 songs. Thirteen of the 15 genres have a single song, so a genre match works like picking one song. Only lofi has real choice.
- **No lyrics, language or artist.** It cannot tell a love song from a protest song. Era, popularity, mood tags and explicit lyrics only count when you set a target for them, and it doesn't know what you have already heard.
- **Exact labels only.** "Indie" gets no credit for "indie pop," and "chill" gets none for "relaxed."
- **It over-favors the genre you name.** Genre and mood are 3 of the 7 core points, so the top 5 stays inside your genre. The diversity penalty softens this by pushing repeat artists and genres down, but it is a small nudge, not a guarantee.
- **Mood counts for little.** A sad listener who wants energetic pop still gets cheerful pop.
- **Gaps in the data.** No song is both high energy and acoustic, so people who want that get the closest thing. The scorer also never says "I'm not sure," so weak matches look as confident as strong ones.
- **Fragile inputs.** A profile with no genre or mood crashes the scorer, and impossible numbers (like energy 1.5) are not flagged.

See [model_card.md](model_card.md) for more detail.

---

## Reflection

Read and complete `model_card.md`:

[**Model Card**](model_card.md)

**How recommenders turn data into predictions.** My recommender is only addition. It gives each song points for matching your genre and mood, and for being close to your energy and other targets. Then it sorts by total points. That simple idea still produced results that felt right, like calm songs for the lofi profile and loud ones for rock. The "Reasons" list made it feel even smarter. But the weights are choices I made, and they matter. When I turned off the mood check, 6 of my 11 test profiles changed order and 3 got a new #1 pick. The new lists were not clearly better, only different.

**Where bias or unfairness could show up.** Most of the bias came from the data, not the math. With only 18 songs, most genres had one song. That song got a big genre bonus and showed up first, so fans of some genres got better lists than others. Gym Hero showing up for happy-pop fans is the clearest example. The system also never says "I'm not sure," so a weak match looks as sure as a strong one. In a real app, the same problems could be bigger. A small or lopsided catalog, or exact-match rules, could quietly give some listeners and some artists less exposure. Nobody would notice unless they tested different kinds of users, like I did with the edge-case profiles.




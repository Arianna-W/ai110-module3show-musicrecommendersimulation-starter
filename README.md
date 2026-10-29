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

## Profile Test Results (Standard and Edge Cases)

Output of `python src/main.py` for every profile in `PROFILES` and `EDGE_PROFILES` (top 5 each, k=5).

### High-Energy Pop

Clean win: Sunrise City matches genre and mood.

```
============================================================
                    TOP RECOMMENDATIONS                     
============================================================
#1  Sunrise City
    Neon Echo  |  Score: 6.72
    Reasons:
      - genre match (+2.00)
      - mood match (+1.00)
      - energy closeness (+1.84)
      - valence closeness (+0.49)
      - acousticness closeness (+0.46)
      - tempo_bpm closeness (+0.46)
      - danceability closeness (+0.47)
------------------------------------------------------------
#2  Gym Hero
    Max Pulse  |  Score: 5.84
    Reasons:
      - genre match (+2.00)
      - energy closeness (+1.94)
      - valence closeness (+0.46)
      - acousticness closeness (+0.47)
      - tempo_bpm closeness (+0.48)
      - danceability closeness (+0.48)
------------------------------------------------------------
#3  Rooftop Lights
    Indigo Parade  |  Score: 4.54
    Reasons:
      - mood match (+1.00)
      - energy closeness (+1.72)
      - valence closeness (+0.48)
      - acousticness closeness (+0.38)
      - tempo_bpm closeness (+0.48)
      - danceability closeness (+0.48)
------------------------------------------------------------
#4  Bass Cathedral
    Kilo Verse  |  Score: 3.82
    Reasons:
      - energy closeness (+1.90)
      - valence closeness (+0.48)
      - acousticness closeness (+0.46)
      - tempo_bpm closeness (+0.50)
      - danceability closeness (+0.47)
------------------------------------------------------------
#5  Storm Runner
    Voltline  |  Score: 3.60
    Reasons:
      - energy closeness (+1.98)
      - valence closeness (+0.32)
      - acousticness closeness (+0.50)
      - tempo_bpm closeness (+0.40)
      - danceability closeness (+0.41)
------------------------------------------------------------
```

### Chill Lofi

Same as the sample output above.

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

### Deep Intense Rock

Only one rock song exists, so #2 onward is energy-driven (a pop song takes #2 on mood).

```
============================================================
                    TOP RECOMMENDATIONS                     
============================================================
#1  Storm Runner
    Voltline  |  Score: 6.80
    Reasons:
      - genre match (+2.00)
      - mood match (+1.00)
      - energy closeness (+1.98)
      - valence closeness (+0.43)
      - acousticness closeness (+0.50)
      - tempo_bpm closeness (+0.49)
      - danceability closeness (+0.40)
------------------------------------------------------------
#2  Gym Hero
    Max Pulse  |  Score: 4.46
    Reasons:
      - mood match (+1.00)
      - energy closeness (+1.98)
      - valence closeness (+0.29)
      - acousticness closeness (+0.47)
      - tempo_bpm closeness (+0.42)
      - danceability closeness (+0.29)
------------------------------------------------------------
#3  Iron Hymn
    Black Ritual  |  Score: 3.75
    Reasons:
      - energy closeness (+1.90)
      - valence closeness (+0.45)
      - acousticness closeness (+0.47)
      - tempo_bpm closeness (+0.42)
      - danceability closeness (+0.50)
------------------------------------------------------------
#4  Bass Cathedral
    Kilo Verse  |  Score: 3.32
    Reasons:
      - energy closeness (+1.94)
      - valence closeness (+0.23)
      - acousticness closeness (+0.46)
      - tempo_bpm closeness (+0.41)
      - danceability closeness (+0.27)
------------------------------------------------------------
#5  Night Drive Loop
    Neon Echo  |  Score: 3.22
    Reasons:
      - energy closeness (+1.66)
      - valence closeness (+0.43)
      - acousticness closeness (+0.44)
      - tempo_bpm closeness (+0.33)
      - danceability closeness (+0.36)
------------------------------------------------------------
```

### Sad but Hyper

The only `sad` song (Blue Highway Blues) lands at #5. Genre + energy (4.0 max) overpower mood (1.0), so the "sad" listener gets upbeat pop.

```
============================================================
                    TOP RECOMMENDATIONS                     
============================================================
#1  Gym Hero
    Max Pulse  |  Score: 4.58
    Reasons:
      - genre match (+2.00)
      - energy closeness (+1.94)
      - valence closeness (+0.21)
      - acousticness closeness (+0.42)
------------------------------------------------------------
#2  Sunrise City
    Neon Echo  |  Score: 4.51
    Reasons:
      - genre match (+2.00)
      - energy closeness (+1.84)
      - valence closeness (+0.18)
      - acousticness closeness (+0.49)
------------------------------------------------------------
#3  Storm Runner
    Voltline  |  Score: 2.79
    Reasons:
      - energy closeness (+1.98)
      - valence closeness (+0.36)
      - acousticness closeness (+0.45)
------------------------------------------------------------
#4  Iron Hymn
    Black Ritual  |  Score: 2.75
    Reasons:
      - energy closeness (+1.86)
      - valence closeness (+0.47)
      - acousticness closeness (+0.42)
------------------------------------------------------------
#5  Blue Highway Blues
    Otis Marlow  |  Score: 2.60
    Reasons:
      - mood match (+1.00)
      - energy closeness (+0.96)
      - valence closeness (+0.45)
      - acousticness closeness (+0.19)
------------------------------------------------------------
```

### Unknown Genre

No song can earn the 2.0 genre points, so the max score drops to ~5.0 and mood + energy decide the ranking.

```
============================================================
                    TOP RECOMMENDATIONS                     
============================================================
#1  Sunrise City
    Neon Echo  |  Score: 3.93
    Reasons:
      - mood match (+1.00)
      - energy closeness (+1.96)
      - valence closeness (+0.48)
      - acousticness closeness (+0.49)
------------------------------------------------------------
#2  Rooftop Lights
    Indigo Parade  |  Score: 3.84
    Reasons:
      - mood match (+1.00)
      - energy closeness (+1.92)
      - valence closeness (+0.49)
      - acousticness closeness (+0.43)
------------------------------------------------------------
#3  Concrete Psalms
    Dre Maddox  |  Score: 2.81
    Reasons:
      - energy closeness (+1.96)
      - valence closeness (+0.39)
      - acousticness closeness (+0.46)
------------------------------------------------------------
#4  Night Drive Loop
    Neon Echo  |  Score: 2.74
    Reasons:
      - energy closeness (+1.90)
      - valence closeness (+0.34)
      - acousticness closeness (+0.49)
------------------------------------------------------------
#5  Gym Hero
    Max Pulse  |  Score: 2.65
    Reasons:
      - energy closeness (+1.74)
      - valence closeness (+0.48)
      - acousticness closeness (+0.42)
------------------------------------------------------------
```

### Near-Miss Genre

`indie` earns nothing against `indie pop` (exact string match); the indie pop song only ranks via mood.

```
============================================================
                    TOP RECOMMENDATIONS                     
============================================================
#1  Rooftop Lights
    Indigo Parade  |  Score: 3.82
    Reasons:
      - mood match (+1.00)
      - energy closeness (+1.88)
      - valence closeness (+0.47)
      - acousticness closeness (+0.47)
------------------------------------------------------------
#2  Sunrise City
    Neon Echo  |  Score: 3.60
    Reasons:
      - mood match (+1.00)
      - energy closeness (+1.76)
      - valence closeness (+0.46)
      - acousticness closeness (+0.39)
------------------------------------------------------------
#3  Night Drive Loop
    Neon Echo  |  Score: 2.68
    Reasons:
      - energy closeness (+1.90)
      - valence closeness (+0.37)
      - acousticness closeness (+0.41)
------------------------------------------------------------
#4  Island Clock
    Sol Tide  |  Score: 2.65
    Reasons:
      - energy closeness (+1.70)
      - valence closeness (+0.47)
      - acousticness closeness (+0.47)
------------------------------------------------------------
#5  Concrete Psalms
    Dre Maddox  |  Score: 2.61
    Reasons:
      - energy closeness (+1.84)
      - valence closeness (+0.41)
      - acousticness closeness (+0.36)
------------------------------------------------------------
```

### Out-of-Range Numbers

No crash and no negative scores in the top 5, but out-of-range targets are accepted silently and tempo 300 earns 0 from every song.

```
============================================================
                    TOP RECOMMENDATIONS                     
============================================================
#1  Sunrise City
    Neon Echo  |  Score: 4.13
    Reasons:
      - genre match (+2.00)
      - mood match (+1.00)
      - energy closeness (+0.64)
      - valence closeness (+0.33)
      - acousticness closeness (+0.16)
      - tempo_bpm closeness (+0.00)
------------------------------------------------------------
#2  Gym Hero
    Max Pulse  |  Score: 3.45
    Reasons:
      - genre match (+2.00)
      - energy closeness (+0.86)
      - valence closeness (+0.36)
      - acousticness closeness (+0.22)
      - tempo_bpm closeness (+0.00)
------------------------------------------------------------
#3  Rooftop Lights
    Indigo Parade  |  Score: 1.94
    Reasons:
      - mood match (+1.00)
      - energy closeness (+0.52)
      - valence closeness (+0.34)
      - acousticness closeness (+0.08)
      - tempo_bpm closeness (+0.00)
------------------------------------------------------------
#4  Iron Hymn
    Black Ritual  |  Score: 1.54
    Reasons:
      - energy closeness (+0.94)
      - valence closeness (+0.38)
      - acousticness closeness (+0.23)
      - tempo_bpm closeness (+0.00)
------------------------------------------------------------
#5  Storm Runner
    Voltline  |  Score: 1.51
    Reasons:
      - energy closeness (+0.82)
      - valence closeness (+0.49)
      - acousticness closeness (+0.20)
      - tempo_bpm closeness (+0.00)
------------------------------------------------------------
```

### Dead Center

Only the single jazz/relaxed song gets a big lead; the rest are near-ties separated by hundredths.

```
============================================================
                    TOP RECOMMENDATIONS                     
============================================================
#1  Coffee Shop Stories
    Slow Stereo  |  Score: 6.38
    Reasons:
      - genre match (+2.00)
      - mood match (+1.00)
      - energy closeness (+1.74)
      - valence closeness (+0.40)
      - acousticness closeness (+0.30)
      - tempo_bpm closeness (+0.46)
      - danceability closeness (+0.48)
------------------------------------------------------------
#2  Dust Road Home
    Hollow Pines  |  Score: 3.71
    Reasons:
      - energy closeness (+1.96)
      - valence closeness (+0.41)
      - acousticness closeness (+0.38)
      - tempo_bpm closeness (+0.49)
      - danceability closeness (+0.47)
------------------------------------------------------------
#3  Velvet Hours
    Marisol Vega  |  Score: 3.64
    Reasons:
      - energy closeness (+1.96)
      - valence closeness (+0.39)
      - acousticness closeness (+0.45)
      - tempo_bpm closeness (+0.43)
      - danceability closeness (+0.41)
------------------------------------------------------------
#4  Midnight Coding
    LoRoom  |  Score: 3.55
    Reasons:
      - energy closeness (+1.84)
      - valence closeness (+0.47)
      - acousticness closeness (+0.40)
      - tempo_bpm closeness (+0.41)
      - danceability closeness (+0.44)
------------------------------------------------------------
#5  Island Clock
    Sol Tide  |  Score: 3.48
    Reasons:
      - energy closeness (+1.90)
      - valence closeness (+0.35)
      - acousticness closeness (+0.47)
      - tempo_bpm closeness (+0.40)
      - danceability closeness (+0.36)
------------------------------------------------------------
```

### Extremist

The lone classical song wins easily (5.44 vs 2.08), then scores fall off a cliff.

```
============================================================
                    TOP RECOMMENDATIONS                     
============================================================
#1  Ashes on the Strings
    Ember Quartet  |  Score: 5.44
    Reasons:
      - genre match (+2.00)
      - mood match (+1.00)
      - energy closeness (+1.56)
      - valence closeness (+0.40)
      - acousticness closeness (+0.48)
------------------------------------------------------------
#2  Spacewalk Thoughts
    Orbit Bloom  |  Score: 2.08
    Reasons:
      - energy closeness (+1.44)
      - valence closeness (+0.17)
      - acousticness closeness (+0.46)
------------------------------------------------------------
#3  Blue Highway Blues
    Otis Marlow  |  Score: 2.00
    Reasons:
      - energy closeness (+1.24)
      - valence closeness (+0.35)
      - acousticness closeness (+0.41)
------------------------------------------------------------
#4  Library Rain
    Paper Lanterns  |  Score: 1.93
    Reasons:
      - energy closeness (+1.30)
      - valence closeness (+0.20)
      - acousticness closeness (+0.43)
------------------------------------------------------------
#5  Coffee Shop Stories
    Slow Stereo  |  Score: 1.85
    Reasons:
      - energy closeness (+1.26)
      - valence closeness (+0.15)
      - acousticness closeness (+0.45)
------------------------------------------------------------
```

### Missing Keys

Crash: `score_song` indexes `user_prefs["genre"]` directly. `main.py` catches the `KeyError` so the run continues.

```
ERROR: recommender crashed, missing preference 'genre'
```

### Genre-Only Loyalist

Mood match + energy (angry/Iron Hymn) beats every lofi song; three lofi songs follow because genre still adds 2.0 despite poor energy fit.

```
============================================================
                    TOP RECOMMENDATIONS                     
============================================================
#1  Iron Hymn
    Black Ritual  |  Score: 3.91
    Reasons:
      - mood match (+1.00)
      - energy closeness (+1.96)
      - valence closeness (+0.47)
      - acousticness closeness (+0.47)
------------------------------------------------------------
#2  Midnight Coding
    LoRoom  |  Score: 3.50
    Reasons:
      - genre match (+2.00)
      - energy closeness (+0.94)
      - valence closeness (+0.37)
      - acousticness closeness (+0.20)
------------------------------------------------------------
#3  Focus Flow
    LoRoom  |  Score: 3.42
    Reasons:
      - genre match (+2.00)
      - energy closeness (+0.90)
      - valence closeness (+0.35)
      - acousticness closeness (+0.16)
------------------------------------------------------------
#4  Library Rain
    Paper Lanterns  |  Score: 3.27
    Reasons:
      - genre match (+2.00)
      - energy closeness (+0.80)
      - valence closeness (+0.35)
      - acousticness closeness (+0.12)
------------------------------------------------------------
#5  Storm Runner
    Voltline  |  Score: 2.83
    Reasons:
      - energy closeness (+1.92)
      - valence closeness (+0.41)
      - acousticness closeness (+0.50)
------------------------------------------------------------
```

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




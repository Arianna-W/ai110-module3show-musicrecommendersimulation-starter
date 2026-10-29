# 🎧 Model Card: Music Recommender Simulation

## 1. Model Name  

**LofiMatch 1.0**, a command-line music recommender simulation.

---

## 2. Intended Use  

**What kind of recommendations it generates:**

LofiMatch suggests songs from a small catalog based on a user's stated taste. Given a favorite genre, a favorite mood, a target energy level and an acoustic preference (and optionally how upbeat they want the music to feel), it returns a ranked list of the top few songs, five by default.

- **Content-based, not collaborative.** It matches a song's own attributes to what the user asked for. It never compares users to each other or looks at what other people listened to.
- **Songs from the catalog only.** It cannot suggest anything outside the 18 songs in the CSV, so it can only pick the best of what's there, not discover new music.
- **Explained.** Each song comes with a short list of reasons for its score, such as "genre match" or "energy closeness", so the user can see why it was picked.
- **Lofi-leaning.** The project was built around lofi listening, such as studying or focusing, so it works best for calm, low-energy, acoustic-leaning requests. The catalog has only three lofi tracks, which are the natural top picks for those users.

**Assumptions about the user:**

- **Taste is a fixed set of preferences.** One favorite genre, one favorite mood and a target energy level describe what they want, and those answers stay the same from one session to the next.
- **They know what they want up front.** The model has no listening history, skips, likes or other behavior to learn from, so it takes the user's word for it.
- **Taste is about closeness, not variety.** A user who wants energy 0.4 is assumed to prefer a song at 0.4 over one at 0.9, and the model doesn't try to mix in different kinds of songs.
- **Acoustic preference is a simple yes or no.** A user either likes acoustic music or doesn't, with nothing in between.
- **One mood at a time.** The model matches a single mood exactly. A user who wants "chill but a bit happy" can't express that, and a near-miss mood such as "relaxed" for "chill" earns no mood points.

**Intended audience:** classroom exploration only. It is a learning project for seeing how a scoring-based recommender turns preferences into rankings, and how small choices like feature weights change the results. It is not meant for real users or production use, and it should not be used to make decisions about what real listeners hear.

---

## 3. How the Model Works  

The recommender works like a judge scoring every song in the catalog against what you say you like, then handing you the highest scorers.

**What it knows about you.** You tell it your favorite genre, your favorite mood, how energetic you want the music to be, whether you lean toward acoustic sounds, and (optionally) how upbeat or positive you want it to feel.

**What it looks at in each song.** Genre, mood, energy, how positive the song sounds (valence), and how acoustic it is.

**How a song earns points.** Each song can earn up to 7 points:

- **Genre (up to 2 points):** all or nothing. If the song's genre is your favorite, it gets the points. If not, it gets none.
- **Mood (1 point):** also all or nothing.
- **Energy (up to 2 points):** the closer the song's energy is to your target, the more points it gets. A perfect match earns the full 2, and a song at the opposite extreme earns close to nothing.
- **Positivity (up to 0.5 points):** scored by closeness, the same way as energy.
- **Acousticness (up to 0.5 points):** scored by closeness. If you like acoustic music, the model aims for a very acoustic song. If not, it aims for a mostly non-acoustic one.
- **Tempo (up to 0.5 points):** scored by closeness to the user's target speed in beats per minute. A gap of 120 BPM or more earns nothing.
- **Danceability (up to 0.5 points):** scored by closeness, the same way as energy.

Tempo and danceability are optional. If the user doesn't give a target for them, they are skipped and no points are awarded or lost.

**Picking the results.** The model adds up the points for every song, sorts from highest to lowest, and shows you the top few. If two songs tie, they are ordered alphabetically by title. Each recommendation also comes with a plain-language list of why it scored as it did, such as "genre match" or "energy closeness".
---

## 4. Data  

**Size.** The catalog is `data/songs.csv`, with 18 songs. Each song has a title, artist, genre, mood, and numeric scores for energy, tempo (BPM), valence (how positive it sounds), danceability and acousticness. The numeric scores run from 0 to 1, except tempo.

**Genres and moods.** There are 15 genres and 14 moods.

- **Genres:** lofi (3 songs), pop (2), and one each of rock, ambient, jazz, synthwave, indie pop, country, electronic, r&b, hip hop, classical, metal, reggae and blues.
- **Moods:** chill (3 songs), happy (2), intense (2), and one each of relaxed, moody, focused, nostalgic, euphoric, romantic, confident, melancholic, angry, laid-back and sad.
- **Energy** ranges from 0.22 (a classical piece) to 0.97 (a metal track), so both calm and intense listening are covered.

**Added data.** The starter file had 10 songs. I added 8 more (ids 11 to 18) to widen the range of genres and moods: country, electronic, r&b, hip hop, classical, metal, reggae and blues. No songs were removed. The songs, artists and scores are made up for the simulation.

**What's missing.**

- **Depth in any one genre.** Because nearly every genre has a single song, a user who picks one of them gets that one song as the only genre match, and the rest of their list is filled by closeness alone. Only lofi has enough songs to give a user real choice.
- **Lyrics and language.** There is no data on lyrics, language or vocals versus instrumental.
- **Era and popularity.** Nothing says when a song came out or how well known it is.
- **Global and niche styles.** K-pop, Latin, Afrobeats, folk and most subgenres are absent.
- **Overlapping labels.** Moods like "chill", "relaxed" and "laid-back" are close in meaning but treated as completely different, since only exact matches count.

---

## 5. Strengths  

Where does your system seem to work well  

Prompts:  

- User types for which it gives reasonable results  
- Any patterns you think your scoring captures correctly  
- Cases where the recommendations matched your intuition  

---

## 6. Limitations and Bias 

Where the system struggles or behaves unfairly. 

Prompts:  

- Features it does not consider  
- Genres or moods that are underrepresented  
- Cases where the system overfits to one preference  
- Ways the scoring might unintentionally favor some users  

---

## 7. Evaluation  

How you checked whether the recommender behaved as expected. 

Prompts:  

- Which user profiles you tested  
- What you looked for in the recommendations  
- What surprised you  
- Any simple tests or comparisons you ran  

No need for numeric metrics unless you created some.

---

## 8. Future Work  

Ideas for how you would improve the model next.  

Prompts:  

- Additional features or preferences  
- Better ways to explain recommendations  
- Improving diversity among the top results  
- Handling more complex user tastes  

---

## 9. Personal Reflection  

A few sentences about your experience.  

Prompts:  

- What you learned about recommender systems  
- Something unexpected or interesting you discovered  
- How this changed the way you think about music recommendation apps  

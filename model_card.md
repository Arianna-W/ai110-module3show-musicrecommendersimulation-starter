# 🎧 Model Card: Music Recommender Simulation

## 1. Model Name  

**LofiMatch 1.0**, a command-line music recommender simulation.

---

## 2. Intended Use  

**What kind of recommendations it generates:**

LofiMatch suggests songs from a small catalog. You tell it your favorite genre, your favorite mood, a target energy level and an acoustic preference. You can also say how upbeat you want the music to feel. It returns the top five songs, best first.

- **Content-based.** It matches a song's own traits to what you asked for. It never looks at what other people listened to.
- **Catalog only.** It can only pick from the 18 songs in the CSV file. It cannot find new music.
- **Explained.** Each song comes with reasons for its score, like "genre match" or "energy closeness."
- **Lofi-leaning.** The project was built around lofi for studying. It works best for calm, low-energy, acoustic requests. The catalog has three lofi songs, so those are the natural top picks.

**Assumptions about the user:**

- **Taste is fixed.** One genre, one mood and one energy level describe what you want. They do not change between sessions.
- **You know what you want.** The model has no history, skips or likes to learn from. It takes your word for it.
- **Closer is better.** If you want energy 0.4, a song at 0.4 beats a song at 0.9. The model never tries to add variety.
- **Acoustic is yes or no.** There is no in-between.
- **One mood at a time.** "Chill but a bit happy" can't be expressed. "Relaxed" earns no points for "chill."

**Intended audience:** classroom exploration only. It is a learning project. It shows how a scoring recommender turns preferences into rankings. It also shows how small choices, like feature weights, change the results.

**Non-intended use:**

- **Real music apps.** The catalog has only 18 made-up songs. It cannot serve real listeners.
- **Judging people.** Do not use it to label a person's taste, mood or personality.
- **Fair exposure for artists.** It was not built to treat artists or genres equally. Some tastes get much better results than others.
- **Trusting weak matches.** It never says "I'm not sure." A poor match can look as certain as a good one.

---

## 3. How the Model Works  

Think of a judge. The judge scores every song against what you like. Then the judge hands you the top scorers.

**What it knows about you.** Your favorite genre and mood. Your target energy. Whether you like acoustic sounds. Optionally, how upbeat you want it to feel.

**What it looks at in each song.** Genre, mood, energy, valence (how positive it sounds) and acousticness. It can also check tempo and danceability.

**How a song earns points.** A song can earn up to 7 points:

- **Genre (up to 2):** all or nothing. If it's your genre, it gets the points. If not, it gets none.
- **Mood (1):** also all or nothing.
- **Energy (up to 2):** the closer to your target, the more points. A perfect match gets the full 2.
- **Valence (up to 0.5):** scored by closeness, like energy.
- **Acousticness (up to 0.5):** scored by closeness. If you like acoustic music, it aims high. If not, it aims low.
- **Tempo (up to 0.5):** scored by closeness in beats per minute. A gap of 120 BPM or more earns nothing.
- **Danceability (up to 0.5):** scored by closeness, like energy.

Tempo and danceability are optional. If you skip them, no points are given or lost.

**Picking the results.** The model adds up the points for every song. It sorts from highest to lowest and shows the top few. Ties are ordered by title.

---

## 4. Data  

**Size.** The catalog is `data/songs.csv`. It has 18 songs. Each song has a title, artist, genre and mood. It also has numbers for energy, tempo (BPM), valence, danceability and acousticness. All numbers run from 0 to 1, except tempo.

**Genres and moods.** There are 15 genres and 14 moods.

- **Genres:** lofi (3 songs), pop (2), and one each of rock, ambient, jazz, synthwave, indie pop, country, electronic, r&b, hip hop, classical, metal, reggae and blues.
- **Moods:** chill (3 songs), happy (2), intense (2), and one each of relaxed, moody, focused, nostalgic, euphoric, romantic, confident, melancholic, angry, laid-back and sad.
- **Energy** runs from 0.22 (classical) to 0.97 (metal). Both calm and intense music are covered.

**Added data.** The starter file had 10 songs. I added 8 more (ids 11 to 18). They add country, electronic, r&b, hip hop, classical, metal, reggae and blues. I removed none. The songs, artists and scores are made up.

**What's missing.**

- **Depth in any genre.** Nearly every genre has one song. That song is the only genre match. The rest of the list is filled by closeness. Only lofi has real choice.
- **Lyrics and language.** No data on lyrics, language or vocals.
- **Era and popularity.** Nothing says when a song came out or how well known it is.
- **Global and niche styles.** K-pop, Latin, Afrobeats, folk and most subgenres are missing.
- **Overlapping labels.** "Chill," "relaxed" and "laid-back" mean almost the same. The model treats them as totally different.

---

## 5. Strengths  

Where does your system seem to work well  

Prompts:  

- User types for which it gives reasonable results  
- Any patterns you think your scoring captures correctly  
- Cases where the recommendations matched your intuition  

**User types it works well for.** People with a clear, steady taste get good results. Chill Lofi, High-Energy Pop and Deep Intense Rock all got top 5 lists I'd be happy to hear. Each top pick matched on genre, mood and energy. Those picks were Midnight Coding, Sunrise City and Storm Runner.

**Patterns the scoring captures correctly.** Energy does a lot of useful work. Calm profiles and loud profiles shared no songs. Partial credit for "close" helps too. A song that is a little off still beats one that is far off. The "Reasons" list shows where every point came from. Anyone can check why a song was picked.

**Cases that matched my intuition.** Dead Center (middle of everything) got a relaxed jazz song. Extremist (as calm, sad and acoustic as possible) got the classical piece. Unknown Genre ("k-pop") still got happy, upbeat songs instead of nothing. Near-Miss Genre still found the indie pop song, even though the genre name didn't match.

---

## 6. Limitations and Bias 

Where the system struggles or behaves unfairly. 

Prompts:  

- Features it does not consider  
- Genres or moods that are underrepresented  
- Cases where the system overfits to one preference  
- Ways the scoring might unintentionally favor some users  

**One weakness I found:** The system gives a big bonus for matching genre. But most genres in the dataset have only one song. Lofi fans get three matching songs, so their top 5 looks great. Fans of almost any other genre get one matching song. The rest of their list is filled by whatever is closest on numbers like energy. The genre match is also exact. So "indie" gets no credit for "indie pop." The recommender works better for some tastes than others. This is mostly because of how the dataset is built.

**Features it does not consider.** It ignores lyrics, language, artist, era and what you've already heard. It also can't tell that some genres or moods are related. "Indie" and "indie pop" are related. So are "chill" and "relaxed."

**Genres or moods that are underrepresented.** The dataset has only 18 songs. Thirteen of the 15 genres have one song. Most moods appear once. No song is both high energy and acoustic. Only one song is calm and upbeat. People who want those mixes get the closest thing, not a real match.

**Where it overfits to one preference.** Genre and mood together are worth 3 of the 7 points. So the top 5 tends to stay inside the genre you named. A lofi fan sees mostly lofi. Nothing tries to show you something different.

**Ways the scoring unintentionally favors some users.** Mood is worth so little that a sad listener still gets cheerful pop. The score never shows low confidence. A weak match looks as sure as a strong one. Songs near the middle of the scale, like Spacewalk Thoughts or Library Rain, show up for many users. Being "kind of close" on everything adds up. A profile with no genre or mood crashes the scorer.

---

## 7. Evaluation  

How you checked whether the recommender behaved as expected. 

Prompts:  

- Which user profiles you tested  
- What you looked for in the recommendations  
- What surprised you  
- Any simple tests or comparisons you ran  

No need for numeric metrics unless you created some.

**Profiles tested.** I ran 11 profiles. Three are normal tastes: High-Energy Pop, Chill Lofi and Deep Intense Rock. Eight are edge cases meant to break the scoring: Sad but Hyper, Unknown Genre, Near-Miss Genre, Out-of-Range Numbers, Dead Center, Extremist, Missing Keys and Genre-Only Loyalist. For each one, I checked if the top 5 looked like what that person would want.

**Why does "Gym Hero" keep showing up for people who just want happy pop?** Gym Hero is a pop song, so it gets the full genre bonus. It is also very high energy and very danceable. That is what "high-energy pop" asks for. It is not happy. It is "intense." So it misses the mood bonus. But mood is only worth 1 point out of 7. Genre plus energy add up to more. So Gym Hero lands at #2, right behind Sunrise City. Sunrise City matches on everything. The dataset has only two pop songs. After Sunrise City, a pop fan has nowhere else to go. Gym Hero also shows up for Deep Intense Rock and Sad but Hyper. It is loud and fast, and that is most of what those profiles want.

**Comparing profiles (what changed and why it makes sense):**

- **High-Energy Pop vs. Chill Lofi:** Pop gets bright, loud songs (Sunrise City, Gym Hero, Bass Cathedral). Lofi gets slow, quiet, acoustic songs (Midnight Coding, Library Rain, Focus Flow). The lists share no songs. That fits two opposite tastes.
- **High-Energy Pop vs. Deep Intense Rock:** Both want loud music. They share Gym Hero, Bass Cathedral and Storm Runner. The top pick differs. Pop gets the cheerful Sunrise City. Rock gets Storm Runner, its only rock song. Rock also wants a darker feel and a faster tempo. That is why the angry metal song Iron Hymn is in its top 5 and not in pop's.
- **Chill Lofi vs. Deep Intense Rock:** These are opposite ends of the energy scale. They share no songs. So the energy score works.
- **High-Energy Pop vs. Sad but Hyper:** Both want energetic pop. But Sad but Hyper asks for a sad mood. No song is both sad and pop. So the mood bonus never fires. The list is almost the same as pop's. Only the sad Blue Highway Blues sneaks in at #5. This surprised me. The system hears energy and genre and mostly ignores the mood. A sad listener gets cheerful pop.
- **High-Energy Pop vs. Unknown Genre (k-pop):** There is no k-pop in the data. So nobody gets the genre bonus. Scores drop from about 6.7 to about 3.9. But the songs still make sense, like Sunrise City and Rooftop Lights. Happy mood and high energy carry the match. It fails gracefully.
- **Unknown Genre vs. Near-Miss Genre ("indie" instead of "indie pop"):** Rooftop Lights is indie pop. But "indie" does not equal "indie pop." So it gets no genre credit. It still ranks #1 because mood and energy fit. That works out by luck. The system can't see that the two names are close.
- **Dead Center vs. Extremist:** Dead Center wants the middle of everything. It gets the jazz song Coffee Shop Stories. Extremist wants the calmest, saddest, most acoustic music. It gets the classical piece Ashes on the Strings with a big lead (5.44 vs. 2.08 for #2). That song is the only one near that edge. For unusual tastes, the top song is great and the rest is filler.
- **Chill Lofi vs. Genre-Only Loyalist:** Both say "lofi." But Loyalist also wants angry, high-energy music. No lofi song offers that. Iron Hymn (angry metal) ranks #1. Lofi songs follow close behind. The user asked for two things that don't go together. The system split the difference.
- **High-Energy Pop vs. Out-of-Range Numbers:** Both want happy pop. The second asks for energy 1.5 and tempo 300. Those are impossible. The top songs are similar (Sunrise City, Gym Hero). But scores fall fast after #2, down to about 1.5 by #5. The math doesn't crash. But it also doesn't warn that the request is impossible.
- **Missing Keys:** This profile has no genre or mood. The scorer crashes, and the program catches the error and moves on. This is the one case where the system fails a user completely.

**What surprised me.** (1) Mood is worth so little that a sad listener still gets happy songs. I tested removing the mood check for a while. In 6 of the 11 profiles, the order changed. In 3, the #1 pick changed. The new order was worse or just different, not better. So I put it back. (2) The strongest pull is "do you share a genre with this one song?" Most genres have only one song. (3) The scoring never says "I'm not sure." A bad match and a good match both look confident.

---

## 8. Future Work  

Ideas for how you would improve the model next.  

Prompts:  

- Additional features or preferences  
- Better ways to explain recommendations  
- Improving diversity among the top results  
- Handling more complex user tastes  

**1. Give partial credit for similar genres and moods.** Right now "indie" gets nothing for "indie pop." "Chill" gets nothing for "relaxed." A small table of close cousins would fix this. It would also help genres that have only one song.

**2. Mix up the top 5.** Right now the list stays inside the genre you picked. I would cap how many songs from one genre or artist can appear. That leaves room for one or two surprises.

**3. Handle complex and missing tastes.** Let users pick more than one mood or genre. Make acousticness and valence optional, like tempo. Stop the crash when genre or mood is missing. Add a warning when the best match is weak. Then a poor result won't look as sure as a great one.

**4. Add more songs.** The catalog needs more songs per genre. It also needs mid-energy songs and high-energy acoustic songs.

---

## 9. Personal Reflection  

A few sentences about your experience.  

Prompts:  

- What you learned about recommender systems  
- Something unexpected or interesting you discovered  
- How this changed the way you think about music recommendation apps  

**My biggest learning moment.** It was the experiment where I turned off the mood check. I expected the results to get worse in a clear way. Instead, 6 of my 11 profiles changed order, and 3 got a new #1 pick. Some changes looked worse. Some were just different. That taught me that "different" is not the same as "better." You need a test to tell them apart. It also showed me that a recommender is a set of choices. I picked the features. I picked the weights. Those choices decided who got good results.

**How AI tools helped, and when I double-checked them.** AI helped me move fast. It ran the experiments, compared the outputs, and spotted patterns I would have missed. One example is that most genres have only one song. But I did not trust it blindly. At one point it guessed the dataset had 17 genres. I checked the code's real output, and the true count was 15. That was a good reminder to verify numbers. It also warned me that its big test used made-up profiles with valence fixed at 0.5. So the "most shown songs" numbers were probably exaggerated. I treated those numbers as rough, not as facts. My rule now is simple. AI is good at finding things to look at. I still check the claims against the data.

**What surprised me about simple algorithms.** The scoring is only addition. It adds points for genre, mood and closeness. Yet the results often felt right. The lofi profile got calm, quiet songs. The rock profile got loud, fast ones. The "Reasons" list made it feel even smarter, because it explained itself. But the feeling can be fake. The system never says "I'm not sure." A sad listener still got cheerful pop. A lot of the "smartness" came from the small catalog, not from the math. Gym Hero showing up for happy-pop fans is the clearest example.

**What I would try next.** First, I would give partial credit for similar genres and moods, so "indie" counts a little for "indie pop." Second, I would limit how many songs from one genre or artist can appear, so the top 5 has some variety. Third, I would add many more songs, especially mid-energy and high-energy acoustic ones. Last, I would add a warning when the best match is weak. That way a bad result would not look as sure as a good one.

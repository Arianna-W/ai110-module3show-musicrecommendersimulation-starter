# AI Interactions Log

> Documents the stretch features I attempted: additional attributes (agentic workflow), ranking modes (design pattern), the diversity penalty and the formatted table output.

---

## Agentic Workflow (SF8: Additional Song Attributes)

> Document your experience using an AI agent (e.g., Cursor Agent, Claude, Copilot) to make multi-step changes autonomously.

**What task did you give the agent?**

Extend the song dataset with 5+ complex attributes that the baseline data lacked, then update both `data/songs.csv` and the scoring logic in `src/recommender.py` so the new attributes affect recommendations.

**Prompts used:**

> Introduce 5 or more complex attributes to your dataset that are not currently present in the baseline data, such as Song Popularity (0-100), Release Decade, or Detailed Mood Tags (e.g., "nostalgic," "aggressive," "euphoric"). Update both data/songs.csv and the scoring logic in src/recommender.py so scoring accounts for the new attributes.

**What did the agent generate or change?**

- `data/songs.csv`: added 6 columns to all 18 songs:
  - `popularity` (0-100)
  - `release_decade` (e.g. 1980, 2010)
  - `mood_tags` (pipe-separated, e.g. `nostalgic|dark|driving`)
  - `instrumentalness` (0-1)
  - `explicit` (0/1)
  - `duration_sec`
- `src/recommender.py`:
  - `Song` has six new fields with defaults, so existing code and tests that build a `Song` without them still work.
  - `UserProfile` has six new optional targets: `target_popularity`, `target_decade`, `favorite_mood_tags`, `target_instrumentalness`, `allow_explicit`, `target_duration_sec`.
  - `load_songs` parses the new columns, including splitting `mood_tags` into a list.
  - `BASE_WEIGHTS` has new weights: mood_tags 1.0, popularity 0.5, release_decade 0.5, instrumentalness 0.5, explicit 0.25, duration_sec 0.25.
  - `score_song` scores the numeric attributes by closeness, scaled by a span per feature (`GAP_SPANS`: popularity 100, decade 50 years, duration 180 s). Mood tags earn partial credit by the fraction of wanted tags the song has. Explicit lyrics earn points unless the user opted out.
  - All new features are optional, so a profile that doesn't state the scores exactly as before.
- `src/main.py`: added two profiles that use the new attributes, "Nostalgic Throwback" and "Aggressive Underground".

**What did you verify or fix manually?**

- Ran `pytest`: both existing tests pass unchanged.
- Ran `python src/main.py`. The two new profiles rank sensibly:
  - "Nostalgic Throwback" puts Night Drive Loop (1980 synthwave) first, with all three mood tags matching (+1.00).
  - "Aggressive Underground" puts Iron Hymn first.
  - The older profiles still run. The only ERROR is the pre-existing "Missing Keys" edge case, which is intentional.
- Caught and removed a leftover duplicate `int_fields = ("id",)` line that the agent's edit introduced in `load_songs`. 
- The editor flagged `field` as undefined mid-edit. It was a stale diagnostic from edits applied before the `field` import, and it is resolved now.

---

## Design Pattern (SF10: Multiple Ranking Modes)

> Document how AI helped you choose or implement a design pattern.

**Which design pattern did you use?**

Strategy pattern: each ranking mode is a swappable `RankingStrategy` object, and the scoring code doesn't change between modes.

**How did AI help you brainstorm or implement it?**

Prompt: *"Build two or more different ranking strategies (e.g., Genre-First, Mood-First, Energy-Focused) so a user can switch between modes in main.py. Help me brainstorm a design pattern, like a simple Strategy pattern, that keeps the code modular."*

The assistant looked at `recommender.py` and noticed that `score_song` already took an optional `weights` dict, and that the old `MOOD_FIRST_WEIGHTS` experiment was effectively a one-off strategy. It weighed three options:

1. **`if mode == ...` branches inside `score_song`.** This is simple but gets messier with every new mode.
2. **One scoring class per strategy.** This is flexible but heavy, because every strategy would duplicate the same closeness math.
3. **Strategy as data: a named weight set plus a registry.** The algorithm stays in one place and only the weights vary.

It recommended option 3, since the modes differ only in how much each feature counts, and I accepted that.

**How does the pattern appear in your final code?**

- `RankingStrategy` (frozen dataclass: name, description, weights) and the `STRATEGIES` registry in `src/recommender.py` define four modes:
  - `balanced` (the default weights)
  - `genre-first`
  - `mood-first`
  - `energy-focused`
- `get_strategy()` accepts a name or a `RankingStrategy` and raises a clear `ValueError` for unknown names.
- `Recommender(songs, strategy=...)` and `recommend_songs(..., strategy=...)` pass the chosen weights into `score_song`. The old explicit `weights=` argument still overrides, so nothing existing breaks.
- `src/main.py` exposes this as `python src/main.py --mode genre-first`. `argparse` builds the choices from the registry, so a new strategy shows up in the CLI automatically.

**Manual verification:**

- Existing tests still pass.
- Switching modes visibly changes the results. For "Genre-Only Loyalist", the #1 song is Iron Hymn under `balanced`, but Midnight Coding (the lofi match) under `genre-first`. For "Sad but Hyper", the #1 song is Gym Hero under `balanced` but Blue Highway Blues (the sad song) under `mood-first`.
- An invalid `--mode` is rejected by `argparse` with the list of valid choices.
- The weight values in the strategies are my judgment calls and could be tuned.

---

## Diversity Penalty (Stretch: Diversity, Novelty or Fairness)

The fairness explanation is in `model_card.md`, section 6 ("Diversity and fairness").

**Prompt:** *"Implement a Diversity Penalty that prevents the recommender from suggesting too many songs from the same artist or genre in the top results. A rule to penalize a song's score if its artist is already present in the top recommendations list."*

**What the agent changed:**

- `recommend_songs` in `src/recommender.py` now picks songs greedily. Each pick is the best remaining song after subtracting `ARTIST_PENALTY` (1.0) per already-picked song by the same artist and `GENRE_PENALTY` (0.5) per already-picked song in the same genre. Both penalties are arguments, and 0 disables them.
- Penalties show up in each song's reasons ("repeat artist penalty (-1.00)"), and the displayed score is the adjusted one.
- `Recommender.recommend` goes through `recommend_songs`, so the OOP and functional paths behave the same.
- `src/main.py` has a `--no-diversity` flag for comparison.

**Manual verification:**

- Tests still pass.
- "Chill Lofi" shows the effect. Without the penalty the top 5 is Midnight Coding, Library Rain, Focus Flow, Spacewalk Thoughts, Coffee Shop Stories, so LoRoom appears twice and lofi three times. With it, Focus Flow (LoRoom again, and lofi again) drops from #3 to #4, below Spacewalk Thoughts.
- Profiles with no repeats are unchanged.
- Zero-cost penalty lines were showing up as "-0.00" with `--no-diversity`; I fixed that so they only print when the cost is above 0.
- The penalty sizes are judgment calls. Because the penalty grows with each repeat, a song that is much better than the rest can still win a second slot.

---

## Formatted Terminal Output (Stretch: Visual Output)

**Prompt:** *"Improve the readability of your terminal output by providing a formatted table or summary. Suggest a way to use a library like tabulate or simple ASCII formatting to display your top recommendations. The table must include the reasons for each score."*

**What the agent changed:** `format_recommendations` in `src/main.py` now draws an ASCII table with columns `#`, `Song / Artist`, `Score` and `Reasons`. Each song gets one row block, with its reasons listed one per line and long text wrapped by `textwrap`.

**Why ASCII instead of `tabulate`:** `tabulate` isn't installed and isn't in `requirements.txt`. Adding a dependency just to draw borders wasn't worth it, and about 30 lines of standard-library code does the job. If you prefer `tabulate`, swapping it in would only touch this one function.

**Manual verification:**

- Ran `python src/main.py` and checked the alignment of the tables.
- Checked that penalty lines (from the diversity penalty) show up in the Reasons column.
- Tests still pass.
- The agent's first version had a syntax error: an escaped newline in `"\n".join` had turned into a literal line break. I caught it when the script failed to run and fixed it.

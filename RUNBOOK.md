# ToonSprout daily run

This branch (`pipeline`) holds the tooling and the content inventory. Finished videos live on the `media` branch and are served from
`https://raw.githubusercontent.com/geenkid/toonsprout-videos/media/<series>/<file>.mp4`.

## Accounts

- Buffer organization "My organization" (id `6b05bed28cc521b0525e124d`), free plan.
  - TikTok `toonsprout0`: channel `6b05c0f28541f09ecb8c900c`
  - YouTube `ToonSprout`: channel `6b05c12c8541f09ecb8c91f2`
- Windsor.ai for Social Media: analytics backup (YouTube upload exists but YouTube rate-limited it on 2026-11-24).

## Hard rules

1. Licensing: only CC BY / public domain / creator-authorized. Record license + evidence URL in `inventory.json` before editing. Every post carries the credit line.
2. Order: never schedule Part N on a channel before Part N-1 is scheduled earlier on that channel. Finish a series before starting the next.
3. No duplicates: before creating a post, `list_posts` for the channel (scheduled + sent) and skip if the same episode is there.
4. Mark `published` only when Buffer `get_post` shows status `sent` with an `externalLink`. On `error`, read the error, fix, retry once, then report.
5. Do not spend money, change plans, or post anything not in the inventory.

## Slots (America/New_York, use the correct -05:00 / -04:00 offset)

- TikTok: 9:00 AM, 12:00 PM, 4:00 PM (3 a day).
- YouTube: 9:00 AM and 12:00 PM only. Buffer refused a 3rd YouTube post in one day ("maximum YouTube allows in a day (2)"). If that limit lifts, add 4:00 PM.
  - The YouTube limit is a ROLLING 24 h window and Buffer sends a few minutes late, so a plain 9 AM + 12 PM every day fails (failed 11-25 and 11-26). Rule: each YouTube post must be more than 24 h after the YouTube post two before it. With the 9 AM / 12 PM slots that is the repeating pattern "9+12, 12, 9" (4 posts per 3 days). See `youtube_spacing_rule` in inventory.json.
- Buffer free plan: at most 10 scheduled posts per channel. Keep each channel 3 days ahead, no more.

## Each day

1. `git pull` this branch. Read `inventory.json`.
2. Check yesterday's posts in Buffer (`get_post`); set status `published` + link, or handle errors.
3. Pull stats (`get_post includeMetrics` / `get_aggregated_post_metrics`) into `stats`. Add `"fetched_at": "<ISO time>"` to each snapshot so views per hour is exact.
4. Run `python3 -I scripts/trending.py inventory.json --write`. This scores every post and stores the `trending` block (see "Story selection").
5. If fewer than 4 unscheduled rendered episodes remain, pick the next story by trending score (see "Story selection"): download, confirm license, plan cuts at scene changes (`ffmpeg ... select='gt(scene,0.3)'`) and subtitle gaps, 50-90 s each, end on a cliffhanger, render with `scripts/render.py`, push mp4s to `media`, add episodes to the inventory. Add the new series to `series_meta` with its tags.
6. Fill free slots up to 3 days ahead per channel, in order.
7. Commit `inventory.json` and post a short summary in the project thread (what was scheduled, any errors, the top 3 posts by trending score, and which story is next and why).

## Story selection (trending score)

```
trending_score = 0.65 x percentile(views_per_hour)
               + 0.25 x percentile(like_rate)
               + 0.10 x percentile(share_rate)
```

`scripts/trending.py` computes it per post. Percentiles are within one platform. `views_per_hour` uses the stats snapshot nearest 48 h after posting, `like_rate` = reactions / views, `share_rate` = shares / views. A platform is ignored for picks until its best post has 50+ views (YouTube is ignored for now). 50 means "average for this channel".

How to use it:

1. **Which story next.** Take the top *unblocked* entry of `trending.queue_ranking`. Each queue entry has `tags`; a tag's score blends the measured average of posts with that tag and the starting guess in `tag_priors` (the guess counts as 5 posts, so real data takes over quickly). Licensing and the series-order rule still come first. If the top entry's host is refused, mark it `blocked` with the date and take the next.
2. **Finding new stories.** When fewer than 3 unblocked entries are left, look for more CC BY / public-domain animated films whose tags match the top 3 tags in `trending.tags`, record license evidence, give them `tags`, and add them to `source_queue`. Favour: funny animals, comedy, spooky/creature stories, no-dialogue films (work with sound off and in any language). Avoid surreal/abstract films unless their measured score rises.
3. **Which moment opens an episode.** The top posts so far are finales and reveal moments (Sintel 5, Sprite Fright 3). Plan cuts so each part opens on action or a question within 3 s, and ends just before a reveal.
4. **Hooks and captions.** Copy the style of the 3 highest-scoring posts' hooks (short, a question or a threat, under 8 words). Captions end with a question that invites comments plus "Follow for Part N+1".
5. **Low scorers.** If a series' first 2 parts both score under 30 on TikTok, finish it (no orphan parts) but drop tags it shares with nothing that scores well from the next pick.
6. **Order of episodes inside a series never changes**, and no duplicates, whatever the score.

## Growth rules (from Nov 2026 research)

- Shorter parts: 50-90 s. Average watch time on our 90-178 s parts is only 10-34 s; short-form data shows 30-60 s videos finish most often, and more, shorter parts give more cliffhangers and more posts per film.
- First 3 s decide retention: no intros; hook text on screen in the first second; something changes on screen every 3-5 s.
- Keep burned-in captions (most viewers watch muted).
- Keep the gap between parts of a series at 1-3 days (current schedule already does this).
- Things Hunter can do by hand (the API can't): pin Part 1 of the current series on the TikTok profile, and reply to comments.

## render.py

`python3 -I scripts/render.py SRC SRT START END TITLE "PART n of N" "Hook|line 2" "Credit line" OUT.mp4`

1080x1920, blurred background, burned subtitles, hook text for the first 3.5 s, H.264 capped at 3.5 Mbps so files stay under 100 MB. Use an empty SRT file for films with no dialogue.

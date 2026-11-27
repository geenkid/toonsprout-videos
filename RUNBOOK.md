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
3. Pull stats (`get_post includeMetrics` / `get_aggregated_post_metrics`) into `stats`.
4. If fewer than 4 unscheduled rendered episodes remain, take the next `source_queue` entry: download, confirm license, plan cuts at scene changes (`ffmpeg ... select='gt(scene,0.3)'`) and subtitle gaps, 90-178 s each, end on a cliffhanger, render with `scripts/render.py`, push mp4s to `media`, add episodes to the inventory.
5. Fill free slots up to 3 days ahead per channel, in order.
6. Commit `inventory.json` and post a short summary in the project thread (what was scheduled, any errors, best and worst performers).

## render.py

`python3 -I scripts/render.py SRC SRT START END TITLE "PART n of N" "Hook|line 2" "Credit line" OUT.mp4`

1080x1920, blurred background, burned subtitles, hook text for the first 3.5 s, H.264 capped at 3.5 Mbps so files stay under 100 MB. Use an empty SRT file for films with no dialogue.

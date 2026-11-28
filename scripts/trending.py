#!/usr/bin/env python3
"""Trending score for ToonSprout posts, series and story tags.

    trending_score = 0.65 * pct(views_per_hour)
                   + 0.25 * pct(like_rate)
                   + 0.10 * pct(share_rate)

pct() is the percentile rank (0-100, ties averaged) within the same platform.
For each post the snapshot used is the one closest to 48 h after posting
(at least 6 h), so old and new posts are compared over a similar window.

  views_per_hour = views / hours since posting (at that snapshot)
  like_rate      = reactions / views
  share_rate     = shares / views

Usage:
  python3 -I scripts/trending.py inventory.json          # print the report
  python3 -I scripts/trending.py inventory.json --write  # also store it in inventory.json["trending"]

The `trending` block is what the daily run uses to pick and order stories
(see "Story selection" in RUNBOOK.md).
"""
import json, re, sys
from datetime import datetime, timedelta, timezone

W_VPH, W_LIKE, W_SHARE = 0.65, 0.25, 0.10
TARGET_H, MIN_H = 48.0, 6.0
MIN_COHORT_VIEWS = 50
PRIOR_WEIGHT = 5   # a platform whose best post has fewer views is "not enough data"
ET = timezone(timedelta(hours=-5))  # good enough for a 12:00 fallback


def snapshot_time(day, snap, platform):
    """Best guess of when a stats snapshot was taken."""
    if snap.get("fetched_at"):
        return datetime.fromisoformat(snap["fetched_at"].replace("Z", "+00:00"))
    text = " ".join(str(snap.get(k, "")) for k in ("source", "note"))
    z = re.findall(r"(\d{1,2}):(\d{2})Z", text)
    if z:
        h, m = z[1] if (platform == "youtube" and len(z) > 1) else z[0]
        return datetime.fromisoformat(f"{day}T{int(h):02d}:{m}:00+00:00")
    et = re.search(r"(\d{1,2}):(\d{2}) ET", text)
    if et:
        return datetime.fromisoformat(f"{day}T{int(et.group(1)):02d}:{et.group(2)}:00-05:00")
    return datetime.fromisoformat(f"{day}T12:00:00").replace(tzinfo=ET)


def pick_snapshot(posted, stats, platform):
    best = None
    for day, snap in stats.items():
        if not isinstance(snap, dict) or "views" not in snap:
            continue
        hours = (snapshot_time(day, snap, platform) - posted).total_seconds() / 3600
        if hours < MIN_H:
            continue
        key = abs(hours - TARGET_H)
        if best is None or key < best[0]:
            best = (key, hours, snap)
    return best


def pct_rank(values):
    """Percentile rank 0-100 with ties averaged."""
    n = len(values)
    if n == 1:
        return [50.0]
    order = sorted(range(n), key=lambda i: values[i])
    ranks = [0.0] * n
    i = 0
    while i < n:
        j = i
        while j + 1 < n and values[order[j + 1]] == values[order[i]]:
            j += 1
        r = (i + j) / 2
        for k in range(i, j + 1):
            ranks[order[k]] = 100.0 * r / (n - 1)
        i = j + 1
    return ranks


def series_tags(inv):
    meta = inv.get("series_meta", {})
    return {s: m.get("tags", []) for s, m in meta.items()}


def compute(inv):
    posts = []
    for ep in inv.get("episodes", []):
        for plat in ("tiktok", "youtube"):
            info = ep.get(plat) or {}
            if info.get("status") != "published" or not info.get("due"):
                continue
            posted = datetime.fromisoformat(info["due"])
            snap = pick_snapshot(posted, (ep.get("stats") or {}).get(plat, {}), plat)
            if not snap:
                continue
            _, hours, s = snap
            views = s.get("views", 0) or 0
            posts.append({
                "id": ep["id"], "series": ep["series"], "part": ep.get("part"),
                "platform": plat, "hours": round(hours, 1), "views": views,
                "views_per_hour": views / hours,
                "like_rate": (s.get("reactions", 0) or 0) / views if views else 0.0,
                "share_rate": (s.get("shares", 0) or 0) / views if views else 0.0,
                "avg_watch_s": s.get("avg_watch_s"),
                "hook": ep.get("hook"),
            })

    platforms = {}
    for plat in ("tiktok", "youtube"):
        group = [p for p in posts if p["platform"] == plat]
        if not group:
            continue
        enough = max(p["views"] for p in group) >= MIN_COHORT_VIEWS and len(group) >= 3
        platforms[plat] = {"posts": len(group), "enough_data": enough}
        for metric in ("views_per_hour", "like_rate", "share_rate"):
            for p, r in zip(group, pct_rank([p[metric] for p in group])):
                p["pct_" + metric] = r
        for p in group:
            p["trending_score"] = round(W_VPH * p["pct_views_per_hour"] + W_LIKE * p["pct_like_rate"]
                                        + W_SHARE * p["pct_share_rate"], 1)

    # Series and tag scores use only platforms with enough data.
    scored = [p for p in posts if platforms[p["platform"]]["enough_data"]]
    tags = series_tags(inv)

    def agg(key_fn):
        out = {}
        for p in scored:
            for k in key_fn(p):
                out.setdefault(k, []).append(p)
        return {k: {"score": round(sum(p["trending_score"] for p in v) / len(v), 1),
                    "posts": len(v),
                    "views_per_hour": round(sum(p["views_per_hour"] for p in v) / len(v), 2)}
                for k, v in sorted(out.items(), key=lambda kv: -sum(p["trending_score"] for p in kv[1]) / len(kv[1]))}

    series = agg(lambda p: [p["series"]])
    tag_scores = agg(lambda p: tags.get(p["series"], []))

    for p in posts:
        for k in ("views_per_hour", "like_rate", "share_rate"):
            p[k] = round(p[k], 4)
        for k in list(p):
            if k.startswith("pct_"):
                p[k] = round(p[k], 1)
    posts.sort(key=lambda p: (p["platform"], -p.get("trending_score", 0)))
    return {
        "computed_at": datetime.now(timezone.utc).isoformat(timespec="minutes"),
        "formula": "0.65*pct(views_per_hour) + 0.25*pct(like_rate) + 0.10*pct(share_rate), percentiles within platform, snapshot nearest 48 h after posting",
        "platforms": platforms,
        "series": series,
        "tags": tag_scores,
        "posts": posts,
    }


def predict(inv, trending):
    """Predicted score for each source_queue entry from its tags.

    Each tag's score blends its measured score with the research prior in
    tag_priors (default 50); the prior counts as PRIOR_WEIGHT posts. A score of
    50 means "average for this channel". Average over the tags.
    """
    priors = inv.get("tag_priors", {})
    out = []
    for s in inv.get("source_queue", []):
        t = s.get("tags", [])
        vals = []
        for tag in t:
            prior = priors.get(tag, 50)
            m = trending["tags"].get(tag)
            if m:  # blend: the prior counts as PRIOR_WEIGHT posts, so data takes over as posts add up
                vals.append((m["score"] * m["posts"] + prior * PRIOR_WEIGHT) / (m["posts"] + PRIOR_WEIGHT))
            else:
                vals.append(prior)
        score = round(sum(vals) / len(vals), 1) if vals else 50.0
        out.append({"series": s["series"], "predicted_score": score,
                    "blocked": bool(s.get("blocked")), "tags": t})
    out.sort(key=lambda x: (x["blocked"], -x["predicted_score"]))
    return out


def main():
    path = sys.argv[1]
    inv = json.load(open(path))
    tr = compute(inv)
    tr["queue_ranking"] = predict(inv, tr)
    for plat, info in tr["platforms"].items():
        print(f"\n== {plat} ({info['posts']} posts{'' if info['enough_data'] else ', NOT enough data, ignored for picks'})")
        print(f"{'post':28} {'score':>5} {'v/h':>7} {'like%':>6} {'share%':>6} {'hrs':>5}")
        for p in tr["posts"]:
            if p["platform"] == plat:
                print(f"{p['id']:28} {p['trending_score']:5.1f} {p['views_per_hour']:7.2f} "
                      f"{100*p['like_rate']:6.1f} {100*p['share_rate']:6.2f} {p['hours']:5.0f}")
    print("\n== series");  [print(f"{k:30} {v['score']:5.1f}  ({v['posts']} posts)") for k, v in tr["series"].items()]
    print("\n== tags");    [print(f"{k:30} {v['score']:5.1f}  ({v['posts']} posts)") for k, v in tr["tags"].items()]
    print("\n== source_queue ranking (pick the top unblocked one)")
    for q in tr["queue_ranking"]:
        print(f"{q['series']:36} {q['predicted_score']:5.1f} {'BLOCKED' if q['blocked'] else ''}")
    if "--write" in sys.argv:
        inv["trending"] = tr
        with open(path, "w") as f:
            json.dump(inv, f, indent=1, ensure_ascii=False)
            f.write("\n")


if __name__ == "__main__":
    main()

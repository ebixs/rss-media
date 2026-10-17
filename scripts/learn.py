"""Learning loop for RSS Instagram content: a Thompson-sampling bandit.

Every published post is scored from its real Instagram numbers (Metricool),
and each "arm" the post used (service/topic, goal, hook formula) gets that
score as evidence. Over time the arms that actually earn saves, shares,
comments and follows get picked more often; weak ones less, but never zero
(exploration). The owner can steer it with learning/directions.json.

    python3 scripts/learn.py update        # rescore from learning/metrics.json
    python3 scripts/learn.py choose        # suggest the next post's arms (JSON)

Files (all in learning/):
    metrics.json     per-post Instagram numbers, written by the check task
                     {"<instagram url>": {"date", "reach", "likes", "comments",
                      "saved", "shares", "follows", "views", "service", "goal",
                      "hook_formula", "source"}}
    directions.json  owner steering from the dashboard
                     {"boost": {"service:<x>": 1.5}, "block": ["service:<y>"],
                      "focus_note": "...", "updated_at": "..."}
    state.json       current posterior per arm (written by update)
    history.json     one row per update, for the learning curve
"""
from __future__ import annotations

import datetime as dt
import json
import pathlib
import random
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
L = ROOT / "learning"
PSEUDO = 20          # how many "trials" one post counts as
PRIOR_STRENGTH = 6   # an untried arm starts near the account average, not at 50%
MIN_AGE_H = 72       # a post is scored only after it had 3 days to collect numbers
DIMENSIONS = ("service", "goal", "hook_formula")

ALLOWED_SERVICES = [
    "تزریق در منزل", "وصل سرم", "نمونه‌گیری خون در منزل", "پانسمان و مراقبت زخم",
    "پانسمان سوختگی", "سونداژ ادراری", "کنترل علائم حیاتی", "تست قند خون",
    "نوار قلب در منزل", "اکسیژن‌درمانی", "مراقبت پس از جراحی", "ویزیت پزشک عمومی در منزل",
]
GOALS = ["ذخیره و اشتراک", "اعتمادسازی", "تماس", "معرفی خدمت"]


def load(name, default):
    p = L / name
    if not p.exists():
        return default
    return json.loads(p.read_text(encoding="utf-8"))


def save(name, data):
    L.mkdir(exist_ok=True)
    (L / name).write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")


def reward(m: dict) -> float:
    """Weighted interactions per person reached, 0..1.

    Saves and shares are what Instagram rewards most and what signal real
    usefulness, so they weigh more than likes. A follow is the strongest.
    """
    reach = max(float(m.get("reach") or 0), 1.0)
    pts = (float(m.get("likes") or 0) + 2 * float(m.get("comments") or 0)
           + 3 * float(m.get("saved") or 0) + 3 * float(m.get("shares") or 0)
           + 5 * float(m.get("follows") or 0))
    return min(pts / reach, 1.0)


def old_enough(m: dict, now: dt.datetime) -> bool:
    try:
        d = dt.datetime.fromisoformat(m["date"])
    except (KeyError, ValueError):
        return False
    if d.tzinfo is None:
        d = d.replace(tzinfo=dt.timezone.utc)
    return (now - d).total_seconds() >= MIN_AGE_H * 3600


def update():
    now = dt.datetime.now(dt.timezone.utc)
    metrics = load("metrics.json", {})
    arms: dict[str, dict] = {}
    scored = []
    ready = [m for m in metrics.values() if old_enough(m, now)]
    mu = sum(reward(m) for m in ready) / len(ready) if ready else 0.15
    prior = prior_for(mu)
    for url, m in metrics.items():
        if not old_enough(m, now):
            continue
        r = reward(m)
        scored.append({"url": url, "date": m["date"], "reward": round(r, 4),
                       "reach": m.get("reach"), "service": m.get("service"),
                       "source": m.get("source", "rss")})
        for dim in DIMENSIONS:
            val = m.get(dim)
            if not val:
                continue
            key = f"{dim}:{val}"
            a = arms.setdefault(key, {"alpha": prior[0], "beta": prior[1], "n": 0, "rewards": []})
            a["alpha"] += r * PSEUDO
            a["beta"] += (1 - r) * PSEUDO
            a["n"] += 1
            a["rewards"].append(round(r, 4))
    for a in arms.values():
        a["mean"] = round(a["alpha"] / (a["alpha"] + a["beta"]), 4)
    scored.sort(key=lambda s: s["date"])
    avg_all = round(sum(s["reward"] for s in scored) / len(scored), 4) if scored else None
    recent = scored[-4:]
    avg_recent = round(sum(s["reward"] for s in recent) / len(recent), 4) if recent else None
    state = {"updated_at": now.isoformat(timespec="seconds"), "posts_scored": len(scored),
             "prior": {"mean": round(mu, 4), "alpha": round(prior[0], 3), "beta": round(prior[1], 3)},
             "avg_reward": avg_all, "avg_reward_last4": avg_recent, "arms": arms, "posts": scored}
    save("state.json", state)
    history = [h for h in load("history.json", []) if h.get("date") != now.date().isoformat()]
    history.append({"date": now.date().isoformat(), "posts_scored": len(scored),
                    "avg_reward": avg_all, "avg_reward_last4": avg_recent,
                    "best": {d: best_arm(arms, d) for d in DIMENSIONS}})
    save("history.json", history[-200:])
    print(json.dumps({k: state[k] for k in ("posts_scored", "avg_reward", "avg_reward_last4")}, ensure_ascii=False))


def prior_for(mu):
    return (1 + mu * PRIOR_STRENGTH, 1 + (1 - mu) * PRIOR_STRENGTH)


def best_arm(arms, dim):
    cands = [(k, v["mean"]) for k, v in arms.items() if k.startswith(dim + ":") and v["n"] > 0]
    return max(cands, key=lambda x: x[1])[0].split(":", 1)[1] if cands else None


def choose(seed=None):
    rng = random.Random(seed)
    state = load("state.json", {"arms": {}})
    directions = load("directions.json", {})
    boost = directions.get("boost", {})
    block = set(directions.get("block", []))
    recent = [p.get("service") for p in sorted(state.get("posts", []), key=lambda p: p["date"])[-3:]]
    options = {"service": ALLOWED_SERVICES, "goal": GOALS}
    out = {"reasoning": {}}
    for dim, values in options.items():
        draws = []
        for v in values:
            key = f"{dim}:{v}"
            if key in block or (dim == "service" and v in recent):
                continue
            pr = state.get("prior", {"alpha": 1.9, "beta": 6.1})
            a = state["arms"].get(key, {"alpha": pr["alpha"], "beta": pr["beta"], "n": 0})
            draw = rng.betavariate(a["alpha"], a["beta"]) * float(boost.get(key, 1.0))
            draws.append((draw, v, a["n"]))
        draws.sort(reverse=True)
        out[dim] = draws[0][1]
        out["reasoning"][dim] = [{"value": v, "draw": round(d, 3), "evidence_posts": n} for d, v, n in draws[:3]]
    hooks = {k.split(":", 1)[1]: v for k, v in state["arms"].items() if k.startswith("hook_formula:")}
    out["hook_formula_scores"] = {k: v["mean"] for k, v in sorted(hooks.items(), key=lambda x: -x[1]["mean"])}
    out["focus_note"] = directions.get("focus_note", "")
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "update"
    {"update": update, "choose": choose}[cmd]()

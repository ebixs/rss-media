"""Build the JSON files the RSS marketing dashboard reads.

    python3 scripts/dashboard_data.py /path/to/rss-social   # writes dashboard/*.json

Outputs (row objects, one file per dashboard source):
    dashboard/pipeline.json          every produced item: SEO page, Instagram post, Telegram post
    dashboard/learning_arms.json     the learner's current estimate per option
    dashboard/learning_history.json  one row per learning update
    dashboard/directions.json        the owner's current steering, as rows
"""
import json, pathlib, re, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "dashboard"
DIM_FA = {"service": "موضوع خدمت", "goal": "هدف پست", "hook_formula": "فرمول قلاب"}


def header(path):
    t = path.read_text(encoding="utf-8")
    if not t.startswith("---"):
        return {}
    meta = {}
    for line in t.split("---", 2)[1].strip().splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            meta[k.strip()] = v.strip()
    return meta


def main(social_dir):
    OUT.mkdir(exist_ok=True)
    rows = []
    for d in sorted((ROOT / "posts").glob("*/post.md")):
        m = header(d)
        rec = {}
        mj = d.parent / "metricool.json"
        if mj.exists():
            rec = json.loads(mj.read_text(encoding="utf-8"))
        result = str(rec.get("result", "")).upper()
        status = {"PUBLISHED": "published", "PENDING": "scheduled", "FAILED": "failed",
                  "NOT_PUBLISHED": "failed"}.get(result, "scheduled" if rec.get("post_id") else "draft")
        if rec.get("instagram_url"):
            status = "published"
        rows.append({"channel": "instagram", "date": d.parent.name[:10], "title": m.get("topic") or m.get("headline", ""),
                     "status": status, "link": rec.get("instagram_url", ""), "detail": m.get("service", "")})
    sdir = pathlib.Path(social_dir) if social_dir else None
    if sdir and sdir.exists():
        for sub, status in (("sent", "published"), ("queue", "scheduled")):
            for f in sorted((sdir / sub).glob("*.md")):
                mt = re.match(r"(\d{4}-\d{2}-\d{2})T\d{4}Z_(.+)\.md", f.name)
                if not mt:
                    continue
                body = f.read_text(encoding="utf-8").split("---", 2)[-1].strip()
                first = next((l.strip() for l in body.splitlines() if l.strip()), "")
                rows.append({"channel": "telegram", "date": mt.group(1), "title": first[:90],
                             "status": status, "link": "", "detail": mt.group(2)})
    seo = json.loads((ROOT / "learning" / "seo.json").read_text(encoding="utf-8"))
    for s in seo:
        rows.append({"channel": "seo", "date": s["date"], "title": s["title"], "status": s["status"],
                     "link": "", "detail": s.get("note", "")})
    rows.sort(key=lambda r: r["date"], reverse=True)
    (OUT / "pipeline.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")

    st = json.loads((ROOT / "learning" / "state.json").read_text(encoding="utf-8"))
    arms = []
    for key, a in st.get("arms", {}).items():
        dim, val = key.split(":", 1)
        lo = a["alpha"] / (a["alpha"] + a["beta"])
        n = a["alpha"] + a["beta"]
        sd = (lo * (1 - lo) / (n + 1)) ** 0.5
        arms.append({"dimension": DIM_FA.get(dim, dim), "option": val, "posts": a["n"],
                     "score": round(a["mean"], 4), "low": round(max(0, a["mean"] - 1.96 * sd), 4),
                     "high": round(min(1, a["mean"] + 1.96 * sd), 4)})
    arms.sort(key=lambda r: (r["dimension"], -r["score"]))
    (OUT / "learning_arms.json").write_text(json.dumps(arms, ensure_ascii=False, indent=1), encoding="utf-8")

    hist = json.loads((ROOT / "learning" / "history.json").read_text(encoding="utf-8"))
    hrows = [{"date": h["date"], "posts_scored": h["posts_scored"], "avg_reward": h["avg_reward"],
              "avg_reward_last4": h["avg_reward_last4"]} for h in hist]
    (OUT / "learning_history.json").write_text(json.dumps(hrows, ensure_ascii=False, indent=1), encoding="utf-8")

    dr = json.loads((ROOT / "learning" / "directions.json").read_text(encoding="utf-8"))
    drows = [{"kind": "تقویت", "target": k, "value": str(v)} for k, v in dr.get("boost", {}).items()]
    drows += [{"kind": "ممنوع", "target": k, "value": ""} for k in dr.get("block", [])]
    if dr.get("focus_note"):
        drows.append({"kind": "یادداشت تمرکز", "target": "", "value": dr["focus_note"]})
    if not drows:
        drows.append({"kind": "هنوز جهتی ثبت نشده", "target": "", "value": ""})
    (OUT / "directions.json").write_text(json.dumps(drows, ensure_ascii=False, indent=1), encoding="utf-8")
    print({p.name: len(json.loads(p.read_text(encoding="utf-8"))) for p in OUT.glob("*.json")})


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "")

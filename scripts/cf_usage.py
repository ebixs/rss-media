"""Print Workers AI usage (neurons per hour and model) for the last 3 days. Read-only."""
import json, os, urllib.request, datetime as dt
since = (dt.datetime.utcnow() - dt.timedelta(days=3)).strftime("%Y-%m-%dT%H:00:00Z")
q = """query($a:String!,$s:Time!){viewer{accounts(filter:{accountTag:$a}){
 aiInferenceAdaptiveGroups(limit:500, filter:{datetimeHour_geq:$s}, orderBy:[datetimeHour_ASC]){
  count sum{totalNeurons} dimensions{datetimeHour modelId}}}}}"""
req = urllib.request.Request("https://api.cloudflare.com/client/v4/graphql",
    data=json.dumps({"query": q, "variables": {"a": os.environ["CF_ACCOUNT_ID"], "s": since}}).encode(),
    headers={"Authorization": f"Bearer {os.environ['CF_API_TOKEN']}", "Content-Type": "application/json"})
try:
    r = json.load(urllib.request.urlopen(req, timeout=60))
except urllib.error.HTTPError as e:
    print("HTTP", e.code, e.read()[:400]); raise SystemExit(0)
if r.get("errors"):
    print("errors:", json.dumps(r["errors"])[:600]); raise SystemExit(0)
rows = r["data"]["viewer"]["accounts"][0]["aiInferenceAdaptiveGroups"]
day = {}
for x in rows:
    d = x["dimensions"]; n = x["sum"]["totalNeurons"]
    print(d["datetimeHour"], d["modelId"], "requests", x["count"], "neurons", round(n))
    day[d["datetimeHour"][:10]] = day.get(d["datetimeHour"][:10], 0) + n
print("per UTC day:", {k: round(v) for k, v in day.items()})

"""Check which Cloudflare account/token the GitHub secrets belong to. Prints no secret."""
import hashlib, json, os, urllib.request
acc, tok = os.environ["CF_ACCOUNT_ID"].strip(), os.environ["CF_API_TOKEN"].strip()
print("account id matches the dashboard account:", acc == "190792b9bf88c5f37656013ef714314d")
print("account id first 6 chars:", acc[:6])
def get(url):
    try:
        r = json.load(urllib.request.urlopen(urllib.request.Request(url, headers={"Authorization": f"Bearer {tok}"}), timeout=30))
        return r
    except urllib.error.HTTPError as e:
        return {"http": e.code, "body": e.read()[:200].decode("utf-8", "replace")}
u = get("https://api.cloudflare.com/client/v4/user/tokens/verify")
print("user-token verify:", json.dumps({k: u.get(k) for k in ("success", "http")}), (u.get("result") or {}).get("status"), (u.get("result") or {}).get("id"))
a = get(f"https://api.cloudflare.com/client/v4/accounts/{acc}/tokens/verify")
print("account-token verify:", json.dumps({k: a.get(k) for k in ("success", "http")}), (a.get("result") or {}).get("status"), (a.get("result") or {}).get("id"))

ra, rt = os.environ.get("CF_REEL_ACCOUNT_ID", "").strip(), os.environ.get("CF_REEL_API_TOKEN", "").strip()
for k in ("CF_REEL_ACCOUNT_ID", "CF_REEL_API_TOKEN", "V_CF_REEL_ACCOUNT_ID", "V_CF_REEL_API_TOKEN"):
    print(k, "present" if os.environ.get(k, "").strip() else "missing")
print("reel account set:", bool(ra and rt), "| is the ebrahimsalimi123 account:", ra == "190792b9bf88c5f37656013ef714314d")
if ra and rt:
    tok = rt
    r = get(f"https://api.cloudflare.com/client/v4/accounts/{ra}/tokens/verify")
    u2 = get("https://api.cloudflare.com/client/v4/user/tokens/verify")
    print("reel token verify (account / user):", r.get("success") or r.get("http"), "/", u2.get("success") or u2.get("http"))

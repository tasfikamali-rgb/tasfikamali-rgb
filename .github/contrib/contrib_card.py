"""Builds assets/contrib-{dark,light}.svg from the live GitHub contribution calendar.

Runs in GitHub Actions on a schedule. Private contributions are included in the total
because the profile has "Include private contributions" turned on; no repo names are read.
"""
import json, os, sys, urllib.request, datetime as dt
from zoneinfo import ZoneInfo

USER = os.environ.get("GH_USER", "tasfikamali-rgb")
TOKEN = os.environ["GITHUB_TOKEN"]
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.environ.get("OUT_DIR", os.path.join(HERE, "..", "..", "assets"))
TZ = ZoneInfo("America/Edmonton")

now = dt.datetime.now(TZ)
year = now.year
q = """query($u:String!,$f:DateTime!,$t:DateTime!){user(login:$u){contributionsCollection(from:$f,to:$t){
  contributionCalendar{totalContributions weeks{contributionDays{date contributionCount weekday}}}}}}"""
body = json.dumps({"query": q, "variables": {"u": USER, "f": f"{year}-01-01T00:00:00Z", "t": now.astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}}).encode()
req = urllib.request.Request("https://api.github.com/graphql", body, {"Authorization": f"bearer {TOKEN}", "User-Agent": USER})
cal = json.load(urllib.request.urlopen(req))["data"]["user"]["contributionsCollection"]["contributionCalendar"]

days = []
for wi, w in enumerate(cal["weeks"]):
    for d in w["contributionDays"]:
        d["col"] = wi; days.append(d)
total = cal["totalContributions"]
counts = [d["contributionCount"] for d in days]
active = sum(1 for c in counts if c)
best = max(counts) if counts else 0
longest = cur = 0
for c in counts:
    cur = cur + 1 if c else 0
    longest = max(longest, cur)
rev = counts[::-1]
if rev and rev[0] == 0: rev = rev[1:]   # today is not over yet
current = 0
for c in rev:
    if not c: break
    current += 1

THEMES = {
    "dark": dict(bg="#0E1411", line="#26332C", ink="#ECE8DC", muted="#8F9C94", faint="#5A6860", gold="#F2CD00",
                 scale=["#1A2420", "#1F4A30", "#2E7A4A", "#5FB37C", "#F2CD00"]),
    "light": dict(bg="#FFFDF7", line="#DED7C7", ink="#15201A", muted="#5D6A62", faint="#9AA59E", gold="#8A7200",
                  scale=["#ECE7DA", "#BFD9C3", "#7DB58E", "#275D38", "#E2BC00"]),
}
FONT_CSS = open(os.path.join(HERE, "fonts.css")).read()
SG = "'SG','Space Grotesk',ui-sans-serif,-apple-system,'Segoe UI',Helvetica,Arial,sans-serif"
IN = "'IN','Inter',ui-sans-serif,-apple-system,'Segoe UI',Helvetica,Arial,sans-serif"
JB = "'JB','JetBrains Mono',ui-monospace,SFMono-Regular,Menlo,Consolas,monospace"

def level(c):
    if c == 0: return 0
    if best <= 4: return min(c, 4)
    r = c / best
    return 1 if r < .25 else 2 if r < .5 else 3 if r < .85 else 4

def card(th):
    t = THEMES[th]; W, H = 1000, 262
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" '
         f'aria-label="{total} contributions in {year}, including private repositories">'
         f'<title>{total} contributions in {year}</title><style>{FONT_CSS}'
         '@keyframes pop{from{opacity:0;transform:scale(.4)}to{opacity:1;transform:scale(1)}}'
         '.c{transform-box:fill-box;transform-origin:center;animation:pop .45s cubic-bezier(.2,.8,.2,1) both}</style>',
         f'<rect x="0.5" y="0.5" width="{W-1}" height="{H-1}" rx="18" fill="{t["bg"]}" stroke="{t["line"]}"/>',
         f'<text x="28" y="44" font-family="{JB}" font-weight="500" font-size="12" letter-spacing="1.3" fill="{t["gold"]}">CONTRIBUTIONS IN {year}</text>']
    # odometer: each digit rolls up from 0 to its value
    digits = f"{total:,}"
    x, dw, base = 28, 39, 112
    o.append(f'<clipPath id="clip"><rect x="20" y="{base-58}" width="260" height="72"/></clipPath><g clip-path="url(#clip)">')
    for i, ch in enumerate(digits):
        if ch == ",":
            o.append(f'<text x="{x+6}" y="{base}" font-family="{SG}" font-weight="600" font-size="64" fill="{t["ink"]}">,</text>'); x += 18; continue
        n = int(ch); col = "".join(f'<text x="{x+dw/2}" y="{base + k*72}" text-anchor="middle" font-family="{SG}" font-weight="600" font-size="64" fill="{t["ink"]}">{k}</text>' for k in range(10))
        o.append(f'<g>{col}<animateTransform attributeName="transform" type="translate" from="0 0" to="0 {-n*72}" dur="{1.2+i*0.25:.2f}s" '
                 f'calcMode="spline" keySplines=".2 .8 .2 1" keyTimes="0;1" fill="freeze"/></g>')
        x += dw
    o.append("</g>")
    o.append(f'<text x="28" y="146" font-family="{IN}" font-weight="400" font-size="14" fill="{t["muted"]}">including private course and client repos</text>')
    # year heatmap
    gx, gy, p, cs = 318, 30, 12.4, 9.6
    for d in days:
        cx, cy = gx + d["col"] * p, gy + d["weekday"] * p
        lv = level(d["contributionCount"])
        o.append(f'<rect class="c" style="animation-delay:{0.3 + d["col"]*0.025:.2f}s" x="{cx:.1f}" y="{cy:.1f}" width="{cs}" height="{cs}" rx="2.4" fill="{t["scale"][lv]}">'
                 f'<title>{d["date"]}: {d["contributionCount"]}</title></rect>')
    if days:
        d = days[-1]; cx, cy = gx + d["col"] * p, gy + d["weekday"] * p
        o.append(f'<rect x="{cx-2:.1f}" y="{cy-2:.1f}" width="{cs+4}" height="{cs+4}" rx="3.5" fill="none" stroke="{t["gold"]}" stroke-width="1.6">'
                 f'<animate attributeName="opacity" values="1;.15;1" dur="1.8s" repeatCount="indefinite"/></rect>')
    seen = set()
    for d in days:
        m = d["date"][:7]
        if m not in seen and int(d["date"][8:]) <= 7:
            seen.add(m)
            o.append(f'<text x="{gx + d["col"]*p:.1f}" y="{gy + 7*p + 14:.1f}" font-family="{JB}" font-weight="400" font-size="10" fill="{t["faint"]}">{dt.date.fromisoformat(d["date"]).strftime("%b").upper()}</text>')
    # stat strip
    stats = [("LONGEST STREAK", f"{longest} days"), ("CURRENT STREAK", f"{current} days"), ("ACTIVE DAYS", f"{active}"), ("BEST DAY", f"{best}")]
    o.append(f'<line x1="28" y1="182" x2="{W-28}" y2="182" stroke="{t["line"]}"/>')
    cw = (W - 56) / 4
    for i, (k, v) in enumerate(stats):
        sx = 28 + i * cw
        o.append(f'<text x="{sx}" y="210" font-family="{JB}" font-weight="500" font-size="11" letter-spacing="1.1" fill="{t["muted"]}">{k}</text>')
        o.append(f'<text x="{sx}" y="238" font-family="{SG}" font-weight="600" font-size="22" fill="{t["ink"]}">{v}</text>')
    o.append(f'<circle cx="{W-150}" cy="142" r="3.5" fill="{t["scale"][3]}"><animate attributeName="opacity" values="1;.2;1" dur="1.6s" repeatCount="indefinite"/></circle>')
    o.append(f'<text x="{W-28}" y="146" text-anchor="end" font-family="{JB}" font-weight="400" font-size="10.5" fill="{t["faint"]}">LIVE  ·  every 30 min</text>')
    o.append("</svg>")
    return "".join(o)

os.makedirs(OUT, exist_ok=True)
for th in THEMES:
    open(os.path.join(OUT, f"contrib-{th}.svg"), "w").write(card(th))
print(total, active, best, longest, current)

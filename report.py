import json
import hashlib
from datetime import datetime


def md5(s: str) -> str:
    return hashlib.md5(s.strip().lower().encode()).hexdigest()


def save_json(email: str, found: list, mx: dict, whois_data: dict,
              provider: str, gravatar: dict, path: str):
    data = {
        "email":      email,
        "username":   email.split("@")[0],
        "domain":     email.split("@")[-1].lower(),
        "scanned_at": datetime.now().isoformat(),
        "provider":   provider,
        "mx":         mx,
        "whois":      whois_data,
        "gravatar":   gravatar,
        "found": [
            {
                "name":     r["name"],
                "category": r["category"],
                "username": r.get("username"),
            }
            for r in found
        ],
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def save_html(email: str, found: list, mx: dict, whois_data: dict,
              provider: str, gravatar: dict, path: str):

    avatar_hash = md5(email)

    gravatar_block = ""
    if gravatar.get("found"):
        linked = " ".join(
            f'<span class="tag">{a["domain"]}</span>'
            for a in gravatar.get("linked_accounts", [])
        )
        urls = " ".join(
            f'<a href="{u}" target="_blank">{u}</a>'
            for u in gravatar.get("urls", [])[:4]
        )
        bio = gravatar.get("bio", "")
        bio = (bio[:120] + "…") if len(bio) > 120 else bio

        gravatar_block = f"""
        <div class="card full">
          <div class="label">Gravatar Profile</div>
          <div class="value" style="display:flex;gap:16px;align-items:flex-start">
            <img src="https://www.gravatar.com/avatar/{avatar_hash}?s=72"
                 style="border-radius:50%;width:72px;height:72px;flex-shrink:0">
            <div>
              <strong style="font-size:16px">{gravatar.get("displayName","")}</strong>
              {"<br><small style='color:#8b949e'>📍 " + gravatar.get("location","") + "</small>" if gravatar.get("location") else ""}
              {"<br><small style='color:#aaa;margin-top:4px;display:block'>" + bio + "</small>" if bio else ""}
              {"<br><div style='margin-top:8px'>" + linked + "</div>" if linked else ""}
              {"<br><div style='margin-top:6px;font-size:12px'>" + urls + "</div>" if urls else ""}
              <br><a href="https://www.gravatar.com/{avatar_hash}" target="_blank"
                     style="font-size:12px;color:#58a6ff">View profile →</a>
            </div>
          </div>
        </div>"""

    rows = "".join(
        f"""<tr>
          <td>{r["name"]}</td>
          <td><span class="tag">{r["category"]}</span></td>
          <td>{"<b style='color:#58a6ff'>@" + r["username"] + "</b>" if r.get("username") else "—"}</td>
        </tr>"""
        for r in sorted(found, key=lambda x: x["category"])
    ) or '<tr><td colspan="3" style="color:#8b949e;text-align:center">No accounts found</td></tr>'

    mx_display    = ("✔ " + mx.get("primary_mx", "")) if mx.get("valid") else "✘ No MX found"
    domain_since  = whois_data.get("created",   "Unknown")
    registrar     = whois_data.get("registrar", "Unknown")
    scanned_at    = datetime.now().strftime("%Y-%m-%d %H:%M")

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>emailsint — {email}</title>
<style>
  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: 'Courier New', monospace;
    background: #0d1117;
    color: #c9d1d9;
    padding: 40px 32px;
    min-height: 100vh;
  }}
  h1 {{ color: #58a6ff; font-size: 22px; margin-bottom: 4px; }}
  h2 {{
    color: #79c0ff;
    font-size: 14px;
    text-transform: uppercase;
    letter-spacing: .08em;
    border-bottom: 1px solid #30363d;
    padding-bottom: 8px;
    margin: 32px 0 16px;
  }}
  .meta {{ color: #8b949e; font-size: 13px; margin-bottom: 8px; }}
  .grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 14px;
  }}
  .card {{
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 8px;
    padding: 16px;
  }}
  .card.full {{ grid-column: 1 / -1; }}
  .label {{
    color: #8b949e;
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: .06em;
    margin-bottom: 6px;
  }}
  .value {{ color: #e6edf3; font-size: 14px; font-weight: bold; }}
  .tag {{
    background: #21262d;
    border: 1px solid #30363d;
    border-radius: 4px;
    padding: 2px 8px;
    font-size: 11px;
    color: #8b949e;
  }}
  table {{ width: 100%; border-collapse: collapse; margin-top: 4px; }}
  th {{
    background: #161b22;
    color: #8b949e;
    text-align: left;
    padding: 10px 12px;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: .05em;
  }}
  td {{ padding: 10px 12px; border-bottom: 1px solid #21262d; font-size: 13px; }}
  tr:hover td {{ background: #161b22; }}
  a {{ color: #58a6ff; text-decoration: none; }}
  a:hover {{ text-decoration: underline; }}
  .footer {{ color: #484f58; font-size: 11px; margin-top: 48px; text-align: center; }}
</style>
</head>
<body>

<h1>📧 emailsint Report</h1>
<p class="meta">
  Email: <strong style="color:#e6edf3">{email}</strong>
  &nbsp;·&nbsp; Scanned: {scanned_at}
  &nbsp;·&nbsp; Accounts found: <strong style="color:#3fb950">{len(found)}</strong>
</p>

<h2>Email Analysis</h2>
<div class="grid">
  <div class="card">
    <div class="label">Provider</div>
    <div class="value">{provider}</div>
  </div>
  <div class="card">
    <div class="label">MX Record</div>
    <div class="value" style="color:{'#3fb950' if mx.get('valid') else '#f85149'}">{mx_display}</div>
  </div>
  <div class="card">
    <div class="label">Domain Registered</div>
    <div class="value">{domain_since}</div>
  </div>
  <div class="card">
    <div class="label">Registrar</div>
    <div class="value" style="font-size:12px">{registrar}</div>
  </div>
  {gravatar_block}
</div>

<h2>Found Accounts ({len(found)})</h2>
<table>
  <tr><th>Platform</th><th>Category</th><th>Username</th></tr>
  {rows}
</table>

<p class="footer">Generated by emailsint v3.0 — for personal use only.</p>
</body>
</html>"""

    with open(path, "w", encoding="utf-8") as f:
        f.write(html)

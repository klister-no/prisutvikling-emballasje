import anthropic
import os
import datetime
import time

def call_api_with_retry(client, max_retries=5, **kwargs):
    """Kaller API med automatisk retry ved overload (529)"""
    for attempt in range(max_retries):
        try:
            return client.messages.create(**kwargs)
        except anthropic.APIStatusError as e:
            if e.status_code == 529 and attempt < max_retries - 1:
                wait = 30 * (attempt + 1)  # 30s, 60s, 90s, 120s
                print(f"API overbelastet. Venter {wait} sekunder (forsøk {attempt+1}/{max_retries})...")
                time.sleep(wait)
            else:
                raise
    raise Exception("Maks antall forsøk nådd")

def update_report():
    client = anthropic.Anthropic(api_key=os.environ["EMBALLASJE_RAPPORT_CLOUDE_KEY"])
    
    today = datetime.date.today().strftime("%d. %B %Y")
    quarter = f"Q{(datetime.date.today().month - 1) // 3 + 1} {datetime.date.today().year}"

    # STEG 1: Søk etter markedsdata
    print(f"Steg 1: Søker markedsdata for {quarter}...")
    
    search_response = call_api_with_retry(
        client,
        model="claude-opus-4-6",
        max_tokens=4000,
        tools=[{"type": "web_search_20250305", "name": "web_search"}],
        messages=[{"role": "user", "content": f"""
Søk etter oppdatert prisinformasjon for europeiske emballasjematerialer per {today}.
Søk etter:
- PET virgin og rPET food-grade priser Europa {datetime.date.today().year}
- PP polypropylen og HDPE priser Europa {datetime.date.today().year}
- Kraftliner og testliner priser Europa {datetime.date.today().year}
- Solid board FBB WLC cartonboard priser Europa {datetime.date.today().year}
- Fluting bølgekjerne OCC returpapp priser Europa
- PPWR regulering nyheter {datetime.date.today().year}
- Papirfabrikk kapasitet nyheter Europa {datetime.date.today().year}
Oppsummer alle funn med prisintervaller per materiale i €/tonn.
"""}]
    )

    market_data = ""
    for block in search_response.content:
        if hasattr(block, 'text'):
            market_data += block.text
    print(f"Steg 1 ferdig: {len(market_data)} tegn hentet.")

    # STEG 2: Generer HTML
    print("Steg 2: Genererer HTML-rapport...")
    
    html_response = call_api_with_retry(
        client,
        model="claude-opus-4-6",
        max_tokens=8000,
        messages=[{"role": "user", "content": f"""Lag en komplett HTML-rapport for europeiske emballasjematerialpriser.

MARKEDSDATA ({quarter}, {today}):
{market_data}

ABSOLUTTE REGLER FOR OUTPUT:
1. Start med nøyaktig: <!DOCTYPE html>
2. Slutt med nøyaktig: </html>
3. INGEN tekst utenfor HTML-tagene - verken før eller etter
4. INGEN markdown, INGEN kodeblokker

HTML-STRUKTUR:
<!DOCTYPE html>
<html lang="no">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Emballasjeprisrapport Europa {quarter}</title>
<link href="https://fonts.googleapis.com/css2?family=DM+Serif+Display&family=Inter:wght@300;400;500;600&display=swap" rel="stylesheet">
<style>
/* CSS her */
:root {{
  --ink: #0f1117; --paper: #f5f1eb; --accent: #c8401a;
  --up: #1a8c4a; --down: #c8401a; --flat: #8a6e2a;
  --border: #d8d2c8; --card: #ffffff; --muted: #7a7570;
}}
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{ font-family: 'Inter', sans-serif; background: var(--paper); color: var(--ink); font-size: 14px; line-height: 1.6; }}
.report-header {{ background: var(--ink); color: var(--paper); padding: 40px 48px; }}
.report-title {{ font-family: 'DM Serif Display', serif; font-size: 38px; margin: 12px 0 8px; }}
.report-meta {{ font-size: 12px; color: rgba(245,241,235,0.5); letter-spacing: 0.1em; text-transform: uppercase; }}
.report-date {{ font-size: 12px; color: rgba(245,241,235,0.4); margin-top: 16px; padding-top: 16px; border-top: 1px solid rgba(245,241,235,0.12); }}
.nav-tabs {{ background: var(--ink); padding: 0 48px; display: flex; gap: 0; overflow-x: auto; border-top: 1px solid rgba(245,241,235,0.1); }}
.nav-tab {{ font-size: 11px; letter-spacing: 0.08em; text-transform: uppercase; color: rgba(245,241,235,0.45); padding: 14px 18px; cursor: pointer; border-bottom: 2px solid transparent; white-space: nowrap; transition: all 0.2s; }}
.nav-tab:hover {{ color: rgba(245,241,235,0.8); }}
.nav-tab.active {{ color: var(--paper); border-bottom-color: var(--accent); }}
.main-content {{ max-width: 1300px; margin: 0 auto; padding: 36px 48px; }}
.section {{ display: none; }}
.section-header {{ margin-bottom: 24px; padding-bottom: 14px; border-bottom: 1px solid var(--border); }}
.section-title {{ font-family: 'DM Serif Display', serif; font-size: 24px; }}
.card {{ background: var(--card); border: 1px solid var(--border); border-radius: 6px; overflow: hidden; margin-bottom: 24px; }}
.card-header {{ padding: 14px 18px; border-bottom: 1px solid var(--border); font-size: 11px; letter-spacing: 0.08em; text-transform: uppercase; color: var(--muted); }}
table {{ width: 100%; border-collapse: collapse; }}
thead th {{ background: #f8f5f0; font-size: 10px; letter-spacing: 0.08em; text-transform: uppercase; color: var(--muted); padding: 10px 14px; text-align: left; border-bottom: 1px solid var(--border); }}
tbody td {{ padding: 10px 14px; border-bottom: 1px solid #f0ece4; font-size: 13px; }}
tbody tr:last-child td {{ border-bottom: none; }}
tbody tr:hover {{ background: #faf7f2; }}
.up {{ color: var(--up); font-weight: 600; }}
.down {{ color: var(--down); font-weight: 600; }}
.flat {{ color: var(--flat); font-weight: 600; }}
.badge {{ display: inline-block; font-size: 10px; padding: 2px 7px; border-radius: 3px; }}
.badge-p {{ background: #dbeafe; color: #1a5fc8; }}
.badge-f {{ background: #d1fae5; color: #1a7a3a; }}
.badge-c {{ background: #fde8d0; color: #8a4a1a; }}
.grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 16px; margin-bottom: 24px; }}
.driver-card {{ background: var(--card); border: 1px solid var(--border); border-radius: 6px; padding: 18px; }}
.driver-icon {{ font-size: 20px; margin-bottom: 8px; }}
.driver-title {{ font-weight: 600; font-size: 14px; margin-bottom: 6px; }}
.driver-body {{ font-size: 13px; color: #3a3530; line-height: 1.65; }}
.summary-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 14px; margin-bottom: 24px; }}
.summary-card {{ background: var(--card); border: 1px solid var(--border); border-radius: 6px; padding: 18px; }}
.summary-label {{ font-size: 10px; letter-spacing: 0.1em; text-transform: uppercase; color: var(--muted); margin-bottom: 6px; }}
.summary-value {{ font-family: 'DM Serif Display', serif; font-size: 24px; line-height: 1; margin-bottom: 4px; }}
.summary-desc {{ font-size: 12px; color: var(--muted); }}
.timeline-item {{ display: flex; gap: 18px; padding: 12px 0; border-bottom: 1px solid #f0ece4; }}
.timeline-year {{ font-family: 'DM Serif Display', serif; font-size: 18px; color: var(--accent); min-width: 55px; }}
.timeline-rule {{ font-weight: 600; font-size: 13px; margin-bottom: 3px; }}
.timeline-desc {{ font-size: 12px; color: var(--muted); }}
.alert {{ background: #fff8f0; border: 1px solid #f0d0b0; border-radius: 6px; padding: 14px 18px; font-size: 13px; margin-bottom: 20px; }}
@media (max-width: 768px) {{
  .report-header, .main-content, .nav-tabs {{ padding-left: 20px; padding-right: 20px; }}
  .report-title {{ font-size: 26px; }}
}}
</style>
</head>
<body>

<header class="report-header">
  <div class="report-meta">🇪🇺 Europeisk marked · FMCG Emballasje · Prisovervåkning</div>
  <h1 class="report-title">Prisrapport Emballasjematerialer</h1>
  <p style="color:rgba(245,241,235,0.65);font-size:15px;max-width:560px">Prisutvikling og markedsdrivere for plast- og fibermaterialer i det europeiske FMCG-markedet.</p>
  <div class="report-date">Oppdatert: {today} · {quarter} · Kilder: ICIS, Fastmarkets, EUWID, Packaging Europe</div>
</header>

<nav class="nav-tabs">
  <div class="nav-tab" onclick="showSection('overview')">Oversikt</div>
  <div class="nav-tab" onclick="showSection('plast')">Plastmaterialer</div>
  <div class="nav-tab" onclick="showSection('fiber')">Solid Board</div>
  <div class="nav-tab" onclick="showSection('corrugated')">Bølgepapp</div>
  <div class="nav-tab" onclick="showSection('kapasitet')">Kapasitet</div>
  <div class="nav-tab" onclick="showSection('drivere')">Markedsdrivere</div>
  <div class="nav-tab" onclick="showSection('regulering')">Regulering</div>
  <div class="nav-tab" onclick="showSection('kilder')">Kilder</div>
</nav>

<main class="main-content">

<section class="section" id="overview">
<div class="section-header"><h2 class="section-title">Markedsoversikt {quarter}</h2></div>
<!-- Fyll inn oversiktstabell og sammendragskort basert på markedsdata -->
<div class="card">
<div class="card-header">Prisindikator alle materialer — {quarter}</div>
<table>
<thead><tr><th>Materiale</th><th>Segment</th><th>Prisnivå (€/t)</th><th>Trend 12 mnd</th><th>Trend 6 mnd</th><th>Utsikt H1</th></tr></thead>
<tbody>
<!-- Bruk markedsdata til å fylle inn reelle priser og trender her -->
</tbody>
</table>
</div>
</section>

<section class="section" id="plast">
<div class="section-header"><h2 class="section-title">Plastmaterialer</h2></div>
</section>

<section class="section" id="fiber">
<div class="section-header"><h2 class="section-title">Solid Board / Fiber</h2></div>
</section>

<section class="section" id="corrugated">
<div class="section-header"><h2 class="section-title">Bølgepapp</h2></div>
</section>

<section class="section" id="kapasitet">
<div class="section-header"><h2 class="section-title">Kapasitet</h2></div>
</section>

<section class="section" id="drivere">
<div class="section-header"><h2 class="section-title">Markedsdrivere</h2></div>
</section>

<section class="section" id="regulering">
<div class="section-header"><h2 class="section-title">Regulering — PPWR</h2></div>
</section>

<section class="section" id="kilder">
<div class="section-header"><h2 class="section-title">Kilder og metode</h2></div>
</section>

</main>

<footer style="background:var(--ink);color:rgba(245,241,235,0.4);padding:18px 48px;font-size:11px;display:flex;justify-content:space-between;flex-wrap:wrap;gap:8px;">
  <span>EMBALLASJEPRISRAPPORT — EUROPA · FMCG</span>
  <span>Oppdatert: {today} · {quarter}</span>
  <span>Indikative priser — ikke erstatning for profesjonelle prisindekser</span>
</footer>

<script>
function showSection(id) {{
  document.querySelectorAll('.section').forEach(function(s) {{ s.style.display = 'none'; }});
  document.querySelectorAll('.nav-tab').forEach(function(t) {{ t.classList.remove('active'); }});
  document.getElementById(id).style.display = 'block';
  event.currentTarget.classList.add('active');
}}
window.onload = function() {{
  document.querySelectorAll('.section').forEach(function(s) {{ s.style.display = 'none'; }});
  var first = document.querySelector('.section');
  if (first) first.style.display = 'block';
  var firstTab = document.querySelector('.nav-tab');
  if (firstTab) firstTab.classList.add('active');
}};
</script>
</body>
</html>

VIKTIG: Erstatt alle kommentarer (<!-- ... -->) med faktisk innhold basert på markedsdataene.
Fyll inn reelle prisintervaller, trender og analysetekster fra søkeresultatene.
Behold all HTML-struktur, CSS og JavaScript nøyaktig som vist.
"""}]
    )

    html_content = ""
    for block in html_response.content:
        if hasattr(block, 'text'):
            html_content += block.text

    html_content = html_content.strip()

    # Rens markdown hvis det finnes
    if "```html" in html_content:
        start = html_content.find("```html") + 7
        end = html_content.rfind("```")
        if end > start:
            html_content = html_content[start:end].strip()
    elif html_content.startswith("```"):
        start = html_content.find("\n") + 1
        end = html_content.rfind("```")
        if end > start:
            html_content = html_content[start:end].strip()

    # Finn HTML-start
    if not html_content.startswith("<!DOCTYPE") and not html_content.startswith("<html"):
        for marker in ["<!DOCTYPE", "<html"]:
            pos = html_content.find(marker)
            if pos != -1:
                html_content = html_content[pos:]
                break

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"✅ Rapport oppdatert: {today}")
    print(f"   Filstørrelse: {len(html_content)} tegn")
    
    if "showSection" in html_content:
        print("   ✅ JavaScript-faner bekreftet")
    else:
        print("   ⚠️  ADVARSEL: JavaScript-faner mangler!")

if __name__ == "__main__":
    update_report()

import anthropic
import os
import datetime
import time

def call_api_with_retry(client, max_retries=7, **kwargs):
    """Kaller API med eksponentiell backoff ved overload (529)"""
    for attempt in range(max_retries):
        try:
            return client.messages.create(**kwargs)
        except anthropic.APIStatusError as e:
            if e.status_code == 529 and attempt < max_retries - 1:
                wait = min(30 * (2 ** attempt), 300)  # 30s, 60s, 120s, 240s, 300s, 300s, 300s
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
        model="claude-sonnet-4-6",
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
Oppsummer alle funn med prisintervaller per materiale i euro per tonn.
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
        model="claude-sonnet-4-6",
        max_tokens=8000,
        messages=[{"role": "user", "content": f"""Du er en frontend-utvikler. Lag en komplett HTML-rapport.

MARKEDSDATA ({quarter}, {today}):
{market_data}

ABSOLUTTE REGLER FOR OUTPUT:
1. Start med nøyaktig: <!DOCTYPE html>
2. Slutt med nøyaktig: </html>
3. INGEN tekst utenfor HTML-tagene - verken før eller etter
4. INGEN markdown, INGEN kodeblokker

KRITISK JAVASCRIPT - inkluder dette eksakt i en script-tag på slutten av body:
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

8 FANER - kopier eksakt med onclick:
<div class="nav-tab" onclick="showSection('overview')">Oversikt</div>
<div class="nav-tab" onclick="showSection('plast')">Plastmaterialer</div>
<div class="nav-tab" onclick="showSection('fiber')">Solid Board</div>
<div class="nav-tab" onclick="showSection('corrugated')">Bolgeapp</div>
<div class="nav-tab" onclick="showSection('kapasitet')">Kapasitet</div>
<div class="nav-tab" onclick="showSection('drivere')">Markedsdrivere</div>
<div class="nav-tab" onclick="showSection('regulering')">Regulering</div>
<div class="nav-tab" onclick="showSection('kilder')">Kilder</div>

8 SEKSJONER - kopier eksakt med id:
<section class="section" id="overview">...</section>
<section class="section" id="plast">...</section>
<section class="section" id="fiber">...</section>
<section class="section" id="corrugated">...</section>
<section class="section" id="kapasitet">...</section>
<section class="section" id="drivere">...</section>
<section class="section" id="regulering">...</section>
<section class="section" id="kilder">...</section>

DESIGN:
- Bakgrunn: #f5f1eb, Header: #0f1117, Aksent: #c8401a
- Google Fonts: DM Serif Display + Inter
- Trend opp: grønn #1a8c4a, ned: rod #c8401a, flat: amber #8a6e2a
- Dato {today} og kvartal {quarter} prominent i header

INNHOLD - bruk markedsdataene til alle prisintervaller, trender og analyser:
- Oversikt: Komplett prisindikator-tabell alle materialer med trender
- Plastmaterialer: PET, rPET, PP, HDPE, LDPE med prishistorikk og driveranalyse
- Solid Board: FBB, WLC med prishistorikk og markedsanalyse
- Bolgeapp: Kraftliner, testliner, fluting, OCC med regionale nyanser
- Kapasitet: Driftsrater, ny kapasitet, M&A-aktivitet
- Markedsdrivere: Drivermatrise per materiale
- Regulering: PPWR-tidslinje og recycled content-krav
- Kilder: Liste over datakilder med beskrivelser
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

    # Finn HTML-start hvis det er tekst foran
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

import anthropic
import os
import datetime

def update_report():
    client = anthropic.Anthropic(api_key=os.environ["EMBALLASJE_RAPPORT_CLOUDE_KEY"])
    
    today = datetime.date.today().strftime("%d. %B %Y")
    quarter = f"Q{(datetime.date.today().month - 1) // 3 + 1} {datetime.date.today().year}"

    # Steg 1: Søk etter markedsdata
    search_prompt = f"""
Søk etter oppdatert prisinformasjon for europeiske emballasjematerialer per {today}.

Søk etter disse materialene:
- PET virgin og rPET food-grade priser Europa
- PP polypropylen og HDPE priser Europa  
- Kraftliner og testliner priser Europa {datetime.date.today().year}
- Solid board FBB WLC cartonboard priser Europa
- Fluting bølgekjerne priser Europa
- OCC returpapp priser Europa
- PPWR regulering oppdateringer
- Papirfabrikk kapasitet nyheter Europa

Oppsummer funnene som strukturert tekst med prisintervaller per materiale.
"""

    print(f"Steg 1: Søker etter markedsdata for {quarter}...")
    
    search_response = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=4000,
        tools=[{"type": "web_search_20250305", "name": "web_search"}],
        messages=[{"role": "user", "content": search_prompt}]
    )

    market_data = ""
    for block in search_response.content:
        if hasattr(block, 'text'):
            market_data += block.text

    print(f"Steg 1 ferdig. Hentet {len(market_data)} tegn med markedsdata.")

    # Steg 2: Generer HTML
    html_prompt = f"""Du er en frontend-utvikler. Lag en KOMPLETT HTML-rapport.

MARKEDSDATA FOR {quarter} ({today}):
{market_data}

ABSOLUTT VIKTIGST - OUTPUT-REGLER:
- Start filen med nøyaktig: <!DOCTYPE html>
- Slutt filen med nøyaktig: </html>
- INGEN tekst eller forklaring utenfor HTML-koden
- INGEN markdown eller kodeblokker

JAVASCRIPT (kopier dette eksakt inn i <script>-tag):
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

8 FANER med onclick (kopier eksakt):
<div class="nav-tab" onclick="showSection('overview')">Oversikt</div>
<div class="nav-tab" onclick="showSection('plast')">Plastmaterialer</div>
<div class="nav-tab" onclick="showSection('fiber')">Solid Board</div>
<div class="nav-tab" onclick="showSection('corrugated')">Bølgepapp</div>
<div class="nav-tab" onclick="showSection('kapasitet')">Kapasitet</div>
<div class="nav-tab" onclick="showSection('drivere')">Markedsdrivere</div>
<div class="nav-tab" onclick="showSection('regulering')">Regulering</div>
<div class="nav-tab" onclick="showSection('kilder')">Kilder</div>

8 SEKSJONER med id (kopier eksakt):
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
- Trend-piler: grønn #1a8c4a for opp, rød #c8401a for ned, amber #8a6e2a for flat
- Dato {today} og kvartal {quarter} i header

INNHOLD: Bruk markedsdataene over til alle prisintervaller og analyser.
"""

    print("Steg 2: Genererer HTML...")

    html_response = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=8000,
        messages=[{"role": "user", "content": html_prompt}]
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

import anthropic
import os
import datetime
import time

def call_api_with_retry(client, max_retries=7, **kwargs):
    """Kaller API med eksponentiell backoff ved overload eller rate limit"""
    for attempt in range(max_retries):
        try:
            return client.messages.create(**kwargs)
        except anthropic.APIStatusError as e:
            if e.status_code in (529, 429) and attempt < max_retries - 1:
                wait = min(30 * (2 ** attempt), 300)
                print(f"API-feil {e.status_code}. Venter {wait} sekunder (forsøk {attempt+1}/{max_retries})...")
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
        max_tokens=2000,
        tools=[{"type": "web_search_20250305", "name": "web_search"}],
        messages=[{"role": "user", "content": f"""
Søk etter europeiske emballasjematerialpriser per {today}.
Gi et KORT sammendrag (maks 800 ord) med:
- Prisintervall i euro/tonn for: PET virgin, rPET, PP, HDPE, LDPE, FBB, WLC, kraftliner, testliner, fluting, OCC
- Trend siste kvartal per materiale (opp/ned/flat)
- 3-5 viktige markedsnyheter
- 6-måneders utsikt per materiale
Vær kortfattet og presis. Kun fakta og tall.
"""}]
    )

    market_data = ""
    for block in search_response.content:
        if hasattr(block, 'text'):
            market_data += block.text

    # Kutt til maks 3000 tegn for å holde oss innenfor token-grensen
    if len(market_data) > 3000:
        market_data = market_data[:3000] + "\n[avkortet]"

    print(f"Steg 1 ferdig: {len(market_data)} tegn hentet.")
    
    # Vent 60 sekunder mellom kallene for å nullstille token-tellingen
    print("Venter 60 sekunder før steg 2...")
    time.sleep(60)

    # STEG 2: Generer HTML
    print("Steg 2: Genererer HTML-rapport...")
    
    html_response = call_api_with_retry(
        client,
        model="claude-sonnet-4-6",
        max_tokens=7000,
        messages=[{"role": "user", "content": f"""Lag en komplett HTML-rapport for europeiske emballasjematerialpriser.

MARKEDSDATA ({quarter}, {today}):
{market_data}

ABSOLUTTE REGLER:
- Start med: <!DOCTYPE html>
- Slutt med: </html>
- INGEN tekst utenfor HTML
- INGEN markdown eller kodeblokker

JAVASCRIPT (inkluder eksakt i script-tag):
function showSection(id) {{
  document.querySelectorAll('.section').forEach(function(s) {{ s.style.display='none'; }});
  document.querySelectorAll('.nav-tab').forEach(function(t) {{ t.classList.remove('active'); }});
  document.getElementById(id).style.display='block';
  event.currentTarget.classList.add('active');
}}
window.onload = function() {{
  document.querySelectorAll('.section').forEach(function(s) {{ s.style.display='none'; }});
  var f=document.querySelector('.section'); if(f) f.style.display='block';
  var t=document.querySelector('.nav-tab'); if(t) t.classList.add('active');
}};

8 FANER (kopier eksakt):
<div class="nav-tab" onclick="showSection('overview')">Oversikt</div>
<div class="nav-tab" onclick="showSection('plast')">Plastmaterialer</div>
<div class="nav-tab" onclick="showSection('fiber')">Solid Board</div>
<div class="nav-tab" onclick="showSection('corrugated')">Bolgeapp</div>
<div class="nav-tab" onclick="showSection('kapasitet')">Kapasitet</div>
<div class="nav-tab" onclick="showSection('drivere')">Markedsdrivere</div>
<div class="nav-tab" onclick="showSection('regulering')">Regulering</div>
<div class="nav-tab" onclick="showSection('kilder')">Kilder</div>

8 SEKSJONER (kopier eksakt):
<section class="section" id="overview">innhold her</section>
<section class="section" id="plast">innhold her</section>
<section class="section" id="fiber">innhold her</section>
<section class="section" id="corrugated">innhold her</section>
<section class="section" id="kapasitet">innhold her</section>
<section class="section" id="drivere">innhold her</section>
<section class="section" id="regulering">innhold her</section>
<section class="section" id="kilder">innhold her</section>

DESIGN:
- Bakgrunn #f5f1eb, Header #0f1117, Aksent #c8401a
- Google Fonts: DM Serif Display + Inter
- Trend opp: #1a8c4a, ned: #c8401a, flat: #8a6e2a
- Oppdatert {today}, kvartal {quarter} i header

INNHOLD: Bruk markedsdataene til prisintervaller, trender og analyser i alle seksjoner.
Oversikt-seksjonen skal ha en komplett tabell med alle materialer.
"""}]
    )

    html_content = ""
    for block in html_response.content:
        if hasattr(block, 'text'):
            html_content += block.text

    html_content = html_content.strip()

    # Rens markdown
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

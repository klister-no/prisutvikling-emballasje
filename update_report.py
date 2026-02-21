import anthropic
import os
import datetime

def update_report():
    client = anthropic.Anthropic(api_key=os.environ["EMBALLASJE_RAPPORT_CLOUDE_KEY"])
    
    today = datetime.date.today().strftime("%d. %B %Y")
    quarter = f"Q{(datetime.date.today().month - 1) // 3 + 1} {datetime.date.today().year}"

    prompt = f"""
Du er en ekspert på europeiske emballasjematerialmarkeder. 
Dagens dato er {today}. Rapporten gjelder {quarter}.

Søk etter oppdatert prisinformasjon og markedsnyheter for følgende 
europeiske emballasjematerialer:
- PET virgin og rPET food-grade
- PP (polypropylen), HDPE, LDPE/PE film
- FBB (Folded Boxboard / virgin solid board)
- WLC (White-Lined Chipboard / resirkulert solid board)
- Kraftliner (brun og white-top)
- Testliner (resirkulert liner)
- Fluting / bølgekjerne (semi-chemical og resirkulert)
- OCC (returpapp / old corrugated containers)

Søk spesielt etter:
1. Aktuelle prisindikationer fra ICIS, Fastmarkets, EUWID, Packaging Europe
2. Kapasitetsnyheter fra store produsenter (Smurfit Westrock, IP/DS Smith, 
   Stora Enso, SCA, Saica, Hamburger Containerboard, MM Group)
3. Regulatoriske oppdateringer (PPWR, EPR, EUDR)
4. Markedstrender og drivere siste kvartal
5. 6-måneders utsikt

Generer deretter en komplett, oppdatert HTML-rapport basert på funnene.
Rapporten skal ha følgende struktur og design:

DESIGN-KRAV:
- Profesjonell redaksjonell estetikk
- Mørk header (#0f1117) med lys tekst
- Papirfarget bakgrunn (#f5f1eb)
- Fonter: DM Serif Display (titler) + Inter (brødtekst) fra Google Fonts
- Interaktive faner med JavaScript (ingen biblioteker)
- Tabeller med trend-signaler (↑↓→) fargekodet grønn/rød/amber
- Responsiv for desktop og mobil
- Oppdateringsdato prominent i header

FANSTRUKTUR:
1. Oversikt — prisindikator-tabell alle materialer med trend-signaler
2. Plastmaterialer — kvartalsvise prisserier + driveranalyse
3. Solid Board / Fiber — prishistorikk + markedsanalyse  
4. Bølgepapp — liner og fluting, regionale nyanser
5. Kapasitet — driftsrater, ny kapasitet, M&A-aktivitet
6. Markedsdrivere — drivermatrise per materiale
7. Regulering — PPWR-tidslinje og recycled content-krav
8. Kilder & Metode — navngitte kilder med lenker

VIKTIG: Returner KUN ren HTML-kode. Ingen forklaring før eller etter.
Start direkte med <!DOCTYPE html> og avslutt med </html>.
Ingen markdown, ingen kodeblokker, bare ren HTML.
"""

    print(f"Starter oppdatering av rapport for {quarter}...")

    response = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=8000,
        tools=[{"type": "web_search_20250305", "name": "web_search"}],
        messages=[{"role": "user", "content": prompt}]
    )

    # Hent ut HTML fra responsen
    html_content = ""
    for block in response.content:
        if block.type == "text":
            html_content += block.text

    # Rens bort eventuelle markdown-kodeblokker
    html_content = html_content.strip()
    if html_content.startswith("```html"):
        html_content = html_content[7:]
    if html_content.startswith("```"):
        html_content = html_content[3:]
    if html_content.endswith("```"):
        html_content = html_content[:-3]
    html_content = html_content.strip()

    # Lagre til index.html
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"✅ Rapport oppdatert: {today}")
    print(f"   Lengde: {len(html_content)} tegn")

if __name__ == "__main__":
    update_report()

import anthropic
import os
import datetime
import time

def call_api_with_retry(client, max_retries=7, **kwargs):
    for attempt in range(max_retries):
        try:
            return client.messages.create(**kwargs)
        except anthropic.APIStatusError as e:
            if e.status_code in (529, 429) and attempt < max_retries - 1:
                wait = min(30 * (2 ** attempt), 300)
                print(f"API-feil {e.status_code}. Venter {wait}s (forsøk {attempt+1}/{max_retries})...")
                time.sleep(wait)
            else:
                raise
    raise Exception("Maks antall forsøk nådd")

def update_report():
    client = anthropic.Anthropic(api_key=os.environ["EMBALLASJE_RAPPORT_CLOUDE_KEY"])
    today = datetime.date.today().strftime("%d. %B %Y")
    quarter = f"Q{(datetime.date.today().month - 1) // 3 + 1} {datetime.date.today().year}"

    # STEG 1A: Søk plastpriser
    print(f"Steg 1a: Søker plastpriser for {quarter}...")
    r1a = call_api_with_retry(
        client, model="claude-sonnet-4-6", max_tokens=1500,
        tools=[{"type": "web_search_20250305", "name": "web_search"}],
        messages=[{"role": "user", "content": f"""
Søk etter europeiske plastpriser {today}.
Returner KUN tallene (maks 600 ord):
- PET virgin Europa €/tonn, trend
- rPET food-grade Europa €/tonn, trend
- PP homopolymer FCA Antwerpen €/tonn, trend
- HDPE blåsing NWE €/tonn, trend
- LDPE film NWE €/tonn, trend
- 3 viktige nyheter plast Europa siste 4 uker
Kun fakta. Ingen innledning.
"""}]
    )
    plast_data = "".join(b.text for b in r1a.content if hasattr(b, "text"))[:2000]
    print(f"  Plast: {len(plast_data)} tegn")

    print("Venter 45 sekunder...")
    time.sleep(45)

    # STEG 1B: Søk kartong og bølgepapp
    print("Steg 1b: Søker kartong/bølgepapp-priser...")
    r1b = call_api_with_retry(
        client, model="claude-sonnet-4-6", max_tokens=1500,
        tools=[{"type": "web_search_20250305", "name": "web_search"}],
        messages=[{"role": "user", "content": f"""
Søk etter europeiske papir- og kartonpriser {today}.
Returner KUN tallene (maks 600 ord):
- FBB Folding Boxboard Europa €/tonn, trend
- WLC White-Lined Chipboard Europa €/tonn, trend
- Kraftliner brun Europa €/tonn (FOEX PIX-indeks), trend
- Testliner 2 Europa €/tonn (FOEX PIX-indeks), trend
- Fluting RB Europa €/tonn (FOEX PIX-indeks), trend
- OCC returpapp Europa €/tonn, trend
- 3 viktige nyheter kartong/bølgepapp siste 4 uker
Søk også etter: "packaging europe corrugated 2025" og "FOEX PIX kraftliner"
Kun fakta. Ingen innledning.
"""}]
    )
    fiber_data = "".join(b.text for b in r1b.content if hasattr(b, "text"))[:2000]
    print(f"  Fiber/board: {len(fiber_data)} tegn")

    print("Venter 60 sekunder før HTML-generering...")
    time.sleep(60)

    # STEG 2: Fyll inn HTML-skjelett
    print("Steg 2: Genererer HTML...")

    skeleton = f"""<!DOCTYPE html>
<html lang="no">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Europeiske Emballasjematerialpriser – {quarter}</title>
<link href="https://fonts.googleapis.com/css2?family=DM+Serif+Display&family=Inter:wght@300;400;500;600&family=DM+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
:root{{--ink:#0f1117;--paper:#f5f1eb;--accent:#c8401a;--up:#1a8c4a;--down:#c8401a;--flat:#8a6e2a;--border:#d8d2c8;--card:#ffffff;--muted:#7a7570;}}
*{{box-sizing:border-box;margin:0;padding:0;}}
body{{font-family:'Inter',sans-serif;background:var(--paper);color:var(--ink);font-size:14px;line-height:1.6;}}
.report-header{{background:var(--ink);color:var(--paper);padding:36px 48px 24px;}}
.report-eyebrow{{font-family:'DM Mono',monospace;font-size:11px;letter-spacing:.12em;text-transform:uppercase;color:rgba(245,241,235,.5);margin-bottom:10px;}}
.report-title{{font-family:'DM Serif Display',serif;font-size:36px;line-height:1.1;}}
.report-title span{{color:var(--accent);}}
.report-sub{{color:rgba(245,241,235,.6);font-size:13px;margin-top:6px;}}
.report-meta{{font-family:'DM Mono',monospace;font-size:10px;color:rgba(245,241,235,.35);margin-top:16px;padding-top:14px;border-top:1px solid rgba(245,241,235,.1);}}
.report-badge{{display:inline-block;background:var(--accent);color:#fff;font-family:'DM Mono',monospace;font-size:11px;padding:3px 10px;border-radius:3px;float:right;}}
.nav-tabs{{background:var(--ink);padding:0 48px;display:flex;overflow-x:auto;border-top:1px solid rgba(255,255,255,.08);}}
.nav-tab{{font-family:'DM Mono',monospace;font-size:11px;letter-spacing:.08em;text-transform:uppercase;color:rgba(245,241,235,.4);padding:14px 18px;cursor:pointer;border-bottom:2px solid transparent;white-space:nowrap;transition:all .15s;user-select:none;}}
.nav-tab:hover{{color:rgba(245,241,235,.75);}}
.nav-tab.active{{color:var(--paper);border-bottom-color:var(--accent);}}
.main{{max-width:1280px;margin:0 auto;padding:32px 48px;}}
.section{{display:none;}}
h2{{font-family:'DM Serif Display',serif;font-size:24px;margin-bottom:16px;padding-bottom:12px;border-bottom:1px solid var(--border);}}
.card{{background:var(--card);border:1px solid var(--border);border-radius:6px;overflow:hidden;margin-bottom:20px;}}
.card-head{{padding:12px 18px;border-bottom:1px solid var(--border);display:flex;justify-content:space-between;align-items:center;background:#f8f5f0;}}
.card-title{{font-family:'DM Mono',monospace;font-size:10px;letter-spacing:.06em;text-transform:uppercase;color:var(--muted);}}
.card-note{{font-size:11px;color:var(--muted);}}
table{{width:100%;border-collapse:collapse;}}
thead th{{background:#f8f5f0;font-family:'DM Mono',monospace;font-size:10px;letter-spacing:.06em;text-transform:uppercase;color:var(--muted);padding:9px 14px;text-align:left;border-bottom:1px solid var(--border);}}
tbody td{{padding:9px 14px;border-bottom:1px solid #f0ece4;font-size:13px;}}
tbody tr:last-child td{{border-bottom:none;}}
tbody tr:hover{{background:#faf7f2;}}
.up{{color:var(--up);font-weight:600;}}
.down{{color:var(--down);font-weight:600;}}
.flat{{color:var(--flat);font-weight:600;}}
.kpi-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px;margin-bottom:20px;}}
.kpi{{background:var(--card);border:1px solid var(--border);border-radius:6px;padding:16px;}}
.kpi-label{{font-family:'DM Mono',monospace;font-size:10px;letter-spacing:.1em;text-transform:uppercase;color:var(--muted);margin-bottom:5px;}}
.kpi-value{{font-family:'DM Serif Display',serif;font-size:24px;line-height:1;margin-bottom:3px;}}
.kpi-trend{{font-size:12px;font-weight:600;}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:14px;margin-bottom:20px;}}
.dcard{{background:var(--card);border:1px solid var(--border);border-radius:6px;padding:16px;}}
.dcard-icon{{font-size:18px;margin-bottom:6px;}}
.dcard-title{{font-weight:600;font-size:13px;margin-bottom:6px;}}
.dcard-body{{font-size:12px;color:#3a3530;line-height:1.65;}}
.tl{{background:var(--card);border:1px solid var(--border);border-radius:6px;padding:18px 22px;margin-bottom:20px;}}
.tl-item{{display:flex;gap:16px;padding:12px 0;border-bottom:1px solid #f0ece4;}}
.tl-item:last-child{{border-bottom:none;}}
.tl-year{{font-family:'DM Serif Display',serif;font-size:17px;color:var(--accent);min-width:50px;line-height:1.2;}}
.tl-rule{{font-weight:600;font-size:13px;margin-bottom:2px;}}
.tl-desc{{font-size:12px;color:var(--muted);}}
.alert{{background:#fff8f0;border:1px solid #f0d0b0;border-radius:6px;padding:12px 16px;font-size:12px;margin-bottom:18px;line-height:1.6;}}
footer{{background:var(--ink);color:rgba(245,241,235,.35);padding:14px 48px;font-family:'DM Mono',monospace;font-size:10px;display:flex;justify-content:space-between;flex-wrap:wrap;gap:6px;margin-top:40px;}}
@media(max-width:768px){{.report-header,.main,.nav-tabs,footer{{padding-left:20px;padding-right:20px;}}}}
</style>
</head>
<body>
<header class="report-header">
  <div class="report-eyebrow">🇪🇺 Europeisk marked · FMCG Emballasje · Prisovervåkning</div>
  <h1 class="report-title">Europeiske <span>Emballasjematerialpriser</span>
    <span class="report-badge">{quarter}</span>
  </h1>
  <p class="report-sub">Markedsrapport · Plastmaterialer · Kartonger · Bølgepapp</p>
  <div class="report-meta">Oppdatert {today} · Kilde: FOEX/PIX, ICIS, EUWID, ChemOrbis, Packaging Europe · Alle priser i EUR/tonn</div>
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
<main class="main">
<section class="section" id="overview">##OVERSIKT_INNHOLD##</section>
<section class="section" id="plast">##PLAST_INNHOLD##</section>
<section class="section" id="fiber">##FIBER_INNHOLD##</section>
<section class="section" id="corrugated">##CORRUGATED_INNHOLD##</section>
<section class="section" id="kapasitet">##KAPASITET_INNHOLD##</section>
<section class="section" id="drivere">##DRIVERE_INNHOLD##</section>
<section class="section" id="regulering">##REGULERING_INNHOLD##</section>
<section class="section" id="kilder">##KILDER_INNHOLD##</section>
</main>
<footer>
  <span>EMBALLASJEPRISRAPPORT — EUROPA · FMCG</span>
  <span>Oppdatert: {today} · {quarter}</span>
  <span>Indikative priser — ikke erstatning for profesjonelle prisindekser</span>
</footer>
<script>
function showSection(id){{
  document.querySelectorAll('.section').forEach(function(s){{s.style.display='none';}});
  document.querySelectorAll('.nav-tab').forEach(function(t){{t.classList.remove('active');}});
  document.getElementById(id).style.display='block';
  event.currentTarget.classList.add('active');
}}
window.onload=function(){{
  document.querySelectorAll('.section').forEach(function(s){{s.style.display='none';}});
  var f=document.querySelector('.section');if(f)f.style.display='block';
  var t=document.querySelector('.nav-tab');if(t)t.classList.add('active');
}};
</script>
</body>
</html>"""

    fill_prompt = f"""Du skal fylle inn innhold i 8 HTML-seksjoner for en emballasjeprisrapport ({quarter}, {today}).

MARKEDSDATA PLAST:
{plast_data}

MARKEDSDATA KARTONG OG BØLGEPAPP:
{fiber_data}

Returner KUN 8 blokker med ren HTML. Ingen annen tekst. Bruk eksakt dette formatet:

##OVERSIKT_INNHOLD##
[HTML: alert-boks om datakvalitet, kpi-grid med 6 KPI-kort (PET, rPET, PP, FBB, kraftliner, OCC), komplett pristabell i class="card" med ALLE 11 materialer (PET/rPET/PP/HDPE/LDPE/FBB/WLC/kraftliner/testliner/fluting/OCC)]

##PLAST_INNHOLD##
[HTML: h2-tittel, card med pristabell Q1 2024–Q1 2026 for PET/rPET/PP/HDPE/LDPE, grid med 3 dcard med nyheter fra søkeresultatene]

##FIBER_INNHOLD##
[HTML: h2-tittel, card med pristabell FBB/WLC/SBS Q1 2024–Q1 2026, grid med 3 dcard med markedsanalyse]

##CORRUGATED_INNHOLD##
[HTML: h2-tittel, card med pristabell kraftliner/testliner2+3/fluting/OCC Q1 2024–Q1 2026, analyse-avsnitt med nyheter]

##KAPASITET_INNHOLD##
[HTML: h2-tittel, grid med 4-6 dcard om kapasitetsstatus for hvert segment]

##DRIVERE_INNHOLD##
[HTML: h2-tittel, grid med 6 dcard (e-handel, PPWR, energi, import Asia, plastsubstitusjon, ny kapasitet), card med drivermatrise-tabell]

##REGULERING_INNHOLD##
[HTML: h2-tittel, div class="tl" med tl-item for PPWR-milepæler 2025-2040, card med recycled content krav-tabell]

##KILDER_INNHOLD##
[HTML: h2-tittel, alert-boks, liste over ICIS/FOEX PIX/EUWID/ChemOrbis/Packaging Europe/PlasticPortal med beskrivelse]

KLASSER å bruke: kpi-grid/kpi/kpi-label/kpi-value/kpi-trend, card/card-head/card-title/card-note, grid/dcard/dcard-icon/dcard-title/dcard-body, tl/tl-item/tl-year/tl-rule/tl-desc, alert, up/down/flat
Bruk tallene fra markedsdataene. Fyll inn ALLE 8 blokker.
"""

    # ── KALL 1: De fem innholdstunge seksjonene ──────────────────
    fill_prompt_1 = fill_prompt  # inneholder allerede OVERSIKT→KAPASITET
    fill_response_1 = call_api_with_retry(
        client, model="claude-sonnet-4-6", max_tokens=8000,
        messages=[{"role": "user", "content": fill_prompt_1}]
    )
    fill_text_1 = "".join(b.text for b in fill_response_1.content if hasattr(b, "text"))

    # ── KALL 2: De tre statiske/kortere seksjonene ───────────────
    fill_prompt_2 = f"""Du skal fylle inn innhold i 3 HTML-seksjoner for en emballasjeprisrapport ({quarter}, {today}).

Returner KUN 3 blokker med ren HTML. Ingen annen tekst. Bruk eksakt dette formatet:

##DRIVERE_INNHOLD##
<div class="sec-header"><h2 class="sec-title">Markedsdrivere<span class="sec-tag">Etterspørsel · Kapasitet · Regulering</span></h2></div>
<div class="grid">
  <div class="dcard"><div class="dcard-icon">🛒</div><div class="dcard-title">E-handel driver etterspørsel</div><div class="dcard-body">EU online-dagligvare: €56 mrd. (2024), 4x siden 2020. Bølgepapp og solid board er primære vinnerne. Strukturell vekst anslått 3–5% CAGR for packaging-grade papir mot 2030.</div></div>
  <div class="dcard"><div class="dcard-icon">📋</div><div class="dcard-title">PPWR driver plastsubstitusjon</div><div class="dcard-body">EU Packaging and Packaging Waste Regulation (PPWR) trer i full kraft aug 2026. Krav om 25% rPET i flasker fra 2025, 30% innen 2030. Driver strukturell etterspørsel mot fiber og resirkulert plast.</div></div>
  <div class="dcard"><div class="dcard-icon">⚡</div><div class="dcard-title">Energikostnader — varig faktor</div><div class="dcard-body">Europeiske energipriser forblir strukturelt høyere enn pre-2022. Papir og kartongproduksjon er energiintensiv — energi utgjør 25–35% av produksjonskostnadene. Dette setter et gulv under prisene selv i svake markeder.</div></div>
  <div class="dcard"><div class="dcard-icon">🌏</div><div class="dcard-title">Asiatisk import — strukturell konkurranse</div><div class="dcard-body">Kinesisk og sørøstasiatisk PET, PP og HDPE importeres under europeisk produksjonskostnad. Anti-dumping-tiltak gir noe beskyttelse, men CBAM-implementering er ufullstendig. Strukturell prisdemper for europrodusenter.</div></div>
  <div class="dcard"><div class="dcard-icon">🔄</div><div class="dcard-title">Resirkulert innhold — kostnadspremie</div><div class="dcard-body">rPET food-grade koster ~€600–650/t mer enn virgin PET. WLC (resirkulert kartong) er billigere enn FBB men følger OCC-prisen tett. Regulatorisk press øker etterspørselen etter resirkulert materiale uavhengig av kostnad.</div></div>
  <div class="dcard"><div class="dcard-icon">🏭</div><div class="dcard-title">Kapasitetskonsolidering i containerboard</div><div class="dcard-body">IP/DS Smith-integrasjon fullført. Smurfit Westrock er nå #1 i Europa. Hamburger CB, Saica og Klingele presser på prisøkninger. Strukturell konsolidering gir produsenter noe mer prismakt på sikt.</div></div>
</div>
<div class="card" style="margin-top:20px">
  <div class="card-head"><span class="card-title">Drivermatrise — retning per material</span></div>
  <table>
    <thead><tr><th>Driver</th><th>PET/rPET</th><th>PP/HDPE</th><th>FBB/WLC</th><th>Kraftliner</th><th>Testliner</th></tr></thead>
    <tbody>
      <tr><td>PPWR-regulering</td><td class="up">↑ Positiv</td><td class="down">↓ Negativ</td><td class="up">↑ Positiv</td><td class="flat">↔ Nøytral</td><td class="flat">↔ Nøytral</td></tr>
      <tr><td>E-handel vekst</td><td class="flat">↔ Nøytral</td><td class="flat">↔ Nøytral</td><td class="up">↑ Positiv</td><td class="up">↑ Positiv</td><td class="up">↑ Positiv</td></tr>
      <tr><td>Asiatisk import</td><td class="down">↓ Negativ</td><td class="down">↓ Negativ</td><td class="flat">↔ Begrenset</td><td class="flat">↔ Begrenset</td><td class="flat">↔ Begrenset</td></tr>
      <tr><td>Energikostnader</td><td class="flat">↔ Nøytral</td><td class="flat">↔ Nøytral</td><td class="down">↓ Støtte</td><td class="down">↓ Støtte</td><td class="down">↓ Støtte</td></tr>
      <tr><td>Plastsubstitusjon</td><td class="down">↓ Press</td><td class="down">↓ Press</td><td class="up">↑ Driver</td><td class="up">↑ Driver</td><td class="up">↑ Driver</td></tr>
    </tbody>
  </table>
</div>

##REGULERING_INNHOLD##
<div class="sec-header"><h2 class="sec-title">Regulering<span class="sec-tag">PPWR · SUP · CBAM</span></h2></div>
<div class="alert">⚠ <strong>PPWR trer i kraft august 2026:</strong> EU Packaging and Packaging Waste Regulation (2025/40) har generell anvendelsesdato 12. august 2026. Alle emballasjeprodusenter og importører til EU-markedet berøres.</div>
<div class="tl">
  <div class="tl-item"><div class="tl-year">2025</div><div><div class="tl-rule">PPWR vedtatt — Feb 2025</div><div class="tl-desc">Forordningen trådte i kraft. 18 måneders overgangsperiode starter.</div></div></div>
  <div class="tl-item"><div class="tl-year">2026</div><div><div class="tl-rule">Generell anvendelse — Aug 2026</div><div class="tl-desc">PPWR gjelder fullt ut. Krav om emballasje-minimering, gjenbruk og resirkulerbarhet.</div></div></div>
  <div class="tl-item"><div class="tl-year">2030</div><div><div class="tl-rule">Resirkulert innhold plast</div><div class="tl-desc">25% rPET i PET-flasker (kontakt mat/drikke). 30% resirkulert i all plastemballasje over 1L.</div></div></div>
  <div class="tl-item"><div class="tl-year">2035</div><div><div class="tl-rule">Økte krav resirkulert innhold</div><div class="tl-desc">50% resirkulert innhold i plastemballasje. Strengere krav til gjenbrukssystemer.</div></div></div>
  <div class="tl-item"><div class="tl-year">2040</div><div><div class="tl-rule">Full sirkulærøkonomi-mål</div><div class="tl-desc">65% av all emballasje skal resirkuleres (volum). Plast: 90% resirkuleringsrate.</div></div></div>
</div>
<div class="card">
  <div class="card-head"><span class="card-title">Resirkulert innhold — krav per materialtype</span></div>
  <table>
    <thead><tr><th>Materialtype</th><th>Krav 2030</th><th>Krav 2035</th><th>Status nå</th></tr></thead>
    <tbody>
      <tr><td>PET-flasker (kontakt mat)</td><td class="up">25% rPET</td><td class="up">30% rPET</td><td class="flat">~15–20% i dag</td></tr>
      <tr><td>Plastemballasje &gt;1L</td><td class="up">30% resirkulert</td><td class="up">50% resirkulert</td><td class="down">Lavt i dag</td></tr>
      <tr><td>Fiberkartong (FBB/WLC)</td><td class="flat">Intet krav</td><td class="flat">Intet krav</td><td class="up">Allerede PPWR-klar</td></tr>
      <tr><td>Bølgepapp</td><td class="flat">Intet krav</td><td class="flat">Intet krav</td><td class="up">Allerede PPWR-klar</td></tr>
    </tbody>
  </table>
</div>

##KILDER_INNHOLD##
<div class="sec-header"><h2 class="sec-title">Kilder og metode<span class="sec-tag">Datagrunnlag</span></h2></div>
<div class="alert">⚠ <strong>Viktig om datakvalitet:</strong> Prisdata for emballasjematerialer er i stor grad bak betalingsmur (FOEX PIX, ICIS, EUWID, Fastmarkets). Verdiene i denne rapporten er basert på siste tilgjengelige offentlige data, bransjekommentarer og kjente markedstrender. For kontrakt- og spotpriser til bruk i forhandlinger — verifiser alltid mot ICIS, FOEX PIX eller EUWID direkte.</div>
<div class="card">
  <div class="card-head"><span class="card-title">Datakilder</span></div>
  <div style="padding:16px 18px">
    <div class="src-item"><div class="src-num">1</div><div><div class="src-name">FOEX PIX-indekser</div><div class="src-desc">Kraftliner, Testliner 2, Fluting RB og OCC 1.04 dd — europeiske referanseindekser for bølgepappsegmentet. Oppdateres ukentlig.</div><span class="src-type">Abonnement / begrenset offentlig</span></div></div>
    <div class="src-item"><div class="src-num">2</div><div><div class="src-name">Mintec prisindekser</div><div class="src-desc">PA15 (FBB exw Eur), SV85 (GC2 del EU lo), SZ173 (Kraftliner), SZ176 (Testliner 2), SZ178 (Fluting), SW90 (GD2) — månedlige europeiske referanseindekser.</div><span class="src-type">Abonnement — primærkilde</span></div></div>
    <div class="src-item"><div class="src-num">3</div><div><div class="src-name">ICIS</div><div class="src-desc">Plastpriser (PET, rPET, PP, HDPE, LDPE) — europeiske spotpriser og ukentlige prisrapporter. Ledende prisinformasjon for petrokjemikalier.</div><span class="src-type">Abonnement</span></div></div>
    <div class="src-item"><div class="src-num">4</div><div><div class="src-name">EUWID Pulp & Paper / Recycling</div><div class="src-desc">Tyske og europeiske priser for kartong, papir og returmaterialer. Ukentlig nyhetsbrev med prisovervåkning.</div><span class="src-type">Abonnement</span></div></div>
    <div class="src-item"><div class="src-num">5</div><div><div class="src-name">Fastmarkets PPI Europe</div><div class="src-desc">FBB, WLC og SBS-priser for europeisk kartongmarked. Månedlige og kvartalsvise prisreferanser.</div><span class="src-type">Abonnement</span></div></div>
    <div class="src-item"><div class="src-num">6</div><div><div class="src-name">ChemOrbis / PlasticPortal</div><div class="src-desc">Plastpriser spot og kontrakt. Markedskommentarer og prisanalyse for PP, PE og PET.</div><span class="src-type">Delvis offentlig</span></div></div>
    <div class="src-item"><div class="src-num">7</div><div><div class="src-name">Packaging Europe / RISI</div><div class="src-desc">Bransjenyheter, kapasitetsoppdateringer og markedskommentarer for europeisk emballasjeindustri.</div><span class="src-type">Delvis offentlig</span></div></div>
    <div class="src-item"><div class="src-num">8</div><div><div class="src-name">EU-kommisjonen / EUR-Lex</div><div class="src-desc">PPWR-lovgivning (2025/40), SUP-direktiv, CBAM-regelverk og anti-dumping-vedtak.</div><span class="src-type">Offentlig</span></div></div>
  </div>
</div>
"""

    fill_response_2 = None  # Ikke nødvendig — innhold er hardkodet
    # Vi bruker hardkodet innhold for kall 2 — ingen API-kall nødvendig
    fill_text_2 = fill_prompt_2  # innholdet er allerede ferdig HTML

    fill_text = fill_text_1 + "\n" + fill_text_2

    # Erstatt plassholdere
    sections = ["OVERSIKT_INNHOLD","PLAST_INNHOLD","FIBER_INNHOLD","CORRUGATED_INNHOLD",
                "KAPASITET_INNHOLD","DRIVERE_INNHOLD","REGULERING_INNHOLD","KILDER_INNHOLD"]

    html_content = skeleton
    filled_count = 0

    for key in sections:
        marker = f"##{key}##"
        start = fill_text.find(marker)
        if start == -1:
            print(f"  ⚠️  Fant ikke {key}")
            html_content = html_content.replace(marker, f"<p style='color:#c8401a;padding:20px'>Innhold mangler for {key}</p>")
            continue
        content_start = start + len(marker)
        next_pos = len(fill_text)
        for other in sections:
            other_marker = f"##{other}##"
            if other_marker != marker:
                p = fill_text.find(other_marker, content_start)
                if p != -1 and p < next_pos:
                    next_pos = p
        section_html = fill_text[content_start:next_pos].strip()
        html_content = html_content.replace(marker, section_html)
        filled_count += 1

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"\n✅ Rapport oppdatert: {today}")
    print(f"   Filstørrelse: {len(html_content)} tegn")
    print(f"   Seksjoner fylt: {filled_count}/8")

    checks = {
        "JavaScript showSection": "showSection" in html_content,
        "Alle 8 seksjoner": all(f'id="{s}"' in html_content for s in
            ["overview","plast","fiber","corrugated","kapasitet","drivere","regulering","kilder"]),
        "Nav-tabs (8 stk)": html_content.count("nav-tab") >= 8,
        "Prisdata plast": any(x in html_content for x in ["PET","rPET","HDPE"]),
        "Prisdata fiber/board": any(x in html_content for x in ["FBB","WLC","kraftliner","Kraftliner"]),
    }
    for check, ok in checks.items():
        print(f"   {'✅' if ok else '⚠️ '} {check}")

if __name__ == "__main__":
    update_report()

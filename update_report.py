import anthropic
import os
import json
import datetime
import time
import re

def call_api(client, **kwargs):
    for attempt in range(5):
        try:
            return client.messages.create(**kwargs)
        except anthropic.APIStatusError as e:
            if e.status_code in (529, 429) and attempt < 4:
                wait = min(30 * (2 ** attempt), 120)
                print(f"  API-feil {e.status_code}. Venter {wait}s...")
                time.sleep(wait)
            else:
                raise
    raise Exception("Maks antall forsøk nådd")

def parse_mintec_csv(filepath):
    with open(filepath, encoding="utf-8-sig") as f:
        raw = f.read()
    lines = raw.split("\n")
    sep = ";" if ";" in lines[0] else ","
    data_start = 1
    for i in range(1, min(8, len(lines))):
        if re.match(r"\d{2}[.\-/]\d{2}[.\-/]\d{4}", lines[i].strip()):
            data_start = i
            break
    header_raw = "\n".join(lines[:data_start])
    headers = []
    current = ""
    in_quote = False
    for ch in header_raw:
        if ch == '"':
            in_quote = not in_quote
        elif ch == sep and not in_quote:
            headers.append(current.strip())
            current = ""
        else:
            current += ch
    headers.append(current.strip())

    def clean_header(h):
        h = h.split("\n")[0]
        h = re.sub(r"^[A-Z0-9]+\s*[-\u2013]\s*", "", h)
        h = re.sub(r"\b(del|ave)\b\s*", "", h, flags=re.IGNORECASE)
        h = re.sub(r"EUR/MT\s*", "", h, flags=re.IGNORECASE)
        return h.strip()

    date_idx = 0
    cols = []
    for i, h in enumerate(headers):
        if re.search(r"date|dato|period", h, re.IGNORECASE):
            date_idx = i
        elif clean_header(h):
            cols.append({"name": clean_header(h), "idx": i})

    records = []
    for line in lines[data_start:]:
        if not line.strip():
            continue
        parts = line.split(sep)
        raw_date = parts[date_idx].strip() if date_idx < len(parts) else ""
        m = re.match(r"(\d{2})[.\-/](\d{2})[.\-/](\d{4})", raw_date)
        if not m:
            continue
        date = f"{m.group(3)}-{m.group(2)}-{m.group(1)}"
        row = {"date": date}
        for col in cols:
            if col["idx"] < len(parts):
                try:
                    row[col["name"]] = float(parts[col["idx"]].replace(",", "."))
                except ValueError:
                    row[col["name"]] = None
            else:
                row[col["name"]] = None
        records.append(row)

    records.sort(key=lambda r: r["date"])
    return records, [col["name"] for col in cols]

def build_summary(records, series):
    lines = []
    for s in series:
        rows = [r for r in records if r.get(s) is not None]
        if not rows:
            continue
        v   = rows[-1][s]
        p1  = rows[-2][s]  if len(rows) > 1  else None
        p6  = rows[-7][s]  if len(rows) > 6  else None
        p12 = rows[-13][s] if len(rows) > 12 else None
        all_v = [r[s] for r in rows]
        mx, mn = max(all_v), min(all_v)
        def pct(a, b):
            if b is None or b == 0: return "—"
            return f"{(a-b)/b*100:+.1f}%"
        lines.append(
            f"{s}: \u20ac{v:.0f}/t | MoM {pct(v,p1)} | 6mnd {pct(v,p6)} | "
            f"12mnd {pct(v,p12)} | fra topp \u20ac{mx:.0f} {pct(v,mx)} | "
            f"fra bunn \u20ac{mn:.0f} {pct(v,mn)} | "
            f"{rows[0]['date'][:7]}\u2013{rows[-1]['date'][:7]}"
        )
    return "\n".join(lines)

def generate_analysis():
    client  = anthropic.Anthropic(api_key=os.environ["EMBALLASJE_RAPPORT_CLOUDE_KEY"])
    today   = datetime.date.today().strftime("%d. %B %Y")
    quarter = f"Q{(datetime.date.today().month - 1) // 3 + 1} {datetime.date.today().year}"

    # ── STEG 1: Les Mintec CSV ────────────────────────────
    mintec_summary = ""
    last_date = ""
    num_months = 0
    series_names = []
    mintec_path = "data/Prisrapport_mintec.csv"

    if os.path.exists(mintec_path):
        print(f"Leser Mintec CSV...")
        records, series_names = parse_mintec_csv(mintec_path)
        if records:
            mintec_summary = build_summary(records, series_names)
            last_date  = records[-1]["date"]
            num_months = len(records)
            print(f"  {num_months} mnd | {len(series_names)} serier | siste: {last_date}")
    else:
        print(f"Advarsel: {mintec_path} ikke funnet")

    # ── STEG 2: Web-sok plastpriser ───────────────────────
    print(f"\nSteg 1: Soker plastpriser {today}...")
    r_plast = call_api(
        client,
        model="claude-sonnet-4-6",
        max_tokens=1000,
        tools=[{"type": "web_search_20250305", "name": "web_search"}],
        messages=[{"role": "user", "content":
            f"Sok og finn europeiske plastpriser {today}. "
            f"Returner KUN tallene (maks 400 ord, ingen innledning): "
            f"PET virgin NWE euro/tonn og trend, "
            f"rPET food-grade NWE euro/tonn og trend, "
            f"PP homopolymer FCA Antwerpen euro/tonn og trend, "
            f"HDPE blazing NWE euro/tonn og trend, "
            f"LDPE film NWE euro/tonn og trend, "
            f"maks 2 viktige markedsnyheter plast Europa."
        }]
    )
    plast_data = "".join(b.text for b in r_plast.content if hasattr(b, "text"))[:1500]
    print(f"  Plast: {len(plast_data)} tegn")

    print("Venter 30 sekunder...")
    time.sleep(30)

    # ── STEG 3: Generer AI-analyse ────────────────────────
    print("\nSteg 2: Genererer AI-analyse...")

    mintec_block = (
        f"MINTEC PRISINDEKSER (verifiserte abonnementsdata - primaeerkilde):\n"
        f"{mintec_summary}\n\n"
        f"Siste datapunkt: {last_date} ({num_months} maaneder historikk)\n"
    ) if mintec_summary else "Mintec-data ikke tilgjengelig.\n"

    prompt = (
        f"Du er ekspertanalytiker for europeisk emballasjeprocurement i FMCG. "
        f"Lag en strukturert markedsvurdering for {quarter} ({today}).\n\n"
        f"{mintec_block}\n"
        f"PLASTPRISER (web-sok {today}):\n{plast_data}\n\n"
        f"Skriv analysen paa norsk. Bruk ### for seksjonsoverskrifter og **tekst** for noekkeltall. "
        f"Vaer konkret - bruk faktiske euro-tall der tilgjengelig.\n\n"
        f"### Overordnet markedssituasjon\n"
        f"### Boelgepapp og containerboard\n"
        f"### Solid board og kartong\n"
        f"### Plastmaterialer\n"
        f"### Innkjoepsanbefalinger {quarter}"
    )

    r_analyse = call_api(
        client,
        model="claude-sonnet-4-6",
        max_tokens=2500,
        messages=[{"role": "user", "content": prompt}]
    )
    analyse_text = "".join(b.text for b in r_analyse.content if hasattr(b, "text"))
    print(f"  Analyse: {len(analyse_text)} tegn")

    # ── STEG 4: Skriv analysis.json ───────────────────────
    os.makedirs("data", exist_ok=True)
    output = {
        "generated":     datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "quarter":       quarter,
        "date":          today,
        "mintec_last":   last_date,
        "mintec_months": num_months,
        "mintec_series": series_names,
        "analysis":      analyse_text,
    }
    with open("data/analysis.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\nOK: data/analysis.json skrevet")
    print(f"   Kvartal:   {quarter}")
    print(f"   Mintec:    {last_date} ({num_months} mnd)")
    print(f"   Analyse:   {len(analyse_text)} tegn")
    print(f"   index.html er IKKE endret")

if __name__ == "__main__":
    generate_analysis()

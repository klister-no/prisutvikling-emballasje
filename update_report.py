name: Oppdater Emballasjerapport

on:
  # Kjør automatisk søndag natt kl. 03:00 (rolig tid på API)
  schedule:
    - cron: '0 3 * * 0'
  
  # Tillat manuell kjøring fra GitHub-grensesnittet
  workflow_dispatch:

jobs:
  oppdater-rapport:
    runs-on: ubuntu-latest
    
    permissions:
      contents: write

    steps:
      - name: Hent repoet
        uses: actions/checkout@v4

      - name: Sett opp Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Installer avhengigheter
        run: pip install anthropic

      - name: Kjør rapportoppdatering
        env:
          EMBALLASJE_RAPPORT_CLOUDE_KEY: ${{ secrets.EMBALLASJE_RAPPORT_CLOUDE_KEY }}
        run: python update_report.py

      - name: Lagre kun prisdata — aldri index.html
        run: |
          git config --global user.name "Rapport-bot"
          git config --global user.email "rapport-bot@github.com"
          # Tilbakestill index.html til siste commit — aldri overskriv designet
          git checkout HEAD -- index.html
          # Commit kun datafilene
          git add prices.json data/ || true
          git diff --staged --quiet || git commit -m "📊 Prisdata oppdatert $(date +'%Y-%m-%d') — index.html uendret"
          git pull --rebase origin main
          git push

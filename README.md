# 🏆 Oscars Watch Party Dashboard

## Why this project?

For the Oscars, a group of friends and I got together for a watch party. Beforehand, everyone submitted their predictions via a Google Form – for each category, who we thought *would* win and who we *wished* would win. The answers landed in a Google Sheet.

During the ceremony, we wanted to enter each winner live as soon as it was announced and instantly see who was right. So I built this Streamlit dashboard: pick the winner from a dropdown, and the leaderboard, charts and prediction table update on the spot.

## What you need

- **Python 3.13** (via `pipenv` or `pip`)
- **Python packages:** `streamlit`, `pandas`, `plotly`, `gspread`, `google-auth`
- **A Google Form + Google Sheet** with the responses, containing:
  - `Zeitstempel` (timestamp) and `Dein Name` (player name)
  - one column per category named `<Category> - Prediction`, and optionally `<Category> - Wunsch` (wish)
- **A Google Cloud service account** with the Sheets API enabled. Download its key as `google_credentials.json` into `scripts/` and share the sheet with the service account's email.
- **`data/Oscar_Options.csv`** – all nominees, one per line: `Category,Nominee — Movie`. Category names must match the sheet columns.

## Setup & run

```bash
pip install -r scripts/requirements.txt
cd scripts
streamlit run oscars_dashboard.py
```

Set your own `SPREADSHEET_ID` at the top of `scripts/oscars_dashboard.py`.

Notes: if someone submits more than once, only their latest answer counts. Names starting with `Test` are ignored, and empty answers count as abstentions. Each correct prediction is worth 1 point.

## Charts & views

- **Leaderboard** – current points per player, plus a progress bar of awards handed out
- **Prediction Race** – line chart of each player's score after every award, in the order the winners were entered
- **Prediction table** – everyone's picks per category, with correct ones highlighted in green
- **Award Overview** – awards per movie as a table, bar chart and pie chart
- **Category tabs** – stacked bar charts of predictions and wishes per nominee, with the winner marked 👑

## ⚠️ Keep your credentials private

Never commit `google_credentials.json`. Make sure it is listed in `.gitignore`.

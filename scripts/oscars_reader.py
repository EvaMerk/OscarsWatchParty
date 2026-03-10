import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# -------------------------
# CONFIG
# -------------------------

SERVICE_ACCOUNT_FILE = "google_credentials.json"
SPREADSHEET_ID = "1ebdcv5O0yMJxGEHj68ef0dfg4gWtGwmj1YdRbCqzXS4"

# Punktevergabe
POINTS_PREDICTION = 2
POINTS_WISH = 1

# -------------------------
# GOOGLE SHEETS CONNECTION
# -------------------------

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.readonly"
]

creds = Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE,
    scopes=SCOPES
)

client = gspread.authorize(creds)

sheet = client.open_by_key(SPREADSHEET_ID).sheet1

data = sheet.get_all_records()
df = pd.DataFrame(data)

# -------------------------
# STREAMLIT UI
# -------------------------

st.title("🏆 Oscars Watchparty Dashboard")

# Spielername Spalte (erste Spalte im Sheet)
player_col = df.columns[0]  

players = df[player_col]

# Gewinner Eingabe
st.sidebar.header("Gewinner eintragen")

# Wir trennen Spalten nach Prediction / Wunsch
award_cols = df.columns[1:]  # alle Fragen außer Name

pred_cols = [c for c in award_cols if "Prediction" in c]
wish_cols = [c for c in award_cols if "Wunsch" in c]

winners_pred = {}
winners_wish = {}

st.sidebar.subheader("Prediction")
for col in pred_cols:
    winners_pred[col] = st.sidebar.text_input(col)

st.sidebar.subheader("Wunsch")
for col in wish_cols:
    winners_wish[col] = st.sidebar.text_input(col)

# -------------------------
# SCORE CALCULATION
# -------------------------

scores = {player:0 for player in players}

# Prediction Punkte
for col, winner in winners_pred.items():
    if winner == "":
        continue
    for i,row in df.iterrows():
        if row[col] == winner:
            scores[row[player_col]] += POINTS_PREDICTION

# Wunsch Punkte
for col, winner in winners_wish.items():
    if winner == "":
        continue
    for i,row in df.iterrows():
        if row[col] == winner:
            scores[row[player_col]] += POINTS_WISH

# Leaderboard
leaderboard = pd.DataFrame(
    scores.items(),
    columns=["Name","Punkte"]
).sort_values("Punkte", ascending=False)

# -------------------------
# DISPLAY
# -------------------------

st.header("🏆 Leaderboard")
st.dataframe(leaderboard, use_container_width=True)

# Fortschritt
awards_done = sum(1 for w in winners_pred.values() if w != "") + \
              sum(1 for w in winners_wish.values() if w != "")

total_awards = len(pred_cols) + len(wish_cols)

st.progress(awards_done / total_awards)
st.write(f"{awards_done} / {total_awards} Awards vergeben")

# Alle Tipps anzeigen
st.header("📋 Alle Tipps")
st.dataframe(df)
import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import plotly.graph_objects as go
import os

from functions import plot_vote_distribution  # external function

# -------------------------
# CONFIG
# -------------------------
SERVICE_ACCOUNT_FILE = st.secrets["google"]
#SERVICE_ACCOUNT_FILE = "google_credentials.json"
SPREADSHEET_ID = "1ebdcv5O0yMJxGEHj68ef0dfg4gWtGwmj1YdRbCqzXS4"
POINTS_PREDICTION = 1

# -------------------------
# GOOGLE SHEETS CONNECTION
# -------------------------
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.readonly"
]
creds = Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES
)
client = gspread.authorize(creds)
sheet = client.open_by_key(SPREADSHEET_ID).sheet1
data = sheet.get_all_records()
df = pd.DataFrame(data)

# -------------------------
# DATA CLEANING
# -------------------------
df["Zeitstempel"] = pd.to_datetime(df["Zeitstempel"], format="%d.%m.%Y %H:%M:%S")
df = df.sort_values("Zeitstempel")
df = df.drop_duplicates(subset="Dein Name", keep="last")

player_col = "Dein Name"
players = df[player_col]

# Farben pro Spieler
color_palette = [
    "#636EFA","#EF553B","#00CC96","#AB63FA","#FFA15A",
    "#19D3F3","#FF6692","#B6E880","#FF97FF","#FECB52"
]
player_colors = {player: color_palette[i % len(color_palette)] for i, player in enumerate(players)}

award_cols = [c for c in df.columns if c not in [player_col, "Zeitstempel"]]
pred_cols = [c for c in award_cols if "Prediction" in c]
wish_cols = [c for c in award_cols if "Wunsch" in c]

# Leere Felder als Enthaltung für Berechnung
for col in pred_cols + wish_cols:
    df[col] = df[col].fillna("").replace("", "Enthaltung")

# -------------------------
# NOMINIERTEN CSV
# -------------------------
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
csv_path = os.path.join(repo_root, "data", "Oscar_Options.csv")
df_nominees = pd.read_csv(csv_path, sep=",", header=None, names=["Category","Nominee"])

# Dict: Kategorie -> Liste Nominierten
nominees_dict = {}
for cat, group in df_nominees.groupby("Category"):
    nominees = group["Nominee"].tolist()
    nominees_dict[cat] = nominees  # keine Enthaltung

# -------------------------
# STREAMLIT UI
# -------------------------
st.title("🏆 Oscars Watchparty Dashboard")
st.sidebar.header("Gewinner eintragen")

# Gewinner über Dropdown (nur echte Nominierten)
# Gewinner über Dropdown (nur echte Nominierten + leeres Feld als Default)
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import time

# -------------------------
# WINNER INPUT (SIDEBAR)
# -------------------------

# Session state für Zeitstempel
if "award_times" not in st.session_state:
    st.session_state.award_times = {}

winners_pred = {}
for col in pred_cols:
    cat_name = col.replace(" - Prediction","")
    options = [" "] + nominees_dict.get(cat_name, [])  # Leeres Feld vorne

    selected = st.sidebar.selectbox(
        f"{cat_name}",
        options=options,
        index=0,
        key=f"dropdown_{cat_name}"
    )

    # Nur Punkte vergeben wenn nicht leer
    winners_pred[col] = selected if selected != " " else ""

    # Zeit speichern wenn Award erstmals gesetzt wird
    if selected != " " and col not in st.session_state.award_times:
        st.session_state.award_times[col] = time.time()

# -------------------------
# SCORE CALCULATION
# -------------------------

scores = {player:0 for player in players}

for col, winner in winners_pred.items():
    if winner == "":
        continue

    for _, row in df.iterrows():
        if row[col] == winner:
            scores[row[player_col]] += POINTS_PREDICTION

leaderboard = pd.DataFrame(scores.items(), columns=["Name","Punkte"]).sort_values("Punkte", ascending=False)

# -------------------------
# TABS
# -------------------------

categories = [c.replace(" - Prediction","") for c in pred_cols]
tabs = st.tabs(["🏠 Übersicht"] + categories)

# -------------------------
# TAB 0: Übersicht
# -------------------------

with tabs[0]:

    st.header("🏆 Leaderboard")
    st.dataframe(leaderboard, use_container_width=True)

    # Fortschritt
    awards_done = sum(1 for w in winners_pred.values() if w != "")
    total_awards = len(pred_cols)

    st.progress(awards_done / total_awards)
    st.write(f"{awards_done} / {total_awards} Awards vergeben")

    # -------------------------
    # Punkteentwicklung (ECHTE VERGABEREIHENFOLGE)
    # -------------------------

    progress_scores = {player: 0 for player in players}
    history = []
    awards_order = []

    # Nur Awards mit gesetztem Winner
    awarded_cols = [c for c in pred_cols if winners_pred.get(c,"") != ""]

    # Nach Eingabezeit sortieren
    awarded_cols_sorted = sorted(
        awarded_cols,
        key=lambda c: st.session_state.award_times.get(c, float("inf"))
    )

    for col in awarded_cols_sorted:

        winner = winners_pred[col]
        award_name = col.replace(" - Prediction","")

        for _, row in df.iterrows():
            if row[col] == winner:
                progress_scores[row[player_col]] += POINTS_PREDICTION

        history.append(progress_scores.copy())
        awards_order.append(award_name)

    if history:

        progress_df = pd.DataFrame(history, index=awards_order)
        progress_df.index.name = "Award"

        fig = go.Figure()

        # aktueller Leader bestimmen
        latest_scores = progress_df.iloc[-1]
        leader = latest_scores.idxmax()

        for player in progress_df.columns:

            is_leader = player == leader

            fig.add_trace(
                go.Scatter(
                    x=progress_df.index,
                    y=progress_df[player],
                    mode="lines+markers+text",
                    name=player,

                    # Leader hervorheben
                    line=dict(
                        color=player_colors[player],
                        width=5 if is_leader else 3,
                        smoothing=1.1
                    ),

                    marker=dict(
                        size=[8]*(len(progress_df)-1) + [16],
                        color=player_colors[player],
                        line=dict(width=2,color="white")
                    ),

                    # Name beim letzten Punkt anzeigen
                    text=[""]*(len(progress_df)-1) + [player],
                    textposition="middle right",

                    hovertemplate=
                    "<b>%{text}</b><br>" +
                    "%{y} Punkte<br>" +
                    "Award: %{x}<extra></extra>"
                )
            )

        fig.update_layout(

            title="📈 Oscar Prediction Race",
            xaxis_title="Vergebene Awards",
            yaxis_title="Punkte",

            template="plotly_white",

            legend_title="Spieler",

            xaxis=dict(
                tickangle=-35,
                showgrid=True
            ),

            yaxis=dict(
                rangemode="tozero",
                gridcolor="rgba(0,0,0,0.1)"
            ),

            hovermode="x unified",

            height=500
        )

        st.plotly_chart(fig, use_container_width=True)

    # Tippmatrix
    st.header("🎬 Prediction Tipps pro Kategorie")
    prediction_table = df.set_index(player_col)[pred_cols].T
    prediction_table.index = [c.replace(" - Prediction","") for c in prediction_table.index]
    prediction_table.index.name = "Kategorie"

    def highlight_correct(row):
        category = row.name + " - Prediction"
        if category not in winners_pred:
            return [""] * len(row)
        winner = winners_pred[category]
        return ["background-color: lightgreen; color: black" if v==winner else "" for v in row]

    styled_table = prediction_table.style.apply(highlight_correct, axis=1)
    st.dataframe(styled_table, use_container_width=True)

# -------------------------
# CATEGORY TABS
# -------------------------
for i, col in enumerate(pred_cols):
    with tabs[i+1]:
        category_name = col.replace(" - Prediction", "")
        st.header(f"🎬 Kategorie: {category_name}")

        # -------------------------
        # Prediction Grafik
        # -------------------------
        fig_pred = plot_vote_distribution(
            df,
            player_col,
            col,
            players,
            player_colors,
            all_options=nominees_dict.get(category_name, [])
        )

        # Gewinner aus Sidebar
        winner = winners_pred.get(col, "")
        if winner and winner != "":
            count = sum(df[col] == winner)
            fig_pred.add_annotation(
                x=winner,
                y=count,
                text="👑",
                showarrow=False,
                yshift=10,
                font=dict(size=20)
            )

        st.subheader("Prediction")
        st.plotly_chart(fig_pred, use_container_width=True, key=f"pred_{category_name}")

        # -------------------------
        # Wunsch Grafik
        # -------------------------
        wish_col = col.replace(" - Prediction", " - Wunsch")
        if wish_col in df.columns:
            fig_wish = plot_vote_distribution(
                df,
                player_col,
                wish_col,
                players,
                player_colors,
                all_options=nominees_dict.get(category_name, [])
            )

            st.subheader("Wunsch")
            st.plotly_chart(fig_wish, use_container_width=True, key=f"wunsch_{category_name}")
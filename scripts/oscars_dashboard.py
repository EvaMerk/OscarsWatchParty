import os
import time
from collections import Counter
import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import plotly.graph_objects as go

from functions import (
    plot_vote_distribution,
    extract_movie,
    highlight_correct,
    make_score_progress_figure,
    make_awards_bar,
    make_awards_pie,
)

# -------------------------
# CONFIG
# -------------------------
# Instance-specific values live in scripts/.streamlit/secrets.toml (git-ignored).
# See secrets.toml.example for the expected keys. Without a spreadsheet_id the
# dashboard starts in demo mode using data/sample_responses.csv.
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
try:
    if os.environ.get("OSCARS_DEMO"):
        raise KeyError("demo mode forced via OSCARS_DEMO")
    SPREADSHEET_ID = st.secrets["spreadsheet_id"]
    # Resolve relative to this script so it works from any working directory
    SERVICE_ACCOUNT_FILE = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        st.secrets.get("credentials_file", "google_credentials.json"),
    )
    DEMO_MODE = False
except (FileNotFoundError, KeyError):
    SPREADSHEET_ID = SERVICE_ACCOUNT_FILE = None
    DEMO_MODE = True
POINTS_PREDICTION = 1

# -------------------------
# DATA SOURCE: GOOGLE SHEETS (or demo CSV)
# -------------------------
if DEMO_MODE:
    df = pd.read_csv(os.path.join(repo_root, "data", "sample_responses.csv"))
else:
    SCOPES = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive.readonly"
    ]
    creds = Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES
    )
    client = gspread.authorize(creds)
    sheet = client.open_by_key(SPREADSHEET_ID).sheet1
    df = pd.DataFrame(sheet.get_all_records())

# -------------------------
# DATA CLEANING
# -------------------------
df["Zeitstempel"] = pd.to_datetime(df["Zeitstempel"], format="%d.%m.%Y %H:%M:%S")
df = df.sort_values("Zeitstempel")
df = df.drop_duplicates(subset="Dein Name", keep="last")
df = df[~df['Dein Name'].str.startswith('Test', na=False)]

player_col = "Dein Name"
players = df[player_col]

# Colors per player
color_palette = [
    "#636EFA","#EF553B","#00CC96","#AB63FA","#FFA15A",
    "#19D3F3","#FF6692","#B6E880","#FF97FF","#FECB52"
]
player_colors = {player: color_palette[i % len(color_palette)] for i, player in enumerate(players)}

award_cols = [c for c in df.columns if c not in [player_col, "Zeitstempel"]]
pred_cols = [c for c in award_cols if "Prediction" in c]
wish_cols = [c for c in award_cols if "Wunsch" in c]

# Treat empty fields as abstention for calculation
for col in pred_cols + wish_cols:
    df[col] = df[col].fillna("")

# -------------------------
# NOMINEES CSV
# -------------------------
csv_path = os.path.join(repo_root, "data", "Oscar_Options.csv")
df_nominees = pd.read_csv(csv_path, sep=",", header=None, names=["Category","Nominee"])

# Dict: category -> list of nominees
nominees_dict = {}
for cat, group in df_nominees.groupby("Category"):
    nominees = group["Nominee"].tolist()
    nominees_dict[cat] = nominees  # keine Enthaltung

# -------------------------
# STREAMLIT UI
# -------------------------
st.title("🏆 Oscars Watchparty Dashboard")
if DEMO_MODE:
    st.info(
        "Demo mode: showing made-up predictions from `data/sample_responses.csv`. "
        "Add a `spreadsheet_id` in `.streamlit/secrets.toml` to use your own Google Sheet."
    )
st.sidebar.header("Enter winners")


# -------------------------
# WINNER INPUT (SIDEBAR)
# -------------------------
# Winners via multiselect (only real nominees). Several selections = a tie:
# everyone who picked any of the winners gets the point.

# Session state for timestamps
if "award_times" not in st.session_state:
    st.session_state.award_times = {}

winners_pred = {}
for col in pred_cols:
    cat_name = col.replace(" - Prediction","").strip()
    selected = st.sidebar.multiselect(
        f"{cat_name}",
        options=nominees_dict.get(cat_name, []),
        key=f"winners_{cat_name}",
        help="Select more than one nominee in case of a tie.",
    )

    # List of winners; empty list = not awarded yet
    winners_pred[col] = selected

    # Save time when award is first set, forget it when cleared again
    if selected and col not in st.session_state.award_times:
        st.session_state.award_times[col] = time.time()
    elif not selected:
        st.session_state.award_times.pop(col, None)

# -------------------------
# SCORE CALCULATION
# -------------------------

scores = {player:0 for player in players}

for col, winners in winners_pred.items():
    if not winners:
        continue

    for _, row in df.iterrows():
        if row[col] in winners:
            scores[row[player_col]] += POINTS_PREDICTION

leaderboard = pd.DataFrame(scores.items(), columns=["Name","Points"]).sort_values("Points", ascending=False)

# -------------------------
# TABS
# -------------------------

categories = [c.replace(" - Prediction","") for c in pred_cols]
tabs = st.tabs(["🏠 Scoreboard"]  +["Award Overview"]+ categories)

# -------------------------
# TAB 0: Overview
# -------------------------

with tabs[0]:

    st.header("🏆 Leaderboard")
    st.dataframe(leaderboard, width="stretch")

    # Progress
    awards_done = sum(1 for w in winners_pred.values() if w)
    total_awards = len(pred_cols)

    st.progress(awards_done / total_awards)
    st.write(f"{awards_done} / {total_awards} Awards awarded")

    # -------------------------
    # Score progression (actual award order)
    # -------------------------

    progress_scores = {player: 0 for player in players}
    history = []
    awards_order = []

    # Only awards with a set winner
    awarded_cols = [c for c in pred_cols if winners_pred.get(c)]

    # Sort by input time
    awarded_cols_sorted = sorted(
        awarded_cols,
        key=lambda c: st.session_state.award_times.get(c, float("inf"))
    )

    for col in awarded_cols_sorted:

        winners = winners_pred[col]
        award_name = col.replace(" - Prediction","")

        for _, row in df.iterrows():
            if row[col] in winners:
                progress_scores[row[player_col]] += POINTS_PREDICTION

        history.append(progress_scores.copy())
        awards_order.append(award_name)

    if history:

        progress_df = pd.DataFrame(history, index=awards_order)
        progress_df.index.name = "Award"

        # build the figure using the helper in scripts/functions.py
        fig = make_score_progress_figure(progress_df, player_colors)

        st.plotly_chart(fig, width="stretch")

    # Prediction matrix
    st.header("🎬 Prediction tips per category")
    prediction_table = df.set_index(player_col)[pred_cols].T
    prediction_table.index = [c.replace(" - Prediction","") for c in prediction_table.index]
    prediction_table.index.name = "Category"

    # use highlight_correct from scripts/functions.py which expects (row, winners_pred)
    styled_table = prediction_table.style.apply(lambda row: highlight_correct(row, winners_pred), axis=1)
    st.dataframe(styled_table, width="stretch")
# -------------------------
# AWARD OVERVIEW
# -------------------------

with tabs[1]:

    st.header("🎬 Award Overview")

    # Movies that won so far. One award per movie per category, so two winners
    # from the same movie in a tie still count once for that movie.
    winners_list_awards = [
        movie
        for winners in winners_pred.values()
        for movie in {extract_movie(w) for w in winners}
    ]

    if len(winners_list_awards) == 0:
        st.info("No winners selected yet. Enter winners in the sidebar to populate the overview.")
    else:

        # Count how often each film was entered as a winner
        counts = Counter(winners_list_awards)

        # All nominated movies (from CSV) as base so that movies with 0 awards are shown
        all_movies = list(set(extract_movie(m) for m in df_nominees["Nominee"]))

        counts_all = [{"Movie": m, "Awards": counts.get(m, 0)} for m in all_movies]
        award_df = pd.DataFrame(counts_all).sort_values("Awards", ascending=False).reset_index(drop=True)

    # Option: show only movies with >0 awards
        show_all = st.checkbox("Show all nominated movies (include 0 awards)", value=False)
        display_df = award_df if show_all else award_df[award_df["Awards"] > 0]

        st.subheader("Awards per Movie")
        st.dataframe(display_df, width="stretch")

        # Bar chart: Number of awards per movie
        if not display_df.empty:
            fig_awards = make_awards_bar(display_df)
            st.plotly_chart(fig_awards, width="stretch")

            # Pie chart: percentage share (only when at least 1 award has been given)
            if display_df["Awards"].sum() > 0:
                fig_pie = make_awards_pie(display_df)
                st.plotly_chart(fig_pie, width="stretch")

# -------------------------
# CATEGORY TABS
# -------------------------
for i, col in enumerate(pred_cols):
    with tabs[i+2]:
        category_name = col.replace(" - Prediction", "")
        st.header(f"🎬 Category: {category_name}")

        # -------------------------
        # Prediction chart
        # -------------------------
        fig_pred = plot_vote_distribution(
            df,
            player_col,
            col,
            players,
            player_colors,
            all_options=nominees_dict.get(category_name, [])
        )

        # Winner from sidebar
        for winner in winners_pred.get(col, []):
            count = sum(df[col] == winner)
            fig_pred.add_annotation(
                x=winner,
                y=count,
                text=f"👑 {winner}",
                showarrow=False,
                yshift=10,
                font=dict(size=14)
            )

        st.subheader("Prediction")
        st.plotly_chart(fig_pred, width="stretch", key=f"pred_{category_name}")

        # -------------------------
        # Wish chart
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
            st.subheader("Wish")
            st.plotly_chart(fig_wish, width="stretch", key=f"wunsch_{category_name}")
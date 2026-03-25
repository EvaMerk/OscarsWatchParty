import os
import time

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
SERVICE_ACCOUNT_FILE = "google_credentials.json"
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
    df[col] = df[col].fillna("").replace("", "Enthaltung")

# -------------------------
# NOMINEES CSV
# -------------------------
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
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
st.sidebar.header("Enter winners")

# Winners via dropdown (only real nominees + empty default option)

# -------------------------
# WINNER INPUT (SIDEBAR)
# -------------------------

# Session state for timestamps
if "award_times" not in st.session_state:
    st.session_state.award_times = {}

winners_pred = {}
for col in pred_cols:
    cat_name = col.replace(" - Prediction","").strip()
    options = [" "] + nominees_dict.get(cat_name, [])  # Leeres Feld vorne

    selected = st.sidebar.selectbox(
        f"{cat_name}",
        options=options,
        index=0,
        key=f"dropdown_{cat_name}"
        )

    # Only award points when not empty
    winners_pred[col] = selected if selected != " " else ""

    # Save time when award is first set
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
    st.dataframe(leaderboard, use_container_width=True)

    # Progress
    awards_done = sum(1 for w in winners_pred.values() if w != "")
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
    awarded_cols = [c for c in pred_cols if winners_pred.get(c,"") != ""]

    # Sort by input time
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

        # build the figure using the helper in scripts/functions.py
        fig = make_score_progress_figure(progress_df, player_colors)

        st.plotly_chart(fig, use_container_width=True)

    # Prediction matrix
    st.header("🎬 Prediction tips per category")
    prediction_table = df.set_index(player_col)[pred_cols].T
    prediction_table.index = [c.replace(" - Prediction","") for c in prediction_table.index]
    prediction_table.index.name = "Category"

    # use highlight_correct from scripts/functions.py which expects (row, winners_pred)
    styled_table = prediction_table.style.apply(lambda row: highlight_correct(row, winners_pred), axis=1)
    st.dataframe(styled_table, use_container_width=True)
# -------------------------
# AWARD OVERVIEW
# -------------------------

with tabs[1]:

    st.header("🎬 Award Overview")

    # List of winners entered so far (only movie part, non-empty)
    winners_list_awards = [extract_movie(w) for w in winners_pred.values() if w and w != ""]

    if len(winners_list_awards) == 0:
        st.info("No winners selected yet. Enter winners in the sidebar to populate the overview.")
    else:
        from collections import Counter

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
        st.dataframe(display_df, use_container_width=True)

        # Bar chart: Number of awards per movie
        if not display_df.empty:
            fig_awards = make_awards_bar(display_df)
            st.plotly_chart(fig_awards, use_container_width=True)

            # Pie chart: percentage share (only when at least 1 award has been given)
            if display_df["Awards"].sum() > 0:
                fig_pie = make_awards_pie(display_df)
                st.plotly_chart(fig_pie, use_container_width=True)

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
        winner = winners_pred.get(col, "")
        if winner and winner != "":
            count = sum(df[col] == winner)
            display_winner = winner
            fig_pred.add_annotation(
                x=winner,
                y=count,
                text=f"👑 {display_winner}",
                showarrow=False,
                yshift=10,
                font=dict(size=14)
            )

        st.subheader("Prediction")
        st.plotly_chart(fig_pred, use_container_width=True, key=f"pred_{category_name}")

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
            st.plotly_chart(fig_wish, use_container_width=True, key=f"wunsch_{category_name}")
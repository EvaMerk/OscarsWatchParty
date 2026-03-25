# functions.py
import plotly.graph_objects as go
import pandas as pd
import re


def extract_movie(s: str) -> str:
    """Extract the movie part after a dash (-, – or —) and trim whitespace.

    Returns an empty string for falsy input.
    """
    if not s:
        return ""
    parts = re.split(r"\s*[-–—]\s*", s, maxsplit=1)
    return parts[1].strip() if len(parts) > 1 else s.strip()


def highlight_correct(row, winners_pred: dict):
    """Return a list of CSS styles for a prediction row.

    The function expects `row.name` to be the category name (without " - Prediction").
    `winners_pred` is a dict mapping full column names (e.g. "Best Picture - Prediction")
    to the selected winner string.
    """
    category = row.name + " - Prediction"

    if category not in winners_pred:
        return [""] * len(row)

    winner_raw = winners_pred[category]

    return [
        "background-color: lightgreen; color: black"
        if v == winner_raw else ""
        for v in row
    ]

def plot_vote_distribution(df, player_col, col, players, player_colors, all_options=None):
    # Group by candidate and player
    counts = df.groupby([col, player_col]).size().unstack(fill_value=0)

    # Ensure all options are present (and in the order provided)
    if all_options:
        for opt in all_options:
            if opt not in counts.index:
                counts.loc[opt] = [0] * len(counts.columns)
        counts = counts.loc[all_options]

    # Stacked bar chart
    fig = go.Figure()
    for player in counts.columns:
        fig.add_trace(go.Bar(
            x=counts.index,
            y=counts[player],
            name=player,
            marker_color=player_colors[player]
        ))
    fig.update_layout(barmode="stack", xaxis_title="Candidate", yaxis_title="Number of Votes")
    return fig


def make_score_progress_figure(progress_df: pd.DataFrame, player_colors: dict) -> go.Figure:
    """Create the score progression line chart used on the leaderboard tab.

    progress_df: rows are Awards (index), columns are player names with cumulative scores.
    player_colors: mapping player -> color string.
    """
    fig = go.Figure()

    # determine current leader
    latest_scores = progress_df.iloc[-1]
    leader = latest_scores.idxmax()

    for player in progress_df.columns:
        is_leader = player == leader

        # ensure marker size array matches number of points
        n = len(progress_df)
        marker_sizes = [8] * max(0, n - 1) + ([16] if n >= 1 else [])

        fig.add_trace(
            go.Scatter(
                x=progress_df.index,
                y=progress_df[player],
                mode="lines+markers+text",
                name=player,
                line=dict(
                    color=player_colors.get(player, None),
                    width=5 if is_leader else 3,
                    smoothing=1.1
                ),
                marker=dict(
                    size=marker_sizes,
                    color=player_colors.get(player, None),
                    line=dict(width=2, color="white")
                ),
                text=[""] * max(0, n - 1) + [player],
                textposition="middle right",
                hovertemplate=(
                    "<b>%{text}</b><br>" +
                    "%{y} Points<br>" +
                    "Award: %{x}<extra></extra>"
                )
            )
        )

    fig.update_layout(
        title="📈 Oscar Prediction Race",
        xaxis_title="Awards Awarded",
        yaxis_title="Points",
        template="plotly_white",
        legend_title="Players",
        xaxis=dict(tickangle=-35, showgrid=True),
        yaxis=dict(rangemode="tozero", gridcolor="rgba(0,0,0,0.1)"),
        hovermode="x unified",
        height=500
    )

    return fig


def make_awards_bar(display_df: pd.DataFrame) -> go.Figure:
    """Create a bar chart of Awards per movie from display_df (columns: Movie, Awards)."""
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=display_df["Movie"],
        y=display_df["Awards"],
        marker_color="#636EFA"
    ))
    fig.update_layout(
        title="Number of Awards per Movie",
        xaxis_tickangle=-45,
        xaxis_title="Movie",
        yaxis_title="Awards",
        template="plotly_white",
        height=450
    )
    return fig


def make_awards_pie(display_df: pd.DataFrame) -> go.Figure:
    """Create a pie chart of award share. Expects display_df with Movie and Awards columns.

    Caller should check that display_df["Awards"].sum() > 0 before calling if desired.
    """
    fig = go.Figure(go.Pie(labels=display_df["Movie"], values=display_df["Awards"], sort=False))
    fig.update_layout(title="Share of Awards", height=400)
    return fig


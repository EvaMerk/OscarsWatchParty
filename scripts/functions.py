# functions.py
import plotly.graph_objects as go
import pandas as pd

def plot_vote_distribution(df, player_col, col, players, player_colors, all_options=None):
    # Gruppiere nach Kandidat und Spieler
    counts = df.groupby([col, player_col]).size().unstack(fill_value=0)

    # Alle Optionen sicherstellen
    if all_options:
        for opt in all_options:
            if opt not in counts.index:
                counts.loc[opt] = [0]*len(counts.columns)
        counts = counts.loc[all_options]  # Reihenfolge wie in all_options

    # Stacked Barplot
    fig = go.Figure()
    for player in counts.columns:
        fig.add_trace(go.Bar(
            x=counts.index,
            y=counts[player],
            name=player,
            marker_color=player_colors[player]
        ))
    fig.update_layout(barmode="stack", xaxis_title="Kandidat", yaxis_title="Anzahl Votes")
    return fig


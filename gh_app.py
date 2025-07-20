import streamlit as st
import pandas as pd
import numpy as np
import requests
from bs4 import BeautifulSoup

# Trait-sensitive tracks
trait_sensitive_tracks = [
    "Wagga", "Nowra", "Maitland", "Angle Park", "Lakeside",
    "Warragul", "The Gardens", "Albion Park", "Shepparton",
    "Dapto", "Mandurah", "Gosford"
]

# Box bias (placeholder)
default_bias = {1: "Good", 2: "Fair", 3: "Fair", 4: "Risky", 5: "Risky", 6: "Fair", 7: "Good", 8: "Good"}

# Trait mappings
rt_score_map = {'E': 1, 'G': 2, 'F': 3, 'S': 4, 'R': 5}
start_map = {'R': 'Railer', 'M': 'Middle', 'W': 'Wide', 'S': 'Straight'}
bias_score_map = {"Good": 1, "Fair": 2, "Risky": 3}
win_score_map = {
    "Last Start": 0.0,
    "2 Starts Ago": 0.2,
    "3+ Starts Ago": 0.4,
    "Never": 0.6
}
rt_options = [f"{r} {s}" for r in rt_score_map for s in start_map]
last_win_options = list(win_score_map.keys())

def process_rt_trait(rt_value):
    if not isinstance(rt_value, str) or len(rt_value) < 3:
        return 3, "Middle"
    parts = rt_value.strip().upper().split()
    rating = parts[0] if parts[0] in rt_score_map else 'F'
    start = parts[1] if len(parts) > 1 and parts[1] in start_map else 'M'
    return rt_score_map[rating], start_map[start]

def assess_collision_risk(row, df):
    risk = 0
    for _, other in df.iterrows():
        if other['Dog'] != row['Dog']:
            if row['Style'] == 'Wide' and other['Box'] < row['Box'] and other['Style'] != 'Wide' and other['Split'] < row['Split']:
                risk += 1
            elif row['Style'] == 'Railer' and other['Box'] > row['Box'] and other['Style'] != 'Railer' and other['Split'] < row['Split']:
                risk += 1
    return risk

def compute_win_probability(scores):
    inverse_scores = -np.array(scores)
    exp_scores = np.exp(inverse_scores - np.max(inverse_scores))
    probs = exp_scores / exp_scores.sum()
    return (probs * 100).round(1)

@st.cache_data(ttl=600)
def get_race_distance(track, race_number):
    url = "https://www.thedogs.com.au/racing"
    try:
        res = requests.get(url)
        soup = BeautifulSoup(res.text, "html.parser")
        meetings = soup.select(".race-meeting")
        for meeting in meetings:
            name_tag = meeting.select_one(".meeting-name")
            if not name_tag:
                continue
            if track.lower() not in name_tag.text.strip().lower():
                continue
            race_tables = meeting.select(".race-table")
            if race_number <= len(race_tables):
                race_table = race_tables[race_number - 1]
                distance_tag = race_table.select_one("caption")
                if distance_tag:
                    return distance_tag.text.strip()
        return "Distance not found"
    except Exception:
        return "Distance not found"

def rank_dogs(df, track_name):
    df['Bias'] = df['Box'].map(default_bias)
    df['Bias Score'] = df['Bias'].map(bias_score_map)
    df['RT Score'], df['Style'] = zip(*df['R/T'].map(process_rt_trait))
    df['Win Recency Score'] = df['Last Win'].map(win_score_map)
    df['Collision Risk'] = df.apply(lambda row: assess_collision_risk(row, df), axis=1)
    df['Speed Rank'] = df['Split'].rank()
    df['Total Score'] = df['Speed Rank'] + df['Bias Score'] + df['Collision Risk'] + df['RT Score'] + df['Win Recency Score']
    df['Rank'] = df['Total Score'].rank(method='min')
    df['Win %'] = compute_win_probability(df['Total Score'])
    return df.sort_values(by='Rank')

# ASCII collision preview
def generate_ascii_collision(df):
    layout = "Box 1   Box 2   Box 3   Box 4   Box 5   Box 6   Box 7   Box 8\n"
    names_line = ""
    traits_line = ""
    arrow_line = ""

    for i in range(1, 9):
        dog_row = df[df['Box'] == i].iloc[0]
        name = dog_row['Dog'][:3].ljust(3)
        trait = dog_row['Style'][0].upper()
        names_line += f" {name}     "
        traits_line += f"[{trait}]     "

    for i in range(1, 9):
        dog = df[df['Box'] == i].iloc[0]
        arrows = ""
        for j in range(1, 9):
            if i == j:
                continue
            other = df[df['Box'] == j].iloc[0]
            if dog['Style'] == 'Wide' and j < i and other['Style'] != 'Wide' and other['Split'] < dog['Split']:
                arrows += "←"
            elif dog['Style'] == 'Railer' and j > i and other['Style'] != 'Railer' and other['Split'] < dog['Split']:
                arrows += "→"
        arrow_line += f" {arrows.ljust(6)} "

    return f"```\n{layout}{names_line}\n{traits_line}\n{arrow_line}\n```"

# ----------------------
# 🎯 Streamlit App
# ----------------------
st.title("🐾 Greyhound Collision & Split Analyser")

col1, col2 = st.columns(2)
track_choice = col1.selectbox("Track", trait_sensitive_tracks)
race_number = col2.selectbox("Race Number", list(range(1, 13)))
distance = get_race_distance(track_choice, race_number)
st.markdown(f"📏 **Race Distance:** `{distance}`")

default_data = pd.DataFrame({
    "Dog": [f"Dog {i}" for i in range(1, 9)],
    "Box": list(range(1, 9)),
    "Split": [5.10]*8,
    "R/T": ["F M"]*8,
    "Last Win": ["2 Starts Ago"]*8
})

df_input = st.data_editor(
    default_data,
    column_config={
        "R/T": st.column_config.SelectboxColumn("R/T", options=rt_options),
        "Last Win": st.column_config.SelectboxColumn("Last Win", options=last_win_options)
    },
    num_rows="fixed"
)

if st.button("Run Analysis"):
    try:
        results = rank_dogs(df_input.copy(), track_choice)
        fastest_split = results['Split'].min()
        highest_risk = results['Collision Risk'].max()

        def highlight_row(row):
            style = ''
            if row['Split'] == fastest_split:
                style += 'background-color: #D0E6FF;'
            if row['Collision Risk'] == highest_risk:
                style += 'background-color: #FFD6D6;'
            return [style] * len(row)

        styled_df = results.style.apply(highlight_row, axis=1)

        st.success("✅ Analysis Complete")
        st.dataframe(styled_df, use_container_width=True)
        st.markdown(f"### 🏆 Predicted Winner: **{results.iloc[0]['Dog']}** (Box {results.iloc[0]['Box']})")

        st.markdown("### 🔀 Collision Risk Preview")
        st.markdown(generate_ascii_collision(results))

    except Exception as e:
        st.error(f"Error: {e}")

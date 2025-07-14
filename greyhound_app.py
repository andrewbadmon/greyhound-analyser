import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime

# R/T scoring
rt_score_map = {'E': 1, 'G': 2, 'F': 3, 'S': 4, 'R': 5}
start_map = {'R': 'Railer', 'M': 'Middle', 'S': 'Middle', 'W': 'Wide'}
bias_score_map = {"Good": 1, "Fair": 2, "Risky": 3, "Wide Bias": 2}

# Basic box bias templates (same layout for all, just examples)
default_bias = {1: "Good", 2: "Fair", 3: "Fair", 4: "Risky", 5: "Risky", 6: "Fair", 7: "Good", 8: "Good"}

# --- Scrape R/T-Enabled Tracks from thedogs.com.au ---
@st.cache_data(ttl=3600)
def get_rt_tracks_today():
    url = "https://www.thedogs.com.au/racing"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")

    tracks_with_rt = []
    for section in soup.select(".race-meeting"):
        track_name_tag = section.select_one(".meeting-name")
        if not track_name_tag:
            continue
        track_name = track_name_tag.get_text(strip=True)

        race_tables = section.select(".race-table thead")
        has_rt = any("R/T" in th.get_text() for table in race_tables for th in table.select("th"))

        if has_rt:
            tracks_with_rt.append(track_name)

    return tracks_with_rt

# --- Process R/T Code ---
def process_rt_trait(rt_value):
    if rt_value in ['NBT', 'SCR', 'N/A', None] or not isinstance(rt_value, str):
        return 3, 'Middle'
    rt_clean = rt_value.strip().upper()
    rating = rt_clean[0] if rt_clean[0] in rt_score_map else 'F'
    start = rt_clean[1] if len(rt_clean) > 1 and rt_clean[1] in start_map else 'M'
    return rt_score_map.get(rating, 3), start_map.get(start, 'Middle')

# --- Collision Risk Function ---
def assess_collision_risk(row, df):
    risk = 0
    for _, other in df.iterrows():
        if other['Dog'] != row['Dog']:
            if row['Style'] == 'Wide' and other['Box'] < row['Box'] and other['Style'] != 'Wide' and other['Split'] < row['Split']:
                risk += 1
            elif row['Style'] == 'Railer' and other['Box'] > row['Box'] and other['Style'] != 'Railer' and other['Split'] < row['Split']:
                risk += 1
    return risk

# --- Ranking Function ---
def rank_dogs(df, selected_track):
    df['Bias'] = df['Box'].map(default_bias)
    df['Bias Score'] = df['Bias'].map(bias_score_map)
    df['RT Score'], df['Style'] = zip(*df['R/T'].map(process_rt_trait))
    df['Collision Risk'] = df.apply(lambda row: assess_collision_risk(row, df), axis=1)
    df['Speed Rank'] = df['Split'].rank()
    df['Total Score'] = df['Speed Rank'] + df['Bias Score'] + df['Collision Risk'] + df['RT Score']
    df['Rank'] = df['Total Score'].rank(method='min')
    return df.sort_values(by='Rank')

# ----------------------
# 🎯 Streamlit App Start
# ----------------------
st.title("🐾 Greyhound R/T Collision & Split Analyser")

# Auto-populate track list from website
st.markdown("#### ✅ Live Tracks with R/T (from thedogs.com.au)")
tracks = get_rt_tracks_today()
if not tracks:
    st.warning("No R/T-enabled tracks found today.")
    st.stop()

track_choice = st.selectbox("Select Track", tracks)

# Editable greyhound input
st.markdown("### 🐶 Enter Race Field Data")
st.caption("Use format like `G W` (Good, Wide), `E R`, or `F M`. Enter 8 dogs.")

default_data = pd.DataFrame({
    "Dog": [f"Dog {i}" for i in range(1, 9)],
    "Box": list(range(1, 9)),
    "Split": [5.10]*8,
    "R/T": ["F M"]*8
})

df_input = st.data_editor(
    default_data,
    column_config={
        "R/T": st.column_config.TextColumn("R/T (e.g. G W, E R)")
    },
    num_rows="fixed"
)

if st.button("Run Analysis"):
    try:
        ranked_df = rank_dogs(df_input.copy(), track_choice)
        st.success("✅ Analysis Complete")
        st.dataframe(ranked_df[['Dog', 'Box', 'Split', 'R/T', 'Style', 'Bias', 'Collision Risk', 'RT Score', 'Total Score', 'Rank']])
        st.markdown(f"### 🏆 Predicted Winner: **{ranked_df.iloc[0]['Dog']}** (Box {ranked_df.iloc[0]['Box']})")
    except Exception as e:
        st.error(f"Error during analysis: {e}")

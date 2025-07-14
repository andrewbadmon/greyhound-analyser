import streamlit as st
import pandas as pd
import numpy as np

# ✅ Trait-sensitive Australian tracks
trait_sensitive_tracks = [
    "Wagga", "Nowra", "Maitland", "Angle Park", "Lakeside",
    "Warragul", "The Gardens", "Albion Park", "Shepparton",
    "Dapto", "Mandurah", "Gosford"
]

# ✅ Box bias template (use same for all for now)
default_bias = {1: "Good", 2: "Fair", 3: "Fair", 4: "Risky", 5: "Risky", 6: "Fair", 7: "Good", 8: "Good"}

# ✅ R/T & start position mappings
rt_score_map = {'E': 1, 'G': 2, 'F': 3, 'S': 4, 'R': 5}
start_map = {'R': 'Railer', 'M': 'Middle', 'W': 'Wide'}
bias_score_map = {"Good": 1, "Fair": 2, "Risky": 3, "Wide Bias": 2}
win_score_map = {
    "Last Start": 0.0,
    "2 Starts Ago": 0.2,
    "3+ Starts Ago": 0.4,
    "Never": 0.6
}

# ✅ Valid R/T options (E/G/F/S/R × R/M/W)
rt_options = [f"{r} {s}" for r in rt_score_map.keys() for s in start_map.keys()]
last_win_options = list(win_score_map.keys())

# 🧠 Process R/T code like "G W"
def process_rt_trait(rt_value):
    if not isinstance(rt_value, str) or len(rt_value) < 3:
        return 3, "Middle"
    parts = rt_value.strip().upper().split()
    rating = parts[0] if parts[0] in rt_score_map else 'F'
    start = parts[1] if len(parts) > 1 and parts[1] in start_map else 'M'
    return rt_score_map[rating], start_map[start]

# 💥 Estimate collision risk based on dog styles
def assess_collision_risk(row, df):
    risk = 0
    for _, other in df.iterrows():
        if other['Dog'] != row['Dog']:
            if row['Style'] == 'Wide' and other['Box'] < row['Box'] and other['Style'] != 'Wide' and other['Split'] < row['Split']:
                risk += 1
            elif row['Style'] == 'Railer' and other['Box'] > row['Box'] and other['Style'] != 'Railer' and other['Split'] < row['Split']:
                risk += 1
    return risk

# 📊 Convert scores to win probabilities
def compute_win_probability(scores):
    inverse_scores = -np.array(scores)
    exp_scores = np.exp(inverse_scores - np.max(inverse_scores))
    probs = exp_scores / exp_scores.sum()
    return (probs * 100).round(1)

# 📈 Rank and score dogs
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

# ----------------------
# 🎯 Streamlit App Start
# ----------------------
st.title("🐾 Greyhound Collision & R/T Race Analyser")

# Track selection
track_choice = st.selectbox("Select Track", trait_sensitive_tracks)

# Initial input table
default_data = pd.DataFrame({
    "Dog": [f"Dog {i}" for i in range(1, 9)],
    "Box": list(range(1, 9)),
    "Split": [5.10]*8,
    "R/T": ["F M"]*8,
    "Last Win": ["2 Starts Ago"]*8
})

# Editable input with dropdowns
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
        st.success("✅ Analysis Complete")
        st.dataframe(results[['Dog', 'Box', 'Split', 'R/T', 'Last Win', 'Bias', 'Collision Risk', 'RT Score', 'Total Score', 'Win %', 'Rank']])
        st.markdown(f"### 🏆 Predicted Winner: **{results.iloc[0]['Dog']}** (Box {results.iloc[0]['Box']})")
    except Exception as e:
        st.error(f"Error during analysis: {e}")

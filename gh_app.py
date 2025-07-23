
import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="Greyhound Collision & Split Analysis", layout="wide")

st.title("🐾 Greyhound Collision & Split Time Analyser")

# --- Track selection with only today's R/T-supported tracks
today_tracks = [
    "Wagga", "Nowra", "Maitland", "Angle Park", "Lakeside",
    "Richmond", "Taree", "Broken Hill", "Rockhampton"
]
selected_track = st.selectbox("Select Track", options=today_tracks)

# --- Race number (for future integration of distance fetch)
race_number = st.selectbox("Select Race Number", options=list(range(1, 13)))

# --- Dropdown for how to handle missing 1st Section times
split_handling_method = st.selectbox(
    "How to handle missing 1st Section times?",
    ["Use Conservative Default (5.60)", "Estimate from Similar Dogs", "Exclude from Win Ranking"]
)

# --- Greyhound input table
st.markdown("### 🐶 Enter Greyhound Data")

num_dogs = 8
default_columns = ["Dog", "Box", "R/T", "Split"]
data = pd.DataFrame("", index=range(num_dogs), columns=default_columns)
data["Box"] = list(range(1, 9))

edited_data = st.data_editor(data, num_rows="fixed")

# --- Process the table
df = edited_data.copy()
df["Box"] = df["Box"].astype(int)
split_col = []

# --- Handle missing splits
imputed_flags = []
for idx, row in df.iterrows():
    split_val = row["Split"]
    try:
        split = float(split_val)
        imputed_flags.append("")
    except:
        if split_handling_method == "Use Conservative Default (5.60)":
            split = 5.60
            imputed_flags.append("⚠️")
        elif split_handling_method == "Estimate from Similar Dogs":
            split = 5.50 + 0.05 * (idx % 3)  # Dummy logic for estimation
            imputed_flags.append("⚠️")
        else:
            split = np.nan
            imputed_flags.append("⚠️")
    split_col.append(round(split, 2) if not np.isnan(split) else np.nan)

df["Split"] = split_col
df["⚠️"] = imputed_flags

# --- Auto-highlight: Fastest and Highest Risk
highlight_fastest = df["Split"].min()
highlight_fastest_idx = df["Split"].idxmin()

# --- Collision Risk ASCII Arrows
def get_trait_code(trait_str):
    try:
        _, pos = trait_str.strip().split()
        return pos
    except:
        return "M"

ascii_boxes = ["Box {:<2}".format(i + 1) for i in range(8)]
ascii_names = ["{:<8}".format(df.iloc[i]["Dog"]) for i in range(8)]
ascii_traits = ["[{}]".format(get_trait_code(df.iloc[i]["R/T"])) for i in range(8)]

movement_arrows = [" " * 8 for _ in range(8)]

for i in range(8):
    trait_i = get_trait_code(df.iloc[i]["R/T"])
    split_i = df.iloc[i]["Split"]
    for j in range(8):
        if i == j:
            continue
        trait_j = get_trait_code(df.iloc[j]["R/T"])
        split_j = df.iloc[j]["Split"]

        if np.isnan(split_i) or np.isnan(split_j):
            continue

        if trait_j == "W" and j < i and split_j < split_i:
            movement_arrows[j] = "←------"
        elif trait_j == "R" and j > i and split_j < split_i:
            movement_arrows[j] = "------→"
        elif abs(j - i) == 1 and abs(split_j - split_i) <= 0.1:
            movement_arrows[j] = "  ↔   "

# --- Final display
st.markdown("### 📊 Greyhound Overview")

def highlight_row(row):
    style = ""
    if row.name == highlight_fastest_idx:
        style = "background-color: #d1ffd1"  # Light green
    return [style] * len(row)

rounded_df = df[["Dog", "Box", "R/T", "Split", "⚠️"]].round(2)
st.dataframe(rounded_df.style.apply(highlight_row, axis=1), use_container_width=True)

# --- ASCII Collision Map
st.markdown("### 🚨 ASCII Collision Map")

ascii_display = [
    "  ".join(ascii_boxes),
    "  ".join(ascii_names),
    "  ".join(ascii_traits),
    "  ".join(movement_arrows)
]

for line in ascii_display:
    st.text(line)

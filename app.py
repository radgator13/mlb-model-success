import streamlit as st
import pandas as pd

# Load the comparison data
@st.cache_data
def load_data():
    df = pd.read_csv("comparison.csv")
    df["GameDate"] = pd.to_datetime(df["GameDate"])
    return df

df = load_data()

# Sidebar: Game date dropdown
st.sidebar.title("📅 Filter Games")
available_dates = sorted(df["GameDate"].dt.date.unique())
selected_date = st.sidebar.selectbox("Select Game Date", available_dates)

# Filter data
filtered = df[df["GameDate"].dt.date == selected_date]

st.title("⚾ MLB Odds Accuracy Dashboard")
st.subheader(f"Games on {selected_date}")

# Display table
st.dataframe(filtered[[
    "HomeTeam", "AwayTeam", "HomeScore", "AwayScore",
    "Winner", "Favorite", "CorrectSide",
    "OpeningPointSpread", "OpeningOverUnder",
    "TotalRuns", "OverHit", "UnderHit", "PushTotal"
]])

# Summary Stats
st.markdown("## 📊 Summary")
total_games = len(filtered)
correct_ml = filtered["CorrectSide"].sum()
over_hits = filtered["OverHit"].sum()
under_hits = filtered["UnderHit"].sum()
pushes = filtered["PushTotal"].sum()

col1, col2, col3 = st.columns(3)
col1.metric("Games Played", total_games)
col2.metric("Correct Moneyline", f"{correct_ml} ({correct_ml / total_games:.0%})")
col3.metric("Pushes", pushes)

col4, col5 = st.columns(2)
col4.metric("Over Hit", over_hits)
col5.metric("Under Hit", under_hits)

# Over/Under Bar Chart
st.markdown("### 🎯 Over/Under Result")
ou_counts = {
    "Over Hit": over_hits,
    "Under Hit": under_hits,
    "Push": pushes
}
ou_df = pd.DataFrame.from_dict(ou_counts, orient='index', columns=["Games"])
st.bar_chart(ou_df)

# Total Runs vs Over/Under Line Chart
st.markdown("### 📈 Total Runs vs Over/Under")
line_df = filtered[["HomeTeam", "AwayTeam", "TotalRuns", "OpeningOverUnder"]].copy()
line_df["Matchup"] = line_df["AwayTeam"] + " @ " + line_df["HomeTeam"]
line_df = line_df.set_index("Matchup")
st.line_chart(line_df[["TotalRuns", "OpeningOverUnder"]])

# Calculate actual spread (Home - Away)
filtered["ActualSpread"] = filtered["HomeScore"] - filtered["AwayScore"]

# Determine spread coverage outcome
def determine_spread_coverage(row):
    if row["Favorite"] == "Home":
        return "Covered" if row["ActualSpread"] > row["OpeningPointSpread"] else "Not Covered"
    elif row["Favorite"] == "Away":
        return "Covered" if -row["ActualSpread"] > row["OpeningPointSpread"] else "Not Covered"
    return "N/A"

filtered["SpreadCovered"] = filtered.apply(determine_spread_coverage, axis=1)

# Simple binary coverage for chart
st.markdown("### 🟢 Favorite Spread Coverage by Game")

filtered["SpreadCoveredResult"] = filtered["SpreadCovered"].map({
    "Covered": 1, "Not Covered": 0
})

coverage_df = filtered[["AwayTeam", "HomeTeam", "SpreadCoveredResult", "SpreadCovered"]].copy()
coverage_df["Matchup"] = coverage_df["AwayTeam"] + " @ " + coverage_df["HomeTeam"]
coverage_df = coverage_df.set_index("Matchup")

st.bar_chart(coverage_df["SpreadCoveredResult"])

# Optional: Table of matchups and spread result
st.markdown("### 📋 Spread Coverage Breakdown")
st.dataframe(
    coverage_df[["SpreadCovered"]].rename(columns={"SpreadCovered": "Favorite ATS Result"})
)

# Footer
st.markdown("---")
st.caption("Built with ❤️ using Streamlit • MLB Odds Dashboard")

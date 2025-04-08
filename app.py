import streamlit as st
import pandas as pd
import altair as alt

# --- Load data ---
@st.cache_data
def load_data():
    df = pd.read_csv("comparison.csv")
    df["GameDate"] = pd.to_datetime(df["GameDate"])
    return df

df = load_data()

# --- Sidebar filters ---
st.sidebar.title("📅 Filter Games")
dates = sorted(df["GameDate"].dt.date.unique())
selected_date = st.sidebar.selectbox("Select Game Date", dates)

teams = sorted(set(df["HomeTeam"].unique()).union(set(df["AwayTeam"].unique())))
selected_team = st.sidebar.selectbox("Filter by Team (optional)", ["All"] + teams)

# --- Filter data ---
filtered = df[df["GameDate"].dt.date == selected_date]
if selected_team != "All":
    filtered = filtered[(filtered["HomeTeam"] == selected_team) | (filtered["AwayTeam"] == selected_team)]

# --- Determine spread coverage ---
filtered["ActualSpread"] = filtered["HomeScore"] - filtered["AwayScore"]

def determine_spread_coverage(row):
    if row["Favorite"] == "Home":
        return "Covered" if row["ActualSpread"] > row["OpeningPointSpread"] else "Not Covered"
    elif row["Favorite"] == "Away":
        return "Covered" if -row["ActualSpread"] > row["OpeningPointSpread"] else "Not Covered"
    return "N/A"

filtered["SpreadCovered"] = filtered.apply(determine_spread_coverage, axis=1)
filtered["SpreadCoveredResult"] = filtered["SpreadCovered"].map({"Covered": 1, "Not Covered": 0})

# --- Dashboard Header ---
st.title("⚾ MLB Odds Accuracy Dashboard")
st.subheader(f"Games on {selected_date}")
if selected_team != "All":
    st.caption(f"Filtered to games with: `{selected_team}`")

# --- Main game table ---
st.dataframe(filtered[[
    "HomeTeam", "AwayTeam", "HomeScore", "AwayScore",
    "Winner", "Favorite", "CorrectSide",
    "OpeningPointSpread", "OpeningOverUnder",
    "TotalRuns", "OverHit", "UnderHit", "PushTotal", "SpreadCovered"
]])

# --- Summary ---
st.markdown("## 📊 Summary Stats")

total = len(filtered)
correct_ml = filtered["CorrectSide"].sum()
over_hits = filtered["OverHit"].sum()
under_hits = filtered["UnderHit"].sum()
pushes = filtered["PushTotal"].sum()
spread_covered = (filtered["SpreadCovered"] == "Covered").sum()

col1, col2, col3 = st.columns(3)
col1.metric("Games Played", total)
col2.metric("Correct Moneyline", f"{correct_ml} ({correct_ml / total:.0%})")
col3.metric("Favorite Covered", spread_covered)

col4, col5 = st.columns(2)
col4.metric("Over Hit", over_hits)
col5.metric("Under Hit", under_hits)
#
# --- Over/Under Bar Chart ---
st.markdown("### 🎯 Over/Under Results")
ou_df = pd.DataFrame({
    "Result": ["Over", "Under", "Push"],
    "Games": [over_hits, under_hits, pushes]
})
st.bar_chart(ou_df.set_index("Result"))

# --- Total Runs Line Chart ---
st.markdown("### 📈 Total Runs vs Over/Under")
line_df = filtered.copy()
line_df["Matchup"] = line_df["AwayTeam"] + " @ " + line_df["HomeTeam"]
line_df = line_df.set_index("Matchup")
st.line_chart(line_df[["TotalRuns", "OpeningOverUnder"]])

# --- Spread Coverage Color Chart ---
st.markdown("### 🟢 Spread Coverage by Game")

spread_chart_df = filtered.copy()
spread_chart_df["Matchup"] = spread_chart_df["AwayTeam"] + " @ " + spread_chart_df["HomeTeam"]
spread_chart_df["Result"] = spread_chart_df["SpreadCovered"]

spread_bar = alt.Chart(spread_chart_df).mark_bar().encode(
    x=alt.X("Matchup", sort=None),
    y=alt.Y("SpreadCoveredResult", title="Covered (1 = Yes, 0 = No)"),
    color=alt.Color("Result", scale=alt.Scale(domain=["Covered", "Not Covered"], range=["green", "red"])),
    tooltip=["Matchup", "Result"]
).properties(height=400)

st.altair_chart(spread_bar, use_container_width=True)

# --- Weekly Summary ---
st.markdown("## 📅 Weekly Aggregate Summary")

weekly_df = df.copy()
weekly_df["Week"] = weekly_df["GameDate"].dt.to_period("W").astype(str)
weekly_df["CorrectSide"] = weekly_df["CorrectSide"].astype(int)

weekly_summary = weekly_df.groupby("Week").agg({
    "CorrectSide": "mean",
    "GameDate": "count",
    "OverHit": "sum",
    "UnderHit": "sum"
}).rename(columns={"CorrectSide": "Moneyline Accuracy", "GameDate": "Games"})

st.dataframe(weekly_summary.style.format({"Moneyline Accuracy": "{:.0%}"}))

# Footer
st.markdown("---")
st.caption("Built with ❤️ using Streamlit • MLB Model Success")

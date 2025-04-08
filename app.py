import streamlit as st
import pandas as pd
import altair as alt

# Load the comparison CSV
@st.cache_data
def load_data():
    df = pd.read_csv("comparison.csv")
    df["GameDate"] = pd.to_datetime(df["GameDate"])
    return df

df = load_data()

# Sidebar filters
st.sidebar.title("📅 Filter Games")
dates = sorted(df["GameDate"].dt.date.unique())
selected_date = st.sidebar.selectbox("Select Game Date", dates)

teams = sorted(set(df["HomeTeam"].unique()).union(df["AwayTeam"].unique()))
selected_team = st.sidebar.selectbox("Filter by Team (optional)", ["All"] + teams)

# Filter data
filtered = df[df["GameDate"].dt.date == selected_date]
if selected_team != "All":
    filtered = filtered[(filtered["HomeTeam"] == selected_team) | (filtered["AwayTeam"] == selected_team)]

# Spread result calculation
filtered["ActualSpread"] = filtered["HomeScore"] - filtered["AwayScore"]

def determine_spread_coverage(row):
    if row["Favorite"] == "Home":
        return "Covered" if row["ActualSpread"] > row["OpeningPointSpread"] else "Not Covered"
    elif row["Favorite"] == "Away":
        return "Covered" if -row["ActualSpread"] > row["OpeningPointSpread"] else "Not Covered"
    return "N/A"

filtered["SpreadCovered"] = filtered.apply(determine_spread_coverage, axis=1)

# Over/Under outcome label
filtered["OU_Result"] = filtered.apply(
    lambda row: "Over" if row["OverHit"]
    else "Under" if row["UnderHit"]
    else "Push", axis=1
)

# Dashboard Header
st.title("⚾ MLB Odds Accuracy Dashboard")
st.subheader(f"Games on {selected_date}")
if selected_team != "All":
    st.caption(f"Filtered to games with: `{selected_team}`")

# === GAME TABLE ===
st.markdown("## 🧾 Game Details Table")

# Rename + clean columns
renamed = filtered[[
    "HomeTeam", "AwayTeam", "HomeScore", "AwayScore",
    "Winner", "Favorite", "CorrectSide",
    "OpeningPointSpread", "OpeningOverUnder",
    "TotalRuns", "OverHit", "UnderHit", "PushTotal", "SpreadCovered"
]].rename(columns={
    "HomeTeam": "Home",
    "AwayTeam": "Away",
    "HomeScore": "H",
    "AwayScore": "A",
    "CorrectSide": "ML ✓",
    "OpeningPointSpread": "Spread",
    "OpeningOverUnder": "O/U",
    "TotalRuns": "Final Total",
    "OverHit": "Over?",
    "UnderHit": "Under?",
    "PushTotal": "Push?",
    "SpreadCovered": "Covered?",
    "Favorite": "Fav",
    "Winner": "Win"
})

# Multiselect columns
default_cols = ["Home", "Away", "H", "A", "Win", "Fav", "ML ✓", "Spread", "O/U", "Final Total", "Covered?"]
columns_to_show = st.multiselect("Choose columns to display:", options=renamed.columns.tolist(), default=default_cols)

# Display full-width table
st.dataframe(renamed[columns_to_show], use_container_width=True)

# === SUMMARY ===
st.markdown("## 📊 Summary Stats")
total = len(filtered)
correct_ml = filtered["CorrectSide"].sum()
over_hits = filtered["OverHit"].sum()
under_hits = filtered["UnderHit"].sum()
pushes = filtered["PushTotal"].sum()
spread_covered = (filtered["SpreadCovered"] == "Covered").sum()

col1, col2, col3 = st.columns(3)
col1.metric("Games", total)
col2.metric("Correct ML", f"{correct_ml} ({correct_ml / total:.0%})")
col3.metric("Spread Covered", spread_covered)

col4, col5 = st.columns(2)
col4.metric("Over Hit", over_hits)
col5.metric("Under Hit", under_hits)

# === OVER/UNDER BAR CHART BY GAME ===
st.markdown("### 🎯 Over/Under by Game")

ou_df = filtered.copy()
ou_df["Matchup"] = ou_df["AwayTeam"] + " @ " + ou_df["HomeTeam"]
ou_df["Indicator"] = 1

ou_chart = alt.Chart(ou_df).mark_bar().encode(
    x=alt.X("Matchup:N", sort=None),
    y=alt.Y("Indicator:Q", title="Outcome"),
    color=alt.Color("OU_Result:N", scale=alt.Scale(
        domain=["Over", "Under", "Push"],
        range=["red", "blue", "gray"]
    )),
    tooltip=["Matchup", "OU_Result"]
).properties(height=400)

st.altair_chart(ou_chart, use_container_width=True)

# === SPREAD COVERAGE BAR CHART ===
st.markdown("### 🟢 Spread Coverage by Game")

spread_df = filtered.copy()
spread_df["Matchup"] = spread_df["AwayTeam"] + " @ " + spread_df["HomeTeam"]
spread_df["Result"] = spread_df["SpreadCovered"]
spread_df["CoveredNumeric"] = 1

spread_chart = alt.Chart(spread_df).mark_bar().encode(
    x=alt.X("Matchup:N", sort=None),
    y=alt.Y("CoveredNumeric:Q", title="Game Present (Color = Result)"),
    color=alt.Color("Result:N", scale=alt.Scale(
        domain=["Covered", "Not Covered"],
        range=["green", "red"]
    )),
    tooltip=["Matchup", "Result"]
).properties(height=400)

st.altair_chart(spread_chart, use_container_width=True)
# === WEEKLY SUMMARY ===
st.markdown("## 📅 Weekly Aggregate Summary")

weekly_df = df.copy()
weekly_df["Week"] = weekly_df["GameDate"].dt.to_period("W").astype(str)
weekly_df["CorrectSide"] = weekly_df["CorrectSide"].astype(int)

weekly_summary = weekly_df.groupby("Week").agg({
    "CorrectSide": "mean",
    "GameDate": "count",
    "OverHit": "sum",
    "UnderHit": "sum"
}).rename(columns={
    "CorrectSide": "Moneyline Accuracy",
    "GameDate": "Games"
})

st.dataframe(weekly_summary.style.format({"Moneyline Accuracy": "{:.0%}"}))



# Footer
st.markdown("---")
st.caption("Built with ❤️ using Streamlit • MLB Model Success")

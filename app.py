import streamlit as st
import pandas as pd
import altair as alt

# Full-width layout
st.set_page_config(layout="wide")

# === GLOBAL CENTERING FOR TABLES ===
st.markdown("""
    <style>
        table td, table th {
            text-align: center !important;
        }
    </style>
""", unsafe_allow_html=True)

# === SECTION TITLE HELPER ===
def section_title(title: str):
    st.markdown(f"<h3 style='text-align: center;'>{title}</h3>", unsafe_allow_html=True)

# === TABLE STYLE HELPER ===
def styled_table(df):
    return df.style.set_properties(**{
        'text-align': 'center'
    }).set_table_styles([
        {'selector': 'th', 'props': [('text-align', 'center')]},
        {'selector': 'td', 'props': [('text-align', 'center')]}
    ])

# === LOAD DATA ===
@st.cache_data
def load_data():
    df = pd.read_csv("comparison.csv")
    df["GameDate"] = pd.to_datetime(df["GameDate"])
    df["GameId"] = df["GameId"].astype(str)
    df = df.drop_duplicates(subset=["GameId"])
    return df

df = load_data()

# === FILTERS AT TOP ===
st.markdown("### 📅 Filter Games")
col1, col2 = st.columns(2)
with col1:
    selected_date = st.selectbox("Select Game Date", sorted(df["GameDate"].dt.date.unique()))
with col2:
    teams = sorted(set(df["HomeTeam"].unique()).union(df["AwayTeam"].unique()))
    selected_team = st.selectbox("Filter by Team (optional)", ["All"] + teams)

# === FILTERED DATA ===
filtered = df[df["GameDate"].dt.date == selected_date]
if selected_team != "All":
    filtered = filtered[(filtered["HomeTeam"] == selected_team) | (filtered["AwayTeam"] == selected_team)]

# === ENRICH FILTERED DATA ===
filtered["ActualSpread"] = filtered["HomeScore"] - filtered["AwayScore"]
filtered["SpreadCovered"] = filtered.apply(
    lambda row: (
        "Home Covered" if row["Favorite"] == "Home" and row["ActualSpread"] > row["OpeningPointSpread"]
        else "Away Covered" if row["Favorite"] == "Away" and -row["ActualSpread"] > row["OpeningPointSpread"]
        else "Home Missed" if row["Favorite"] == "Home"
        else "Away Missed"
    ), axis=1
)
filtered["OU_Result"] = filtered.apply(
    lambda row: "Over" if row["OverHit"] else "Under" if row["UnderHit"] else "Push",
    axis=1
)

# === GAME DETAILS TABLE ===
section_title("📋 Game Details Table")
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

default_cols = ["Home", "Away", "H", "A", "Win", "Fav", "ML ✓", "Spread", "O/U", "Final Total", "Covered?"]
columns_to_show = st.multiselect("Choose columns to display:", options=renamed.columns.tolist(), default=default_cols)

format_dict = {"Spread": "{:.2f}", "O/U": "{:.2f}"}
styled_main = renamed[columns_to_show].style \
    .format(format_dict) \
    .set_properties(**{'text-align': 'center'}) \
    .set_table_styles([
        {'selector': 'th', 'props': [('text-align', 'center')]},
        {'selector': 'td', 'props': [('text-align', 'center')]}
    ])
st.table(styled_main)

# === SUMMARY METRICS ===
section_title("📊 Summary Stats")
total = len(filtered)
correct_ml = filtered["CorrectSide"].sum()
over_hits = filtered["OverHit"].sum()
under_hits = filtered["UnderHit"].sum()
spread_covered = (filtered["SpreadCovered"].str.contains("Covered")).sum()

col1, col2, col3 = st.columns(3)
col1.metric("Games", total)
col2.metric("Correct ML", f"{correct_ml} ({correct_ml / total:.0%})")
col3.metric("Spread Covered", spread_covered)

col4, col5 = st.columns(2)
col4.metric("Over Hit", over_hits)
col5.metric("Under Hit", under_hits)

# === OVER/UNDER BY GAME ===
section_title("🎯 Over/Under by Game")
ou_df = filtered.copy()
ou_df["Matchup"] = ou_df["AwayTeam"] + " @ " + ou_df["HomeTeam"]
ou_df["Indicator"] = 1
ou_chart = alt.Chart(ou_df).mark_bar().encode(
    x=alt.X("Matchup:N", sort=None),
    y=alt.Y("Indicator:Q", title="Outcome"),
    color=alt.Color("OU_Result:N", scale=alt.Scale(domain=["Over", "Under", "Push"], range=["red", "blue", "gray"])),
    tooltip=["Matchup", "OU_Result"]
).properties(height=400)
st.altair_chart(ou_chart, use_container_width=True)

# === SPREAD COVERAGE BY GAME ===
section_title("🟢 Spread Coverage by Game")
spread_df = filtered.copy()
spread_df["Matchup"] = spread_df["AwayTeam"] + " @ " + spread_df["HomeTeam"]
spread_df["Result"] = spread_df["SpreadCovered"]
spread_df["CoveredNumeric"] = 1
spread_chart = alt.Chart(spread_df).mark_bar().encode(
    x=alt.X("Matchup:N", sort=None),
    y=alt.Y("CoveredNumeric:Q", title="Game Present (Color = Result)"),
    color=alt.Color("Result:N", scale=alt.Scale(
        domain=["Home Covered", "Away Covered", "Home Missed", "Away Missed"],
        range=["green", "green", "red", "red"]
    )),
    tooltip=["Matchup", "Result"]
).properties(height=400)
st.altair_chart(spread_chart, use_container_width=True)

# === AGGREGATES ===
section_title("📅 Weekly + Overall Analysis")
all_df = df.copy()
all_df["Week"] = all_df["GameDate"].dt.to_period("W").astype(str)
all_df["CorrectSide"] = all_df["CorrectSide"].astype(int)
all_df["ActualSpread"] = all_df["HomeScore"] - all_df["AwayScore"]

# Spread and total result labels
all_df["SpreadCovered"] = all_df.apply(
    lambda row: (
        "Home Covered" if row["Favorite"] == "Home" and row["ActualSpread"] > row["OpeningPointSpread"]
        else "Away Covered" if row["Favorite"] == "Away" and -row["ActualSpread"] > row["OpeningPointSpread"]
        else "Home Missed" if row["Favorite"] == "Home"
        else "Away Missed"
    ), axis=1
)
all_df["TotalResult"] = all_df.apply(
    lambda row: (
        "Over Home" if row["OverHit"] and row["Favorite"] == "Home"
        else "Over Away" if row["OverHit"] and row["Favorite"] == "Away"
        else "Under Home" if row["UnderHit"] and row["Favorite"] == "Home"
        else "Under Away"
    ), axis=1
)

# Weekly summary
weekly_raw = all_df.groupby("Week").agg({
    "CorrectSide": "mean",
    "GameDate": "count",
    "OverHit": "sum",
    "UnderHit": "sum"
}).rename(columns={"CorrectSide": "ML_Accuracy", "GameDate": "Games"})

weekly_display = weekly_raw.copy()
weekly_display["Moneyline Accuracy"] = (weekly_display["ML_Accuracy"] * 100).round().astype(int).astype(str) + "%"
weekly_display = weekly_display[["Moneyline Accuracy", "Games", "OverHit", "UnderHit"]]
st.table(styled_table(weekly_display))

# === OVERALL TOTALS ===
section_title("🧮 Overall Totals Across All Weeks")
total_games_all = weekly_raw["Games"].sum()
correct_pct_all = (weekly_raw["ML_Accuracy"] * weekly_raw["Games"]).sum() / total_games_all
total_overs = weekly_raw["OverHit"].sum()
total_unders = weekly_raw["UnderHit"].sum()
over_pct = total_overs / total_games_all
under_pct = total_unders / total_games_all

totals_df = pd.DataFrame({
    "Games": [total_games_all],
    "ML Accuracy": [f"{correct_pct_all:.0%}"],
    "Over Hit": [f"{total_overs} ({over_pct:.0%})"],
    "Under Hit": [f"{total_unders} ({under_pct:.0%})"]
}, index=["Total"])
st.table(styled_table(totals_df))

# === SPREAD SUMMARY ===
section_title("📐 Spread Coverage Summary")
spread_counts = all_df["SpreadCovered"].value_counts()
spread_total = spread_counts.sum()
spread_summary = spread_counts.reset_index()
spread_summary.columns = ["Outcome", "Games"]
spread_summary["%"] = (spread_summary["Games"] / spread_total).apply(lambda x: f"{x:.0%}")
st.table(styled_table(spread_summary))

# === TOTAL RESULT SUMMARY ===
section_title("🌡️ Total Results by Favorite")
total_counts = all_df["TotalResult"].value_counts()
total_total = total_counts.sum()
total_summary = total_counts.reset_index()
total_summary.columns = ["Outcome", "Games"]
total_summary["%"] = (total_summary["Games"] / total_total).apply(lambda x: f"{x:.0%}")
st.table(styled_table(total_summary))

# === FOOTER ===
st.markdown("---")
st.caption("Built with ❤️ using Streamlit • MLB Model Success")

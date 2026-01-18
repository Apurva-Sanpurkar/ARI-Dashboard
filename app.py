import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np

# ================= CONFIG =================
st.set_page_config(
    page_title="Authentication Resilience Intelligence (ARI)",
    layout="wide"
)

DATA_PATH = "data_processed/ARI_final_district_final.csv"

# ================= LOAD DATA =================
@st.cache_data
def load_data():
    df = pd.read_csv(DATA_PATH)

    if "MonthDate" in df.columns:
        df["MonthDate"] = pd.to_datetime(df["MonthDate"], errors="coerce")

    for col in ["ARI", "BUR", "BUD", "AWF", "MAF_raw"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    for col in ["state", "district", "Risk", "MonthName"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()

    return df.dropna(subset=["ARI", "state", "district"])

df = load_data()

# ================= SIDEBAR FILTERS =================
st.sidebar.title("Filters")

states = ["All"] + sorted(df["state"].unique())
risks = ["All"] + sorted(df["Risk"].unique())

sel_state = st.sidebar.selectbox("State", states)
sel_risk = st.sidebar.selectbox("Risk Category", risks)
district_search = st.sidebar.text_input("District Search")

df_f = df.copy()
if sel_state != "All":
    df_f = df_f[df_f["state"] == sel_state]
if sel_risk != "All":
    df_f = df_f[df_f["Risk"] == sel_risk]
if district_search.strip():
    df_f = df_f[df_f["district"].str.contains(district_search, case=False, na=False)]

# ================= HELPERS =================
def show_kpis(d):
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Average ARI", round(d["ARI"].mean(), 3))
    c2.metric("High Risk", int((d["Risk"] == "High").sum()))
    c3.metric("Medium Risk", int((d["Risk"] == "Medium").sum()))
    c4.metric("Low Risk", int((d["Risk"] == "Low").sum()))

def explain_district(row):
    reasons = []
    if row["BUR"] > df["BUR"].median():
        reasons.append("outdated biometrics")
    if row["BUD"] < df["BUD"].median():
        reasons.append("low update density")
    if row["AWF"] > df["AWF"].median():
        reasons.append("high authentication load")
    return ", ".join(reasons) if reasons else "no dominant driver"

def compute_early_warning(d):
    d = d.sort_values(["state", "district", "MonthDate"]).copy()
    d["ARI_prev"] = d.groupby(["state", "district"])["ARI"].shift(1)
    d["ARI_change_pct"] = (d["ARI"] - d["ARI_prev"]) / d["ARI_prev"]
    d["Early_Warning"] = d["ARI_change_pct"] < -0.15
    return d

def risk_transition_flag(d):
    d = d.sort_values(["state", "district", "MonthDate"]).copy()
    d["Risk_prev"] = d.groupby(["state", "district"])["Risk"].shift(1)
    d["Transition"] = (d["Risk_prev"] == "Medium") & (d["Risk"] == "High")
    return d

def compute_priority_score(d):
    """
    Composite impact score:
    - ARI (lower = worse)
    - BUR (higher = worse)
    - BUD (lower = worse)
    - Population proxy via AWF
    """
    s = d.copy()

    s["ARI_norm"] = 1 - (s["ARI"] - s["ARI"].min()) / (s["ARI"].max() - s["ARI"].min())
    s["BUR_norm"] = (s["BUR"] - s["BUR"].min()) / (s["BUR"].max() - s["BUR"].min())
    s["BUD_norm"] = 1 - (s["BUD"] - s["BUD"].min()) / (s["BUD"].max() - s["BUD"].min())
    s["AWF_norm"] = (s["AWF"] - s["AWF"].min()) / (s["AWF"].max() - s["AWF"].min())

    s["Priority_Score"] = (
        0.4 * s["ARI_norm"]
        + 0.25 * s["BUR_norm"]
        + 0.2 * s["BUD_norm"]
        + 0.15 * s["AWF_norm"]
    )

    return s.sort_values("Priority_Score", ascending=False)

def simple_forecast(d):
    """
    Safe forecast: rolling trend extrapolation
    """
    d = d.sort_values(["state", "district", "MonthDate"]).copy()
    d["ARI_trend"] = d.groupby(["state", "district"])["ARI"].diff()
    d["Forecast_ARI_Next"] = d["ARI"] + d["ARI_trend"].fillna(0)
    return d

# ================= NAVIGATION =================
page = st.sidebar.radio(
    "Navigate",
    [
        "Home",
        "National Overview",
        "High Risk Ranking",
        "Explainability",
        "Early Warning System",
        "Priority Intelligence",
        "Action Planner",
    ],
)

# ================= HOME =================
if page == "Home":
    st.title("Authentication Resilience Intelligence Platform")

    st.markdown("""
This system converts Aadhaar authentication data into **preventive intelligence**.

It answers:
- Where will failures occur?
- Why are they occurring?
- Where should UIDAI intervene first?
""")

    show_kpis(df_f)

# ================= NATIONAL OVERVIEW =================
elif page == "National Overview":
    st.title("National Risk Overview")
    show_kpis(df_f)

    risk_counts = df_f["Risk"].value_counts().reset_index()
    risk_counts.columns = ["Risk", "Count"]

    fig = px.pie(
        risk_counts,
        names="Risk",
        values="Count",
        hole=0.55,
        color="Risk",
        color_discrete_map={
            "High": "#c0392b",
            "Medium": "#f39c12",
            "Low": "#27ae60",
        },
    )
    st.plotly_chart(fig, width="stretch")

    st.subheader("Lowest ARI Districts")
    st.dataframe(
        df_f.sort_values("ARI").head(20)[
            ["state", "district", "ARI", "Risk", "BUR", "BUD"]
        ],
        width="stretch",
    )

# ================= HIGH RISK RANKING =================
elif page == "High Risk Ranking":
    st.title("High Risk Ranking")

    top = df_f.sort_values("ARI").head(15)
    fig = px.bar(
        top,
        x="ARI",
        y="district",
        orientation="h",
        color="Risk",
        text="ARI",
    )
    fig.update_traces(texttemplate="%{text:.3f}", textposition="outside")
    st.plotly_chart(fig, width="stretch")

# ================= EXPLAINABILITY =================
elif page == "Explainability":
    st.title("Explainability")

    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(
            px.scatter(df_f, x="BUR", y="ARI", color="Risk"),
            width="stretch",
        )
    with col2:
        st.plotly_chart(
            px.scatter(df_f, x="BUD", y="ARI", color="Risk"),
            width="stretch",
        )

    worst = df_f.sort_values("ARI").head(15).copy()
    worst["Primary Driver"] = worst.apply(explain_district, axis=1)

    st.dataframe(
        worst[
            ["state", "district", "ARI", "Risk", "Primary Driver"]
        ],
        width="stretch",
    )

# ================= EARLY WARNING =================
elif page == "Early Warning System":
    st.title("Early Warning Monitor")

    ew = compute_early_warning(df)
    sudden = ew[ew["Early_Warning"] == True]

    st.subheader("Sudden ARI Degradation")
    if len(sudden) == 0:
        st.info("No sudden drops detected.")
    else:
        st.dataframe(
            sudden[
                ["state", "district", "MonthName", "ARI_prev", "ARI", "ARI_change_pct"]
            ],
            width="stretch",
        )

    trans = risk_transition_flag(df)
    st.subheader("Medium to High Risk Transitions")
    st.dataframe(
        trans[trans["Transition"] == True][
            ["state", "district", "MonthName", "ARI", "Risk"]
        ],
        width="stretch",
    )

# ================= PRIORITY INTELLIGENCE =================
elif page == "Priority Intelligence":
    st.title("Priority Intelligence Engine")

    scored = compute_priority_score(df_f)

    fig = px.bar(
        scored.head(15),
        x="Priority_Score",
        y="district",
        orientation="h",
        text="Priority_Score",
    )
    fig.update_traces(texttemplate="%{text:.2f}", textposition="outside")
    st.plotly_chart(fig, width="stretch")

    st.dataframe(
        scored.head(25)[
            ["state", "district", "Priority_Score", "ARI", "Risk"]
        ],
        width="stretch",
    )

# ================= ACTION PLANNER =================
elif page == "Action Planner":
    st.title("Action Planner")

    scored = compute_priority_score(df_f)
    forecasted = simple_forecast(scored)

    forecasted["Recommended Action"] = np.where(
        forecasted["Forecast_ARI_Next"] < forecasted["ARI"],
        "Immediate biometric update drive",
        "Monitor and optimize throughput",
    )

    st.dataframe(
        forecasted.head(25)[
            ["state", "district", "ARI", "Forecast_ARI_Next", "Risk", "Recommended Action"]
        ],
        width="stretch",
    )

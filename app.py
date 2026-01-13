import streamlit as st
import pandas as pd
import plotly.express as px
from fpdf import FPDF
from io import BytesIO

# ---------------- CONFIG ----------------
st.set_page_config(page_title="ARI Dashboard", page_icon="📊", layout="wide")

DATA_PATH = "data_processed/ARI_final_district_final.csv"



# ---------------- LOAD DATA ----------------
@st.cache_data
def load_data():
    df = pd.read_csv(DATA_PATH)

    # Date conversion
    if "MonthDate" in df.columns:
        df["MonthDate"] = pd.to_datetime(df["MonthDate"], errors="coerce")

    # Numeric conversion safety
    for col in ["ARI", "BUR", "BUD", "AWF", "MAF_raw"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Text cleanup
    for col in ["state", "district", "Risk", "MonthName"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()

    return df


# ---------------- PDF HELPERS ----------------
def safe_txt(x, max_len=60):
    x = "" if x is None else str(x)
    x = x.replace("\n", " ").replace("\r", " ").strip()
    if len(x) > max_len:
        x = x[:max_len] + "..."
    return x


def create_pdf_report(df_report, title="ARI Dashboard Report"):
    """
    Safe PDF generator:
    - prevents 'Not enough horizontal space'
    - prevents bytearray encode errors
    """
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # Title
    pdf.set_font("Arial", "B", 16)
    pdf.multi_cell(0, 10, title, align="C")
    pdf.ln(2)

    # Summary
    pdf.set_font("Arial", "", 12)

    if len(df_report) > 0:
        avg_ari = float(df_report["ARI"].mean())
        high = int((df_report["Risk"] == "High").sum()) if "Risk" in df_report.columns else 0
        med = int((df_report["Risk"] == "Medium").sum()) if "Risk" in df_report.columns else 0
        low = int((df_report["Risk"] == "Low").sum()) if "Risk" in df_report.columns else 0
    else:
        avg_ari, high, med, low = 0.0, 0, 0, 0

    pdf.multi_cell(
        0,
        7,
        "This report summarizes ARI (Authentication Resilience Index).\n"
        "Interpretation:\n"
        "- Lower ARI  => Higher authentication vulnerability\n"
        "- Higher ARI => More resilient authentication system\n\n"
        f"Total Records: {len(df_report)}\n"
        f"Average ARI: {avg_ari:.3f}\n"
        f"High Risk Count: {high}\n"
        f"Medium Risk Count: {med}\n"
        f"Low Risk Count: {low}\n"
    )
    pdf.ln(2)

    # Top 20 worst districts
    pdf.set_font("Arial", "B", 12)
    pdf.multi_cell(0, 8, "Top 20 Worst Districts (Lowest ARI)")
    pdf.ln(1)

    pdf.set_font("Arial", "", 9)

    if len(df_report) > 0:
        top20 = df_report.sort_values("ARI", ascending=True).head(20)

        for _, row in top20.iterrows():
            state = safe_txt(row.get("state", ""), 35)
            district = safe_txt(row.get("district", ""), 45)
            risk = safe_txt(row.get("Risk", ""), 12)
            ari = float(row.get("ARI", 0))

            line = f"State: {state} | District: {district} | ARI: {ari:.3f} | Risk: {risk}"
            pdf.multi_cell(0, 5, line)
            pdf.ln(0.5)

    # output for all fpdf2 versions (string OR bytearray)
    pdf_out = pdf.output(dest="S")
    if isinstance(pdf_out, (bytes, bytearray)):
        pdf_bytes = bytes(pdf_out)
    else:
        pdf_bytes = pdf_out.encode("latin1")

    return BytesIO(pdf_bytes)


# ---------------- MAIN ----------------
df = load_data()

# ---------------- SIDEBAR ----------------
st.sidebar.title("⚙️ Filters")

months = ["All"] + sorted(df["MonthName"].dropna().unique().tolist()) if "MonthName" in df.columns else ["All"]
states = ["All"] + sorted(df["state"].dropna().unique().tolist()) if "state" in df.columns else ["All"]
risks = ["All"] + sorted(df["Risk"].dropna().unique().tolist()) if "Risk" in df.columns else ["All"]

sel_month = st.sidebar.selectbox("📅 Month", months)
sel_state = st.sidebar.selectbox("🗺️ State", states)
sel_risk = st.sidebar.selectbox("🚦 Risk", risks)
district_search = st.sidebar.text_input("🔎 Search district (optional)")

# Apply filters
df_f = df.copy()

if sel_month != "All" and "MonthName" in df_f.columns:
    df_f = df_f[df_f["MonthName"] == sel_month]

if sel_state != "All" and "state" in df_f.columns:
    df_f = df_f[df_f["state"] == sel_state]

if sel_risk != "All" and "Risk" in df_f.columns:
    df_f = df_f[df_f["Risk"] == sel_risk]

if district_search.strip() != "" and "district" in df_f.columns:
    df_f = df_f[df_f["district"].str.contains(district_search, case=False, na=False)]

st.sidebar.markdown("---")
page = st.sidebar.radio("📌 Navigate", [
    "🏠 Home",
    "📍 Page 1: National Overview",
    "🚨 Page 2: High Risk Ranking",
    "🔍 Page 3: Explainability",
    "🛠️ Page 4: Action Planner",
])

# PDF Download
st.sidebar.markdown("---")
pdf_file = create_pdf_report(df_f, title="ARI Dashboard Report")
st.sidebar.download_button(
    label="📄 Download PDF Report",
    data=pdf_file,
    file_name="ARI_Report.pdf",
    mime="application/pdf"
)

st.sidebar.caption("✅ Hackathon-ready Streamlit Application")


# ---------------- HELPERS ----------------
def show_kpis(dataframe):
    c1, c2, c3, c4 = st.columns(4)
    avg = float(dataframe["ARI"].mean()) if len(dataframe) > 0 else 0.0
    c1.metric("Average ARI", round(avg, 3))
    c2.metric("High Risk", int((dataframe["Risk"] == "High").sum()))
    c3.metric("Medium Risk", int((dataframe["Risk"] == "Medium").sum()))
    c4.metric("Low Risk", int((dataframe["Risk"] == "Low").sum()))


# ---------------- HOME ----------------
if page == "🏠 Home":
    st.title("📊 Authentication Resilience Index (ARI) Dashboard")

    st.markdown("""
## ✅ Problem
Biometric authentication failures due to stale biometric updates and weak fallback mechanisms increase authentication risk.

## ✅ Solution
We developed **Authentication Resilience Index (ARI)** using key drivers:
- **BUR**: Biometric Update Recency (higher = more outdated)
- **BUD**: Biometric Update Density
- **AWF**: Authentication Workload Factor
- **MAF**: Multi-auth failure risk indicator

## ✅ What this dashboard indicates
- Identifies priority districts (lowest ARI)
- Explains why risk is high (Explainability)
- Provides interventions (Action Planner)
""")

    show_kpis(df_f)

    st.subheader("✅ Key Insights from selected filters")
    if len(df_f) > 0:
        worst = df_f.sort_values("ARI", ascending=True).iloc[0]
        best = df_f.sort_values("ARI", ascending=False).iloc[0]

        st.error(f"⚠️ Worst District: {worst['district']} ({worst['state']}) | ARI={worst['ARI']:.3f} | Risk={worst['Risk']}")
        st.success(f"✅ Best District: {best['district']} ({best['state']}) | ARI={best['ARI']:.3f} | Risk={best['Risk']}")

    st.info("Use sidebar filters (Month/State/Risk) and navigate pages for interactive demo.")


# ---------------- PAGE 1 ----------------
elif page == "📍 Page 1: National Overview":
    st.title("📍 Page 1: National Overview")

    st.markdown("""
### What this page indicates
- ✅ **Low ARI** = higher authentication vulnerability
- ✅ **High ARI** = better authentication resilience
""")

    show_kpis(df_f)

    st.subheader("Risk Distribution")
    risk_counts = df_f["Risk"].value_counts().reset_index()
    risk_counts.columns = ["Risk", "Count"]
    fig_pie = px.pie(risk_counts, names="Risk", values="Count", hole=0.55, title="Risk Distribution")
    st.plotly_chart(fig_pie, use_container_width=True)

    st.subheader("Top 20 Worst Districts (Lowest ARI)")
    top20 = df_f.sort_values("ARI", ascending=True).head(20)
    st.dataframe(top20[["state", "district", "ARI", "Risk", "BUR", "BUD"]], use_container_width=True)


# ---------------- PAGE 2 ----------------
elif page == "🚨 Page 2: High Risk Ranking":
    st.title("🚨 Page 2: High Risk Ranking")

    st.markdown("""
### What this page indicates
District ranking from worst-to-best using ARI.
Judges can clearly see which districts need urgent intervention.
""")

    st.subheader("Top 10 Worst Districts")
    top10 = df_f.sort_values("ARI", ascending=True).head(10)

    fig_bar = px.bar(
        top10,
        x="ARI",
        y="district",
        color="Risk",
        orientation="h",
        text="ARI",
        title="Top 10 Worst Districts (Lowest ARI)"
    )
    fig_bar.update_traces(texttemplate="%{text:.3f}", textposition="outside")
    fig_bar.update_layout(height=500)
    st.plotly_chart(fig_bar, use_container_width=True)

    st.subheader("Full Ranking Table")
    st.dataframe(
        df_f.sort_values("ARI", ascending=True)[
            ["state", "district", "ARI", "Risk", "BUR", "BUD", "AWF", "MAF_raw"]
        ],
        use_container_width=True
    )


# ---------------- PAGE 3 ----------------
elif page == "🔍 Page 3: Explainability":
    st.title("🔍 Page 3: Explainability (Risk Drivers)")

    st.markdown("""
### What this page indicates
This page explains *why* a district is high risk.

Key logic:
- Higher **BUR** (older biometrics) → authentication failures → ARI decreases
- Lower **BUD** (less update density) → ARI decreases
""")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("BUR vs ARI")
        fig1 = px.scatter(
            df_f, x="BUR", y="ARI", color="Risk",
            hover_data=["state", "district", "BUD", "AWF"],
            title="BUR vs ARI (Recency Gap Impact)"
        )
        st.plotly_chart(fig1, use_container_width=True)

    with col2:
        st.subheader("BUD vs ARI")
        fig2 = px.scatter(
            df_f, x="BUD", y="ARI", color="Risk",
            hover_data=["state", "district", "BUR", "AWF"],
            title="BUD vs ARI (Update Density Impact)"
        )
        st.plotly_chart(fig2, use_container_width=True)

    st.subheader("Driver Table (Top 50 Worst ARI)")
    st.dataframe(
        df_f.sort_values("ARI", ascending=True)[
            ["state", "district", "ARI", "Risk", "BUR", "BUD", "AWF", "MAF_raw"]
        ].head(50),
        use_container_width=True
    )


# ---------------- PAGE 4 ----------------
elif page == "🛠️ Page 4: Action Planner":
    st.title("🛠️ Page 4: Action Planner")

    st.markdown("""
### What this page indicates
This page converts risk analytics into **implementation-ready recommendations**.

Recommended usage:
- Select **Risk = High** for urgent district list
""")

    show_kpis(df_f)

    cols = ["state", "district", "ARI", "Risk", "BUR", "BUD"]
    if "Recommendation" in df_f.columns:
        cols.append("Recommendation")

    st.subheader("Recommended Intervention Plan")
    st.dataframe(df_f.sort_values("ARI", ascending=True)[cols], use_container_width=True)

    st.success("✅ Action Planner makes the dashboard policy-operational ready.")

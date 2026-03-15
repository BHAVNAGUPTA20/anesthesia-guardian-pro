import streamlit as st
import pandas as pd
import os
from datetime import datetime, date, timedelta
import plotly.express as px

st.set_page_config(
    page_title="🩺 Anesthesia Guardian Pro",
    layout="wide",
    page_icon="🩺",
    initial_sidebar_state="expanded"
)

DATA_FILE = "anesthesia_data.csv"

required_columns = [
    "date","resident_id","clinical_hours","procedures","patient_load",
    "night_shifts","critical_cases","sleep",
    "case_complexity","airway_difficulty",
    "mood_stress","mood_fatigue","mood_focus",
    "energy_vigilance","energy_decision",
    "energy_physical","energy_recovery",
    "notes","risk_score"
]

# ---------------- DATA LOADER ----------------

def load_data():

    if os.path.exists(DATA_FILE):
        df = pd.read_csv(DATA_FILE)
    else:
        df = pd.DataFrame(columns=required_columns)

    for col in required_columns:
        if col not in df.columns:
            df[col] = None

    df["date_dt"] = pd.to_datetime(df["date"], errors="coerce")

    return df

# ---------------- RISK SCORE ----------------

def calculate_risk_score(row):

    ot = (row["clinical_hours"] or 0) * 2
    night = (row["night_shifts"] or 0) * 5
    critical = (row["critical_cases"] or 0) * 3
    sleep_debt = max(0, 7 - (row["sleep"] or 0)) * 4
    vigilance = (10 - (row["energy_vigilance"] or 5)) * 3
    complexity = (row["case_complexity"] or 1) * 2
    airway = (row["airway_difficulty"] or 0) * 3

    return ot + night + critical + sleep_debt + vigilance + complexity + airway


def get_risk_advice(score):

    if score >= 40:
        return "🚨 CRITICAL – Do NOT operate alone"
    elif score >= 30:
        return "⚠️ HIGH RISK – Senior supervision required"
    elif score >= 20:
        return "🟡 MODERATE – Monitor closely"
    else:
        return "✅ SAFE"

# ---------------- LOAD DATA ----------------

df = load_data()

if not df.empty and "risk_score" not in df.columns:
    df["risk_score"] = df.apply(calculate_risk_score, axis=1)

# ---------------- HEADER ----------------

st.markdown("""
# 🩺 **Anesthesia Guardian Pro**
### AI-Powered Vigilance & Fatigue Risk System
""")

st.info("👉 Click **➕ Enter Shift Data** tab to log your shift.")

# ---------------- LOGIN ----------------

with st.sidebar:

    st.header("🔐 Access Control")

    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
        st.session_state.current_user = None

    if not st.session_state.logged_in:

        user = st.text_input("Resident ID")

        if st.button("Login"):
            if user.strip():
                st.session_state.logged_in = True
                st.session_state.current_user = user.strip()
                st.rerun()

        st.stop()

    st.success(f"Welcome {st.session_state.current_user}")

    if st.button("Logout"):
        st.session_state.clear()
        st.rerun()

    st.divider()

    st.header("Filters")

    resident_options = ["My Data Only"] + list(df["resident_id"].dropna().unique())

    selected_resident = st.selectbox("View Data", resident_options)

    period_options = {"Last 7 days":7,"Last 30 days":30,"All Time":None}

    period = st.radio("Time Period", list(period_options.keys()))

    start_date = None

    if period_options[period]:
        start_date = date.today() - timedelta(days=period_options[period])

# ---------------- FILTER DATA ----------------

df_filtered = df.copy()

if selected_resident != "My Data Only":
    df_filtered = df_filtered[df_filtered["resident_id"] == selected_resident]

if start_date:
    df_filtered = df_filtered[df_filtered["date_dt"] >= pd.to_datetime(start_date)]

# ---------------- TABS ----------------

tabs = st.tabs([
"📊 Dashboard",
"➕ Enter Shift Data",
"📈 Trends",
"🧠 Risk Advisor",
"📋 Audit Trail"
])

# ---------------- DASHBOARD ----------------

with tabs[0]:

    if df_filtered.empty:
        st.info("No data yet")
    else:

        col1,col2,col3,col4 = st.columns(4)

        col1.metric("Avg OT Hours", round(df_filtered["clinical_hours"].mean(),1))
        col2.metric("Sleep Avg", round(df_filtered["sleep"].mean(),1))
        col3.metric("Night Duties", int(df_filtered["night_shifts"].sum()))
        col4.metric("Critical Cases", int(df_filtered["critical_cases"].sum()))

# ---------------- ENTER SHIFT DATA ----------------

with tabs[1]:

    st.header("➕ Enter Shift Data")

    with st.form("shift_form"):

        col1,col2 = st.columns(2)

        with col1:

            clinical_hours = st.number_input("OT Hours",0.0,24.0,8.0)

            night_shifts = st.number_input("Night Calls",0,3,0)

            procedures = st.number_input("Procedures",0,50,0)

            critical_cases = st.number_input("Critical Cases",0,20,0)

            sleep = st.number_input("Sleep Hours",0.0,16.0,6.0)

            st.markdown("### Case Complexity")

            case_complexity = st.selectbox(
                "Case Complexity Level",
                [1,2,3,4],
                format_func=lambda x: [
                    "1 – Minor",
                    "2 – Moderate",
                    "3 – Major",
                    "4 – Emergency"
                ][x-1]
            )

            airway_difficulty = st.slider(
                "Airway Difficulty Encountered",
                0,3,0,
                help="0 normal | 1 mild difficulty | 2 difficult airway | 3 airway crisis"
            )

        with col2:

            st.markdown("### 🧠 Cognitive & Performance Status")

            st.markdown("""
**Use these objective anchors while rating yourself during the shift**

**Vigilance**
1–2 → Missing monitor trends, delayed response to alarms  
3–4 → Concentration drifting  
5–6 → Adequate vigilance but subtle changes may be missed  
7–8 → Consistent monitoring  
9–10 → Detect subtle physiologic changes immediately
""")

            energy_vigilance = st.slider("👁️ Vigilance",1,10,6)

            st.markdown("""
**Clinical Decision Clarity**
1–2 → Unable to process complex cases  
3–4 → Decision fatigue obvious  
5–6 → Thinking slower than usual  
7–8 → Clear clinical reasoning  
9–10 → Rapid confident decisions
""")

            energy_decision = st.slider("🧠 Decision Clarity",1,10,6)

            st.markdown("""
**Physical Fatigue**
1–2 → Severe exhaustion  
3–4 → Fatigue affecting work  
5–6 → Noticeable tiredness  
7–8 → Mild tiredness  
9–10 → Fully energetic
""")

            mood_fatigue = st.slider("😴 Physical Fatigue",1,10,5)

            st.markdown("""
**Stress Load**
1–2 → Overwhelmed  
3–4 → Very high stress  
5–6 → Moderate stress  
7–8 → Mild stress  
9–10 → Calm and composed
""")

            mood_stress = st.slider("😰 Stress",1,10,5)

            notes = st.text_area("Notes")

            log_date = st.date_input("Date",value=date.today())

        submit = st.form_submit_button("Save Shift")

        if submit:

            new_row = {
                "date":datetime.combine(log_date,datetime.now().time()),
                "resident_id":st.session_state.current_user,
                "clinical_hours":clinical_hours,
                "procedures":procedures,
                "patient_load":0,
                "night_shifts":night_shifts,
                "critical_cases":critical_cases,
                "sleep":sleep,
                "case_complexity":case_complexity,
                "airway_difficulty":airway_difficulty,
                "mood_stress":mood_stress,
                "mood_fatigue":mood_fatigue,
                "mood_focus":6,
                "energy_vigilance":energy_vigilance,
                "energy_decision":energy_decision,
                "energy_physical":6,
                "energy_recovery":6,
                "notes":notes
            }

            new_row["risk_score"] = calculate_risk_score(pd.Series(new_row))

            df_new = pd.concat([df,pd.DataFrame([new_row])],ignore_index=True)

            df_new["date_dt"] = pd.to_datetime(df_new["date"],errors="coerce")

            df_new.to_csv(DATA_FILE,index=False)

            st.success(f"Shift saved | Risk Score: {new_row['risk_score']}")

            st.rerun()

# ---------------- TRENDS ----------------

with tabs[2]:

    if df_filtered.empty:
        st.info("No data yet")
    else:

        fig = px.line(
            df_filtered.sort_values("date_dt"),
            x="date_dt",
            y="risk_score",
            title="Risk Score Trend"
        )

        st.plotly_chart(fig,use_container_width=True)

# ---------------- RISK ADVISOR ----------------

with tabs[3]:

    if df_filtered.empty:
        st.warning("Log a shift first")
    else:

        latest = df_filtered.iloc[0]

        risk = latest["risk_score"]

        st.metric("Latest Risk Score", risk)

        st.info(get_risk_advice(risk))

# ---------------- AUDIT ----------------

with tabs[4]:

    if df_filtered.empty:
        st.info("No data")
    else:

        high = df_filtered[df_filtered["risk_score"] >= 30]

        if high.empty:
            st.success("No high-risk shifts")
        else:
            st.dataframe(high)

# ---------------- FOOTER ----------------

st.markdown("---")

st.markdown("""
<center>
<b>Anesthesia Guardian Pro</b><br>
Dr Bhavna Gupta | AIIMS Rishikesh
</center>
""", unsafe_allow_html=True)
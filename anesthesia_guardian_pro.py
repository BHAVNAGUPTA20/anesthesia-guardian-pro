import streamlit as st
import pandas as pd
from datetime import datetime, date
import plotly.express as px
import plotly.graph_objects as go
import gspread
from oauth2client.service_account import ServiceAccountCredentials

st.set_page_config(page_title="Anesthesia Guardian Pro", layout="wide")

SHEET_NAME = "AnesthesiaGuardianDB"

# ---------------- GOOGLE SHEET CONNECTION ----------------

def connect_sheet():

    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]

    creds = ServiceAccountCredentials.from_json_keyfile_name(
        "credentials.json", scope
    )

    client = gspread.authorize(creds)

    return client.open(SHEET_NAME).sheet1


# ---------------- LOAD DATA ----------------

def load_data():

    sheet = connect_sheet()

    data = sheet.get_all_records()

    if len(data) == 0:
        return pd.DataFrame()

    df = pd.DataFrame(data)

    numeric_cols = [
        "clinical_hours","procedures","patient_load","night_shifts",
        "critical_cases","sleep","case_complexity","airway_difficulty",
        "mood_stress","mood_fatigue","energy_vigilance","energy_decision",
        "risk_score"
    ]

    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df["date_dt"] = pd.to_datetime(df["date"], errors="coerce")

    return df


# ---------------- RISK SCORE ----------------

def calculate_risk_score(row):

    clinical_hours = float(row.get("clinical_hours",0) or 0)
    night_shifts = float(row.get("night_shifts",0) or 0)
    critical_cases = float(row.get("critical_cases",0) or 0)
    sleep = float(row.get("sleep",0) or 0)
    vigilance = float(row.get("energy_vigilance",5) or 5)
    complexity = float(row.get("case_complexity",1) or 1)
    airway = float(row.get("airway_difficulty",0) or 0)

    ot = clinical_hours * 2
    night = night_shifts * 5
    critical = critical_cases * 3
    sleep_debt = max(0,7 - sleep) * 4
    vigilance_penalty = (10 - vigilance) * 3
    complexity_penalty = complexity * 2
    airway_penalty = airway * 3

    return round(
        ot + night + critical +
        sleep_debt +
        vigilance_penalty +
        complexity_penalty +
        airway_penalty
    )


# ---------------- ADVISORY ----------------

def generate_advice(row):

    score = float(row.get("risk_score",0) or 0)

    factors=[]

    if row["sleep"] < 6:
        factors.append("Sleep deficit (<6h) detected.")

    if row["night_shifts"] >=1:
        factors.append("Night duty contributing to circadian fatigue.")

    if row["clinical_hours"] >10:
        factors.append("Prolonged OT hours increasing decision fatigue.")

    if row["energy_vigilance"] <=5:
        factors.append("Low vigilance score may increase monitoring risk.")

    if row["case_complexity"] >=3:
        factors.append("High case complexity increases cognitive workload.")

    if row["airway_difficulty"] >=2:
        factors.append("Difficult airway increases procedural stress.")

    if score >=40:
        headline="🚨 CRITICAL RISK"
        recommendation="Avoid independent anesthesia practice. Seek senior supervision."

    elif score >=30:
        headline="⚠️ HIGH RISK"
        recommendation="Senior backup recommended for complex or emergency cases."

    elif score >=20:
        headline="🟡 MODERATE RISK"
        recommendation="Maintain heightened vigilance."

    else:
        headline="✅ LOW RISK"
        recommendation="Operational readiness acceptable."

    return headline,factors,recommendation


# ---------------- FATIGUE GAUGE ----------------

def fatigue_gauge(score):

    # dynamic upper limit so gauge never cuts off
    max_range = max(60, score + 10)

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score,
        title={'text': "Fatigue Risk Meter"},
        gauge={
            'axis': {'range': [0, max_range]},
            'bar': {'color': "white"},

            'steps': [
                {'range': [0,20], 'color': "#00a65a"},     # green
                {'range': [20,30], 'color': "#f4e842"},    # yellow
                {'range': [30,40], 'color': "#f39c12"},    # orange
                {'range': [40,max_range], 'color': "#dd4b39"}  # red
            ],

            'threshold': {
                'line': {'color': "white", 'width': 5},
                'value': score
            }
        }
    ))

    fig.update_layout(
        height=450,
        paper_bgcolor="#0e1117",
        font={'color': "white", 'size': 16}
    )

    st.plotly_chart(fig, use_container_width=True)

# ---------------- HEADER ----------------

st.title("🩺 Anesthesia Guardian Pro")
st.caption("Fatigue & Vigilance Monitoring System for Anesthesia Residents")


# ---------------- LOGIN ----------------

with st.sidebar:

    st.header("Resident Login")

    if "logged_in" not in st.session_state:
        st.session_state.logged_in=False

    if not st.session_state.logged_in:

        st.info("""
This application monitors **fatigue, vigilance and clinical workload risk**
in anesthesia residents.

Log your shift data to receive a **real-time fatigue risk assessment**
and safety recommendations.
""")

        user=st.text_input("Resident ID").lower().strip()

        if st.button("Login"):
            if user:
                st.session_state.logged_in=True
                st.session_state.user=user
                st.rerun()

        st.markdown("---")

        st.subheader("About the Developer")

        st.write("""
**Dr Bhavna Gupta**

Associate Professor, Anaesthesiology  
AIIMS Rishikesh  

Researcher | Educator | AI enthusiast  

This tool was designed to explore **fatigue-related safety risks in anesthesia practice**
and support resident wellbeing and patient safety.
""")

        st.stop()

    st.success(f"Logged in: {st.session_state.user}")

    if st.button("Logout"):
        st.session_state.clear()
        st.rerun()


# ---------------- LOAD DATA ----------------

df=load_data()

if not df.empty:
    df["risk_score"]=df.apply(calculate_risk_score,axis=1)
    df_user=df[df["resident_id"]==st.session_state.user]
else:
    df_user=pd.DataFrame()


# ---------------- TABS ----------------

tab1,tab2,tab3,tab4=st.tabs([
"Dashboard",
"Enter Shift",
"Trends",
"Risk Advisor"
])


# ---------------- DASHBOARD ----------------

with tab1:

    if df_user.empty:
        st.info("No shifts logged yet")

    else:

        c1,c2,c3,c4=st.columns(4)

        c1.metric("Avg OT Hours",round(df_user["clinical_hours"].mean(),1))
        c2.metric("Avg Sleep",round(df_user["sleep"].mean(),1))
        c3.metric("Night Duties",int(df_user["night_shifts"].sum()))
        c4.metric("Critical Cases",int(df_user["critical_cases"].sum()))


# ---------------- ENTER SHIFT ----------------

with tab2:

    with st.form("shift_form"):

        col1,col2=st.columns(2)

        with col1:

            clinical_hours=st.number_input("OT Hours",0.0,24.0,8.0)
            night_shifts=st.number_input("Night Calls",0,3,0)
            procedures=st.number_input("Procedures",0,50,0)
            critical_cases=st.number_input("Critical Cases",0,20,0)
            sleep=st.number_input("Sleep Hours",0.0,16.0,6.0)

            case_complexity=st.selectbox(
                "Case Complexity",
                [1,2,3,4],
                format_func=lambda x:[
                    "1 Minor elective case",
                    "2 Moderate surgery",
                    "3 Major surgery",
                    "4 Emergency / unstable"
                ][x-1]
            )

            airway_difficulty=st.selectbox(
                "Airway Difficulty",
                [0,1,2,3],
                format_func=lambda x:[
                    "0 Normal airway",
                    "1 Mild difficulty",
                    "2 Difficult airway",
                    "3 Airway crisis"
                ][x]
            )

        with col2:

            st.markdown("""
### Vigilance Guide
1–2 Missing monitor trends  
3–4 Attention drifting  
5–6 Adequate vigilance but slower reactions  
7–8 Consistent monitoring  
9–10 Detect subtle physiologic changes
""")

            energy_vigilance=st.slider("Vigilance",1,10,6)

            st.markdown("""
### Decision Clarity Guide
1–2 Unable to process complex situations  
3–4 Decision fatigue obvious  
5–6 Slower reasoning  
7–8 Clear judgement  
9–10 Rapid confident decisions
""")

            energy_decision=st.slider("Decision Clarity",1,10,6)

            mood_fatigue=st.slider("Physical Fatigue",1,10,5)
            mood_stress=st.slider("Stress Level",1,10,5)

            notes=st.text_area("Notes")

        submit=st.form_submit_button("Save Shift")

        if submit:

            new_row={
                "date":str(datetime.now()),
                "resident_id":st.session_state.user,
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
                "energy_vigilance":energy_vigilance,
                "energy_decision":energy_decision,
                "notes":notes
            }

            new_row["risk_score"]=calculate_risk_score(pd.Series(new_row))

            sheet=connect_sheet()

            sheet.append_row(list(new_row.values()))

            st.success(f"Shift saved | Risk Score: {new_row['risk_score']}")

            st.rerun()


# ---------------- TRENDS ----------------

with tab3:

    if not df_user.empty:

        fig=px.line(
            df_user.sort_values("date_dt"),
            x="date_dt",
            y="risk_score",
            title="Fatigue Risk Trend"
        )

        st.plotly_chart(fig,use_container_width=True)


# ---------------- RISK ADVISOR ----------------

with tab4:

    if df_user.empty:
        st.info("Log a shift first")

    else:

        latest=df_user.sort_values("date_dt",ascending=False).iloc[0]

        score=latest["risk_score"]

        fatigue_gauge(score)

        headline,factors,recommendation=generate_advice(latest)

        st.subheader(headline)

        st.write("### Contributing Factors")

        for f in factors:
            st.write("•",f)

        st.write("### Recommendation")

        st.info(recommendation)

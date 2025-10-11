import streamlit as st
import pandas as pd

# Reuse existing Mano components and utilities
from components.table import render_styled_table
from components.card import render_kpi_card
try:
    from components.slider import render_styled_slider
except Exception:
    # Fallback if the custom slider component isn't available during local testing
    def render_styled_slider(label, min_val, max_val, value, help_text=None):
        return st.slider(label, min_value=min_val, max_value=max_val, value=value, help=help_text)

import utils.css as styling
import utils.colors as colors
import utils.date as date_utils

STEPS = [{'name': 'Prequalification of Bidders', 'default_days': 30}, {'name': 'Bidder Shortlist Agreed', 'default_days': 10}, {'name': 'Scope & RFP Package Prepared', 'default_days': 10}, {'name': 'Scope & RFP Package Approved', 'default_days': 5}, {'name': 'RFP Issued', 'default_days': 30}, {'name': 'RFP Information Requests Due', 'default_days': 10}, {'name': 'RFP Information Requests Answered', 'default_days': 5}, {'name': 'Proposals Levels & Analysed', 'default_days': 15}, {'name': 'Bidder Selection', 'default_days': 5}, {'name': 'Scope of RFP Funding Approval', 'default_days': 20}, {'name': 'Bidder Contract Execution', 'default_days': 30}]

st.set_page_config(page_title="Vendor Onboarding Calculator", layout="wide")
styling.inject_custom_css()
st.logo("./assets/images/Mano_Logo_Main.svg", icon_image="./assets/images/Mano_Mark_Mark.svg")

# ---------------- Sidebar ----------------
with st.sidebar:
    st.header("Vendor Onboarding Inputs")

    mode = st.radio("Calculation Mode", ["Start Date → End Date", "End Date → Start Recommendation"], index=0)
    country = st.selectbox("Holiday Calendar", ["United States","Mexico","United Kingdom","Italy","Spain"], index=0)
    st.caption("Working‑day math respects public holidays in the selected country.")
    preset = st.selectbox("Durations Preset", ["Typical", "Aggressive (-10%)", "Conservative (+15%)"], index=0)

    # Date input
    today_year = date_utils.date.today().year
    if mode == "Start Date → End Date":
        start_date = st.date_input("Onboarding Start", value=date_utils.date.today())
        target_end = None
    else:
        target_end = st.date_input("Target Onboard Complete", value=date_utils.date(today_year, 6, 30))
        start_date = None

    st.divider()
    st.header("Steps & Durations (working days)")

    scale = {"Typical":1.0, "Aggressive (-10%)":0.9, "Conservative (+15%)":1.15}[preset]

    # Build per‑step controls (include toggle + duration slider)
    step_controls = []
    for s in STEPS:
        col1, col2 = st.columns([1,2])
        with col1:
            include = st.checkbox(f"Include", value=True, key=f"inc_{s['name']}")
        with col2:
            default_days = max(1, int(round(s['default_days']*scale)))
            dur = render_styled_slider(s['name'], 1, 60, default_days)
        step_controls.append({
            "name": s["name"],
            "include": include,
            "days": dur if include else 0
        })

# Holidays pre‑expansion (covers a generous multi‑year span)
years = list(range( date_utils.date.today().year-1, 2041 ))
HOLIDAYS = date_utils.expand_holidays(country, years)

def forward_schedule(start_date, controls):
    """Return list of dict rows with Start/Finish for each included step, working days only."""
    rows = []
    current = start_date
    for ctrl in controls:
        if not ctrl["include"]:
            continue
        s_start = current
        s_finish = date_utils.add_workdays(s_start, int(ctrl["days"]), HOLIDAYS, workdays_per_week=5)
        rows.append({
            "Step": ctrl["name"],
            "Start": s_start,
            "Finish": s_finish,
            "Duration (work days)": int(ctrl["days"]),
        })
        # Next step starts the day after finish
        current = s_finish
    return rows

def backward_schedule(target_end, controls):
    """Work backward from target_end. Returns rows ordered in the natural forward sequence."""
    # Work with a reversed list to place tasks back to back backward in time
    reversed_steps = [c for c in controls if c["include"]][::-1]
    rows = []
    current_finish = target_end
    for ctrl in reversed_steps:
        s_start = date_utils.add_workdays(current_finish, -int(ctrl["days"]), HOLIDAYS, workdays_per_week=5)
        rows.append({
            "Step": ctrl["name"],
            "Start": s_start,
            "Finish": current_finish,
            "Duration (work days)": int(ctrl["days"]),
        })
        current_finish = s_start
    # Re‑order to forward sequence for display
    return rows[::-1]

# ---------------- Main UI ----------------
st.title("Vendor Onboarding Calculator")

if mode == "Start Date → End Date":
    rows = forward_schedule(start_date, step_controls)
    recommended_start = start_date
    recommended_finish = rows[-1]["Finish"] if rows else start_date
else:
    rows = backward_schedule(target_end, step_controls)
    recommended_start = rows[0]["Start"] if rows else target_end
    recommended_finish = target_end

# KPI Cards
colA, colB, colC = st.columns(3)
with colA:
    st.markdown(render_kpi_card({"building_name":"Vendor Onboarding","start":recommended_start}, "Start", "start"), unsafe_allow_html=True)
with colB:
    st.markdown(render_kpi_card({"building_name":"Vendor Onboarding","end":recommended_finish}, "Complete", "end"), unsafe_allow_html=True)
with colC:
    total_days = sum(c["days"] for c in step_controls if c["include"])
    st.markdown(render_kpi_card({"building_name":"Vendor Onboarding","days":total_days}, "Total (working days)", "days"), unsafe_allow_html=True)

st.divider()

result_df = pd.DataFrame(rows)
# Results Table
render_styled_table(result_df)

# Download
st.download_button("Download Schedule (CSV)", result_df.to_csv(index=False).encode("utf-8"), "vendor_onboarding_schedule.csv", "text/csv")

st.markdown('<p class="small-muted">Notes: Columns F and G from the source planning sheet are informational and not included in duration math. Durations are working days (Mon–Fri) with standard public holidays applied per country.</p>', unsafe_allow_html=True)

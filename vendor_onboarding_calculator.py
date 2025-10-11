import streamlit as st
import pandas as pd

# Reuse existing Mano components and utilities
from components.table import render_styled_table
from components.card import render_kpi_card
try:
    from components.slider import render_styled_slider
except Exception:
    # Fallback if the custom slider component isn't available during local testing
    def render_styled_slider(label, min_val, max_val, value, step=1, help=None, key=None, disabled=False):
        return st.slider(
            label,
            min_value=min_val,
            max_value=max_val,
            value=value,
            step=step,
            help=help,
            key=key,
            disabled=disabled,
        )

import utils.css as styling
import utils.colors as colors
import utils.date as date_utils

STEPS = [
    {"key": "prequal", "name": "Prequalification of Bidders", "default_days": 30, "min_days": 5, "max_days": 90},
    {"key": "shortlist", "name": "Bidder Shortlist Agreed", "default_days": 10, "min_days": 2, "max_days": 45},
    {"key": "package_prepared", "name": "Scope & RFP Package Prepared", "default_days": 10, "min_days": 2, "max_days": 60},
    {"key": "package_approved", "name": "Scope & RFP Package Approved", "default_days": 5, "min_days": 1, "max_days": 30},
    {"key": "rfp_issued", "name": "RFP Issued", "default_days": 30, "min_days": 5, "max_days": 120, "required": True},
    {"key": "proposals", "name": "Proposals Levels & Analysed", "default_days": 15, "min_days": 3, "max_days": 60},
    {"key": "bidder_selection", "name": "Bidder Selection", "default_days": 5, "min_days": 1, "max_days": 30},
    {"key": "funding", "name": "Scope of RFP Funding Approval", "default_days": 20, "min_days": 5, "max_days": 90},
    {"key": "contract", "name": "Bidder Contract Execution", "default_days": 30, "min_days": 5, "max_days": 120},
    {"key": "construction", "name": "Construction & Commissioning", "default_days": 365, "min_days": 5, "max_days": 1825, "step": 5, "required": True},
]

INFO_REQUEST_DEFAULTS = {"due": 10, "answered": 5}


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
        default_required = start_date + date_utils.timedelta(days=365)
        required_completion = st.date_input("Required Construction Completion", value=default_required)
        target_end = None
    else:
        required_completion = st.date_input("Required Construction Completion", value=date_utils.date(today_year, 6, 30))
        start_date = None
        target_end = required_completion

    st.divider()
    st.header("Steps & Durations (working days)")

    scale = {"Typical":1.0, "Aggressive (-10%)":0.9, "Conservative (+15%)":1.15}[preset]

    # Build per-step controls (include toggle + duration slider)
    step_controls = []
    rfp_issue_config = None
    for s in STEPS:
        col1, col2 = st.columns([1, 2])
        with col1:
            checkbox_kwargs = {"value": True, "key": f"inc_{s['key']}"}
            if s.get("required"):
                checkbox_kwargs["disabled"] = True
            include = st.checkbox("Include", **checkbox_kwargs)
            if s.get("required"):
                include = True
        with col2:
            min_days = int(s.get("min_days", 1))
            max_days = int(s.get("max_days", 60))
            step_size = int(s.get("step", 1))
            default_days = int(round(s["default_days"] * scale))
            default_days = max(min_days, min(max_days, default_days))
            if step_size > 1:
                offset = (default_days - min_days) % step_size
                default_days -= offset
                if offset >= step_size / 2 and default_days + step_size <= max_days:
                    default_days += step_size
                if default_days < min_days:
                    default_days = min_days
            dur = render_styled_slider(
                s["name"],
                min_days,
                max_days,
                default_days,
                step=step_size,
                key=f"slider_{s['key']}",
            )
        ctrl = {
            "name": s["name"],
            "key": s["key"],
            "include": include,
            "days": int(dur) if include else 0,
            "raw_days": int(dur),
        }
        if s.get("required"):
            ctrl["include"] = True
            ctrl["days"] = int(dur)
        step_controls.append(ctrl)
        if s["key"] == "rfp_issued":
            rfp_issue_config = ctrl

    rfp_issue_span = int(rfp_issue_config.get("raw_days", 0)) if rfp_issue_config else 0
    scaled_due_default = int(round(INFO_REQUEST_DEFAULTS["due"] * scale))
    scaled_due_default = max(0, min(rfp_issue_span, scaled_due_default))
    info_due = render_styled_slider(
        "RFP Information Requests Due",
        0,
        rfp_issue_span,
        scaled_due_default,
        key="slider_info_due",
        help="Working days from RFP issue until questions close.",
    )

    answered_max = max(0, rfp_issue_span - int(info_due))
    scaled_answer_default = int(round(INFO_REQUEST_DEFAULTS["answered"] * scale))
    scaled_answer_default = max(0, min(answered_max, scaled_answer_default))
    info_answered = render_styled_slider(
        "RFP Information Requests Answered",
        0,
        answered_max,
        scaled_answer_default,
        key="slider_info_answered",
        help="Working days after questions close to deliver responses.",
    )

    info_controls = {"due_days": int(info_due), "answered_days": int(info_answered)}

# Holidays pre‑expansion (covers a generous multi‑year span)
years = list(range( date_utils.date.today().year-1, 2041 ))
HOLIDAYS = date_utils.expand_holidays(country, years)

def forward_schedule(start_date, controls, info_controls):
    """Return list of dict rows with Start/Finish for each included step, working days only."""
    rows = []
    current = start_date
    milestones = {"rfp_closed": None, "info_due": None, "info_answered": None}
    for ctrl in controls:
        if not ctrl["include"]:
            continue
        duration = int(ctrl["days"])
        s_start = current
        s_finish = date_utils.add_workdays(s_start, duration, HOLIDAYS, workdays_per_week=5)
        rows.append({
            "Step": ctrl["name"],
            "Start": s_start,
            "Finish": s_finish,
            "Duration (work days)": duration,
        })
        if ctrl.get("key") == "rfp_issued":
            due_days = int(info_controls.get("due_days", 0) or 0)
            answered_days = int(info_controls.get("answered_days", 0) or 0)
            due_date = date_utils.add_workdays(s_start, due_days, HOLIDAYS, workdays_per_week=5)
            answered_finish = date_utils.add_workdays(due_date, answered_days, HOLIDAYS, workdays_per_week=5)
            rows.append({
                "Step": "RFP Information Requests Due",
                "Start": s_start,
                "Finish": due_date,
                "Duration (work days)": due_days,
            })
            rows.append({
                "Step": "RFP Information Requests Answered",
                "Start": due_date,
                "Finish": answered_finish,
                "Duration (work days)": answered_days,
            })
            milestones["rfp_closed"] = s_finish
            milestones["info_due"] = due_date
            milestones["info_answered"] = answered_finish
        current = s_finish
    return rows, milestones


def backward_schedule(target_end, controls, info_controls):
    """Work backward from target_end. Returns rows ordered in the natural forward sequence."""
    reversed_steps = [c for c in controls if c["include"]][::-1]
    rows = []
    milestones = {"rfp_closed": None, "info_due": None, "info_answered": None}
    current_finish = target_end
    for ctrl in reversed_steps:
        duration = int(ctrl["days"])
        s_start = date_utils.add_workdays(current_finish, -duration, HOLIDAYS, workdays_per_week=5)
        row = {
            "Step": ctrl["name"],
            "Start": s_start,
            "Finish": current_finish,
            "Duration (work days)": duration,
        }
        if ctrl.get("key") == "rfp_issued":
            due_days = int(info_controls.get("due_days", 0) or 0)
            answered_days = int(info_controls.get("answered_days", 0) or 0)
            due_date = date_utils.add_workdays(s_start, due_days, HOLIDAYS, workdays_per_week=5)
            answered_finish = date_utils.add_workdays(due_date, answered_days, HOLIDAYS, workdays_per_week=5)
            info_answered_row = {
                "Step": "RFP Information Requests Answered",
                "Start": due_date,
                "Finish": answered_finish,
                "Duration (work days)": answered_days,
            }
            info_due_row = {
                "Step": "RFP Information Requests Due",
                "Start": s_start,
                "Finish": due_date,
                "Duration (work days)": due_days,
            }
            rows.extend([info_answered_row, info_due_row, row])
            milestones["rfp_closed"] = current_finish
            milestones["info_due"] = due_date
            milestones["info_answered"] = answered_finish
        else:
            rows.append(row)
        current_finish = s_start
    return rows[::-1], milestones

# ---------------- Main UI ----------------
st.title("Vendor Onboarding Calculator")

if mode == "Start Date → End Date":
    rows, milestones = forward_schedule(start_date, step_controls, info_controls)
    recommended_start = start_date
    recommended_finish = rows[-1]["Finish"] if rows else start_date
else:
    rows, milestones = backward_schedule(target_end, step_controls, info_controls)
    recommended_start = rows[0]["Start"] if rows else target_end
    recommended_finish = target_end

rfp_closed = milestones.get("rfp_closed")
alerts = []
if required_completion and recommended_finish and recommended_finish > required_completion:
    alerts.append(f"Construction completes on {recommended_finish} which is after the required completion date of {required_completion}. Adjust durations or move the start date.")
if rfp_closed and milestones.get("info_due") and milestones["info_due"] > rfp_closed:
    alerts.append(f"RFP information requests are due on {milestones['info_due']} but the RFP closes on {rfp_closed}. Extend the RFP Issued window or move the due date earlier.")
if rfp_closed and milestones.get("info_answered") and milestones["info_answered"] > rfp_closed:
    alerts.append(f"RFP information request answers finish on {milestones['info_answered']} but the RFP closes on {rfp_closed}. Adjust durations so answers are complete before closing.")
for msg in alerts:
    st.error(msg)

def format_card_value(value):
    return value if value is not None else "—"

colA, colB, colC, colD = st.columns(4)
with colA:
    st.markdown(render_kpi_card({"building_name":"Vendor Onboarding","start":format_card_value(recommended_start)}, "Start", "start"), unsafe_allow_html=True)
with colB:
    st.markdown(render_kpi_card({"building_name":"Vendor Onboarding","rfp_closed":format_card_value(rfp_closed)}, "RFP Closed", "rfp_closed"), unsafe_allow_html=True)
with colC:
    st.markdown(render_kpi_card({"building_name":"Vendor Onboarding","end":format_card_value(recommended_finish)}, "Complete", "end"), unsafe_allow_html=True)
with colD:
    total_days = sum(c["days"] for c in step_controls if c["include"])
    st.markdown(render_kpi_card({"building_name":"Vendor Onboarding","days":total_days}, "Total (working days)", "days"), unsafe_allow_html=True)

st.divider()

result_df = pd.DataFrame(rows)
# Results Table
render_styled_table(result_df)

# Download
st.download_button("Download Schedule (CSV)", result_df.to_csv(index=False).encode("utf-8"), "vendor_onboarding_schedule.csv", "text/csv")

st.markdown('<p class="small-muted">Notes: Columns F and G from the source planning sheet are informational and not included in duration math. Durations are working days (Mon–Fri) with standard public holidays applied per country.</p>', unsafe_allow_html=True)

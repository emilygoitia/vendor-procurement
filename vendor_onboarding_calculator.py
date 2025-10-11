# rfs_calculator_app_mano_updates_v2.py
import streamlit as st
import pandas as pd

from components.chart import render_gantt
from components.card import render_kpi_card
from components.table import render_styled_table
from components.slider import render_styled_slider

import data.equipment as equipment

import utils.building as building
import utils.css as styling
import utils.date as date_utils
import utils.colors as colors

st.set_page_config(page_title="Mano RFS Calculator", layout="wide")
styling.inject_custom_css()
st.logo("./assets/images/Mano_Logo_Main.svg", icon_image="./assets/images/Mano_Mark_Mark.svg")


# ======================= Sidebar (Inputs) =======================
with st.sidebar:
    st.header("Calendar")
    country = "United States"
    st.markdown("**Holiday Calendar:** United States")
    st.caption("Calendar utilizes standard United States public holidays.")
    six_day_construction = st.checkbox("Use 6‑day workweek for construction activities", value=False)

    st.divider()
    st.header("Presets")
    preset = st.selectbox("Durations Preset", ["Typical", "Aggressive (-10%)", "Conservative (+15%)"])

    st.divider()
    st.header("Gate Dates")
    base_building_name = st.text_input("Base Building Name", value="Building")
    today_year = date_utils.date.today().year
    ntp = st.date_input("Notice to Proceed", value=date_utils.date(today_year, 1, 15))
    ldp = st.date_input("Land Disturbance Permit", value=date_utils.date(today_year, 2, 1))
    bp  = st.date_input("Building Permit", value=date_utils.date(today_year, 5, 1))
    perm_power = st.date_input("Permanent Power Delivery", value=date_utils.date(today_year, 12, 1))
    temp_power_allowed = st.checkbox("Allow L3/L4 on Temporary Power", value=False)
    temp_power_date = st.date_input("Temporary Power Available", value=None, disabled=not temp_power_allowed)

    st.divider()
    st.header("Buildings")
    num_buildings = st.number_input("Number of Buildings", min_value=1, max_value=10, value=2, step=1)
    building_offset = st.number_input("Offset between buildings (days)", min_value=0, max_value=3650, value=90, step=5)

    # Per-building config editor: Name, Halls, MW — defaults prefilled
    default_rows = []
    for i in range(1, int(num_buildings)+1):
        default_rows.append({"Building Name": f"{base_building_name} {i}", "Halls": 8, "MW (total)": 16.8 * 8})
    st.caption("Edit buildings individually (name, # halls, total MW).")
    build_df = st.data_editor(pd.DataFrame(default_rows), hide_index=True, num_rows="fixed", use_container_width=True)

    st.divider()
    st.header("Durations (working days)")
    site_work = 100; shell = 180; mep_yard = 65; fitup = 50; L3d = 40; L4d = 15; L5d = 2
    scale = {"Typical":1.0, "Aggressive (-10%)":0.9, "Conservative (+15%)":1.15}[preset]
    site_work = int(round(site_work*scale))
    shell = int(round(shell*scale))
    mep_yard = max(1, int(round(mep_yard*scale)))
    fitup = max(1, int(round(fitup*scale)))
    L3d = int(round(L3d*scale))
    L4d = int(round(L4d*scale))
    L5d = max(1,int(round(L5d*scale)))

    # Sliders
    site_work = render_styled_slider("Site Work", 40, 180, site_work)
    shell = render_styled_slider("Shell", 60, 300, shell)
    mep_yard = render_styled_slider("MEP Yard", 30, 180, mep_yard)
    dryin_pct = render_styled_slider("Dry‑In point within Shell (%)", 10, 90, 60, "Dry‑In is the earliest allowed set for house equipment.")
    fitup = render_styled_slider("Hall Fitup", 20, 200, fitup)
    L3d = render_styled_slider("Commissioning L3", 5, 90, L3d)
    L4d = render_styled_slider("Commissioning L4", 5, 60, L4d)
    L5d = render_styled_slider("Commissioning L5", 1, 30, L5d)

    # Reset
    if st.button("Reset to Defaults"):
        st.session_state.clear()
        st.rerun()

# Determine a broad year range for holidays automatically (no UI)
max_year = 2040
min_year = min(ntp.year, ldp.year, bp.year)
years = list(range(min_year, max_year+1))
HOLIDAYS = date_utils.expand_holidays(country, years)

# ======================= Scheduling per building =======================
WW_CONST = 6 if six_day_construction else 5
WW_ADMIN = 5

def schedule_building(build_idx:int, row):
    bname = str(row["Building Name"])
    halls_count = int(row["Halls"])
    total_mw = float(row["MW (total)"]) if pd.notna(row["MW (total)"]) else 0.0
    mw_per_hall = total_mw / halls_count if halls_count > 0 else 0

    offset = (build_idx-1) * int(building_offset)
    gates = {
        "ntp": ntp + date_utils.timedelta(days=offset),
        "ldp": ldp + date_utils.timedelta(days=offset),
        "bp": bp + date_utils.timedelta(days=offset),
        "perm_power": perm_power + date_utils.timedelta(days=offset),
        "temp_power": (temp_power_date + date_utils.timedelta(days=offset)) if (temp_power_allowed and temp_power_date) else None,
    }

    civil_start = max(gates["ntp"], gates["ldp"])
    civil_finish = date_utils.add_workdays(civil_start, site_work, HOLIDAYS, workdays_per_week=WW_CONST)

    shell_trigger = date_utils.add_workdays(civil_start, 80, HOLIDAYS, workdays_per_week=WW_CONST)
    shell_start = max(shell_trigger, gates["bp"])
    shell_finish = date_utils.add_workdays(shell_start, shell, HOLIDAYS, workdays_per_week=WW_CONST)
    dryin_wd = max(1, int(round(shell * (dryin_pct/100.0))))
    dryin_date = date_utils.add_workdays(shell_start, dryin_wd, HOLIDAYS, workdays_per_week=WW_CONST)

    mep_finish = shell_finish
    mep_start = date_utils.add_workdays(mep_finish, -mep_yard, HOLIDAYS, workdays_per_week=WW_CONST)
    fitup_gate = date_utils.add_workdays(mep_start, 40, HOLIDAYS, workdays_per_week=WW_CONST)

    hall1_earliest = fitup_gate
    spacer = 90  # default per your preference; we still expose Fitup duration above
    cap_parallel = 10**6  # no explicit cap here; can add later if you want

    def commissioning_power_gate():
        return gates["temp_power"] if (temp_power_allowed and gates["temp_power"]) else gates["perm_power"]

    def schedule_one_hall(start_candidate, prev_l3_start):
        fitup_start = max(start_candidate, fitup_gate)
        fitup_finish = date_utils.add_workdays(fitup_start, fitup, HOLIDAYS, workdays_per_week=WW_CONST)
        pwr_gate_L34 = commissioning_power_gate()
        l3_candidates = [fitup_finish, pwr_gate_L34]
        if prev_l3_start:
            l3_candidates.append(date_utils.add_workdays(prev_l3_start, 5, HOLIDAYS, workdays_per_week=WW_CONST))
        L3_start = max([c for c in l3_candidates if c is not None])
        L3_finish = date_utils.add_workdays(L3_start, L3d, HOLIDAYS, workdays_per_week=WW_CONST)
        L4_start = L3_finish
        L4_finish = date_utils.add_workdays(L4_start, L4d, HOLIDAYS, workdays_per_week=WW_CONST)
        L5_start = max(L4_finish, gates["perm_power"])
        L5_finish = date_utils.add_workdays(L5_start, L5d, HOLIDAYS, workdays_per_week=WW_CONST)
        return dict(FitupStart=fitup_start, FitupFinish=fitup_finish,
                    L3Start=L3_start, L3Finish=L3_finish,
                    L4Start=L4_start, L4Finish=L4_finish,
                    L5Start=L5_start, L5Finish=L5_finish, RFS=L5_finish)

    halls = []
    active = []
    prev_l3_start = None
    for idx in range(1, halls_count+1):
        candidate = hall1_earliest if idx == 1 else halls[-1]["FitupStart"] + date_utils.timedelta(days=spacer)
        def in_progress(day): return [d for d in active if d > day]
        while len(in_progress(candidate)) >= cap_parallel:
            earliest_free = min(active)
            candidate = max(earliest_free + date_utils.timedelta(days=1), halls[-1]["FitupStart"] + date_utils.timedelta(days=spacer) if idx>1 else candidate)
        h = schedule_one_hall(candidate, prev_l3_start)
        halls.append(h)
        prev_l3_start = h["L3Start"]
        active.append(h["RFS"])
        active = [d for d in active if d >= candidate]

    return dict(
        building_name=bname,
        halls_count=halls_count,
        mw_per_hall=mw_per_hall,
        civil_start=civil_start, civil_finish=civil_finish,
        shell_start=shell_start, shell_finish=shell_finish,
        mep_start=mep_start, mep_finish=mep_finish,
        dryin_date=dryin_date, perm_power=gates["perm_power"],
        halls=halls
    )

# Build schedules
build_df = build_df.fillna({"Halls":8, "MW (total)":16.8 * 8})
buildings = []
for i in range(len(build_df)):
    buildings.append(schedule_building(i+1, build_df.iloc[i]))

equip_rows = []
for b in buildings:
    equip_rows.extend(building.get_modeled_equipment_rows(b, WW_ADMIN, HOLIDAYS))
EQUIP_DF = pd.DataFrame(equip_rows)

# ======================= UI =======================
st.title("RFS Calculator")
tab1, tab2, tab3 = st.tabs(["Results", "Timeline", "Equipment List"])

with tab1:
    st.subheader("Key Milestones per Building")
    for b in buildings:
        container = st.container()
        combinedCards = f"""
        <div class="cards-wrapper">
          <div class="cards-container">
              {render_kpi_card(b, "Civil Start", 'civil_start')}
              {render_kpi_card(b, "Dry‑In", 'dryin_date')}
              {render_kpi_card(b, "Shell Complete", 'shell_finish')}
              {render_kpi_card(b, "Permanent Power", 'perm_power')}
          </div>
        </div>
        """
        container.markdown(combinedCards, unsafe_allow_html=True)
    st.divider()
    st.subheader("Data Hall RFS (All Buildings)")
    rows = []
    for b in buildings:
        for j, h in enumerate(b["halls"], start=1):
            rows.append({
                "Building Name": b["building_name"],
                "Hall": j,
                "MW per Hall": round(b["mw_per_hall"],2),
                "Fitup Start": h["FitupStart"],
                "Fitup Finish": h["FitupFinish"],
                "L3 Start": h["L3Start"],
                "RFS (L5 Finish)": h["RFS"]
            })
    rfs_df = pd.DataFrame(rows)
    # st.dataframe(rfs_df, hide_index=True, use_container_width=True)

    render_styled_table(rfs_df)

    st.download_button("Download RFS (CSV)", rfs_df.to_csv(index=False).encode("utf-8"), "rfs_multi_building.csv", "text/csv")

with tab2:
    st.subheader("Project Timeline")
    gantt_rows = []
    for b in buildings:
        gantt_rows.append({"Task": f"{b['building_name']} • Shell", "Start": b["shell_start"], "Finish": b["shell_finish"], "Phase":"Shell"})
        gantt_rows.append({"Task": f"{b['building_name']} • MEP Yard", "Start": b["mep_start"], "Finish": b["mep_finish"], "Phase":"MEP Yard"})
        for j, h in enumerate(b["halls"], start=1):
            gantt_rows += [
                {"Task": f"{b['building_name']} • Hall {j} • Fitup", "Start": h["FitupStart"], "Finish": h["FitupFinish"], "Phase":"Fitup"},
                {"Task": f"{b['building_name']} • Hall {j} • L3",     "Start": h["L3Start"],    "Finish": h["L3Finish"],   "Phase":"L3"},
                {"Task": f"{b['building_name']} • Hall {j} • L4",     "Start": h["L4Start"],    "Finish": h["L4Finish"],   "Phase":"L4"},
                {"Task": f"{b['building_name']} • Hall {j} • L5",     "Start": h["L5Start"],    "Finish": h["L5Finish"],   "Phase":"L5"},
            ]
    gdf = pd.DataFrame(gantt_rows)
    render_gantt(gdf)

with tab3:
    st.subheader("Equipment List")
    # st.dataframe(EQUIP_DF, hide_index=True, use_container_width=True)
    render_styled_table(EQUIP_DF, [110, 200, 90, 110, 90, 90, 90, 90, 110])
    st.download_button("Download Equipment (CSV)", EQUIP_DF.to_csv(index=False).encode("utf-8"), "equipment_roj.csv", "text/csv")

st.markdown('<p class="small-muted">Calendar uses United States public holidays • Site Work waits for Notice to Proceed & Land Disturbance Permit • Shell waits for the Building Permit and begins 80 working days after Site Work starts • MEP Yard runs finish-to-finish with Shell • Hall Fitup starts 40 working days after MEP Yard starts • L3 ties to the prior hall (SS+5) and L3/L4 may use Temporary Power • L5 waits for Permanent Power • House equipment ≥ Dry‑In; Hall equipment during Fitup.</p>', unsafe_allow_html=True)

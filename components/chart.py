import streamlit as st
import utils.colors as colors

# ---- Plotly guard (clear message if missing on Cloud) ----
try:
    import plotly.express as px
except ModuleNotFoundError:
    st.error("Plotly isn’t installed. Add `plotly==6.3.0` to requirements.txt and Restart the app.")
    st.stop()


def render_gantt(schedule_df):
    """Render a gantt chart for the supplied schedule dataframe."""
    if schedule_df.empty:
        st.info("Add steps to display the gantt chart.")
        return

    # Plotly expects y-axis inverted for gantt readability
    gantt_df = schedule_df.copy()
    gantt_df["Task"] = gantt_df["Step"]
    gantt_df["Phase"] = gantt_df.get("Category", "Vendor Onboarding Step")

    base_colors = [
        colors.MANO_BLUE,
        colors.FITOUT_COLOR,
        colors.L3_COLOR,
        colors.L4_COLOR,
        colors.L5_COLOR,
        colors.MANO_GREY,
    ]
    unique_phases = list(dict.fromkeys(gantt_df["Phase"].tolist()))
    color_map = {phase: base_colors[i % len(base_colors)] for i, phase in enumerate(unique_phases)}

    fig = px.timeline(
        gantt_df,
        x_start="Start",
        x_end="Finish",
        y="Task",
        color="Phase",
        color_discrete_map=color_map,
        hover_data={"Duration (work days)": True},
        title="",
    )
    fig.update_xaxes(showgrid=True, gridcolor="lightgray", linewidth=1, linecolor=colors.MANO_BLUE)
    fig.update_yaxes(showgrid=True, autorange="reversed", linewidth=1, linecolor=colors.MANO_BLUE)
    fig.update_layout(
        plot_bgcolor="#FFFFFF",
        paper_bgcolor=colors.MANO_OFFWHITE,
        font_family="Raleway",
        legend_title_text="Category",
        margin=dict(l=0, r=0, t=10, b=0),
    )
    st.plotly_chart(fig, use_container_width=True)


import streamlit as st
import utils.colors as colors

# ---- Plotly guard (clear message if missing on Cloud) ----
try:
    import plotly.express as px
    from plotly import graph_objects as go
except ModuleNotFoundError:
    st.error("Plotly isn’t installed. Add `plotly==6.3.0` to requirements.txt and Restart the app.")
    st.stop()


def render_schedule_gantt(tasks_df, milestone_points, milestone_track_label="Milestones"):
    """Render a Mano-branded Gantt chart with milestone markers."""

    if tasks_df.empty:
        st.info("Add at least one step to see the schedule timeline.")
        return

    # Always display tasks from the earliest start date at the top of the chart.
    sorted_tasks = (
        tasks_df.sort_values(by=["Start", "Finish", "Step"], ascending=[True, True, True])
        .reset_index(drop=True)
    )

    # Build the base timeline with a consistent Mano Blue bar colour.
    timeline_fig = px.timeline(
        sorted_tasks,
        x_start="Start",
        x_end="Finish",
        y="Step",
        color_discrete_sequence=[colors.MANO_BLUE],
        custom_data=["Start", "Finish"],
    )

    # Remove the base trace from the legend and ensure Mano styling.
    timeline_fig.update_traces(
        showlegend=False,
        selector={"type": "bar"},
        hovertemplate="<b>%{y}</b><br>Start: %{customdata[0]|%b %d, %Y}<br>Finish: %{customdata[1]|%b %d, %Y}<extra></extra>",
    )

    # Keep the explicit order of tasks as defined in the dataframe.
    ordered_steps = list(dict.fromkeys(sorted_tasks["Step"].tolist()))

    def ensure_step(step_name):
        if step_name not in ordered_steps:
            ordered_steps.append(step_name)

    # Add milestone markers as scatter traces.
    for point in milestone_points:
        milestone_date = point.get("date")
        if not milestone_date:
            continue
        label = point.get("label", "Milestone")
        color = point.get("color", colors.MANO_BLUE)
        y_value = point.get("step") or milestone_track_label
        ensure_step(y_value)
        timeline_fig.add_trace(
            go.Scatter(
                x=[milestone_date],
                y=[y_value],
                mode="markers",
                marker=dict(color=color, size=14, symbol="circle", line=dict(color="#FFFFFF", width=2)),
                name=label,
                hovertemplate=f"<b>{label}</b><br>%{{x|%b %d, %Y}}<extra></extra>",
            )
        )

    timeline_fig.update_yaxes(
        showgrid=True,
        autorange="reversed",
        linewidth=1,
        linecolor=colors.MANO_BLUE,
        categoryorder="array",
        categoryarray=list(reversed(ordered_steps)) if ordered_steps else None,
    )
    timeline_fig.update_xaxes(showgrid=True, gridcolor="lightgray", linewidth=1, linecolor=colors.MANO_BLUE)
    timeline_fig.update_layout(
        plot_bgcolor="#FFFFFF",
        paper_bgcolor=colors.MANO_OFFWHITE,
        font_family="Raleway",
        hoverlabel=dict(font=dict(family="Raleway")),
        legend_title_text="Milestones",
        margin=dict(l=20, r=20, t=40, b=20),
    )

    st.plotly_chart(timeline_fig, use_container_width=True)

import streamlit as st
import pandas as pd
import utils.colors as colors

# ---- Plotly guard (clear message if missing on Cloud) ----
try:
    import plotly.graph_objects as go
except ModuleNotFoundError:
    st.error("Plotly isn’t installed. Add `plotly==6.3.0` to requirements.txt and Restart the app.")
    st.stop()


def render_gantt(schedule_df, color_map=None):
    """Render a single-line onboarding timeline with callout nodes."""
    if schedule_df.empty:
        st.info("Add steps to display the timeline.")
        return

    timeline_df = schedule_df.sort_values("Start").copy()
    viz_col = "Visualization"
    if viz_col in timeline_df.columns:
        segments_df = timeline_df[timeline_df[viz_col] != "callout"]
        callouts_df = timeline_df[timeline_df[viz_col] == "callout"]
    else:
        segments_df = timeline_df
        callouts_df = timeline_df.iloc[0:0]

    if color_map is None:
        ordered_steps = timeline_df["Step"].tolist()
        palette = [
            colors.MANO_BLUE,
            colors.FITOUT_COLOR,
            colors.L3_COLOR,
            colors.L4_COLOR,
            colors.L5_COLOR,
            colors.MANO_GREY,
        ]
        color_map = {}
        for idx, step in enumerate(ordered_steps):
            if step not in color_map:
                color_map[step] = palette[idx % len(palette)]

    baseline_start = timeline_df["Start"].min()
    baseline_end = timeline_df["Finish"].max()

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=[baseline_start, baseline_end],
            y=[-0.05, -0.05],
            mode="lines",
            line=dict(color="rgba(36, 51, 59, 0.35)", width=6, shape="linear"),
            hoverinfo="skip",
            showlegend=False,
        )
    )

    legend_steps = set()
    duration_key = "Duration (work days)"

    for _, row in segments_df.iterrows():
        step = row["Step"]
        start = row["Start"]
        finish = row["Finish"]
        color = color_map.get(step, colors.MANO_BLUE)
        duration = row.get(duration_key, None)
        duration_label = f"{duration} work days" if duration is not None else "—"
        customdata = [[start, finish, duration_label]] * 2

        fig.add_trace(
            go.Scatter(
                x=[start, finish],
                y=[0, 0],
                mode="lines",
                line=dict(color=color, width=18, shape="linear"),
                hovertemplate=(
                    f"<b>{step}</b><br>"
                    "Start: %{customdata[0]|%b %d, %Y}<br>"
                    "Finish: %{customdata[1]|%b %d, %Y}<br>"
                    "Duration: %{customdata[2]}<extra></extra>"
                ),
                customdata=customdata,
                legendgroup=step,
                showlegend=False,
            )
        )

        midpoint = start
        if pd.notna(start) and pd.notna(finish):
            midpoint = start + (finish - start) / 2
        node_custom = [[start, finish, duration_label]]
        fig.add_trace(
            go.Scatter(
                x=[midpoint],
                y=[0.22],
                mode="markers+text",
                marker=dict(
                    color=color,
                    size=18,
                    line=dict(color=colors.MANO_OFFWHITE, width=2),
                    symbol="circle",
                ),
                text=[step],
                textposition="top center",
                textfont=dict(size=12, color=colors.MANO_GREY),
                customdata=node_custom,
                hovertemplate=(
                    f"<b>{step}</b><br>"
                    "Start: %{customdata[0]|%b %d, %Y}<br>"
                    "Finish: %{customdata[1]|%b %d, %Y}<br>"
                    "Duration: %{customdata[2]}<extra></extra>"
                ),
                legendgroup=step,
                showlegend=step not in legend_steps,
                name=step,
            )
        )
        legend_steps.add(step)

    for _, row in callouts_df.iterrows():
        step = row["Step"]
        marker_date = row.get("MarkerDate", row["Finish"])
        start = row["Start"]
        finish = row["Finish"]
        if pd.isna(marker_date):
            marker_date = finish if pd.notna(finish) else start
        duration = row.get(duration_key, None)
        duration_label = f"{duration} work days" if duration is not None else "—"
        color = color_map.get(step, color_map.get("RFP Issued", colors.MANO_BLUE))
        fig.add_trace(
            go.Scatter(
                x=[marker_date],
                y=[0.45],
                mode="markers+text",
                marker=dict(
                    color=color,
                    size=14,
                    symbol="diamond",
                    line=dict(color=colors.MANO_OFFWHITE, width=1.5),
                ),
                text=[step],
                textposition="top center",
                textfont=dict(size=11, color=colors.MANO_GREY),
                customdata=[[start, finish, duration_label]],
                hovertemplate=(
                    f"<b>{step}</b><br>"
                    "Start: %{customdata[0]|%b %d, %Y}<br>"
                    "Finish: %{customdata[1]|%b %d, %Y}<br>"
                    "Duration: %{customdata[2]}<extra></extra>"
                ),
                legendgroup=step,
                showlegend=False,
            )
        )

    fig.update_xaxes(
        showgrid=True,
        gridcolor="rgba(36, 51, 59, 0.15)",
        linewidth=1,
        linecolor=colors.MANO_BLUE,
        zeroline=False,
    )
    fig.update_yaxes(visible=False, range=[-0.2, 0.8])
    fig.update_layout(
        plot_bgcolor="#FFFFFF",
        paper_bgcolor=colors.MANO_OFFWHITE,
        font_family="Raleway",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.25,
            x=0,
            xanchor="left",
            title="Timeline Key",
        ),
        margin=dict(l=0, r=0, t=30, b=60),
        hoverlabel=dict(
            bgcolor=colors.MANO_BLUE,
            font=dict(color=colors.MANO_OFFWHITE, family="Raleway"),
        ),
    )

    st.plotly_chart(fig, use_container_width=True)

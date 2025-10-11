def render_kpi_card(building, label, key, color=None):
  dot = ""
  if color:
    dot = f"<span class=\"milestone-dot\" style=\"background:{color}\"></span>"
  return (
    "<div class=\"kpi-card\">"
    "<div class=\"label-row\">"
    f"{dot}<span class='label'>{label}</span>"
    "</div>"
    f"<span class='date'>{building[key]}</span>"
    "</div>"
  )

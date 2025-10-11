def render_kpi_card(title, label, value, accent_color=None):
  border_style = f" style=\"border-left-color: {accent_color};\"" if accent_color else ""
  dot_html = f"<span class='milestone-dot' style='background: {accent_color};'></span>" if accent_color else ""
  return (
      f"<div class=\"kpi-card\"{border_style}>"
      f"  <div class='kpi-card-header'>{dot_html}<div><p>{title}</p><span class='label'>{label}</span></div></div>"
      f"  <span class='date'>{value}</span>"
      f"</div>"
  )

import utils.colors as colors

def render_kpi_card(building, label, key):
  return f"<div class=\"kpi-card\"><div><p>{building['building_name']}</p><span class='label'>{label}</span></div><span class='date'>{building[key]}</span></div>"

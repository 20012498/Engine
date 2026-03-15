from logic.criteria.pore import render_pore
from logic.criteria.sppa import render_sppa

def render_criteria_simulator(code, det, lov_df):
    if code == "PORE": return render_pore(det, lov_df, code)
    if code == "SPPA": return render_sppa(det, code)
    return None
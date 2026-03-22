import streamlit as st
import json
from logic.bq_tools import execute_engine_simulation

def render_wcta(details, lovs=None):
    st.markdown("**Consommation d'eau - robinets**")

    d = details[0]
    att_id = str(d.get('att_id', '')).strip()
    curr_val = d.get('current_value', 0)
    try:
        default_val = float(curr_val) if curr_val not in [None, '', 'None'] else 0.0
    except:
        default_val = 0.0

    val = st.number_input(f"Débit (L/min) ({att_id})", value=default_val, min_value=0.0, step=0.01, key=f"wcta_{att_id}")

    return {"code": "WCTA", "val": val}


def simulate_wcta(bu_id, prod_ref, p_info, choice):
    if not choice or choice.get('val') is None:
        return 0, {}, ""

    json_entry = {
        "productBuReference": int(prod_ref),
        "businessUnitIdentifier": int(bu_id),
        "productDescriptiveModelIdentifier": str(p_info.get('productDescriptiveModelIdentifier', '')),
        "criteria": [{
            "criteriaCode": "WCTA",
            "criteriaValue": str(choice['val'])
        }]
    }

    res = execute_engine_simulation({"calls": [[json_entry]]})
    print("DEBUG WCTA res:", res)

    note = 0
    try:
        if res and "f0_" in res[0]:
            raw = res[0]["f0_"]
            data = raw[0] if isinstance(raw, list) else raw
            for pillar in data.get('pillars', []):
                for crit in pillar.get('criteria', []):
                    if crit.get('criteriaCode') == 'WCTA':
                        note = crit.get('criteriaNote', 0)
                        break
    except Exception as e:
        st.write("Erreur parsing WCTA:", e)

    full_func_name = "`din-homeindex-dev-irq.asfr_home_index_score_flow`.call_single_engine"
    sql_debug = f"SELECT {full_func_name}(PARSE_JSON('{json.dumps(json_entry)}'))"

    return note, json_entry, sql_debug
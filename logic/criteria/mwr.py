import streamlit as st
import json
from logic.bq_tools import execute_engine_simulation

def render_mwr(details, lovs=None):
    st.markdown("**Garantie fabricant**")

    d = details[0]
    att_id = str(d.get('att_id', '')).strip()
    curr_val = d.get('current_value', 0)
    try:
        default_val = int(float(curr_val)) if curr_val not in [None, '', 'None'] else 0
    except:
        default_val = 0

    val = st.number_input(f"Durée garantie (années) ({att_id})", value=default_val, min_value=0, key=f"mwr_{att_id}")

    return {"code": "MWR", "val": val}


def simulate_mwr(bu_id, prod_ref, p_info, choice):
    if not choice or choice.get('val') is None:
        return 0, {}, ""

    json_entry = {
        "productBuReference": int(prod_ref),
        "businessUnitIdentifier": int(bu_id),
        "productDescriptiveModelIdentifier": str(p_info.get('productDescriptiveModelIdentifier', '')),
        "criteria": [{
            "criteriaCode": "MWR",
            "criteriaValue": str(choice['val'])
        }]
    }

    res = execute_engine_simulation({"calls": [[json_entry]]})
    print("DEBUG MWR res:", res)

    note = 0
    try:
        if res and "f0_" in res[0]:
            raw = res[0]["f0_"]
            data = raw[0] if isinstance(raw, list) else raw
            for pillar in data.get('pillars', []):
                for crit in pillar.get('criteria', []):
                    if crit.get('criteriaCode') == 'MWR':
                        note = crit.get('criteriaNote', 0)
                        break
    except Exception as e:
        st.write("Erreur parsing MWR:", e)

    full_func_name = "`din-homeindex-dev-irq.asfr_home_index_score_flow`.call_single_engine"
    sql_debug = f"SELECT {full_func_name}(PARSE_JSON('{json.dumps(json_entry)}'))"

    return note, json_entry, sql_debug
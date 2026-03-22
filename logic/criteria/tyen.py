import streamlit as st
import json
from logic.bq_tools import execute_engine_simulation

def render_tyen(details, lovs=None):
    st.markdown("**Type d'énergie utilisée**")

    d = details[0]
    curr_val = str(d.get('current_value', '')).strip()

    val = st.text_input("Code modèle (productDescriptiveModelIdentifier)", value=curr_val, key="tyen_val")

    return {"code": "TYEN", "val": val}


def simulate_tyen(bu_id, prod_ref, p_info, choice):
    if not choice or not choice.get('val'):
        return 0, {}, ""

    json_entry = {
        "productBuReference": int(prod_ref),
        "businessUnitIdentifier": int(bu_id),
        "productDescriptiveModelIdentifier": str(p_info.get('productDescriptiveModelIdentifier', '')),
        "criteria": [{
            "criteriaCode": "TYEN",
            "criteriaValueIdentifier": str(choice['val'])
        }]
    }

    res = execute_engine_simulation({"calls": [[json_entry]]})
    print("DEBUG TYEN res:", res)

    note = 0
    try:
        if res and "f0_" in res[0]:
            raw = res[0]["f0_"]
            data = raw[0] if isinstance(raw, list) else raw
            for pillar in data.get('pillars', []):
                for crit in pillar.get('criteria', []):
                    if crit.get('criteriaCode') == 'TYEN':
                        note = crit.get('criteriaNote', 0)
                        break
    except Exception as e:
        st.write("Erreur parsing TYEN:", e)

    full_func_name = "`din-homeindex-dev-irq.asfr_home_index_score_flow`.call_single_engine"
    sql_debug = f"SELECT {full_func_name}(PARSE_JSON('{json.dumps(json_entry)}'))"

    return note, json_entry, sql_debug
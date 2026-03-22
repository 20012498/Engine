import streamlit as st
import json
from logic.bq_tools import execute_engine_simulation

def render_prof(details, lovs=None):
    st.markdown("**Profil produit**")

    d = details[0]
    # Pour PROF, current_value EST le productDescriptiveModelIdentifier
    # On prend current_value_id si disponible, sinon current_value
    curr_val = str(d.get('current_value_id') or d.get('current_value', '')).strip()
    if curr_val in ['None', 'nan', '']:
        curr_val = str(d.get('current_value', '')).strip()

    val = st.text_input("Code modèle (productDescriptiveModelIdentifier)", value=curr_val, key="prof_val")

    return {"code": "PROF", "val": val}


def simulate_prof(bu_id, prod_ref, p_info, choice):
    if not choice or not choice.get('val'):
        return 0, {}, ""

    json_entry = {
        "productBuReference": int(prod_ref),
        "businessUnitIdentifier": int(bu_id),
        "productDescriptiveModelIdentifier": str(p_info.get('productDescriptiveModelIdentifier', '')),
        "criteria": [{
            "criteriaCode": "PROF",
            "criteriaValueIdentifier": str(choice['val'])
        }]
    }

    res = execute_engine_simulation({"calls": [[json_entry]]})
    print("DEBUG PROF res:", res)

    note = 0
    try:
        if res and "f0_" in res[0]:
            raw = res[0]["f0_"]
            data = raw[0] if isinstance(raw, list) else raw
            for pillar in data.get('pillars', []):
                for crit in pillar.get('criteria', []):
                    if crit.get('criteriaCode') == 'PROF':
                        note = crit.get('criteriaNote', 0)
                        break
    except Exception as e:
        st.write("Erreur parsing PROF:", e)

    full_func_name = "`din-homeindex-dev-irq.asfr_home_index_score_flow`.call_single_engine"
    sql_debug = f"SELECT {full_func_name}(PARSE_JSON('{json.dumps(json_entry)}'))"

    return note, json_entry, sql_debug
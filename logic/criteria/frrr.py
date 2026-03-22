import streamlit as st
import json
from logic.bq_tools import execute_engine_simulation

def render_frrr(details, lovs=None):
    st.markdown("**Taux de retour / réclamation**")
    choices = []

    for d in details:
        att_id = str(d.get('att_id', '')).strip()
        att_name = d.get('att_name', '')
        curr_val = str(d.get('current_value', '0')).strip()

        try:
            default_val = int(float(curr_val)) if curr_val not in ['None', '', 'null'] else 0
        except:
            default_val = 0

        val = st.number_input(f"{att_name}", value=default_val, min_value=0, key=f"frrr_{att_id}")
        choices.append({"att_id": att_id, "val": val})

    return {"code": "FRRR", "choices": choices}


def simulate_frrr(bu_id, prod_ref, p_info, choice):
    if not choice or not choice.get('choices'):
        return 0, {}, ""

    characteristics = []
    for c in choice['choices']:
        characteristics.append({
            "characteristicName": c['att_id'],
            "characteristicValue": c['val']
        })

    json_entry = {
        "productBuReference": int(prod_ref),
        "businessUnitIdentifier": int(bu_id),
        "productDescriptiveModelIdentifier": str(p_info.get('productDescriptiveModelIdentifier', '')),
        "criteria": [{
            "criteriaCode": "FRRR",
            "characteristic": characteristics
        }]
    }

    res = execute_engine_simulation({"calls": [[json_entry]]})
    print("DEBUG FRRR res:", res)

    note = 0
    try:
        if res and "f0_" in res[0]:
            raw = res[0]["f0_"]
            data = raw[0] if isinstance(raw, list) else raw
            for pillar in data.get('pillars', []):
                for crit in pillar.get('criteria', []):
                    if crit.get('criteriaCode') == 'FRRR':
                        note = crit.get('criteriaNote', 0)
                        break
    except Exception as e:
        st.write("Erreur parsing FRRR:", e)

    full_func_name = "`din-homeindex-dev-irq.asfr_home_index_score_flow`.call_single_engine"
    sql_debug = f"SELECT {full_func_name}(PARSE_JSON('{json.dumps(json_entry)}'))"

    return note, json_entry, sql_debug
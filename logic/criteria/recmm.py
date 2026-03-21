import streamlit as st
import json
from logic.bq_tools import execute_engine_simulation

def render_recmm(details, lovs):
    st.markdown("**Recyclabilité du matériau principal**")
    
    d = details[0]
    att_id = str(d.get('att_id', '')).strip()
    curr_val = str(d.get('current_value', '')).strip()

    col_label = 'characteristicValue' if 'characteristicValue' in lovs.columns else 'label'
    col_id = 'characteristicValueCode' if 'characteristicValueCode' in lovs.columns else 'id'

    options = lovs[col_label].tolist() if not lovs.empty else []
    if not options:
        options = [curr_val] if curr_val else ["N/A"]

    default_idx = options.index(curr_val) if curr_val in options else 0

    val = st.selectbox(f"Matériau principal ({att_id})", options, index=default_idx, key=f"recmm_{att_id}")

    try:
        val_id = lovs[lovs[col_label] == val].iloc[0][col_id]
    except:
        val_id = val

    return {"code": "RECMM", "val": val, "val_id": str(val_id)}


def simulate_recmm(bu_id, prod_ref, p_info, choice):
    if not choice or not choice.get('val'):
        return 0, {}, ""

    json_entry = {
        "productBuReference": int(prod_ref),
        "businessUnitIdentifier": int(bu_id),
        "productDescriptiveModelIdentifier": str(p_info.get('productDescriptiveModelIdentifier', '')),
        "criteria": [{
            "criteriaCode": "RECMM",
            "criteriaValue": str(choice['val'])
        }]
    }

    res = execute_engine_simulation({"calls": [[json_entry]]})
    print("DEBUG RECMM res:", res)

    note = 0
    try:
        if res and "f0_" in res[0]:
            raw = res[0]["f0_"]
            data = raw[0] if isinstance(raw, list) else raw
            for pillar in data.get('pillars', []):
                for crit in pillar.get('criteria', []):
                    if crit.get('criteriaCode') == 'RECMM':
                        note = crit.get('criteriaNote', 0)
                        break
    except Exception as e:
        st.write("Erreur parsing RECMM:", e)

    full_func_name = "`din-homeindex-dev-irq.asfr_home_index_score_flow`.call_single_engine"
    sql_debug = f"SELECT {full_func_name}(PARSE_JSON('{json.dumps(json_entry)}'))"

    return note, json_entry, sql_debug
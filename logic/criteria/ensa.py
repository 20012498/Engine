import streamlit as st
import json
from logic.bq_tools import execute_engine_simulation

def render_ensa(details, lovs):
    st.markdown(f"**Classe Énergétique**")
    
    if isinstance(details, list) and len(details) > 0:
        d = details[0]
    elif hasattr(details, 'iloc') and not details.empty:
        d = details.iloc[0]
    else:
        d = {}
        
    curr_val = str(d.get('current_value', ''))
    
    col_label = 'label' if 'label' in lovs.columns else 'characteristicValue'
    col_id = 'id' if 'id' in lovs.columns else 'characteristicValueCode'
    
    options = lovs[col_label].tolist() if col_label in lovs.columns else []
    
    try:
        default_idx = options.index(curr_val)
    except:
        default_idx = 0
    
    val = st.selectbox("Sélectionner la classe", options, index=default_idx, key="ensa_select")
    
    try:
        v_id = lovs[lovs[col_label] == val].iloc[0][col_id]
    except:
        v_id = val

    return {"code": "ENSA", "val": val, "val_id": v_id}

def simulate_ensa(bu_id, prod_ref, p_info, choice):
    if not choice or not choice.get('val'):
        return 0, {}, "--"

    json_entry = {
        "businessUnitIdentifier": int(bu_id),
        "criteria": [{
            "criteriaCode": "ENSA",
            "criteriaValue": str(choice['val']),
            "criteriaValueIdentifier": str(choice['val_id'])
        }],
        "productBuReference": int(prod_ref),
        "productDescriptiveModelIdentifier": str(p_info.get('productDescriptiveModelIdentifier', ''))
    }

    payload = {"calls": [[json_entry]]}
    res = execute_engine_simulation(payload)
    
    note = 0
    try:
        if res and "f0_" in res[0]:
            raw = res[0]["f0_"]
            # f0_ est déjà une liste Python, pas besoin de json.loads()
            data = raw[0] if isinstance(raw, list) else raw
            for pillar in data.get('pillars', []):
                for crit in pillar.get('criteria', []):
                    if crit.get('criteriaCode') == 'ENSA':
                        note = crit.get('criteriaNote', 0)
                        break
    except Exception as e:
        st.write("Erreur parsing:", e)

    full_func_name = "`din-homeindex-dev-irq.asfr_home_index_score_flow`.call_single_engine"
    sql_debug = f"SELECT {full_func_name}(PARSE_JSON('{json.dumps(json_entry)}'))"
    
    return note, payload, sql_debug
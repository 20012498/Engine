import streamlit as st
import json
from logic.bq_tools import execute_engine_simulation

def render_pore(details, lovs):
    d = details[0]
    st.markdown(f"**Indice de réparabilité**")
    
    options = lovs['characteristicValue'].tolist()
    current_val = d.get('current_value')
    default_idx = options.index(current_val) if current_val in options else 0
    
    val = st.selectbox("Valeur", options, index=default_idx, key=f"pore_v_{d['att_id']}")
    
    try:
        v_id = lovs[lovs['characteristicValue'] == val].iloc[0]['characteristicValueCode']
    except:
        v_id = val
        
    current_proof = str(d.get('proof', 'Yes'))
    p_idx = 0 if current_proof == 'Yes' else 1
    proof = st.radio("Preuve (Simulation)", ["Yes", "No"], index=p_idx, horizontal=True, key=f"pore_p_{d['att_id']}")
    
    return {"code": "PORE", "val": val, "val_id": v_id, "att_id": d['att_id'], "proof": proof}


def simulate_pore(bu_id, prod_ref, p_info, choice):
    if not choice:
        return 0, {}, ""

    json_entry = {
        "productBuReference": int(prod_ref),
        "businessUnitIdentifier": int(bu_id),
        "productDescriptiveModelIdentifier": str(p_info.get('productDescriptiveModelIdentifier', '')),
        "supplierPurchaseSiteIdentifier": str(p_info.get('supplierPurchaseSiteIdentifier', '')),
        "criteria": [{
            "criteriaCode": "PORE",
            "criteriaValue": str(choice['val']),
            "criteriaValueIdentifier": str(choice['val_id']),
            "proof": choice['proof'],
            "characteristic": str(choice['att_id'])
        }]
    }

    res = execute_engine_simulation({"calls": [[json_entry]]})

    note = 0
    try:
        if res and "f0_" in res[0]:
            raw = res[0]["f0_"]
            data = raw[0] if isinstance(raw, list) else raw
            for pillar in data.get('pillars', []):
                for crit in pillar.get('criteria', []):
                    if crit.get('criteriaCode') == 'PORE':
                        note = crit.get('criteriaNote', 0)
                        break
    except Exception as e:
        st.write("Erreur parsing PORE:", e)

    full_func_name = "`din-homeindex-dev-irq.asfr_home_index_score_flow`.call_single_engine"
    sql_debug = f"SELECT {full_func_name}(PARSE_JSON('{json.dumps(json_entry)}'))"

    return note, json_entry, sql_debug
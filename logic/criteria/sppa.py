import streamlit as st
from logic.bq_tools import execute_engine_simulation

# --- ATTENTION : SUPPRIME TOUTE LIGNE DISANT "from logic.criteria.sppa import ..." ---

def render_sppa(det, lovs=None):
    # Titre avec Nom du critère et Code ATT
    st.markdown(f"**{det['methodName']} (SPPA)**")
    st.caption(f"ATT: {det['att_id']}")
    
    try:
        # Conversion sécurisée de la valeur actuelle
        current_val = int(float(det['current_value']))
    except:
        current_val = 0
        
    val = st.number_input("Années de garantie", value=current_val, key="sim_sppa_val")
    
    return {
        "code": "SPPA",
        "val": str(val),
        "val_id": "",
        "att_id": det['att_id'],
        "proof": "Yes"
    }

def simulate_sppa(bu_id, prod_ref, p_info, choice):
    payload = {
        "productBuReference": prod_ref,
        "businessUnitIdentifier": bu_id,
        "productDescriptiveModelIdentifier": str(p_info['productDescriptiveModelIdentifier']),
        "supplierPurchaseSiteIdentifier": str(p_info['supplierPurchaseSiteIdentifier']),
        "criteria": [{
            "criteriaCode": "SPPA",
            "criteriaValue": choice['val'],
            "criteriaValueIdentifier": "",
            "proof": "Yes",
            "characteristic": choice['att_id']
        }]
    }
    res = execute_engine_simulation(payload)
    if res:
        for pillar in res[0].get('pillars', []):
            for crit in pillar.get('criteria', []):
                if crit['criteriaCode'] == 'SPPA':
                    return crit.get('criteriaNote')
    return None
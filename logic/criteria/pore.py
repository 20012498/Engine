import streamlit as st
from logic.bq_tools import execute_engine_simulation

def render_pore(det, lovs):
    # Titre et Code ATT
    st.markdown(f"**{det['methodName']} (PORE)**")
    st.caption(f"ATT: {det['att_id']}")
    
    # Sélecteur de valeur
    options = lovs['characteristicValue'].tolist()
    default_val = det['current_value'] if det['current_value'] in options else options[0]
    val = st.selectbox("Valeur", options, index=options.index(default_val), key="sim_pore_val")
    row = lovs[lovs['characteristicValue'] == val].iloc[0]
    
    # Contrôle de la preuve
    proof = st.radio("Preuve (Proof)", ["Yes", "No"], index=0, horizontal=True, key="sim_pore_proof")
    
    return {
        "code": "PORE",
        "val": val,
        "val_id": row['characteristicValueCode'],
        "att_id": det['att_id'],
        "proof": proof
    }

def simulate_pore(bu_id, prod_ref, p_info, choice):
    payload = {
        "productBuReference": prod_ref,
        "businessUnitIdentifier": bu_id,
        "productDescriptiveModelIdentifier": str(p_info['productDescriptiveModelIdentifier']),
        "supplierPurchaseSiteIdentifier": str(p_info['supplierPurchaseSiteIdentifier']),
        "criteria": [{
            "criteriaCode": "PORE",
            "criteriaValue": choice['val'],
            "criteriaValueIdentifier": choice['val_id'],
            "proof": choice['proof'], # Utilisation dynamique du choix UI
            "characteristic": choice['att_id']
        }]
    }
    res = execute_engine_simulation(payload)
    if res:
        for pillar in res[0].get('pillars', []):
            for crit in pillar.get('criteria', []):
                if crit['criteriaCode'] == 'PORE':
                    return crit.get('criteriaNote')
    return None
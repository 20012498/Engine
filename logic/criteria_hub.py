import streamlit as st
import json
from logic.bq_tools import call_engine_raw

def simulate_pore(bu_id, prod_ref, model_id, supplier_id, choice):
    """Simulation spécifique pour PORE."""
    # Construction du JSON spécifique à PORE
    payload = {
        "productBuReference": prod_ref,
        "businessUnitIdentifier": bu_id,
        "productDescriptiveModelIdentifier": str(model_id),
        "supplierPurchaseSiteIdentifier": str(supplier_id),
        "criteria": [{
            "criteriaCode": "PORE",
            "criteriaValue": choice['val'],
            "criteriaValueIdentifier": choice['val_id'],
            "proof": "Yes",
            "characteristic": choice['att_id']
        }]
    }
    
    res_json = call_engine_raw(json.dumps(payload))
    if res_json:
        data = json.loads(res_json)
        # Extraction de la note dans la structure complexe de l'Engine
        for pillar in data[0].get('pillars', []):
            for crit in pillar.get('criteria', []):
                if crit['criteriaCode'] == 'PORE':
                    return crit.get('criteriaNote')
    return None

def simulate_sppa(bu_id, prod_ref, model_id, supplier_id, choice):
    """Simulation spécifique pour SPPA (Durée)."""
    payload = {
        "productBuReference": prod_ref,
        "businessUnitIdentifier": bu_id,
        "productDescriptiveModelIdentifier": str(model_id),
        "supplierPurchaseSiteIdentifier": str(supplier_id),
        "criteria": [{
            "criteriaCode": "SPPA",
            "criteriaValue": str(choice['val']),
            "criteriaValueIdentifier": "", # Toujours vide pour SPPA
            "proof": "Yes",
            "characteristic": choice['att_id']
        }]
    }
    
    res_json = call_engine_raw(json.dumps(payload))
    if res_json:
        data = json.loads(res_json)
        for pillar in data[0].get('pillars', []):
            for crit in pillar.get('criteria', []):
                if crit['criteriaCode'] == 'SPPA':
                    return crit.get('criteriaNote')
    return None

def render_criteria_simulator(code, det, lovs):
    """Affiche le widget de sélection (reste identique)."""
    if code == "PORE":
        options = lovs['characteristicValue'].tolist()
        val = st.selectbox(f"Modif {code}", options, key=f"sim_{code}")
        row = lovs[lovs['characteristicValue'] == val].iloc[0]
        return {"code": code, "val": val, "val_id": row['characteristicValueCode'], "att_id": det['att_id']}
    
    if code == "SPPA":
        val = st.number_input(f"Années {code}", value=int(det['current_value']), key=f"sim_{code}")
        return {"code": code, "val": val, "val_id": "", "att_id": det['att_id']}
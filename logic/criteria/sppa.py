import streamlit as st
import json
from logic.bq_tools import execute_engine_simulation

def render_sppa(details, lovs=None):
    st.markdown("**Disponibilité pièces détachées**")
    choices = []

    for d in details:
        att_id = str(d.get('att_id')).strip()
        att_name = d.get('att_name', '')
        curr_val = str(d.get('current_value', '')).strip()

        if att_id == "17017" or "durée" in att_name.lower() or "année" in att_name.lower():
            try:
                default_val = int(float(curr_val)) if curr_val not in ['None', ''] else 0
            except:
                default_val = 0
            
            val = st.number_input(f"{att_name}", value=default_val, min_value=0, key=f"sppa_v_{att_id}")
            choices.append({"att_id": att_id, "val": str(val)})
            
    if not choices and details:
        d = details[0]
        val = st.number_input(f"Fallback: {d.get('att_name')}", value=0, key="sppa_fallback")
        choices.append({"att_id": str(d.get('att_id')), "val": str(val)})

    return {"code": "SPPA", "choices": choices}


def simulate_sppa(bu_id, prod_ref, p_info, choice):
    if not choice or not choice.get('choices'):
        return 0, {}, "ERREUR : Aucun attribut sélectionné pour la simulation"

    criteria_items = []
    for c in choice['choices']:
        criteria_items.append({
            "criteriaCode": "SPPA",
            "criteriaValue": str(c['val']),
            "criteriaValueIdentifier": "",
            "proof": "Yes",
            "characteristic": str(c['att_id'])
        })

    json_entry = {
        "productBuReference": int(prod_ref),
        "businessUnitIdentifier": int(bu_id),
        "productDescriptiveModelIdentifier": str(p_info.get('productDescriptiveModelIdentifier', '')),
        "supplierPurchaseSiteIdentifier": str(p_info.get('supplierPurchaseSiteIdentifier', '')),
        "criteria": criteria_items
    }

    res = execute_engine_simulation({"calls": [[json_entry]]})
    
    note = 0
    try:
        if res and "f0_" in res[0]:
            raw = res[0]["f0_"]
            data = raw[0] if isinstance(raw, list) else raw
            for pillar in data.get('pillars', []):
                for crit in pillar.get('criteria', []):
                    if crit.get('criteriaCode') == 'SPPA':
                        note = crit.get('criteriaNote', 0)
                        break
    except Exception as e:
        st.write("Erreur parsing SPPA:", e)

    full_func_name = "`din-homeindex-dev-irq.asfr_home_index_score_flow`.call_single_engine"
    sql_debug = f"SELECT {full_func_name}(PARSE_JSON('{json.dumps(json_entry)}'))"

    return note, json_entry, sql_debug
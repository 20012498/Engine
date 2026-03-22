import streamlit as st
import json
from logic.bq_tools import execute_engine_simulation

def render_rewo(details, lovs=None):
    st.markdown("**Bois responsable**")

    d = details[0]
    curr_val = str(d.get('current_value', 'false')).strip()
    curr_proof = str(d.get('proof', 'Yes')).strip()

    val = st.radio(
        "Certification bois responsable",
        ["true", "false"],
        index=0 if curr_val == "true" else 1,
        horizontal=True,
        key="rewo_val"
    )

    proof = st.radio(
        "Preuve",
        ["Yes", "No"],
        index=0 if curr_proof == "Yes" else 1,
        horizontal=True,
        key="rewo_proof"
    )

    return {"code": "REWO", "val": val, "proof": proof}


def simulate_rewo(bu_id, prod_ref, p_info, choice):
    if not choice:
        return 0, {}, ""

    json_entry = {
        "productBuReference": int(prod_ref),
        "businessUnitIdentifier": int(bu_id),
        "productDescriptiveModelIdentifier": str(p_info.get('productDescriptiveModelIdentifier', '')),
        "criteria": [{
            "criteriaCode": "REWO",
            "criteriaValue": str(choice['val']),
            "proof": str(choice['proof'])
        }]
    }

    res = execute_engine_simulation({"calls": [[json_entry]]})
    print("DEBUG REWO res:", res)

    note = 0
    try:
        if res and "f0_" in res[0]:
            raw = res[0]["f0_"]
            data = raw[0] if isinstance(raw, list) else raw
            for pillar in data.get('pillars', []):
                for crit in pillar.get('criteria', []):
                    if crit.get('criteriaCode') == 'REWO':
                        note = crit.get('criteriaNote', 0)
                        break
    except Exception as e:
        st.write("Erreur parsing REWO:", e)

    full_func_name = "`din-homeindex-dev-irq.asfr_home_index_score_flow`.call_single_engine"
    sql_debug = f"SELECT {full_func_name}(PARSE_JSON('{json.dumps(json_entry)}'))"

    return note, json_entry, sql_debug
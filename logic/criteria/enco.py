import streamlit as st
import json
from logic.bq_tools import execute_engine_simulation

ENERGY_CLASSES = ["A+++", "A++", "A+", "A", "B", "C", "D", "E", "F", "G"]

# Mapping ATT_ID -> characteristicName pour le payload
ATT_TO_CHARACTERISTIC = {
    "ATT_25732": "energyConsumptionGrades25732",
    "ATT_26515": "energyConsumptionGrades26515",
    "ATT_25766": "energyConsumptionGrades25766",
    "ATT_25768": "energyConsumptionGrades25768",
    "ATT_25769": "energyConsumptionGrades25769",
    "ATT_25771": "energyConsumptionGrades25771",
    "ATT_07180": "energyConsumptionGrades07180",
    "ATT_26059": "energyConsumptionGrades26059",
}

def render_enco(details, lovs):
    st.markdown("**Consommation d'énergie**")
    choices = []

    for d in details:
        att_id = str(d.get('att_id', '')).strip()
        att_name = d.get('att_name', '')
        curr_val = str(d.get('current_value', '')).strip()

        # Champs avec LOV (selectbox)
        col_label = 'characteristicValue' if 'characteristicValue' in lovs.columns else 'label'
        col_id = 'characteristicValueCode' if 'characteristicValueCode' in lovs.columns else 'id'

        options = lovs[col_label].tolist() if not lovs.empty else ENERGY_CLASSES

        options = [o for o in options if o in ENERGY_CLASSES]
        if not options:
            options = ENERGY_CLASSES

        # Fallback sur ENERGY_CLASSES si LOV vide
        if not options:
            options = ENERGY_CLASSES

        default_idx = options.index(curr_val) if curr_val in options else 0

        val = st.selectbox(
            f"{att_name} ({att_id})",
            options,
            index=default_idx,
            key=f"enco_{att_id}"
        )

        # Récupération de l'ID de valeur
        try:
            val_id = lovs[lovs[col_label] == val].iloc[0][col_id]
        except:
            val_id = val

        choices.append({
            "att_id": att_id,
            "att_name": att_name,
            "val": val,
            "val_id": str(val_id)
        })

    return {"code": "ENCO", "choices": choices}


def simulate_enco(bu_id, prod_ref, p_info, choice):
    if not choice or not choice.get('choices'):
        return 0, {}, ""

    # La valeur choisie par l'utilisateur
    c = choice['choices'][0]
    val = c['val']
    val_id = c['val_id']

    # Structure exacte attendue par le moteur
    json_entry = {
        "businessUnitIdentifier": int(bu_id),
        "productBuReference": int(prod_ref),
        "productDescriptiveModelIdentifier": str(p_info.get('productDescriptiveModelIdentifier', '')),
        "criteria": [{
            "criteriaCode": "ENCO",
            "characteristic": [
                {"characteristicName": "powerSupply", "characteristicTop": 0},
                {"characteristicName": "power", "characteristicTop": 0},
                {"characteristicName": "colorTemperature", "characteristicTop": 0},
                {"characteristicName": "isSoldInEurope", "characteristicTop": 0},
                {"characteristicName": "lightSourceIsSeparable", "characteristicTop": 0},
                {"characteristicName": "energyConsumptionGrades26515", "characteristicTop": 0},
                {"characteristicName": "energyConsumptionGrades25732", "characteristicTop": 0},
                {
                    "characteristicName": "energyClass",
                    "characteristicTop": 1,
                    "characteristicValue": val,
                    "characteristicValueIdentifier": str(val_id)
                }
            ]
        }]
    }

    res = execute_engine_simulation({"calls": [[json_entry]]})
    print("DEBUG ENCO res:", res)

    note = 0
    try:
        if res and "f0_" in res[0]:
            raw = res[0]["f0_"]
            data = raw[0] if isinstance(raw, list) else raw
            for pillar in data.get('pillars', []):
                for crit in pillar.get('criteria', []):
                    if crit.get('criteriaCode') == 'ENCO':
                        note = crit.get('criteriaNote', 0)
                        break
    except Exception as e:
        st.write("Erreur parsing ENCO:", e)

    full_func_name = "`din-homeindex-dev-irq.asfr_home_index_score_flow`.call_single_engine"
    sql_debug = f"SELECT {full_func_name}(PARSE_JSON('{json.dumps(json_entry)}'))"

    return note, json_entry, sql_debug
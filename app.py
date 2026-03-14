import streamlit as st
from google.cloud import bigquery
import pandas as pd
import json

# --- CONFIGURATION ---
PROJECT_ID = "din-homeindex-dev-irq"
client = bigquery.Client(project=PROJECT_ID, location="EU")

st.set_page_config(layout="wide", page_title="Engine Home Index 2026", page_icon="🌱")

# --- FONCTIONS DATA ---

def run_query(query):
    return client.query(query).to_dataframe()

def get_product_details(bu_id, prod_ref):
    query = f"""
    SELECT prod.productAdministrativeDesignation, prod.topInternationalOffer, art.itemPicture
    FROM `dfdp-data-foundation-prod.productDataFoundation.productCatalogue` prod
    LEFT JOIN `din-homeindex-prd-08n.homeIndexPerformance.article` art
      ON CAST(art.businessUnitIdentifier AS STRING) = CAST(prod.businessUnitIdentifier AS STRING)
      AND CAST(art.itemIdentifier AS STRING) = CAST(prod.productBuReference AS STRING)
    WHERE prod.businessUnitIdentifier = {bu_id} AND prod.productBuReference = {prod_ref}
    """
    return run_query(query)

def get_actual_data_and_score(bu_id, prod_ref, criteria_code, top_intl):
    bu_proof = 15 if top_intl == 1 else bu_id
    query = f"""
    WITH target_chars AS (
      SELECT methodName, characteristicIdentifier 
      FROM `{PROJECT_ID}.homeIndex.homeIndexCharacteristic` 
      WHERE methodIdentifier = '{criteria_code}'
    ),
    actual_info AS (
      SELECT 
        tc.characteristicIdentifier as att_id,
        MAX(tc.methodName) as criteria_full_name,
        MAX(p.characteristicName) as att_name,
        MAX(p.value) as current_val,
        STRING_AGG(DISTINCT proof.productDocumentaryProofName, ' / ') as proof_names,
        MAX(IF(proof.productDocumentaryInterventionIsDone, 1, 0)) as is_done
      FROM target_chars tc
      LEFT JOIN `dfdp-data-foundation-prod.productDataFoundation.productCharacteristicsDenormalized` p
        ON p.characteristicIdentifier = tc.characteristicIdentifier
        AND p.productBuReference = {prod_ref} 
        AND p.businessUnitIdentifier = {bu_id}
      LEFT JOIN `dfdp-data-foundation-prod.productDataFoundation.productDocumentaryProof` proof
        ON tc.characteristicIdentifier = proof.productDocumentaryProofClaimedBy
        AND proof.productBuReference = {prod_ref}
        AND proof.businessUnitIdentifier = {bu_proof}
      GROUP BY tc.characteristicIdentifier
    ),
    engine_results AS (
      SELECT 
        `{PROJECT_ID}.asfr_home_index_score_flow`.call_single_engine(
            PARSE_JSON(TO_JSON_STRING(JSON_STRIP_NULLS(JSON_OBJECT(
              'productBuReference', productBuReference,
              'businessUnitIdentifier', businessUnitIdentifier,
              'productDescriptiveModelIdentifier', productDescriptiveModelIdentifier,
              'supplierPurchaseSiteIdentifier', supplierPurchaseSiteIdentifier,
              'criteria', ARRAY_AGG(JSON_OBJECT(
                    'criteriaCode', criteriaCode,
                    'criteriaValue', criteriaValue,
                    'criteriaValueIdentifier', criteriaValueIdentifier,
                    'proof', proof,
                    'characteristic', characteristic
                  ))
            ))))
        ) as raw_res
      FROM `{PROJECT_ID}.asfr_home_index_score_flow.v_homeIndexCriteriaData`
      WHERE criteriaCode = '{criteria_code}'
      AND productBuReference = {prod_ref} AND businessUnitIdentifier = {bu_id}
      GROUP BY productBuReference, businessUnitIdentifier, productDescriptiveModelIdentifier, supplierPurchaseSiteIdentifier
    )
    SELECT * FROM actual_info LEFT JOIN engine_results ON 1=1
    """
    df = run_query(query)
    if 'raw_res' not in df.columns: df['raw_res'] = None
    return df

def get_simu_options(criteria_code):
    query = f"""
    SELECT DISTINCT 
        CAST(valCar.characteristicValue AS STRING) as characteristicValue, 
        CAST(valCar.characteristicValueCode AS STRING) as characteristicValueCode, 
        hiCar.characteristicIdentifier as att_id,
        hiCar.methodName as att_name
    FROM `{PROJECT_ID}.homeIndex.homeIndexCharacteristic` hiCar
    LEFT JOIN `dfdp-data-foundation-prod.productDataFoundation.characteristicValuesLink` valCar
      ON CONCAT('ATT_',valCar.characteristicIdentifier) = hiCar.characteristicIdentifier
    WHERE hiCar.methodIdentifier = '{criteria_code}'
    """
    return run_query(query)

def run_multi_simulation(bu_id, prod_ref, model_id, supplier_id, criteria_code, list_simu_criteria):
    json_payload = {
        "productBuReference": int(prod_ref), "businessUnitIdentifier": int(bu_id),
        "productDescriptiveModelIdentifier": str(model_id) if pd.notna(model_id) else "",
        "supplierPurchaseSiteIdentifier": int(supplier_id) if pd.notna(supplier_id) else 0,
        "criteria": list_simu_criteria
    }
    payload_str = json.dumps(json_payload).replace("'", "\\'")
    query = f"SELECT TO_JSON_STRING(`{PROJECT_ID}.asfr_home_index_score_flow`.call_single_engine(PARSE_JSON('{payload_str}'))) as result_json"
    return json.loads(run_query(query)['result_json'].iloc[0])[0]

# --- INTERFACE ---

with st.sidebar:
    st.image("https://media.adeo.com/media/3083810/media.png", use_container_width=True)
    st.divider()
    st.header("🔎 Recherche")
    bu_id = st.number_input("Business Unit", value=1)
    prod_ref = st.number_input("Référence Produit", value=90346525)
    list_criteria = ["PORE", "SPPA", "RECMM", "OTL", "ENCO", "ENSA", "PROF", "TYEN", "WCWC"]
    selected_criteria = st.selectbox("Critère à simuler", list_criteria)

if prod_ref:
    df_p = get_product_details(bu_id, prod_ref)
    if not df_p.empty:
        p_row = df_p.iloc[0]
        col_img, col_txt = st.columns([1, 4])
        with col_img:
            if p_row['itemPicture']: st.image(p_row['itemPicture'], use_container_width=True)
            else: st.write("🖼️ (No Photo)")
        with col_txt:
            st.header(p_row['productAdministrativeDesignation'])
            st.write(f"**BU:** {bu_id} | **Ref:** {prod_ref}")

        st.divider()

        # 2. ÉTAT ACTUEL
        df_act = get_actual_data_and_score(bu_id, prod_ref, selected_criteria, p_row['topInternationalOffer'])
        
        avg_note = "0"
        if not df_act.empty and pd.notna(df_act['raw_res'].iloc[0]):
            try:
                raw = json.loads(df_act['raw_res'].iloc[0])[0]
                avg_note = raw.get('averageNote', "0")
            except: pass

        st.subheader(f"📊 État actuel : {selected_criteria}")
        atts_in_base = df_act['att_id'].unique().tolist()
        for _, row in df_act.iterrows():
            st.write(f"**{row['att_name']}** (`{row['att_id']}`) : `{row['current_val']}` | Preuve : {'✅ Yes' if row['is_done']==1 else '❌ No'}")
        st.metric("Note Globale Actuelle", avg_note)

        st.divider()

        # 3. ZONE DE SIMULATION
        st.subheader(f"🧪 Zone de Simulation")
        df_opts = get_simu_options(selected_criteria)
        
        simu_payload_list = []
        for att_id in atts_in_base:
            # On cherche les options pour cet attribut
            specific_opts = df_opts[(df_opts['att_id'] == att_id) & (df_opts['characteristicValue'].notna())]
            att_display_name = df_act[df_act['att_id'] == att_id]['att_name'].iloc[0]
            
            with st.expander(f"Modifier {att_display_name} ({att_id})", expanded=True):
                col1, col2 = st.columns(2)
                
                with col1:
                    # LOGIQUE HYBRIDE : Selectbox si options, sinon Saisie libre
                    if not specific_opts.empty:
                        sim_val = st.selectbox(
                            f"Valeur ({att_id})", 
                            options=specific_opts['characteristicValue'].unique(),
                            key=f"val_sim_{att_id}"
                        )
                        sim_val_id = specific_opts[specific_opts['characteristicValue'] == sim_val]['characteristicValueCode'].iloc[0]
                    else:
                        st.info("💡 Aucune liste de valeurs trouvée. Saisie libre activée.")
                        sim_val = st.text_input(f"Saisir la valeur ({att_id})", value="", key=f"val_sim_{att_id}")
                        sim_val_id = sim_val # Dans ce cas, on utilise la même valeur pour l'ID

                with col2:
                    sim_proof = st.toggle("Preuve OK ?", value=True, key=f"proof_sim_{att_id}")
                
                simu_payload_list.append({
                    "criteriaCode": selected_criteria,
                    "criteriaValue": sim_val,
                    "criteriaValueIdentifier": sim_val_id,
                    "proof": "Yes" if sim_proof else "No",
                    "characteristic": att_id
                })

        if st.button("🚀 Simuler l'impact global", type="primary", use_container_width=True):
            t_q = f"SELECT productDescriptiveModelIdentifier, supplierPurchaseSiteIdentifier FROM `{PROJECT_ID}.asfr_home_index_score_flow.v_homeIndexCriteriaData` WHERE productBuReference = {prod_ref} LIMIT 1"
            df_t = run_query(t_q)
            if not df_t.empty:
                res = run_multi_simulation(bu_id, prod_ref, df_t['productDescriptiveModelIdentifier'].iloc[0], df_t['supplierPurchaseSiteIdentifier'].iloc[0], selected_criteria, simu_payload_list)
                
                st.success("Simulation terminée !")
                r1, r2, r3 = st.columns(3)
                r1.metric("Note Simulée", res.get('averageNote'), delta=round(float(res.get('averageNote')) - float(avg_note), 2))
                p_sim = res.get('pillars', [{}])[0]
                r2.metric(f"Pilier {p_sim.get('pillarName')}", p_sim.get('pillarAverage'))
                c_sim = p_sim.get('criteria', [{}])[0]
                r3.metric(f"Critère {selected_criteria}", c_sim.get('criteriaNote'))
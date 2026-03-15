import streamlit as st
from google.cloud import bigquery
import pandas as pd

client = bigquery.Client(project="din-homeindex-dev-irq", location="EU")

# --- CONFIGURATION UI ---
st.set_page_config(layout="wide", page_title="Simulateur HI 2026")

# --- 1. FONCTIONS DE RÉCUPÉRATION ---

def get_product_basics(bu_id, prod_ref):
    query = f"SELECT * FROM `dfdp-data-foundation-prod.productDataFoundation.productCatalogue` WHERE businessUnitIdentifier = {bu_id} AND productBuReference = {prod_ref} LIMIT 1"
    return client.query(query).to_dataframe()

def get_single_criteria_data(bu_id, prod_ref, top_intl, att_id):
    bu_proof = 15 if top_intl == 1 else bu_id
    query = f"""
    SELECT 
        p.characteristicIdentifier as att_id,
        p.characteristicName as att_name,
        p.value as current_value, 
        p.valueIdentifier as val_id,
        proof.productDocumentaryProofName as proof_name,
        CAST(proof.productDocumentaryInterventionIsDone AS BOOL) as is_done
    FROM `dfdp-data-foundation-prod.productDataFoundation.productCharacteristicsDenormalized` p
    LEFT JOIN `dfdp-data-foundation-prod.productDataFoundation.productDocumentaryProof` proof
        ON p.productBuReference = proof.productBuReference 
        AND p.characteristicIdentifier = proof.productDocumentaryProofClaimedBy
        AND proof.businessUnitIdentifier = {bu_proof}
    WHERE p.productBuReference = {prod_ref} 
    AND p.businessUnitIdentifier = {bu_id}
    AND p.characteristicIdentifier = '{att_id}'
    QUALIFY ROW_NUMBER() OVER (
      PARTITION BY
        p.businessUnitIdentifier,
        p.productBuReference,
        p.characteristicIdentifier
      ORDER BY proof.productDocumentaryProofIsActive DESC, proof.productDocumentaryInterventionIsDone DESC
    ) = 1
    """
    return client.query(query).to_dataframe()

@st.cache_data
def get_lov(att_id):
    query = f"SELECT characteristicValue, characteristicValueCode FROM `dfdp-data-foundation-prod.productDataFoundation.characteristicValuesLink` WHERE characteristicIdentifier = '{att_id}'"
    return client.query(query).to_dataframe()

# --- 2. HEADER ---
col_logo, col_title = st.columns([1, 6])
with col_logo:
    st.image("https://media.leroymerlin.fr/media/15112520/format/jpg?width=150", width=100)
with col_title:
    st.title("Engine Home Index 2026")

# --- 3. SIDEBAR ---
with st.sidebar:
    st.header("📍 Paramètres")
    bu_id = st.number_input("BU ID", value=1)
    prod_ref = st.number_input("Product Ref", value=90346525)

if prod_ref:
    df_prod = get_product_basics(bu_id, prod_ref)
    
    if not df_prod.empty:
        prod_info = df_prod.iloc[0]
        top_intl = int(prod_info['topInternationalOffer'])
        
        # Header Produit
        c_img, c_txt = st.columns([1, 4])
        with c_img:
            st.image(f"https://media.adeo.com/media/{prod_ref}/format/jpg?width=250", use_container_width=True)
        with c_txt:
            st.header(prod_info['productAdministrativeDesignation'])
            st.caption(f"Ref: {prod_ref} | Modèle: {prod_info.get('productDescriptiveModelIdentifier', 'N/A')}")

        st.divider()

        # Récupération DATA
        df_pore = get_single_criteria_data(bu_id, prod_ref, top_intl, 'ATT_25674')
        df_sppa = get_single_criteria_data(bu_id, prod_ref, top_intl, 'ATT_17017')

        # --- TABLEAU COMPARATIF ---
        st.subheader("📊 Comparateur de Score")
        
        h1, h2, h3, h4 = st.columns([3, 1, 3, 1])
        h1.markdown("**Critère (Donnée Réelle)**")
        h2.markdown("**Score Actuel**")
        h3.markdown("**Simulateur**")
        h4.markdown("**Score Simulé**")
        st.markdown("---")

        # --- LIGNE PORE ---
        l1_c1, l1_c2, l1_c3, l1_c4 = st.columns([3, 1, 3, 1])
        
        with l1_c1:
            if not df_pore.empty:
                r_p = df_pore.iloc[0]
                st.markdown(f"**Potential of Repairability** (`{r_p['att_id']}`)")
                st.write(f"ATT Name: {r_p['att_name']}")
                st.write(f"Valeur: **{r_p['current_value']}**")
                p_status = "✅ Validée" if r_p['is_done'] is True else "❌ Non validée"
                st.caption(f"Preuve: {r_p['proof_name'] if pd.notna(r_p['proof_name']) else 'Aucune'} ({p_status})")
                score_p_reel = 100 if r_p['is_done'] is True else 75
            else:
                st.error("Donnée PORE manquante")
                score_p_reel = 0

        with l1_c2:
            st.title(f"{score_p_reel}")

        with l1_c3:
            df_lov_p = get_lov('ATT_25674')
            idx_p = 0
            if not df_lov_p.empty and not df_pore.empty:
                try: idx_p = df_lov_p['characteristicValue'].tolist().index(df_pore['current_value'].iloc[0])
                except: idx_p = 0
            
            sim_pore_val = st.selectbox("Simuler valeur :", df_lov_p['characteristicValue'].tolist() if not df_lov_p.empty else ["Yes"], index=idx_p, key="s_p")
            # Initialise le toggle avec l'état réel de la base
            real_proof_state = df_pore['is_done'].iloc[0] if not df_pore.empty else False
            sim_pore_proof = st.toggle("Simuler Preuve Validée", value=bool(real_proof_state), key="t_p")

        with l1_c4:
            # Score simulé identique au réel par défaut grâce au toggle initialisé
            score_p_sim = 100 if sim_pore_proof else 75
            st.title(f"{score_p_sim}")

        st.markdown("---")

        # --- LIGNE SPPA ---
        l2_c1, l2_c2, l2_c3, l2_c4 = st.columns([3, 1, 3, 1])
        
        with l2_c1:
            if not df_sppa.empty:
                r_s = df_sppa.iloc[0]
                st.markdown(f"**Spare Parts Availability** (`{r_s['att_id']}`)")
                st.write(f"ATT Name: {r_s['att_name']}")
                st.write(f"Valeur: **{r_s['current_value']} ans**")
                score_s_reel = 100 if int(r_s['current_value']) >= 10 else 50
            else:
                st.error("Donnée SPPA manquante")
                score_s_reel = 0

        with l2_c2:
            st.title(f"{score_s_reel}")

        with l2_c3:
            try: curr_v = int(df_sppa['current_value'].iloc[0])
            except: curr_v = 0
            sim_sppa_val = st.slider("Simuler durée :", 0, 25, curr_v, key="s_s")

        with l2_c4:
            score_s_sim = 100 if sim_sppa_val >= 10 else 50
            st.title(f"{score_s_sim}")

        # --- FOOTER ---
        st.divider()
        if st.button("🚀 Calculer Score Global", type="primary", use_container_width=True):
            st.metric("Score Global DUR", "92 / 100", delta="Simulation active")
    else:
        st.error("Produit introuvable.")
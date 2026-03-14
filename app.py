import streamlit as st
from google.cloud import bigquery
import pandas as pd
import plotly.graph_objects as go

# --- CONFIGURATION CLIENT ---
# On utilise les identifiants par défaut (gcloud auth application-default login)
client = bigquery.Client(project="din-homeindex-dev-irq", location="EU")

st.set_page_config(layout="wide", page_title="Simulateur HI 2026")
st.title("🌱 Engine Home Index 2026")

# --- FONCTIONS DE RÉCUPÉRATION ---

def get_product_basics(bu_id, prod_ref):
    query = f"""
    SELECT productAdministrativeDesignation, topInternationalOffer 
    FROM `dfdp-data-foundation-prod.productDataFoundation.productCatalogue` 
    WHERE businessUnitIdentifier = {bu_id} AND productBuReference = {prod_ref} LIMIT 1
    """
    return client.query(query).to_dataframe()

def get_characteristic_data(bu_id, prod_ref, att_id, top_intl):
    # Logique BU 15 pour les preuves internationales
    bu_proof = 15 if top_intl == 1 else bu_id
    query = f"""
    SELECT 
        p.characteristicIdentifier as att_id,
        p.characteristicName as att_name,
        p.value as current_value, 
        p.valueIdentifier as val_id,
        proof.productDocumentaryProofName as proof_name,
        proof.productDocumentaryInterventionIsDone as is_done
    FROM `dfdp-data-foundation-prod.productDataFoundation.productCharacteristicsDenormalized` p
    LEFT JOIN `dfdp-data-foundation-prod.productDataFoundation.productDocumentaryProof` proof
        ON p.productBuReference = proof.productBuReference 
        AND p.characteristicIdentifier = proof.productDocumentaryProofClaimedBy
        AND proof.businessUnitIdentifier = {bu_proof}
    WHERE p.productBuReference = {prod_ref} 
    AND p.businessUnitIdentifier = {bu_id}
    AND p.characteristicIdentifier = '{att_id}'
    LIMIT 1
    """
    return client.query(query).to_dataframe()

@st.cache_data
def get_lov(att_id):
    query = f"SELECT characteristicValue, characteristicValueCode FROM `dfdp-data-foundation-prod.productDataFoundation.characteristicValuesLink` WHERE characteristicIdentifier = '{att_id}'"
    return client.query(query).to_dataframe()

# --- INTERFACE ---

with st.sidebar:
    st.header("Paramètres Produit")
    bu_id = st.number_input("BU ID", value=1)
    prod_ref = st.number_input("Product Ref", value=90346525)

if prod_ref:
    df_prod = get_product_basics(bu_id, prod_ref)
    if not df_prod.empty:
        top_intl = df_prod['topInternationalOffer'].iloc[0]
        st.header(f"📦 {df_prod['productAdministrativeDesignation'].iloc[0]}")
        
        # --- SECTION PORE ---
        st.divider()
        st.subheader("🔧 Critère : PORE (Potential of Repairability)")
        df_pore = get_characteristic_data(bu_id, prod_ref, 'ATT_25674', top_intl)
        df_lov_pore = get_lov('ATT_25674')
        
        c1, c2 = st.columns(2)
        with c1:
            st.info("Données Réelles")
            if not df_pore.empty:
                st.write(f"**{df_pore['att_name'].iloc[0]}** (`{df_pore['att_id'].iloc[0]}`)")
                st.write(f"Valeur : {df_pore['current_value'].iloc[0]} (`{df_pore['val_id'].iloc[0]}`)")
                st.write(f"Preuve : {df_pore['proof_name'].iloc[0] if df_pore['proof_name'].iloc[0] else '❌ Non'}")
        with c2:
            st.success("Simulateur")
            sim_pore = st.selectbox("Nouvelle Valeur PORE", df_lov_pore['characteristicValue'].tolist())
            sim_pore_proof = st.toggle("Preuve Validée", value=True)

        # --- SECTION SPPA ---
        st.divider()
        st.subheader("🛠️ Critère : SPPA (Spare Parts Availability)")
        df_sppa = get_characteristic_data(bu_id, prod_ref, 'ATT_17017', top_intl)
        
        c3, c4 = st.columns(2)
        with c3:
            st.info("Données Réelles")
            if not df_sppa.empty:
                st.write(f"**{df_sppa['att_name'].iloc[0]}** (`{df_sppa['att_id'].iloc[0]}`)")
                st.metric("Durée actuelle", f"{df_sppa['current_value'].iloc[0]} ans")
        with c4:
            st.success("Simulateur")
            sim_sppa = st.slider("Années de disponibilité", 0, 20, 10)

        if st.button("🚀 Calculer Score Global Simulé", type="primary"):
            st.balloons()
            st.metric("Score Durabilité (DUR)", "85/100", delta="+15")
    else:
        st.error("Produit introuvable.")
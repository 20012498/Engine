import streamlit as st
import pandas as pd
from logic.bq_tools import get_full_product_data, get_all_lovs, get_criteria_details, get_simulated_score
from logic.criteria_hub import render_criteria_simulator

st.set_page_config(layout="wide", page_title="Home Index Simulator", page_icon="🟢")

# --- STYLE CSS ---
st.markdown("""
    <style>
    .main { background-color: #f9f9f9; }
    .tech-label { color: #7f8c8d; font-size: 12px; font-family: monospace; }
    .big-note { font-size: 40px !important; font-weight: 800; text-align: center; color: #2c3e50; }
    .simu-note { font-size: 40px !important; font-weight: 800; text-align: center; color: #27ae60; }
    /* Suppression des bordures blanches par défaut sur certaines colonnes */
    div[data-testid="stColumn"] {
        padding: 0px;
    }
    </style>
    """, unsafe_allow_html=True)

if "data_loaded" not in st.session_state:
    st.session_state.data_loaded, st.session_state.criteria_data = False, []
    st.session_state.simulation_result, st.session_state.product_info = None, {}

# --- SIDEBAR ---
with st.sidebar:
    st.image("https://media.adeo.com/media/3083810/media.png", width=180)
    st.header("🔍 Recherche")
    bu_id = st.number_input("BU ID", value=1)
    prod_ref = st.number_input("Product Ref", value=90346525)
    
    if st.button("📥 Charger le produit", use_container_width=True, type="primary"):
        st.session_state.criteria_data = []
        st.session_state.simulation_result = None
        
        with st.spinner("Chargement..."):
            df_full = get_full_product_data(bu_id, prod_ref)
            st.session_state.lovs = get_all_lovs()
            
            if not df_full.empty:
                st.session_state.product_info = df_full.iloc[0].to_dict()
                top_intl = int(st.session_state.product_info.get('topInternationalOffer', 0))
                
                temp_list = []
                codes = [c for c in df_full['criteriaCode'].unique() if c]
                for code in codes:
                    det = get_criteria_details(bu_id, prod_ref, top_intl, code)
                    if not det.empty:
                        temp_list.append({
                            "code": code, 
                            "note_reelle": df_full[df_full['criteriaCode'] == code]['criteriaNote'].iloc[0], 
                            "det": det.iloc[0].to_dict()
                        })
                st.session_state.criteria_data, st.session_state.data_loaded = temp_list, True
            else:
                st.error("Produit introuvable.")

# --- CONTENU PRINCIPAL ---
if st.session_state.data_loaded:
    p = st.session_state.product_info
    
    # En-tête : Image + Titre
    head_left, head_mid = st.columns([1, 4])
    with head_left:
        if p.get('itemPicture'):
            st.image(p['itemPicture'], use_container_width=True)
    with head_mid:
        st.title(p.get('productAdministrativeDesignation', 'Produit'))
        st.markdown(f"**MODÈLE :** `{p.get('productDescriptiveModelIdentifier')}` | **SUPPLIER :** `{p.get('supplierPurchaseSiteIdentifier')}`")

    st.divider()

    # Simulation Layout
    SUPPORTED = ["PORE", "SPPA"]
    display_items = [i for i in st.session_state.criteria_data if i['code'] in SUPPORTED]

    # En-têtes de colonnes (Remplacement de overline par bold + caption)
    cols_h = st.columns([3, 1, 3, 1])
    cols_h[0].caption("**DÉTAILS CRITÈRE**")
    cols_h[1].caption("**RÉEL**")
    cols_h[2].caption("**SIMULATEUR**")
    cols_h[3].caption("**SCORE SIMU**")

    current_choices = []
    for item in display_items:
        code, det = item['code'], item['det']
        st.write("") 
        l1, l2, l3, l4 = st.columns([3, 1, 3, 1])
        
        with l1:
            st.markdown(f"**{det['methodName']}**")
            st.markdown(f"<div class='tech-label'>{det['att_name']} ({det['att_id']})<br>Actuel : {det['current_value']} (ID: {det.get('val_id','')})</div>", unsafe_allow_html=True)
        
        with l2:
            st.markdown(f"<p class='big-note'>{int(item['note_reelle'])}</p>", unsafe_allow_html=True)
        
        with l3:
            lov_f = st.session_state.lovs[st.session_state.lovs['code'] == code].rename(
                columns={'label': 'characteristicValue', 'id': 'characteristicValueCode'}
            )
            choice = render_criteria_simulator(code, det, lov_f)
            current_choices.append(choice)
        
        with l4:
            if st.session_state.simulation_result is not None:
                res = st.session_state.simulation_result
                score_row = res[res['criteriaCode'] == code]
                if not score_row.empty:
                    st.markdown(f"<p class='simu-note'>{int(score_row['criteria_note'].iloc[0])}</p>", unsafe_allow_html=True)
                else: st.error("Null")
            else: st.write("")

    st.divider()
    if st.button("🚀 LANCER LA SIMULATION", type="primary", use_container_width=True):
        st.session_state.simulation_result = get_simulated_score(
            bu_id, prod_ref, 
            p.get('productDescriptiveModelIdentifier'), 
            p.get('supplierPurchaseSiteIdentifier'), 
            current_choices
        )
        st.rerun()
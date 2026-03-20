import streamlit as st
import pandas as pd
from logic.bq_tools import get_full_product_data, get_all_lovs, get_criteria_details
from logic.criteria.pore import render_pore, simulate_pore
from logic.criteria.sppa import render_sppa, simulate_sppa

st.set_page_config(layout="wide", page_title="Home Index Simulator", page_icon="🚀")

# --- CSS PRÉCIS (Cible uniquement les boutons de la grille de simulation) ---
st.markdown("""
    <style>
    .tech-label { color: #808495; font-size: 12px; font-family: monospace; line-height: 1.4; margin-top: 5px; }
    .big-note { font-size: 38px !important; font-weight: 800; text-align: center; color: #2c3e50; margin: 0; }
    .simu-note { font-size: 38px !important; font-weight: 800; text-align: center; color: #27ae60; margin: 0; }
    
    /* Cible uniquement les boutons à l'intérieur des colonnes du corps principal */
    [data-testid="column"] .stButton > button {
        border-radius: 50% !important;
        width: 45px !important;
        height: 45px !important;
        padding: 0px !important;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 20px;
        margin-top: 10px;
    }
    
    /* Les boutons de la sidebar restent standards car ils ne sont pas dans les mêmes containers 'column' */
    section[data-testid="stSidebar"] .stButton > button {
        border-radius: 4px !important;
        width: 100% !important;
        height: auto !important;
        padding: 10px !important;
    }
    </style>
    """, unsafe_allow_html=True)

if "data_loaded" not in st.session_state:
    st.session_state.update({"data_loaded": False, "criteria_data": [], "product_info": {}, "lovs": pd.DataFrame(), "current_choices": {}})

# --- SIDEBAR (Standard) ---
with st.sidebar:
    st.image("https://media.adeo.com/media/3083810/media.png", width=150)
    st.header("🔍 Recherche")
    bu_id = st.number_input("BU ID", value=1)
    prod_ref = st.number_input("Product Ref", value=90346525)
    
    if st.button("📥 Charger le Produit", type="primary", use_container_width=True):
        df_full = get_full_product_data(bu_id, prod_ref)
        st.session_state.lovs = get_all_lovs()
        if not df_full.empty:
            st.session_state.product_info = df_full.iloc[0].to_dict()
            top_intl = int(st.session_state.product_info.get('topInternationalOffer', 0))
            temp_list = []
            for code in [c for c in df_full['criteriaCode'].unique() if c]:
                det = get_criteria_details(bu_id, prod_ref, top_intl, code)
                if not det.empty:
                    note = df_full[df_full['criteriaCode'] == code]['criteriaNote'].iloc[0]
                    temp_list.append({"code": code, "note_reelle": note, "det": det.iloc[0].to_dict()})
            st.session_state.criteria_data = temp_list
            st.session_state.data_loaded = True
            for item in temp_list: st.session_state.pop(f"res_{item['code']}", None)

    if st.session_state.data_loaded:
        st.divider()
        if st.button("🔥 TOUT SIMULER", type="secondary", use_container_width=True):
            p = st.session_state.product_info
            for code, choice in st.session_state.current_choices.items():
                if code == "PORE": st.session_state[f"res_PORE"] = simulate_pore(bu_id, prod_ref, p, choice)
                elif code == "SPPA": st.session_state[f"res_SPPA"] = simulate_sppa(bu_id, prod_ref, p, choice)
            st.rerun()

# --- MAIN ---
if st.session_state.data_loaded:
    p = st.session_state.product_info
    
    col_img, col_titre = st.columns([1, 4])
    with col_img:
        if p.get('itemPicture'): st.image(p['itemPicture'], width=130)
            
    with col_titre:
        st.title(p.get('productAdministrativeDesignation'))
        st.caption(f"MODÈLE : {p.get('productDescriptiveModelIdentifier')} | SUPPLIER : {p.get('supplierPurchaseSiteIdentifier')}")

    st.divider()

    # En-têtes
    h1, h2, h3, h4 = st.columns([2.5, 1, 3.5, 1])
    h1.caption("**NOM CRITÈRE & ATT**")
    h2.caption("**RÉEL**")
    h3.caption("**SIMULATEUR**")
    h4.caption("**SCORE**")

    for item in st.session_state.criteria_data:
        code, det = item['code'], item['det']
        if code not in ["PORE", "SPPA"]: continue

        l1, l2, l3, l4 = st.columns([2.5, 1, 3.5, 1])
        
        with l1:
            # Affichage complet : Nom (Code) + Nom ATT + ID ATT
            st.markdown(f"**{det['methodName']} ({code})**")
            st.markdown(f"""<div class='tech-label'>
                <b>{det.get('att_name', 'N/A')}</b><br>
                ID: {det['att_id']}<br>
                Actuel: {det['current_value']}
            </div>""", unsafe_allow_html=True)
        
        with l2:
            st.markdown(f"<p class='big-note'>{int(item['note_reelle'])}</p>", unsafe_allow_html=True)
        
        with l3:
            if code == "PORE":
                lov_f = st.session_state.lovs[st.session_state.lovs['code'] == "PORE"].rename(columns={'label': 'characteristicValue', 'id': 'characteristicValueCode'})
                choice = render_pore(det, lov_f)
            else:
                choice = render_sppa(det)
            st.session_state.current_choices[code] = choice
        
        with l4:
            # Bouton individuel "Cible"
            if st.button("🎯", key=f"btn_{code}"):
                if code == "PORE": st.session_state[f"res_PORE"] = simulate_pore(bu_id, p['productBuReference'], p, choice)
                else: st.session_state[f"res_SPPA"] = simulate_sppa(bu_id, p['productBuReference'], p, choice)
                st.rerun()
            
            res_val = st.session_state.get(f"res_{code}")
            if res_val is not None:
                st.markdown(f"<p class='simu-note'>{int(res_val)}</p>", unsafe_allow_html=True)
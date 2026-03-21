import streamlit as st
import pandas as pd
import importlib
import json
from logic.bq_tools import get_full_product_data, get_all_lovs, get_criteria_details

# --- CONFIGURATION & INITIALISATION ---
st.set_page_config(layout="wide", page_title="Home Index Simulator")

# Initialisation critique des variables d'état
if "data_loaded" not in st.session_state:
    st.session_state.data_loaded = False
if "criteria_data" not in st.session_state:
    st.session_state.criteria_data = []
if "product_info" not in st.session_state:
    st.session_state.product_info = {}
if "current_choices" not in st.session_state:
    st.session_state.current_choices = {}
if "lovs" not in st.session_state:
    st.session_state.lovs = pd.DataFrame()

# --- STYLE CSS ---
st.markdown("""
    <style>
    .pillar-header { background-color: #f8f9fb; padding: 12px; border-radius: 8px; margin: 25px 0 15px 0; font-weight: 800; color: #1f77b4; border-left: 5px solid #1f77b4; text-transform: uppercase; }
    .tech-label { color: #808495; font-size: 11px; font-family: monospace; line-height: 1.2; margin-top: 5px; }
    .big-note { font-size: 32px !important; font-weight: 800; text-align: center; color: #2c3e50; margin: 0; }
    .simu-note { font-size: 32px !important; font-weight: 800; text-align: center; color: #27ae60; margin: 0; }
    /* Bouton Target Rond */
    [data-testid="column"] .stButton > button {
        border-radius: 50% !important; width: 42px !important; height: 42px !important;
        display: flex; align-items: center; justify-content: center;
        font-size: 18px; margin-top: 15px; border: 1px solid #ddd;
    }
    /* Boutons Sidebar */
    section[data-testid="stSidebar"] .stButton > button { border-radius: 4px !important; width: 100% !important; margin-bottom: 10px; height: auto !important; }
    </style>
    """, unsafe_allow_html=True)

# --- LOGIQUE CHARGEMENT MODULES ---
def get_criteria_module(code):
    try:
        return importlib.import_module(f"logic.criteria.{code.lower()}")
    except Exception as e:
        return None

# --- SIDEBAR ---
with st.sidebar:
    st.header("🔍 Recherche")
    bu_id = st.number_input("BU ID", value=1)
    prod_ref = st.number_input("Product Ref", value=90346525)
    
    if st.button("📥 Charger le Produit", type="primary"):
        df_full = get_full_product_data(bu_id, prod_ref)
        st.session_state.lovs = get_all_lovs()
        
        if not df_full.empty:
            st.session_state.product_info = df_full.iloc[0].to_dict()
            top_intl = int(st.session_state.product_info.get('topInternationalOffer', 0))
            
            temp_list = []
            for code in [c for c in df_full['criteriaCode'].unique() if c]:
                det_df = get_criteria_details(bu_id, prod_ref, top_intl, code)
                if not det_df.empty:
                    note = df_full[df_full['criteriaCode'] == code]['criteriaNote'].iloc[0]
                    temp_list.append({"code": code, "note_reelle": note, "details": det_df.to_dict('records')})
            
            st.session_state.criteria_data = temp_list
            st.session_state.data_loaded = True
            st.session_state.current_choices = {}
            # Nettoyage des anciens résultats de simulation
            for key in list(st.session_state.keys()):
                if any(key.startswith(pre) for pre in ["res_", "sql_", "payload_"]):
                    del st.session_state[key]
            st.rerun()
        else:
            st.error(f"Produit {prod_ref} non trouvé (BU {bu_id})")

    # Bouton Simulation Globale
    if st.session_state.data_loaded:
        st.divider()
        st.subheader("Actions")
        if st.button("🚀 SIMULATION GLOBALE", type="secondary"):
            for item in st.session_state.criteria_data:
                code = item['code']
                mod = get_criteria_module(code)
                choice = st.session_state.current_choices.get(code)
                if mod and choice:
                    sim_func = getattr(mod, f"simulate_{code.lower()}")
                    res_val, payload, sql = sim_func(bu_id, prod_ref, st.session_state.product_info, choice)
                    st.session_state[f"res_{code}"] = res_val
                    st.session_state[f"sql_{code}"] = sql
            st.rerun()

# --- MAIN PAGE ---
if st.session_state.data_loaded:
    p = st.session_state.product_info
    
    # Header Produit
    c_img, c_txt = st.columns([1, 4])
    with c_img:
        url = p.get('itemPicture')
        if url and str(url) != 'None':
            st.image(url, width=150)
        else:
            st.info("No Photo")
    with c_txt:
        st.title(p.get('productAdministrativeDesignation', 'Produit'))
        st.caption(f"REF: {prod_ref} | MODÈLE: {p.get('productDescriptiveModelIdentifier')}")

    # Mapping des Piliers
    MAPPING_PILIERS = {
        "🛠️ DURABILITY": ["PORE", "SPPA"],
        "⚡ USE": ["ENSA"]
    }

    for pillar_name, target_codes in MAPPING_PILIERS.items():
        criteria_in_pillar = [c for c in st.session_state.criteria_data if c['code'] in target_codes]
        if not criteria_in_pillar:
            continue
            
        st.markdown(f"<div class='pillar-header'>{pillar_name}</div>", unsafe_allow_html=True)
        
        for item in criteria_in_pillar:
            code = item['code']
            mod = get_criteria_module(code)
            if not mod:
                continue

            # Colonnes : 1:Infos, 2:Note Réelle, 3:Simulation, 4:Action & Note Simu
            l1, l2, l3, l4 = st.columns([2.5, 1, 3.5, 1.5])
            
            with l1:
                st.markdown(f"**{item['details'][0].get('methodName', code)}** ({code})")
                for d in item['details']:
                    st.markdown(f"<div class='tech-label'><b>{d['att_name']}</b> ({d['att_id']})<br>Actuel: {d['current_value']}</div>", unsafe_allow_html=True)
            
            with l2:
                st.markdown(f"<p class='big-note'>{int(item['note_reelle'])}</p>", unsafe_allow_html=True)
            
            with l3:
                render_func = getattr(mod, f"render_{code.lower()}")
                lov_f = st.session_state.lovs[st.session_state.lovs['code'] == code].rename(
                    columns={'label': 'characteristicValue', 'id': 'characteristicValueCode'}
                )
                # Stockage automatique du choix actuel
                st.session_state.current_choices[code] = render_func(item['details'], lov_f)
            
            with l4:
                if st.button("🎯", key=f"btn_{code}"):
                    sim_func = getattr(mod, f"simulate_{code.lower()}")
                    res_val, payload, sql = sim_func(bu_id, prod_ref, p, st.session_state.current_choices[code])
                    st.session_state[f"res_{code}"] = res_val
                    st.session_state[f"sql_{code}"] = sql
                    st.rerun()
                
                # Note simulée
                res_sim = st.session_state.get(f"res_{code}")
                if res_sim is not None:
                    st.markdown(f"<p class='simu-note'>{int(res_sim)}</p>", unsafe_allow_html=True)
                
                # SQL Debugger
                sql_debug = st.session_state.get(f"sql_{code}")
                if sql_debug:
                    with st.expander("🛠️ SQL", expanded=False):
                        st.code(sql_debug, language="sql")
else:
    st.info("Veuillez charger un produit depuis la barre latérale pour commencer.")
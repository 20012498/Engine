import streamlit as st

def render_sppa(det, code):
    st.markdown(f"**{det['methodName']}**")
    try: 
        v_init = int(float(det['current_value']))
    except: 
        v_init = 0
    sim_years = st.slider("Années :", 0, 25, v_init, key=f"s_{code}_{det['att_id']}")
    return {"code": code, "val": str(sim_years), "val_id": "", "proof": "Yes", "att_id": det['att_id']}
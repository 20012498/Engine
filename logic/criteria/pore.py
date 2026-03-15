import streamlit as st

def render_pore(det, lov_df, code):
    st.markdown(f"**{det['methodName']}**")
    idx = 0
    if not lov_df.empty:
        try: idx = lov_df['characteristicValue'].tolist().index(det['current_value'])
        except: idx = 0
    sim_val = st.selectbox("Valeur :", lov_df['characteristicValue'].tolist() if not lov_df.empty else [det['current_value']], index=idx, key=f"v_{code}_{det['att_id']}")
    sim_id = lov_df[lov_df['characteristicValue'] == sim_val]['characteristicValueCode'].iloc[0] if not lov_df.empty else ""
    sim_proof = st.toggle("Preuve Validée", value=bool(det['is_done']), key=f"t_{code}_{det['att_id']}")
    return {"code": code, "val": sim_val, "val_id": sim_id, "proof": "Yes" if sim_proof else "No", "att_id": det['att_id']}
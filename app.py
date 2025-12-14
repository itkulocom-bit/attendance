# test_imports.py
try:
    import streamlit
    st.success("✅ streamlit OK")
except: st.error("❌ streamlit failed")

try:
    import supabase
    st.success("✅ supabase OK")
except: st.error("❌ supabase failed")

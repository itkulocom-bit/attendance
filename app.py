import streamlit as st

st.set_page_config(page_title="Test Deploy", layout="centered")
st.title("✅ DEPLOY TEST BERHASIL!")

st.success("""
Aplikasi berhasil di-deploy di Streamlit Cloud!
Python 3.13 + uv installer
""")

# Test basic imports
try:
    import pandas as pd
    st.write("✅ pandas berhasil diimport")
    
    # Create sample data
    df = pd.DataFrame({
        'Siswa': ['Sastro', 'Muda', 'Jabal'],
        'NIM': ['001', '002', '003'],
        'Status': ['Aktif', 'Aktif', 'Aktif']
    })
    
    st.dataframe(df)
    
except Exception as e:
    st.error(f"❌ Error pandas: {e}")

# Simple attendance form
st.divider()
st.header("Form Absensi Sederhana")

nama = st.text_input("Nama Siswa")
if st.button("Absen"):
    if nama:
        st.success(f"✅ {nama} telah diabsen!")
    else:
        st.warning("Masukkan nama dulu")

st.divider()
st.caption("App sederhana untuk test deployment Streamlit Cloud")

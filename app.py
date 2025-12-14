import streamlit as st
import pandas as pd
from datetime import datetime

# App paling sederhana dulu
st.set_page_config(page_title="Attendance Test", layout="centered")
st.title("✅ TEST APP - BISA JALAN")

st.success("Aplikasi berhasil di-deploy!")

# Test pandas
df = pd.DataFrame({
    'Nama': ['Sastro', 'Muda', 'Jabal'],
    'NIM': ['001', '002', '003'],
    'Status': ['Active', 'Active', 'Active']
})

st.dataframe(df)

# Attendance form
st.header("Input Absensi")
nama = st.selectbox("Pilih Nama", df['Nama'].tolist())
status = st.selectbox("Status", ["Hadir", "Izin", "Sakit"])

if st.button("Simpan"):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    st.success(f"{nama} - {status} pada {timestamp}")
    
    # Simpan ke CSV
    import csv
    with open("attendance.csv", "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([timestamp, nama, status])
    
    # Baca dan tampilkan data
    try:
        log_df = pd.read_csv("attendance.csv", names=['Waktu', 'Nama', 'Status'])
        st.dataframe(log_df)
    except:
        st.info("Data pertama kali disimpan")

st.divider()
st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

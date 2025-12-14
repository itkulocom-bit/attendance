import streamlit as st
import pandas as pd
from datetime import datetime
import base64
import os

# ========== SETUP ==========
st.set_page_config(page_title="Absensi Sederhana", layout="wide")
st.title("📝 ABSENSI SEDERHANA - MVP")

# ========== SESSION STATE ==========
if 'students' not in st.session_state:
    st.session_state.students = [
        {"nim": "001", "nama": "Sastro", "kelas": "XII-A"},
        {"nim": "002", "nama": "Muda", "kelas": "XII-A"},
        {"nim": "003", "nama": "Jabal", "kelas": "XII-A"}
    ]

if 'attendance' not in st.session_state:
    st.session_state.attendance = []

# ========== FUNGSI ==========
def save_attendance_local(nama, nim, status):
    """Simpan ke session state dan CSV"""
    entry = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "nim": nim,
        "nama": nama,
        "status": status
    }
    st.session_state.attendance.append(entry)
    
    # Juga simpan ke file CSV
    df = pd.DataFrame(st.session_state.attendance)
    df.to_csv("attendance.csv", index=False)
    
    return True

def generate_csv():
    """Generate CSV untuk download"""
    df = pd.DataFrame(st.session_state.attendance)
    return df.to_csv(index=False)

# ========== UI ==========
tab1, tab2, tab3 = st.tabs(["📝 Absensi", "👥 Data Siswa", "📊 Laporan"])

with tab1:
    st.header("Input Absensi")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("Pilih Siswa")
        
        # List siswa
        student_names = [s["nama"] for s in st.session_state.students]
        selected_name = st.selectbox("Nama Siswa:", student_names)
        
        # Ambil data siswa terpilih
        selected_student = next(
            s for s in st.session_state.students 
            if s["nama"] == selected_name
        )
        
        st.write(f"**NIM:** {selected_student['nim']}")
        st.write(f"**Kelas:** {selected_student['kelas']}")
        
        status = st.radio("Status:", ["Hadir", "Izin", "Sakit", "Alpha"])
        
        if st.button("✅ SIMPAN ABSENSI", type="primary"):
            success = save_attendance_local(
                selected_student["nama"],
                selected_student["nim"],
                status
            )
            
            if success:
                st.balloons()
                st.success(f"✅ {selected_name} dicatat sebagai **{status}**")
    
    with col2:
        st.subheader("Absensi Hari Ini")
        
        if st.session_state.attendance:
            # Filter untuk hari ini
            today = datetime.now().strftime("%Y-%m-%d")
            today_attendance = [
                a for a in st.session_state.attendance
                if a["timestamp"].startswith(today)
            ]
            
            if today_attendance:
                df_today = pd.DataFrame(today_attendance)
                st.dataframe(df_today, use_container_width=True)
                
                # Stats
                col_a, col_b, col_c = st.columns(3)
                with col_a:
                    hadir = len(df_today[df_today["status"] == "Hadir"])
                    st.metric("Hadir", hadir)
                with col_b:
                    izin = len(df_today[df_today["status"] == "Izin"])
                    st.metric("Izin", izin)
                with col_c:
                    sakit = len(df_today[df_today["status"] == "Sakit"])
                    st.metric("Sakit", sakit)
            else:
                st.info("Belum ada absensi hari ini")
        else:
            st.info("Belum ada data absensi")

with tab2:
    st.header("Data Siswa")
    
    # Tampilkan data siswa
    students_df = pd.DataFrame(st.session_state.students)
    st.dataframe(students_df, use_container_width=True)
    
    # Form tambah siswa
    with st.expander("➕ Tambah Siswa Baru"):
        col1, col2 = st.columns(2)
        
        with col1:
            new_nim = st.text_input("NIM")
            new_nama = st.text_input("Nama Lengkap")
        
        with col2:
            new_kelas = st.selectbox("Kelas", ["XII-A", "XII-B", "XII-C"])
        
        if st.button("Tambah Siswa"):
            if new_nim and new_nama:
                st.session_state.students.append({
                    "nim": new_nim,
                    "nama": new_nama,
                    "kelas": new_kelas
                })
                st.success(f"✅ {new_nama} ditambahkan!")
                st.rerun()
            else:
                st.warning("Isi NIM dan Nama!")

with tab3:
    st.header("Laporan Absensi")
    
    if st.session_state.attendance:
        # Full attendance data
        df_all = pd.DataFrame(st.session_state.attendance)
        
        # Date filter
        st.subheader("Filter Tanggal")
        col1, col2 = st.columns(2)
        
        with col1:
            start_date = st.date_input("Dari tanggal")
        with col2:
            end_date = st.date_input("Sampai tanggal")
        
        # Convert dates to string for filtering
        start_str = start_date.strftime("%Y-%m-%d")
        end_str = end_date.strftime("%Y-%m-%d")
        
        # Filter data
        filtered_df = df_all[
            (df_all["timestamp"] >= start_str) & 
            (df_all["timestamp"] <= f"{end_str} 23:59:59")
        ]
        
        if not filtered_df.empty:
            st.dataframe(filtered_df, use_container_width=True)
            
            # Download buttons
            col1, col2 = st.columns(2)
            
            with col1:
                csv_data = filtered_df.to_csv(index=False)
                st.download_button(
                    "📥 Download CSV",
                    data=csv_data,
                    file_name=f"absensi_{start_str}_to_{end_str}.csv",
                    mime="text/csv"
                )
            
            with col2:
                # Export to Excel (via CSV)
                st.download_button(
                    "📊 Download Excel",
                    data=csv_data,
                    file_name=f"absensi_{start_str}_to_{end_str}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            
            # Summary statistics
            st.subheader("Statistik")
            summary = filtered_df["status"].value_counts()
            st.bar_chart(summary)
        else:
            st.info("Tidak ada data pada rentang tanggal tersebut")
    else:
        st.info("Belum ada data absensi")

# ========== SIDEBAR ==========
with st.sidebar:
    st.header("⚙️ Pengaturan")
    
    # Reset data
    if st.button("🔄 Reset Data Absensi"):
        st.session_state.attendance = []
        st.rerun()
    
    st.divider()
    
    # Import/Export
    st.header("📁 Import/Export")
    
    # Upload CSV
    uploaded_file = st.file_uploader("Upload data CSV", type=['csv'])
    if uploaded_file:
        try:
            df_upload = pd.read_csv(uploaded_file)
            st.session_state.attendance = df_upload.to_dict('records')
            st.success("✅ Data berhasil diimport!")
        except:
            st.error("❌ Format file tidak valid")
    
    # Export all data
    if st.session_state.attendance:
        csv_all = generate_csv()
        st.download_button(
            "💾 Export Semua Data",
            data=csv_all,
            file_name=f"absensi_full_{datetime.now().strftime('%Y%m%d')}.csv"
        )

# ========== FOOTER ==========
st.divider()
st.caption(f"© 2024 - Absensi App v1.0 | Total Data: {len(st.session_state.attendance)} records")

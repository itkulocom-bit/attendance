import streamlit as st
import pandas as pd
from datetime import datetime

# ========== SETUP ==========
st.set_page_config(
    page_title="Absensi Digital",
    page_icon="📱",
    layout="wide"
)

# ========== TITLE ==========
st.title("📱 ABSENSI DIGITAL")
st.markdown("**Sistem absensi sederhana dengan Streamlit Cloud**")

# ========== DATABASE SIMULASI ==========
if 'students' not in st.session_state:
    st.session_state.students = [
        {"nim": "001", "nama": "Sastro", "kelas": "XII-A"},
        {"nim": "002", "nama": "Muda", "kelas": "XII-A"},
        {"nim": "003", "nama": "Jabal", "kelas": "XII-A"}
    ]

if 'attendance' not in st.session_state:
    st.session_state.attendance = []

# ========== FUNGSI ==========
def save_attendance(nama, nim, status):
    """Simpan data absensi"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    entry = {
        "timestamp": timestamp,
        "nim": nim,
        "nama": nama,
        "status": status
    }
    
    st.session_state.attendance.append(entry)
    return True

def export_to_csv():
    """Export data ke CSV"""
    df = pd.DataFrame(st.session_state.attendance)
    return df.to_csv(index=False)

# ========== UI ==========
tab1, tab2, tab3 = st.tabs(["📝 Absensi", "👥 Data", "📊 Laporan"])

with tab1:
    st.header("Input Absensi")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Pilih siswa
        student_names = [s["nama"] for s in st.session_state.students]
        selected_name = st.selectbox("Pilih Siswa:", student_names)
        
        # Get student data
        student = next(s for s in st.session_state.students if s["nama"] == selected_name)
        
        st.write(f"**NIM:** {student['nim']}")
        st.write(f"**Kelas:** {student['kelas']}")
        
        # Status
        status = st.radio(
            "Status Kehadiran:",
            ["Hadir", "Izin", "Sakit", "Alpha"],
            horizontal=True
        )
        
        # Tombol simpan
        if st.button("✅ Simpan Absensi", type="primary", use_container_width=True):
            if save_attendance(student["nama"], student["nim"], status):
                st.balloons()
                st.success(f"**{selected_name}** dicatat sebagai **{status}**")
    
    with col2:
        st.header("Absensi Hari Ini")
        
        if st.session_state.attendance:
            # Filter hari ini
            today = datetime.now().strftime("%Y-%m-%d")
            today_data = [
                a for a in st.session_state.attendance
                if a["timestamp"].startswith(today)
            ]
            
            if today_data:
                df_today = pd.DataFrame(today_data)
                st.dataframe(df_today, use_container_width=True)
                
                # Stats
                col_a, col_b, col_c, col_d = st.columns(4)
                
                stats = df_today["status"].value_counts()
                
                with col_a:
                    st.metric("Hadir", stats.get("Hadir", 0))
                with col_b:
                    st.metric("Izin", stats.get("Izin", 0))
                with col_c:
                    st.metric("Sakit", stats.get("Sakit", 0))
                with col_d:
                    st.metric("Alpha", stats.get("Alpha", 0))
            else:
                st.info("Belum ada absensi hari ini")
        else:
            st.info("Belum ada data absensi")

with tab2:
    st.header("Data Siswa & Pengaturan")
    
    # Tampilkan data siswa
    st.subheader("Siswa Terdaftar")
    df_students = pd.DataFrame(st.session_state.students)
    st.dataframe(df_students, use_container_width=True)
    
    # Tambah siswa baru
    with st.expander("➕ Tambah Siswa Baru"):
        new_nim = st.text_input("NIM Baru")
        new_nama = st.text_input("Nama Lengkap")
        new_kelas = st.selectbox("Kelas", ["XII-A", "XII-B", "XII-C"])
        
        if st.button("Daftarkan Siswa"):
            if new_nim and new_nama:
                st.session_state.students.append({
                    "nim": new_nim,
                    "nama": new_nama,
                    "kelas": new_kelas
                })
                st.success(f"✅ {new_nama} berhasil didaftarkan!")
                st.rerun()
    
    # Export/Import
    st.subheader("Backup Data")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Export
        if st.session_state.attendance:
            csv_data = export_to_csv()
            st.download_button(
                "📥 Export Absensi (CSV)",
                data=csv_data,
                file_name=f"absensi_{datetime.now().strftime('%Y%m%d')}.csv",
                use_container_width=True
            )
    
    with col2:
        # Import
        uploaded_file = st.file_uploader("Import CSV", type=['csv'])
        if uploaded_file:
            try:
                df_import = pd.read_csv(uploaded_file)
                st.session_state.attendance = df_import.to_dict('records')
                st.success("✅ Data berhasil diimport!")
            except:
                st.error("❌ Format file tidak valid")

with tab3:
    st.header("Laporan & Analisis")
    
    if st.session_state.attendance:
        df_all = pd.DataFrame(st.session_state.attendance)
        
        # Date range filter
        st.subheader("Filter Periode")
        
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("Tanggal Awal")
        with col2:
            end_date = st.date_input("Tanggal Akhir")
        
        if start_date and end_date:
            start_str = start_date.strftime("%Y-%m-%d")
            end_str = end_date.strftime("%Y-%m-%d")
            
            # Filter data
            mask = (df_all['timestamp'] >= start_str) & \
                   (df_all['timestamp'] <= f"{end_str} 23:59:59")
            filtered_df = df_all[mask]
            
            if not filtered_df.empty:
                # Tampilkan data
                st.dataframe(filtered_df, use_container_width=True)
                
                # Chart
                st.subheader("Grafik Kehadiran")
                chart_data = filtered_df['status'].value_counts()
                st.bar_chart(chart_data)
                
                # Summary
                st.subheader("Ringkasan")
                total = len(filtered_df)
                hadir = len(filtered_df[filtered_df['status'] == 'Hadir'])
                percentage = (hadir / total * 100) if total > 0 else 0
                
                st.metric("Total Absensi", total)
                st.metric("Kehadiran", f"{percentage:.1f}%")
            else:
                st.info("Tidak ada data pada periode ini")
    else:
        st.info("Belum ada data absensi")

# ========== SIDEBAR ==========
with st.sidebar:
    st.image("https://streamlit.io/images/brand/streamlit-mark-color.png", width=50)
    st.title("Absensi App")
    
    st.divider()
    
    # Stats
    st.metric("Total Siswa", len(st.session_state.students))
    st.metric("Total Absensi", len(st.session_state.attendance))
    
    st.divider()
    
    # Reset data
    if st.button("🔄 Reset Semua Data", use_container_width=True):
        st.session_state.attendance = []
        st.success("Data absensi direset!")
        st.rerun()
    
    # Info
    st.divider()
    st.caption(f"Versi: 1.0.0")
    st.caption(f"Python: 3.13")
    st.caption(f"Update: {datetime.now().strftime('%d/%m/%Y %H:%M')}")

# ========== FOOTER ==========
st.divider()
st.caption("© 2024 - Absensi Digital v1.0 | Deployed on Streamlit Cloud")

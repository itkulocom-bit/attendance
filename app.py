import streamlit as st
from supabase import create_client, Client
import face_recognition
import numpy as np
from PIL import Image
from datetime import datetime
import tempfile
import os

# ========== SUPABASE CONFIG ==========
@st.cache_resource
def init_supabase():
    # Untuk production: simpan di Streamlit Secrets
    SUPABASE_URL = st.secrets.get("SUPABASE_URL", "https://your-project.supabase.co")
    SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", "your-anon-key")
    
    return create_client(SUPABASE_URL, SUPABASE_KEY)

# ========== STREAMLIT APP ==========
st.set_page_config(page_title="Absensi Wajah", layout="wide")
st.title("🎓 Absensi Wajah dengan Supabase")

# Inisialisasi Supabase
supabase = init_supabase()

# ========== FUNGSI DATABASE ==========
def get_all_students():
    """Ambil semua data siswa dari Supabase"""
    try:
        response = supabase.table("students").select("*").execute()
        return response.data
    except Exception as e:
        st.error(f"Error: {str(e)}")
        return []

def save_attendance(student_data, confidence):
    """Simpan data absensi"""
    try:
        data = {
            "nim": student_data.get("nim", ""),
            "nama": student_data.get("nama", ""),
            "status": "HADIR",
            "confidence": confidence
        }
        
        response = supabase.table("attendance").insert(data).execute()
        return True
    except Exception as e:
        st.error(f"Gagal simpan: {str(e)}")
        return False

def register_new_student(nim, nama, foto_url=None):
    """Registrasi siswa baru"""
    try:
        data = {
            "nim": nim,
            "nama": nama,
            "foto_url": foto_url
        }
        
        response = supabase.table("students").insert(data).execute()
        return True
    except:
        return False

# ========== FACE RECOGNITION ==========
def process_face_image(image):
    """Process image untuk face recognition"""
    try:
        # Convert to numpy array
        img_array = np.array(image)
        
        # Find face encodings
        face_encodings = face_recognition.face_encodings(img_array)
        
        if len(face_encodings) > 0:
            return face_encodings[0]
    except:
        pass
    return None

# ========== MAIN APP ==========
tab1, tab2, tab3 = st.tabs(["📸 Absensi", "👥 Data Siswa", "📊 Dashboard"])

with tab1:
    st.header("Absensi Wajah")
    
    # Load registered faces
    students = get_all_students()
    
    if not students:
        st.warning("Belum ada siswa terdaftar. Tambah dulu di tab Data Siswa.")
    else:
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # Camera input
            picture = st.camera_input("Ambil foto wajah")
            
            if picture:
                # Process image
                image = Image.open(picture)
                st.image(image, caption="Foto yang diambil", width=300)
                
                # Extract face encoding
                with st.spinner("Memproses wajah..."):
                    encoding = process_face_image(image)
                    
                    if encoding is not None:
                        # TODO: Compare dengan database siswa
                        # Untuk sekarang, manual selection dulu
                        st.success("✅ Wajah terdeteksi!")
                        
                        # Pilih siswa (sementara)
                        selected_name = st.selectbox(
                            "Pilih siswa:",
                            [s["nama"] for s in students]
                        )
                        
                        if st.button("Simpan Absensi"):
                            student = next(s for s in students if s["nama"] == selected_name)
                            if save_attendance(student, 95.0):
                                st.balloons()
                                st.success(f"✅ {selected_name} berhasil diabsen!")
                    else:
                        st.error("❌ Wajah tidak terdeteksi")

with tab2:
    st.header("Data Siswa")
    
    # Tampilkan data siswa
    students = get_all_students()
    
    if students:
        st.dataframe(students)
    else:
        st.info("Belum ada data siswa")
    
    # Form tambah siswa baru
    with st.expander("➕ Tambah Siswa Baru"):
        col1, col2 = st.columns(2)
        
        with col1:
            nim = st.text_input("NIM")
            nama = st.text_input("Nama Lengkap")
        
        with col2:
            foto_file = st.file_uploader("Upload Foto", type=['jpg', 'png'])
        
        if st.button("Simpan Siswa"):
            if nim and nama:
                # Simpan foto ke temp (nanti bisa upload ke Supabase Storage)
                foto_url = None
                if foto_file:
                    # Upload logic here
                    pass
                
                if register_new_student(nim, nama, foto_url):
                    st.success(f"✅ {nama} berhasil ditambahkan!")
                    st.rerun()
            else:
                st.warning("Isi NIM dan Nama dulu!")

with tab3:
    st.header("Dashboard Absensi")
    
    # Get attendance data
    try:
        response = supabase.table("attendance").select("*").execute()
        attendance_data = response.data
        
        if attendance_data:
            # Convert to DataFrame untuk display
            import pandas as pd
            df = pd.DataFrame(attendance_data)
            
            # Stats
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Absensi", len(df))
            with col2:
                today = datetime.now().date()
                today_count = len([a for a in attendance_data 
                                 if a['created_at'].startswith(str(today))])
                st.metric("Hari Ini", today_count)
            with col3:
                unique_students = df['nama'].nunique()
                st.metric("Siswa Unique", unique_students)
            
            # Data table
            st.dataframe(df)
            
            # Download button
            csv = df.to_csv(index=False)
            st.download_button(
                "📥 Download CSV",
                data=csv,
                file_name="absensi.csv"
            )
        else:
            st.info("Belum ada data absensi")
    except Exception as e:
        st.error(f"Error: {str(e)}")

# ========== FOOTER ==========
st.divider()
st.caption("Powered by Supabase • Face Attendance System v1.0")

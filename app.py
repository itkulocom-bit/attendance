import streamlit as st
import pandas as pd
from datetime import datetime
from PIL import Image
import io
import base64
import os

# ========== SETUP ==========
st.set_page_config(page_title="Absensi dengan Foto", layout="wide")
st.title("📸 ABSENSI DENGAN FOTO - SIMPLE")

# ========== SESSION STATE ==========
if 'students' not in st.session_state:
    st.session_state.students = []
if 'attendance' not in st.session_state:
    st.session_state.attendance = []
if 'student_photos' not in st.session_state:
    st.session_state.student_photos = {}

# ========== FUNGSI ==========
def image_to_base64(image):
    """Convert PIL Image to base64"""
    buffered = io.BytesIO()
    image.save(buffered, format="JPEG", quality=50)
    return base64.b64encode(buffered.getvalue()).decode()

def save_attendance(nim, nama, status, foto_b64=None):
    """Simpan data absensi"""
    entry = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "nim": nim,
        "nama": nama,
        "status": status,
        "foto": foto_b64[:100] + "..." if foto_b64 else None  # Simpan sebagian
    }
    st.session_state.attendance.append(entry)
    return True

def compare_images_simple(img1_b64, img2_b64):
    """Simple image comparison menggunakan base64"""
    try:
        # Decode base64
        img1_data = base64.b64decode(img1_b64)
        img2_data = base64.b64decode(img2_b64)
        
        # Buka gambar
        img1 = Image.open(io.BytesIO(img1_data)).convert('L').resize((100, 100))
        img2 = Image.open(io.BytesIO(img2_data)).convert('L').resize((100, 100))
        
        # Convert ke numpy array
        import numpy as np
        arr1 = np.array(img1)
        arr2 = np.array(img2)
        
        # Hitung similarity sederhana
        diff = np.mean(np.abs(arr1 - arr2))
        similarity = max(0, 100 - diff)
        
        return similarity > 60, similarity
    except:
        return False, 0

# ========== UI ==========
tab1, tab2, tab3, tab4 = st.tabs(["📸 Absensi Foto", "👥 Data Siswa", "📊 Laporan", "🖼️ Face Match"])

with tab1:
    st.header("Absensi dengan Foto")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        # Input data
        nama = st.text_input("Nama")
        nim = st.text_input("NIM")
        status = st.selectbox("Status", ["Hadir", "Izin", "Sakit", "Alpha"])
        
        # Upload foto
        foto_file = st.file_uploader("Upload Foto Absensi", type=['jpg', 'jpeg', 'png'])
        
        if st.button("💾 Simpan Absensi", type="primary"):
            if nama and nim:
                # Convert foto ke base64 jika ada
                foto_b64 = None
                if foto_file:
                    image = Image.open(foto_file)
                    foto_b64 = image_to_base64(image)
                    st.image(image, caption="Foto yang diupload", width=200)
                
                if save_attendance(nim, nama, status, foto_b64):
                    st.balloons()
                    st.success(f"✅ {nama} berhasil diabsen!")
            else:
                st.warning("⚠️ Isi Nama dan NIM dulu!")
    
    with col2:
        st.header("Data Terakhir")
        if st.session_state.attendance:
            # Ambil 5 data terakhir
            recent = st.session_state.attendance[-5:][::-1]
            for entry in recent:
                with st.container():
                    st.write(f"**{entry['nama']}** - {entry['status']}")
                    st.caption(f"Waktu: {entry['timestamp']}")
                    st.divider()

with tab2:
    st.header("Registrasi Siswa")
    
    # Form registrasi
    with st.form("register_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            reg_nim = st.text_input("NIM (Registrasi)")
            reg_nama = st.text_input("Nama Lengkap")
            reg_kelas = st.selectbox("Kelas", ["XII-A", "XII-B", "XII-C"])
        
        with col2:
            reg_foto = st.file_uploader("Foto Wajah (untuk registrasi)", type=['jpg', 'png'])
            if reg_foto:
                image = Image.open(reg_foto)
                st.image(image, width=150)
        
        if st.form_submit_button("📝 Daftarkan Siswa"):
            if reg_nim and reg_nama and reg_foto:
                # Convert foto ke base64
                foto_b64 = image_to_base64(image)
                
                # Simpan ke database
                st.session_state.students.append({
                    "nim": reg_nim,
                    "nama": reg_nama,
                    "kelas": reg_kelas,
                    "foto_b64": foto_b64
                })
                
                # Simpan ke session photos
                st.session_state.student_photos[reg_nim] = foto_b64
                
                st.success(f"✅ {reg_nama} berhasil didaftarkan!")
                st.rerun()
            else:
                st.warning("Isi semua field dan upload foto!")
    
    # Tampilkan siswa terdaftar
    st.subheader("Siswa Terdaftar")
    if st.session_state.students:
        students_df = pd.DataFrame(st.session_state.students)
        # Jangan tampilkan foto_b64 (terlalu panjang)
        display_df = students_df.drop(columns=['foto_b64'], errors='ignore')
        st.dataframe(display_df)
    else:
        st.info("Belum ada siswa terdaftar")

with tab3:
    st.header("Laporan Absensi")
    
    if st.session_state.attendance:
        df = pd.DataFrame(st.session_state.attendance)
        
        # Filter tanggal
        st.subheader("Filter")
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("Dari")
        with col2:
            end_date = st.date_input("Sampai")
        
        if start_date and end_date:
            start_str = start_date.strftime("%Y-%m-%d")
            end_str = end_date.strftime("%Y-%m-%d")
            
            filtered = df[
                (df['timestamp'] >= start_str) & 
                (df['timestamp'] <= f"{end_str} 23:59:59")
            ]
            
            if not filtered.empty:
                st.dataframe(filtered)
                
                # Stats
                st.subheader("Statistik")
                stats = filtered['status'].value_counts()
                st.bar_chart(stats)
                
                # Download
                csv = filtered.to_csv(index=False)
                st.download_button(
                    "📥 Download CSV",
                    data=csv,
                    file_name=f"absensi_{start_str}_to_{end_str}.csv"
                )
            else:
                st.info("Tidak ada data pada rentang ini")
    else:
        st.info("Belum ada data absensi")

with tab4:
    st.header("Cek Foto Matching (Simple)")
    
    if len(st.session_state.students) < 2:
        st.info("Daftarkan minimal 2 siswa dulu di tab Data Siswa")
    else:
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Foto Referensi")
            student_names = [s['nama'] for s in st.session_state.students]
            ref_name = st.selectbox("Pilih siswa referensi", student_names)
            
            # Tampilkan foto referensi
            ref_student = next(s for s in st.session_state.students if s['nama'] == ref_name)
            if 'foto_b64' in ref_student:
                ref_image_data = base64.b64decode(ref_student['foto_b64'])
                ref_image = Image.open(io.BytesIO(ref_image_data))
                st.image(ref_image, caption=f"Foto {ref_name}", width=200)
        
        with col2:
            st.subheader("Foto untuk Compare")
            test_foto = st.file_uploader("Upload foto untuk compare", type=['jpg', 'png'])
            
            if test_foto:
                test_image = Image.open(test_foto)
                st.image(test_image, caption="Foto test", width=200)
                
                if st.button("🔍 Compare Faces"):
                    # Convert ke base64
                    test_b64 = image_to_base64(test_image)
                    
                    # Compare
                    match, similarity = compare_images_simple(
                        ref_student['foto_b64'], 
                        test_b64
                    )
                    
                    if match:
                        st.success(f"✅ MATCH! Similarity: {similarity:.1f}%")
                        st.balloons()
                    else:
                        st.error(f"❌ NOT MATCH! Similarity: {similarity:.1f}%")

# ========== SIDEBAR ==========
with st.sidebar:
    st.header("⚙️ Kontrol")
    
    # Reset data
    if st.button("🗑️ Reset Semua Data"):
        st.session_state.students = []
        st.session_state.attendance = []
        st.session_state.student_photos = {}
        st.success("Data direset!")
        st.rerun()
    
    # Stats
    st.divider()
    st.metric("Siswa Terdaftar", len(st.session_state.students))
    st.metric("Total Absensi", len(st.session_state.attendance))
    
    # Export semua data
    if st.session_state.attendance:
        st.divider()
        all_df = pd.DataFrame(st.session_state.attendance)
        csv_all = all_df.to_csv(index=False)
        st.download_button(
            "💾 Export Semua Data",
            data=csv_all,
            file_name=f"absensi_full_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
        )

# ========== FOOTER ==========
st.divider()
st.caption(f"App Version 1.0 • Python 3.13 • Total Records: {len(st.session_state.attendance)}")

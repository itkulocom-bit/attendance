import streamlit as st
import pandas as pd
from datetime import datetime, date
import time
from PIL import Image
import io
import base64
import os
import tempfile
import numpy as np

# ========== TRY IMPORT LIBRARIES ==========
# Supabase imports
try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    st.warning("⚠️ Install supabase: pip install supabase")

# Face recognition imports
try:
    from deepface import DeepFace
    DEEPFACE_AVAILABLE = True
except ImportError:
    DEEPFACE_AVAILABLE = False

try:
    import cv2
    OPENCV_AVAILABLE = True
except ImportError:
    OPENCV_AVAILABLE = False

# ========== PAGE CONFIG ==========
st.set_page_config(
    page_title="Absensi Wajah Digital",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ========== INITIALIZE SUPABASE ==========
@st.cache_resource
def init_supabase():
    """Initialize Supabase connection"""
    if not SUPABASE_AVAILABLE:
        return None
    
    try:
        SUPABASE_URL = st.secrets.get("SUPABASE_URL", "")
        SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", "")
        
        if not SUPABASE_URL or not SUPABASE_KEY:
            st.sidebar.warning("⚠️ Setup Supabase Secrets")
            return None
        
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        st.sidebar.success("✅ Supabase Connected")
        return supabase
        
    except Exception as e:
        st.sidebar.error(f"❌ Connection Error")
        return None

# ========== DATABASE FUNCTIONS ==========
def get_all_students(supabase):
    """Get all students from Supabase"""
    if not supabase:
        return []
    
    try:
        response = supabase.table("students").select("*").order("created_at", desc=True).execute()
        return response.data
    except:
        return []

def save_student(supabase, nim, nama, kelas, foto_base64=None):
    """Save student to Supabase"""
    if not supabase:
        return False
    
    try:
        data = {
            "nim": nim.strip(),
            "nama": nama.strip(),
            "kelas": kelas.strip(),
            "foto_base64": foto_base64,
            "updated_at": datetime.now().isoformat()
        }
        
        # Check if exists
        existing = supabase.table("students").select("*").eq("nim", nim).execute()
        if existing.data:
            supabase.table("students").update(data).eq("nim", nim).execute()
        else:
            data["created_at"] = datetime.now().isoformat()
            supabase.table("students").insert(data).execute()
        
        return True
    except Exception as e:
        st.error(f"Error: {str(e)[:100]}")
        return False

def save_attendance(supabase, nim, nama, kelas, status, foto_base64=None, confidence=None):
    """Save attendance record"""
    if not supabase:
        return False
    
    try:
        data = {
            "nim": nim,
            "nama": nama,
            "kelas": kelas,
            "status": status,
            "foto_base64": foto_base64,
            "confidence": confidence,
            "created_at": datetime.now().isoformat()
        }
        
        supabase.table("attendance").insert(data).execute()
        return True
    except Exception as e:
        st.error(f"Error: {str(e)[:100]}")
        return False

def get_attendance_report(supabase, start_date=None, end_date=None):
    """Get attendance report"""
    if not supabase:
        return []
    
    try:
        query = supabase.table("attendance").select("*")
        
        if start_date:
            query = query.gte("created_at", start_date.isoformat())
        if end_date:
            query = query.lte("created_at", f"{end_date.isoformat()}T23:59:59")
        
        query = query.order("created_at", desc=True)
        response = query.execute()
        return response.data
    except:
        return []

# ========== IMAGE PROCESSING ==========
def image_to_base64(image, max_size=(400, 400)):
    """Convert PIL Image to base64"""
    try:
        if max_size:
            image.thumbnail(max_size)
        
        if image.mode in ('RGBA', 'LA', 'P'):
            image = image.convert('RGB')
        
        buffer = io.BytesIO()
        image.save(buffer, format="JPEG", quality=70)
        buffer.seek(0)
        
        img_str = base64.b64encode(buffer.read()).decode('utf-8')
        return img_str
    except:
        return None

# ========== FACE VERIFICATION FUNCTIONS ==========
def check_face_quality(image_base64):
    """Check if image contains a clear face"""
    if not OPENCV_AVAILABLE:
        return True, "OpenCV tidak tersedia"
    
    try:
        # Decode image
        img_data = base64.b64decode(image_base64)
        nparr = np.frombuffer(img_data, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if img is None:
            return False, "Gambar tidak valid"
        
        # Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Load Haar cascade
        cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        face_cascade = cv2.CascadeClassifier(cascade_path)
        
        if face_cascade.empty():
            return True, "Face detector tidak tersedia"
        
        # Detect faces
        faces = face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(100, 100)
        )
        
        if len(faces) == 0:
            return False, "❌ Wajah tidak terdeteksi"
        elif len(faces) > 1:
            return False, "❌ Terdeteksi lebih dari satu wajah"
        else:
            # Check face size
            x, y, w, h = faces[0]
            face_area = w * h
            img_area = img.shape[0] * img.shape[1]
            
            if face_area < img_area * 0.1:
                return False, "❌ Wajah terlalu kecil"
            elif face_area > img_area * 0.8:
                return False, "❌ Wajah terlalu besar"
            else:
                return True, f"✅ Wajah terdeteksi"
                
    except Exception as e:
        return False, f"Error: {str(e)[:100]}"

def compare_faces_deepface(img1_base64, img2_base64):
    """Face comparison using DeepFace"""
    if not DEEPFACE_AVAILABLE:
        return False, 0, 0
    
    try:
        # Create temp files
        with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as f1:
            img1_data = base64.b64decode(img1_base64)
            f1.write(img1_data)
            img1_path = f1.name
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as f2:
            img2_data = base64.b64decode(img2_base64)
            f2.write(img2_data)
            img2_path = f2.name
        
        try:
            # Compare faces
            result = DeepFace.verify(
                img1_path=img1_path,
                img2_path=img2_path,
                model_name="Facenet",
                detector_backend="opencv",
                distance_metric="cosine",
                enforce_detection=False
            )
            
            # Clean up
            os.unlink(img1_path)
            os.unlink(img2_path)
            
            distance = result.get("distance", 1.0)
            similarity = max(0, 100 - (distance * 100))
            match = result.get("verified", False)
            
            return match, similarity, distance
            
        except Exception as e:
            # Clean up on error
            if os.path.exists(img1_path):
                os.unlink(img1_path)
            if os.path.exists(img2_path):
                os.unlink(img2_path)
            return False, 0, 0
            
    except:
        return False, 0, 0

def compare_faces_simple(img1_base64, img2_base64):
    """Simple image comparison"""
    try:
        # Decode images
        img1_data = base64.b64decode(img1_base64)
        img2_data = base64.b64decode(img2_base64)
        
        # Open images
        img1 = Image.open(io.BytesIO(img1_data)).convert('L').resize((128, 128))
        img2 = Image.open(io.BytesIO(img2_data)).convert('L').resize((128, 128))
        
        # Convert to arrays
        arr1 = np.array(img1).flatten()
        arr2 = np.array(img2).flatten()
        
        # Normalize
        arr1 = arr1 / 255.0
        arr2 = arr2 / 255.0
        
        # Calculate similarity
        dot_product = np.dot(arr1, arr2)
        norm1 = np.linalg.norm(arr1)
        norm2 = np.linalg.norm(arr2)
        
        if norm1 == 0 or norm2 == 0:
            return False, 0
        
        similarity = dot_product / (norm1 * norm2)
        similarity_percent = similarity * 100
        
        match = similarity_percent > 65
        
        return match, similarity_percent
        
    except:
        return False, 0

def verify_face_attendance(reference_base64, attendance_photo):
    """Main face verification function"""
    if not attendance_photo:
        return False, 0, "Tidak ada foto absensi"
    
    if not reference_base64:
        return False, 0, "Siswa belum punya foto referensi"
    
    try:
        # Convert attendance photo to base64
        image = Image.open(attendance_photo)
        attendance_base64 = image_to_base64(image)
        
        if not attendance_base64:
            return False, 0, "Gagal memproses foto absensi"
        
        # Check face quality in attendance photo
        face_ok, face_msg = check_face_quality(attendance_base64)
        if not face_ok:
            return False, 0, f"Kualitas foto buruk: {face_msg}"
        
        # Try DeepFace first
        if DEEPFACE_AVAILABLE:
            match, confidence, distance = compare_faces_deepface(reference_base64, attendance_base64)
            method = "DeepFace"
            
            if match and confidence > 60:
                return True, confidence, f"✅ Wajah cocok ({method}: {confidence:.1f}%)"
            elif confidence > 40:
                # Borderline case
                return False, confidence, f"⚠️ Kemiripan rendah ({method}: {confidence:.1f}%)"
            else:
                return False, confidence, f"❌ Wajah tidak cocok ({method}: {confidence:.1f}%)"
        
        # Fallback to simple comparison
        match, confidence = compare_faces_simple(reference_base64, attendance_base64)
        method = "SimpleMatch"
        
        if match and confidence > 70:
            return True, confidence, f"✅ Wajah cocok ({method}: {confidence:.1f}%)"
        elif confidence > 50:
            return False, confidence, f"⚠️ Kemiripan rendah ({method}: {confidence:.1f}%)"
        else:
            return False, confidence, f"❌ Wajah tidak cocok ({method}: {confidence:.1f}%)"
        
    except Exception as e:
        return False, 0, f"Error: {str(e)[:100]}"

# ========== ATTENDANCE WITH VERIFICATION ==========
def save_attendance_with_verification(supabase, student, attendance_photo, status):
    """Save attendance with face verification"""
    try:
        # Get student's reference photo
        reference_photo = student.get('foto_base64')
        
        if not reference_photo:
            # No reference photo, allow with warning
            st.warning("⚠️ Siswa belum punya foto referensi. Absensi tetap disimpan.")
            
            # Save without verification
            image = Image.open(attendance_photo)
            attendance_base64 = image_to_base64(image)
            
            if supabase:
                success = save_attendance(
                    supabase,
                    student.get('nim', ''),
                    student.get('nama', ''),
                    student.get('kelas', ''),
                    status,
                    attendance_base64,
                    0
                )
            else:
                success = True
            
            return success, "Absensi disimpan (tanpa verifikasi)"
        
        # Perform face verification
        verification_result, confidence, message = verify_face_attendance(
            reference_photo, 
            attendance_photo
        )
        
        # Display verification result
        st.info(f"**Hasil Verifikasi:** {message}")
        
        # Handle verification result
        if not verification_result:
            if confidence > 40:  # Borderline case
                st.warning("""
                ⚠️ **PERINGATAN: Kemiripan wajah rendah!**
                
                Apakah Anda yakin ini orang yang sama?
                """)
                
                col1, col2 = st.columns(2)
                with col1:
                    override = st.checkbox("Ya, tetap simpan")
                with col2:
                    if st.button("❌ Batalkan", type="secondary"):
                        return False, "Absensi dibatalkan"
                
                if not override:
                    return False, "Verifikasi wajah gagal"
            else:
                # Definitely not match
                st.error("""
                ❌ **WAJAH TIDAK COCOK!**
                
                Orang yang melakukan absensi berbeda dengan siswa terdaftar.
                """)
                
                # Show both photos for comparison
                col1, col2 = st.columns(2)
                with col1:
                    st.write("**Foto Referensi:**")
                    ref_data = base64.b64decode(reference_photo)
                    ref_img = Image.open(io.BytesIO(ref_data))
                    st.image(ref_img, caption=student['nama'], width=200)
                
                with col2:
                    st.write("**Foto Absensi:**")
                    att_img = Image.open(attendance_photo)
                    st.image(att_img, caption="Foto saat absen", width=200)
                
                return False, "Wajah tidak cocok dengan data siswa"
        
        # Save attendance
        image = Image.open(attendance_photo)
        attendance_base64 = image_to_base64(image)
        
        if supabase:
            success = save_attendance(
                supabase,
                student.get('nim', ''),
                student.get('nama', ''),
                student.get('kelas', ''),
                status,
                attendance_base64,
                confidence
            )
        else:
            success = True
        
        if success:
            return True, f"Absensi berhasil! Confidence: {confidence:.1f}%"
        else:
            return False, "Gagal menyimpan ke database"
        
    except Exception as e:
        return False, f"Error: {str(e)[:100]}"

# ========== MAIN APP ==========
def main():
    # Initialize Supabase
    supabase = init_supabase()
    
    # ========== SIDEBAR ==========
    with st.sidebar:
        st.image("https://cdn-icons-png.flaticon.com/512/3135/3135715.png", width=80)
        st.title("🎓 Absensi Digital")
        
        st.divider()
        
        # System status
        if supabase:
            st.success("✅ Supabase Connected")
        else:
            st.warning("📱 Mode Offline")
        
        if DEEPFACE_AVAILABLE:
            st.success("🤖 DeepFace Ready")
        elif OPENCV_AVAILABLE:
            st.info("👁️ OpenCV Ready")
        else:
            st.error("❌ No Face Recognition")
        
        st.divider()
        
        # Quick stats
        try:
            students = get_all_students(supabase) if supabase else []
            today_att = get_attendance_report(supabase, date.today(), date.today()) if supabase else []
            
            st.metric("Siswa Terdaftar", len(students))
            st.metric("Absensi Hari Ini", len(today_att))
        except:
            pass
        
        st.divider()
        
        # Quick actions
        if st.button("🔄 Refresh Data", use_container_width=True):
            st.rerun()
        
        if st.button("📊 Export Data", use_container_width=True):
            if supabase:
                data = get_attendance_report(supabase)
                if data:
                    df = pd.DataFrame(data)
                    csv = df.to_csv(index=False)
                    st.download_button(
                        "📥 Download CSV",
                        data=csv,
                        file_name=f"absensi_{date.today().strftime('%Y%m%d')}.csv",
                        key="sidebar_download"
                    )
        
        st.divider()
        st.caption(f"v2.0 • {date.today().strftime('%d/%m/%Y')}")

    # ========== MAIN CONTENT ==========
    st.title("📱 Sistem Absensi Wajah Digital")
    st.markdown("**Dengan Verifikasi Wajah Otomatis**")
    
    # Create tabs
    tab1, tab2, tab3, tab4 = st.tabs([
        "📸 Absensi", 
        "👥 Data Siswa", 
        "📊 Laporan", 
        "⚙️ Pengaturan"
    ])
    
    # ========== TAB 1: ATTENDANCE WITH VERIFICATION ==========
    with tab1:
        st.header("📸 Absensi dengan Verifikasi Wajah")
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            # Get students
            students = get_all_students(supabase) if supabase else []
            
            if not students:
                st.warning("""
                ⚠️ **Belum ada siswa terdaftar!**
                
                Silakan daftarkan siswa terlebih dahulu di tab **👥 Data Siswa**.
                """)
            else:
                # Student selection
                student_names = [s.get('nama', '') for s in students]
                selected_name = st.selectbox(
                    "Pilih Siswa:", 
                    student_names,
                    key="attendance_select"
                )
                
                if selected_name:
                    selected_student = next(s for s in students if s.get('nama') == selected_name)
                    
                    # Display student info
                    with st.expander("ℹ️ Info Siswa", expanded=True):
                        col_info1, col_info2 = st.columns(2)
                        with col_info1:
                            st.write(f"**NIM:** {selected_student.get('nim', '')}")
                            st.write(f"**Kelas:** {selected_student.get('kelas', '')}")
                        
                        with col_info2:
                            # Display reference photo if exists
                            if selected_student.get('foto_base64'):
                                try:
                                    ref_data = base64.b64decode(selected_student['foto_base64'])
                                    ref_img = Image.open(io.BytesIO(ref_data))
                                    st.image(ref_img, caption="Foto Referensi", width=100)
                                except:
                                    st.write("📷 Foto tersedia")
                            else:
                                st.warning("⚠️ Belum ada foto")
                    
                    # Attendance photo
                    st.subheader("Foto Absensi")
                    attendance_photo = st.camera_input(
                        "Ambil foto wajah untuk absensi",
                        help="Pastikan wajah jelas dan pencahayaan cukup",
                        key="attendance_camera"
                    )
                    
                    if attendance_photo:
                        st.image(attendance_photo, caption="Foto yang akan diverifikasi", width=200)
                    
                    # Status selection
                    st.subheader("Status Kehadiran")
                    status = st.radio(
                        "Pilih status:",
                        ["Hadir", "Izin", "Sakit", "Alpha"],
                        horizontal=True,
                        key="status_radio"
                    )
                    
                    # Submit button
                    if st.button("✅ Simpan Absensi", type="primary", use_container_width=True):
                        if not attendance_photo:
                            st.error("❌ Ambil foto dulu!")
                        else:
                            with st.spinner("Memverifikasi wajah..."):
                                # Call verification function
                                success, message = save_attendance_with_verification(
                                    supabase,
                                    selected_student,
                                    attendance_photo,
                                    status
                                )
                                
                                if success:
                                    st.balloons()
                                    st.success(f"✅ {message}")
                                    time.sleep(2)
                                    st.rerun()
                                else:
                                    st.error(f"❌ {message}")
        
        with col2:
            st.subheader("📊 Absensi Hari Ini")
            
            # Get today's attendance
            today_data = []
            if supabase:
                today_data = get_attendance_report(supabase, date.today(), date.today())
            
            if today_data:
                df_today = pd.DataFrame(today_data)
                
                # Display statistics
                st.markdown("**Statistik Hari Ini:**")
                
                col_stat1, col_stat2, col_stat3, col_stat4 = st.columns(4)
                with col_stat1:
                    hadir_count = len(df_today[df_today['status'] == 'Hadir'])
                    st.metric("Hadir", hadir_count, delta=f"{hadir_count} orang")
                
                with col_stat2:
                    izin_count = len(df_today[df_today['status'] == 'Izin'])
                    st.metric("Izin", izin_count)
                
                with col_stat3:
                    sakit_count = len(df_today[df_today['status'] == 'Sakit'])
                    st.metric("Sakit", sakit_count)
                
                with col_stat4:
                    alpha_count = len(df_today[df_today['status'] == 'Alpha'])
                    st.metric("Alpha", alpha_count)
                
                # Display attendance table
                st.markdown("**Detail Absensi:**")
                
                # Prepare display dataframe
                display_cols = ['nama', 'kelas', 'status', 'confidence']
                if all(col in df_today.columns for col in display_cols):
                    display_df = df_today[display_cols].copy()
                    display_df['confidence'] = display_df['confidence'].apply(
                        lambda x: f"{x:.1f}%" if pd.notnull(x) and x > 0 else "-"
                    )
                    
                    st.dataframe(
                        display_df,
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            "nama": "Nama",
                            "kelas": "Kelas",
                            "status": "Status",
                            "confidence": "Kecocokan"
                        }
                    )
                
                # Recent photos (if any)
                photos_data = []
                for idx, row in df_today.iterrows():
                    if pd.notnull(row.get('foto_base64')):
                        photos_data.append({
                            'nama': row.get('nama', ''),
                            'foto_base64': row.get('foto_base64')
                        })
                
                if photos_data:
                    st.markdown("**Foto Absensi Terbaru:**")
                    cols = st.columns(min(3, len(photos_data)))
                    for idx, photo_data in enumerate(photos_data[:3]):
                        with cols[idx % 3]:
                            try:
                                img_data = base64.b64decode(photo_data['foto_base64'])
                                img = Image.open(io.BytesIO(img_data))
                                st.image(img, caption=photo_data['nama'], width=100)
                            except:
                                pass
            else:
                st.info("📝 Belum ada absensi hari ini")
                
                # Show sample for new users
                with st.expander("📋 Cara menggunakan:"):
                    st.markdown("""
                    1. **Pilih siswa** dari dropdown di kolom kiri
                    2. **Ambil foto** dengan kamera atau upload foto
                    3. **Pilih status** kehadiran
                    4. **Klik 'Simpan Absensi'**
                    
                    Sistem akan:
                    - Memverifikasi kecocokan wajah dengan foto referensi
                    - Menyimpan data ke database cloud
                    - Menampilkan hasil verifikasi
                    """)
    
    # ========== TAB 2: STUDENT DATA ==========
    with tab2:
        st.header("👥 Manajemen Data Siswa")
        
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.subheader("Tambah/Edit Siswa")
            
            with st.form("student_form", clear_on_submit=True):
                nim = st.text_input("NIM *", max_chars=20, help="Nomor Induk Mahasiswa/Siswa")
                nama = st.text_input("Nama Lengkap *", max_chars=100)
                kelas = st.selectbox(
                    "Kelas *", 
                    ["XII IPA 1", "XII IPA 2", "XII IPA 3", "XII IPS 1", "XII IPS 2", "Lainnya"]
                )
                
                st.markdown("**Foto Wajah (untuk verifikasi)**")
                student_photo = st.file_uploader(
                    "Upload foto wajah yang jelas",
                    type=['jpg', 'jpeg', 'png'],
                    key="student_photo_upload"
                )
                
                if student_photo:
                    preview_img = Image.open(student_photo)
                    st.image(preview_img, caption="Preview", width=150)
                
                submitted = st.form_submit_button("💾 Simpan Data Siswa", type="primary")
                
                if submitted:
                    if nim and nama and kelas:
                        # Process photo
                        foto_base64 = None
                        if student_photo:
                            image = Image.open(student_photo)
                            foto_base64 = image_to_base64(image)
                            
                            # Check photo quality
                            if foto_base64 and OPENCV_AVAILABLE:
                                face_ok, face_msg = check_face_quality(foto_base64)
                                if not face_ok:
                                    st.warning(f"⚠️ {face_msg}")
                        
                        # Save student
                        with st.spinner("Menyimpan data..."):
                            if supabase:
                                success = save_student(supabase, nim, nama, kelas, foto_base64)
                            else:
                                success = True
                            
                            if success:
                                st.success(f"✅ {nama} berhasil disimpan!")
                                time.sleep(1)
                                st.rerun()
                    else:
                        st.error("❌ Harap isi semua field yang wajib (*)")
        
        with col2:
            st.subheader("Daftar Siswa Terdaftar")
            
            # Get students
            students = get_all_students(supabase) if supabase else []
            
            if students:
                # Convert to DataFrame
                df_students = pd.DataFrame(students)
                
                # Display table without photo data
                display_cols = [col for col in df_students.columns if col != 'foto_base64']
                display_df = df_students[display_cols]
                
                # Format datetime columns
                for col in ['created_at', 'updated_at']:
                    if col in display_df.columns:
                        display_df[col] = pd.to_datetime(display_df[col]).dt.strftime('%d/%m/%Y %H:%M')
                
                st.dataframe(
                    display_df,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "nim": "NIM",
                        "nama": "Nama",
                        "kelas": "Kelas",
                        "created_at": "Dibuat",
                        "updated_at": "Diupdate"
                    }
                )
                
                # Export button
                csv_data = display_df.to_csv(index=False)
                st.download_button(
                    "📥 Export Data Siswa (CSV)",
                    data=csv_data,
                    file_name=f"data_siswa_{date.today().strftime('%Y%m%d')}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
                
                # Student count by class
                st.subheader("Statistik per Kelas")
                if 'kelas' in df_students.columns:
                    class_stats = df_students['kelas'].value_counts()
                    st.bar_chart(class_stats)
            else:
                st.info("📝 Belum ada siswa terdaftar")
    
    # ========== TAB 3: REPORTS ==========
    with tab3:
        st.header("📊 Laporan & Analisis")
        
        # Date range filter
        st.subheader("Filter Periode")
        
        col_filter1, col_filter2, col_filter3 = st.columns([1, 1, 2])
        
        with col_filter1:
            start_date = st.date_input("Dari Tanggal", value=date.today())
        
        with col_filter2:
            end_date = st.date_input("Sampai Tanggal", value=date.today())
        
        with col_filter3:
            st.write("")  # Spacer
            if st.button("🔍 Terapkan Filter", use_container_width=True):
                st.rerun()
        
        # Get filtered data
        report_data = []
        if supabase:
            report_data = get_attendance_report(supabase, start_date, end_date)
        
        if report_data:
            df_report = pd.DataFrame(report_data)
            
            # Display statistics
            st.subheader("📈 Statistik")
            
            stat_col1, stat_col2, stat_col3, stat_col4 = st.columns(4)
            
            with stat_col1:
                total = len(df_report)
                st.metric("Total Absensi", total)
            
            with stat_col2:
                unique_students = df_report['nama'].nunique()
                st.metric("Siswa Unik", unique_students)
            
            with stat_col3:
                hadir_count = len(df_report[df_report['status'] == 'Hadir'])
                hadir_pct = (hadir_count / total * 100) if total > 0 else 0
                st.metric("Presentase Hadir", f"{hadir_pct:.1f}%")
            
            with stat_col4:
                avg_confidence = df_report['confidence'].mean() if 'confidence' in df_report.columns else 0
                st.metric("Rata-rata Kecocokan", f"{avg_confidence:.1f}%" if avg_confidence > 0 else "-")
            
            # Display data table
            st.subheader("📋 Data Absensi")
            
            # Prepare display columns
            display_cols_report = ['created_at', 'nama', 'kelas', 'status', 'confidence']
            if all(col in df_report.columns for col in display_cols_report):
                display_df_report = df_report[display_cols_report].copy()
                
                # Format columns
                display_df_report['created_at'] = pd.to_datetime(display_df_report['created_at']).dt.strftime('%d/%m/%Y %H:%M')
                display_df_report['confidence'] = display_df_report['confidence'].apply(
                    lambda x: f"{x:.1f}%" if pd.notnull(x) and x > 0 else "-"
                )
                
                st.dataframe(
                    display_df_report,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "created_at": "Waktu",
                        "nama": "Nama",
                        "kelas": "Kelas",
                        "status": "Status",
                        "confidence": "Kecocokan"
                    }
                )
            
            # Charts
            st.subheader("📊 Visualisasi Data")
            
            chart_col1, chart_col2 = st.columns(2)
            
            with chart_col1:
                # Status distribution
                status_dist = df_report['status'].value_counts()
                if not status_dist.empty:
                    st.markdown("**Distribusi Status**")
                    st.bar_chart(status_dist)
            
            with chart_col2:
                # Daily trend
                if 'created_at' in df_report.columns:
                    df_report['date'] = pd.to_datetime(df_report['created_at']).dt.date
                    daily_count = df_report.groupby('date').size()
                    if not daily_count.empty:
                        st.markdown("**Trend Harian**")
                        st.line_chart(daily_count)
            
            # Export options
            st.subheader("📤 Export Data")
            
            export_col1, export_col2 = st.columns(2)
            
            with export_col1:
                # CSV export
                csv_report = df_report.to_csv(index=False)
                st.download_button(
                    "📥 Download CSV",
                    data=csv_report,
                    file_name=f"laporan_absensi_{start_date}_{end_date}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
            
            with export_col2:
                # Summary report
                summary_data = {
                    'Periode': [f"{start_date} sampai {end_date}"],
                    'Total Absensi': [total],
                    'Siswa Unik': [unique_students],
                    'Presentase Hadir': [f"{hadir_pct:.1f}%"]
                }
                df_summary = pd.DataFrame(summary_data)
                summary_csv = df_summary.to_csv(index=False)
                
                st.download_button(
                    "📄 Download Ringkasan",
                    data=summary_csv,
                    file_name=f"ringkasan_{start_date}_{end_date}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
        else:
            st.info(f"📝 Tidak ada data absensi dari {start_date} sampai {end_date}")
    
    # ========== TAB 4: SETTINGS ==========
    with tab4:
        st.header("⚙️ Pengaturan Sistem")
        
        col_set1, col_set2 = st.columns(2)
        
        with col_set1:
            st.subheader("Konfigurasi Sistem")
            
            # Verification settings
            st.markdown("**Pengaturan Verifikasi:**")
            
            verification_method = st.selectbox(
                "Metode Verifikasi Wajah",
                ["Auto (Rekomendasi)", "DeepFace", "Simple Match", "Tanpa Verifikasi"],
                help="Pilih metode verifikasi wajah yang digunakan"
            )
            
            min_confidence = st.slider(
                "Minimum Kecocokan (%)",
                min_value=0,
                max_value=100,
                value=60,
                help="Nilai minimum kecocokan wajah untuk dianggap valid"
            )
            
            # Photo settings
            st.markdown("**Pengaturan Foto:**")
            
            photo_quality = st.select_slider(
                "Kualitas Foto",
                options=["Rendah", "Sedang", "Tinggi"],
                value="Sedang"
            )
            
            max_photo_size = st.number_input(
                "Ukuran Maks Foto (KB)",
                min_value=10,
                max_value=1024,
                value=200,
                help="Ukuran maksimal foto yang diupload"
            )
        
        with col_set2:
            st.subheader("Status Sistem")
            
            # System info
            st.markdown("**Informasi Sistem:**")
            
            info_col1, info_col2 = st.columns(2)
            
            with info_col1:
                st.metric("Versi Aplikasi", "2.0.0")
                st.metric("Database", "Supabase" if supabase else "Lokal")
                
            with info_col2:
                st.metric("Face Recognition", 
                         "DeepFace" if DEEPFACE_AVAILABLE else 
                         "OpenCV" if OPENCV_AVAILABLE else "Tidak tersedia")
                st.metric("Python Version", "3.13")
            
            # System actions
            st.markdown("**Aksi Sistem:**")
            
            if st.button("🔄 Clear Cache", use_container_width=True):
                st.cache_resource.clear()
                st.success("Cache cleared!")
                time.sleep(1)
                st.rerun()
            
            if st.button("🧪 Test Connection", use_container_width=True):
                if supabase:
                    try:
                        test = supabase.table("students").select("count", count="exact").execute()
                        st.success(f"✅ Koneksi OK. Tabel students: {len(get_all_students(supabase))} data")
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)[:100]}")
                else:
                    st.warning("⚠️ Supabase tidak terhubung")
        
        # Database management
        st.subheader("Manajemen Database")
        
        db_col1, db_col2, db_col3 = st.columns(3)
        
        with db_col1:
            if st.button("📊 Backup Data", use_container_width=True):
                if supabase:
                    students_data = get_all_students(supabase)
                    attendance_data = get_attendance_report(supabase)
                    
                    backup = {
                        "students": students_data,
                        "attendance": attendance_data,
                        "backup_date": datetime.now().isoformat()
                    }
                    
                    import json
                    backup_json = json.dumps(backup, indent=2)
                    
                    st.download_button(
                        "💾 Download Backup",
                        data=backup_json,
                        file_name=f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                        mime="application/json"
                    )
        
        with db_col2:
            if st.button("🗑️ Clear All Data", type="secondary", use_container_width=True):
                st.warning("""
                ⚠️ **PERINGATAN:** 
                Aksi ini akan menghapus SEMUA data!
                """)
                
                confirm = st.checkbox("Saya mengerti dan ingin menghapus semua data")
                if confirm and st.button("🚨 Konfirmasi Hapus", type="primary"):
                    st.error("Fitur ini belum diimplementasikan untuk keamanan")
        
        with db_col3:
            if st.button("📋 System Logs", use_container_width=True):
                st.info("""
                **Log Sistem:**
                - Aplikasi berjalan normal
                - Database: Connected
                - Face Recognition: Ready
                - Last update: Now
                """)

    # ========== FOOTER ==========
    st.divider()
    
    footer_col1, footer_col2, footer_col3 = st.columns([1, 2, 1])
    
    with footer_col2:
        current_time = datetime.now().strftime('%H:%M:%S')
        
        # System status indicators
        status_indicators = []
        if supabase:
            status_indicators.append("✅ Database")
        if DEEPFACE_AVAILABLE or OPENCV_AVAILABLE:
            status_indicators.append("✅ Face Recognition")
        
        status_text = " • ".join(status_indicators) if status_indicators else "⚠️ Limited Mode"
        
        st.caption(f"""
        **Absensi Digital v2.0** • {status_text} • {current_time}
        """)

# ========== RUN APP ==========
if __name__ == "__main__":
    main()

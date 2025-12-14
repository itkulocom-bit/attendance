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

# OpenCV for face detection
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
            return None
        
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        return supabase
        
    except:
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
        
        existing = supabase.table("students").select("*").eq("nim", nim).execute()
        if existing.data:
            supabase.table("students").update(data).eq("nim", nim).execute()
        else:
            data["created_at"] = datetime.now().isoformat()
            supabase.table("students").insert(data).execute()
        
        return True
    except:
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
    except:
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

# ========== FACE DETECTION & VERIFICATION ==========
def detect_faces(image_base64):
    """Detect faces in image using OpenCV"""
    if not OPENCV_AVAILABLE:
        return [], "OpenCV tidak tersedia"
    
    try:
        # Decode image
        img_data = base64.b64decode(image_base64)
        nparr = np.frombuffer(img_data, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if img is None:
            return [], "Gambar tidak valid"
        
        # Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Load Haar cascade
        cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        if not os.path.exists(cascade_path):
            return [], "File detektor wajah tidak ditemukan"
        
        face_cascade = cv2.CascadeClassifier(cascade_path)
        
        if face_cascade.empty():
            return [], "Gagal memuat detektor wajah"
        
        # Detect faces
        faces = face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(100, 100)
        )
        
        face_count = len(faces)
        
        if face_count == 0:
            return [], "❌ Wajah tidak terdeteksi"
        elif face_count > 1:
            return [], f"❌ Terdeteksi {face_count} wajah (harus 1)"
        else:
            # Get face coordinates
            x, y, w, h = faces[0]
            
            # Calculate face position and size
            img_height, img_width = img.shape[:2]
            face_area = w * h
            img_area = img_width * img_height
            face_ratio = face_area / img_area
            
            # Check face quality
            if face_ratio < 0.05:  # Face too small
                return [], "❌ Wajah terlalu kecil, dekatkan ke kamera"
            elif face_ratio > 0.7:  # Face too large
                return [], "❌ Wajah terlalu besar, jauhkan dari kamera"
            
            # Extract face region
            face_img = img[y:y+h, x:x+w]
            
            # Convert back to base64
            _, buffer = cv2.imencode('.jpg', face_img)
            face_base64 = base64.b64encode(buffer).decode('utf-8')
            
            return [(x, y, w, h, face_base64)], f"✅ Wajah terdeteksi ({int(face_ratio*100)}% frame)"
            
    except Exception as e:
        return [], f"Error: {str(e)[:100]}"

def extract_face_features(image_base64):
    """Extract simple features from face for comparison"""
    try:
        # Decode image
        img_data = base64.b64decode(image_base64)
        nparr = np.frombuffer(img_data, np.uint8)
        
        # If it's a color image, decode normally
        try:
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if img is None:
                # Try as grayscale
                img = cv2.imdecode(nparr, cv2.IMREAD_GRAYSCALE)
        except:
            # Use PIL as fallback
            img = Image.open(io.BytesIO(img_data)).convert('L')
            img = np.array(img)
        
        if img is None:
            return None
        
        # Resize to standard size
        img_resized = cv2.resize(img, (128, 128))
        
        # Convert to grayscale if needed
        if len(img_resized.shape) == 3:
            img_resized = cv2.cvtColor(img_resized, cv2.COLOR_BGR2GRAY)
        
        # Flatten and normalize
        features = img_resized.flatten()
        features = features / 255.0
        
        # Simple feature extraction (histogram)
        hist = cv2.calcHist([img_resized], [0], None, [64], [0, 256])
        hist = hist.flatten()
        hist = hist / hist.sum() if hist.sum() > 0 else hist
        
        return {
            'pixels': features,
            'histogram': hist,
            'shape': img_resized.shape
        }
        
    except:
        return None

def compare_faces_features(ref_features, test_features):
    """Compare two faces using extracted features"""
    if ref_features is None or test_features is None:
        return 0
    
    try:
        # Compare histograms (correlation)
        if 'histogram' in ref_features and 'histogram' in test_features:
            hist_corr = cv2.compareHist(
                ref_features['histogram'].astype(np.float32),
                test_features['histogram'].astype(np.float32),
                cv2.HISTCMP_CORREL
            )
            hist_score = (hist_corr + 1) / 2 * 100  # Convert to 0-100 scale
        else:
            hist_score = 0
        
        # Compare pixel values (cosine similarity)
        if 'pixels' in ref_features and 'pixels' in test_features:
            ref_pixels = ref_features['pixels']
            test_pixels = test_features['pixels']
            
            dot_product = np.dot(ref_pixels, test_pixels)
            norm_ref = np.linalg.norm(ref_pixels)
            norm_test = np.linalg.norm(test_pixels)
            
            if norm_ref > 0 and norm_test > 0:
                cosine_sim = dot_product / (norm_ref * norm_test)
                pixel_score = max(0, cosine_sim * 100)
            else:
                pixel_score = 0
        else:
            pixel_score = 0
        
        # Combined score (weighted average)
        combined_score = (hist_score * 0.6) + (pixel_score * 0.4)
        
        return min(100, max(0, combined_score))
        
    except:
        return 0

def verify_face_simple(reference_base64, test_photo):
    """Simple but effective face verification"""
    if not test_photo:
        return False, 0, "Tidak ada foto absensi"
    
    if not reference_base64:
        return False, 0, "Siswa belum punya foto referensi"
    
    try:
        # Convert test photo to base64
        test_image = Image.open(test_photo)
        test_base64 = image_to_base64(test_image)
        
        if not test_base64:
            return False, 0, "Gagal memproses foto"
        
        # Step 1: Detect faces in both images
        ref_faces, ref_msg = detect_faces(reference_base64)
        test_faces, test_msg = detect_faces(test_base64)
        
        if not ref_faces:
            return False, 0, f"Foto referensi: {ref_msg}"
        if not test_faces:
            return False, 0, f"Foto absensi: {test_msg}"
        
        # Step 2: Extract features from detected faces
        ref_face_base64 = ref_faces[0][4]  # Extracted face image
        test_face_base64 = test_faces[0][4]
        
        ref_features = extract_face_features(ref_face_base64)
        test_features = extract_face_features(test_face_base64)
        
        if ref_features is None:
            return False, 0, "Gagal ekstraksi fitur referensi"
        if test_features is None:
            return False, 0, "Gagal ekstraksi fitur absensi"
        
        # Step 3: Compare features
        similarity_score = compare_faces_features(ref_features, test_features)
        
        # Determine match based on threshold
        match_threshold = 65  # Adjust based on testing
        is_match = similarity_score >= match_threshold
        
        # Provide detailed feedback
        if is_match:
            if similarity_score >= 80:
                message = f"✅ WAJAH COCOK! ({similarity_score:.1f}%)"
            else:
                message = f"✅ Wajah cocok ({similarity_score:.1f}%)"
        else:
            if similarity_score >= 50:
                message = f"⚠️ Kemiripan rendah ({similarity_score:.1f}%)"
            else:
                message = f"❌ Wajah tidak cocok ({similarity_score:.1f}%)"
        
        return is_match, similarity_score, message
        
    except Exception as e:
        return False, 0, f"Error verifikasi: {str(e)[:100]}"

# ========== ATTENDANCE WITH VERIFICATION ==========
def save_attendance_with_verification(supabase, student, attendance_photo, status):
    """Save attendance with face verification"""
    try:
        # Get student's reference photo
        reference_photo = student.get('foto_base64')
        
        if not reference_photo:
            # No reference photo, allow with warning
            st.warning("⚠️ Siswa belum punya foto referensi")
            
            # Convert and save
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
            
            if success:
                return True, "Absensi disimpan (tanpa verifikasi wajah)"
            else:
                return False, "Gagal menyimpan"
        
        # Perform face verification
        verification_result, confidence, message = verify_face_simple(
            reference_photo, 
            attendance_photo
        )
        
        # Display verification result
        st.info(f"**Hasil Verifikasi:** {message}")
        
        # Handle different verification outcomes
        if not verification_result:
            if confidence >= 50:  # Borderline case
                st.warning(f"""
                ⚠️ **PERINGATAN!**
                
                Kecocokan wajah hanya {confidence:.1f}%
                Mungkin ini orang yang sama dengan ekspresi/pose berbeda?
                """)
                
                col1, col2 = st.columns(2)
                with col1:
                    override = st.checkbox("Ya, ini orang yang sama")
                with col2:
                    if st.button("❌ Batalkan", type="secondary", key="cancel_borderline"):
                        return False, "Absensi dibatalkan"
                
                if not override:
                    return False, f"Verifikasi gagal ({confidence:.1f}%)"
            else:
                # Definitely not match
                st.error(f"""
                ❌ **WAJAH TIDAK COCOK!**
                
                Kecocokan hanya {confidence:.1f}%
                Orang yang absen berbeda dengan siswa terdaftar.
                """)
                
                # Show comparison
                col_compare1, col_compare2 = st.columns(2)
                with col_compare1:
                    st.write("**Foto Referensi:**")
                    ref_data = base64.b64decode(reference_photo)
                    ref_img = Image.open(io.BytesIO(ref_data))
                    st.image(ref_img, caption=student['nama'], width=200)
                
                with col_compare2:
                    st.write("**Foto Absensi:**")
                    att_img = Image.open(attendance_photo)
                    st.image(att_img, caption="Foto saat absen", width=200)
                
                return False, f"Wajah tidak cocok ({confidence:.1f}%)"
        
        # Save successful attendance
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
            return True, f"✅ Absensi berhasil! Kecocokan: {confidence:.1f}%"
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
        status_text = []
        if supabase:
            status_text.append("✅ Database")
        if OPENCV_AVAILABLE:
            status_text.append("✅ Face Detection")
        
        if status_text:
            st.success(" • ".join(status_text))
        else:
            st.warning("⚠️ Mode Terbatas")
        
        st.divider()
        
        # Quick stats
        try:
            students = get_all_students(supabase) if supabase else []
            today_att = get_attendance_report(supabase, date.today(), date.today()) if supabase else []
            
            st.metric("Siswa", len(students))
            st.metric("Absensi Hari Ini", len(today_att))
        except:
            pass
        
        st.divider()
        
        # Quick actions
        if st.button("🔄 Refresh", use_container_width=True):
            st.rerun()
        
        st.divider()
        st.caption(f"v2.1 • {date.today().strftime('%d/%m/%Y')}")

    # ========== MAIN CONTENT ==========
    st.title("📱 Sistem Absensi Wajah")
    st.markdown("**Dengan Verifikasi Wajah Menggunakan OpenCV**")
    
    # Create tabs
    tab1, tab2, tab3 = st.tabs(["📸 Absensi", "👥 Data Siswa", "📊 Laporan"])
    
    # ========== TAB 1: ATTENDANCE ==========
    with tab1:
        st.header("📸 Absensi dengan Verifikasi Wajah")
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            # Get students
            students = get_all_students(supabase) if supabase else []
            
            if not students:
                st.warning("""
                ⚠️ **Belum ada siswa terdaftar!**
                
                Daftarkan siswa dulu di tab **👥 Data Siswa**.
                """)
            else:
                # Student selection
                student_names = [s.get('nama', '') for s in students]
                selected_name = st.selectbox("Pilih Siswa:", student_names)
                
                if selected_name:
                    selected_student = next(s for s in students if s.get('nama') == selected_name)
                    
                    # Display student info
                    st.info(f"""
                    **Info Siswa:**
                    - NIM: {selected_student.get('nim', '')}
                    - Kelas: {selected_student.get('kelas', '')}
                    - Foto Referensi: {'✅ Ada' if selected_student.get('foto_base64') else '❌ Belum ada'}
                    """)
                    
                    # Show reference photo if available
                    if selected_student.get('foto_base64'):
                        try:
                            ref_data = base64.b64decode(selected_student['foto_base64'])
                            ref_img = Image.open(io.BytesIO(ref_data))
                            st.image(ref_img, caption="Foto Referensi", width=150)
                        except:
                            pass
                    
                    # Attendance photo
                    st.subheader("Ambil Foto Absensi")
                    attendance_photo = st.camera_input(
                        "Hadapkan wajah ke kamera",
                        key="attendance_camera"
                    )
                    
                    if attendance_photo:
                        st.image(attendance_photo, caption="Foto yang akan diverifikasi", width=200)
                    
                    # Status selection
                    status = st.radio(
                        "Status Kehadiran:",
                        ["Hadir", "Izin", "Sakit", "Alpha"],
                        horizontal=True
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
                col_stat1, col_stat2, col_stat3, col_stat4 = st.columns(4)
                with col_stat1:
                    hadir = len(df_today[df_today['status'] == 'Hadir'])
                    st.metric("Hadir", hadir)
                with col_stat2:
                    izin = len(df_today[df_today['status'] == 'Izin'])
                    st.metric("Izin", izin)
                with col_stat3:
                    sakit = len(df_today[df_today['status'] == 'Sakit'])
                    st.metric("Sakit", sakit)
                with col_stat4:
                    alpha = len(df_today[df_today['status'] == 'Alpha'])
                    st.metric("Alpha", alpha)
                
                # Display table
                if 'confidence' in df_today.columns and 'nama' in df_today.columns:
                    display_df = df_today[['nama', 'status', 'confidence']].copy()
                    display_df['confidence'] = display_df['confidence'].apply(
                        lambda x: f"{x:.1f}%" if pd.notnull(x) and x > 0 else "-"
                    )
                    
                    st.dataframe(display_df, use_container_width=True, hide_index=True)
            else:
                st.info("📝 Belum ada absensi hari ini")
    
    # ========== TAB 2: STUDENT DATA ==========
    with tab2:
        st.header("👥 Data Siswa")
        
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.subheader("Tambah/Edit Siswa")
            
            with st.form("student_form"):
                nim = st.text_input("NIM *", max_chars=20)
                nama = st.text_input("Nama Lengkap *", max_chars=100)
                kelas = st.selectbox("Kelas *", ["XII IPA 1", "XII IPA 2", "XII IPA 3", "XII IPS 1", "XII IPS 2"])
                
                st.write("Foto Wajah")
                student_photo = st.file_uploader("Upload foto wajah", type=['jpg', 'jpeg', 'png'])
                
                if student_photo:
                    st.image(student_photo, width=150)
                
                if st.form_submit_button("💾 Simpan", type="primary"):
                    if nim and nama and kelas:
                        foto_base64 = None
                        if student_photo:
                            image = Image.open(student_photo)
                            foto_base64 = image_to_base64(image)
                        
                        if supabase:
                            success = save_student(supabase, nim, nama, kelas, foto_base64)
                        else:
                            success = True
                        
                        if success:
                            st.success(f"✅ {nama} tersimpan!")
                            time.sleep(1)
                            st.rerun()
        
        with col2:
            st.subheader("Daftar Siswa")
            
            students = get_all_students(supabase) if supabase else []
            
            if students:
                df_students = pd.DataFrame(students)
                
                # Remove photo column for display
                if 'foto_base64' in df_students.columns:
                    display_df = df_students.drop(columns=['foto_base64'])
                else:
                    display_df = df_students
                
                st.dataframe(display_df, use_container_width=True, hide_index=True)
                
                # Export
                csv_data = display_df.to_csv(index=False)
                st.download_button(
                    "📥 Export CSV",
                    data=csv_data,
                    file_name=f"siswa_{date.today().strftime('%Y%m%d')}.csv"
                )
            else:
                st.info("📝 Belum ada siswa")
    
    # ========== TAB 3: REPORTS ==========
    with tab3:
        st.header("📊 Laporan")
        
        # Date filter
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("Dari", value=date.today())
        with col2:
            end_date = st.date_input("Sampai", value=date.today())
        
        # Get report
        report_data = []
        if supabase:
            report_data = get_attendance_report(supabase, start_date, end_date)
        
        if report_data:
            df_report = pd.DataFrame(report_data)
            
            # Stats
            st.subheader("Statistik")
            col_a, col_b, col_c = st.columns(3)
            with col_a:
                total = len(df_report)
                st.metric("Total", total)
            with col_b:
                unique = df_report['nama'].nunique()
                st.metric("Siswa Unik", unique)
            with col_c:
                if 'confidence' in df_report.columns:
                    avg_conf = df_report['confidence'].mean()
                    st.metric("Rata Kecocokan", f"{avg_conf:.1f}%")
            
            # Data
            st.subheader("Data")
            display_cols = ['created_at', 'nama', 'status']
            if 'confidence' in df_report.columns:
                display_cols.append('confidence')
            
            if all(col in df_report.columns for col in display_cols):
                display_df = df_report[display_cols].copy()
                if 'confidence' in display_df.columns:
                    display_df['confidence'] = display_df['confidence'].apply(
                        lambda x: f"{x:.1f}%" if pd.notnull(x) else "-"
                    )
                
                st.dataframe(display_df, use_container_width=True, hide_index=True)
            
            # Export
            csv_report = df_report.to_csv(index=False)
            st.download_button(
                "📥 Download Laporan",
                data=csv_report,
                file_name=f"laporan_{start_date}_{end_date}.csv",
                use_container_width=True
            )
        else:
            st.info(f"📝 Tidak ada data {start_date} sampai {end_date}")
    
    # ========== FOOTER ==========
    st.divider()
    st.caption(f"Absensi Wajah v2.1 • {datetime.now().strftime('%H:%M:%S')}")

# ========== RUN APP ==========
if __name__ == "__main__":
    main()

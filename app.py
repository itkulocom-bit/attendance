import streamlit as st
import pandas as pd
from datetime import datetime, date
import time
from PIL import Image
import io
import base64
import hashlib

# Supabase imports
try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False

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
        st.warning("⚠️ Supabase library tidak tersedia. Install: pip install supabase")
        return None
    
    try:
        # Get credentials from Streamlit Secrets
        SUPABASE_URL = st.secrets.get("SUPABASE_URL", "")
        SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", "")
        
        if not SUPABASE_URL or not SUPABASE_KEY:
            st.warning("⚠️ Supabase credentials belum diatur di Streamlit Secrets")
            return None
        
        # Create client
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        
        # Test connection
        test_response = supabase.table("_test").select("count", count="exact").execute()
        st.success("✅ Terhubung ke Supabase!")
        return supabase
        
    except Exception as e:
        st.error(f"❌ Gagal koneksi ke Supabase: {str(e)}")
        return None

# ========== DATABASE FUNCTIONS ==========
def setup_database(supabase):
    """Setup database tables if not exist"""
    if not supabase:
        return False
    
    try:
        # Check if students table exists
        try:
            supabase.table("students").select("count", count="exact").limit(1).execute()
        except:
            # Create students table
            st.info("📝 Membuat tabel 'students'...")
            # Table akan dibuat via Supabase dashboard
        
        # Check if attendance table exists
        try:
            supabase.table("attendance").select("count", count="exact").limit(1).execute()
        except:
            # Create attendance table
            st.info("📝 Membuat tabel 'attendance'...")
            
        return True
    except Exception as e:
        st.error(f"Error setup database: {str(e)}")
        return False

def get_all_students(supabase):
    """Get all students from Supabase"""
    if not supabase:
        return []
    
    try:
        response = supabase.table("students").select("*").order("created_at", desc=True).execute()
        return response.data
    except Exception as e:
        st.error(f"Error mengambil data siswa: {str(e)}")
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
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        
        response = supabase.table("students").insert(data).execute()
        return True
    except Exception as e:
        st.error(f"Error menyimpan siswa: {str(e)}")
        return False

def save_attendance(supabase, nim, nama, kelas, status, foto_base64=None, confidence=None):
    """Save attendance record to Supabase"""
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
        
        response = supabase.table("attendance").insert(data).execute()
        return True
    except Exception as e:
        st.error(f"Error menyimpan absensi: {str(e)}")
        return False

def get_attendance_report(supabase, start_date=None, end_date=None):
    """Get attendance report with optional date filter"""
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
    except Exception as e:
        st.error(f"Error mengambil laporan: {str(e)}")
        return []

# ========== IMAGE PROCESSING ==========
def image_to_base64(image, max_size=(400, 400), quality=70):
    """Convert PIL Image to optimized base64"""
    try:
        # Resize if too large
        if max_size:
            image.thumbnail(max_size, Image.Resampling.LANCZOS)
        
        # Convert to RGB if necessary
        if image.mode in ('RGBA', 'LA', 'P'):
            image = image.convert('RGB')
        
        # Save to bytes with optimization
        buffer = io.BytesIO()
        image.save(buffer, format="JPEG", quality=quality, optimize=True)
        buffer.seek(0)
        
        # Encode to base64
        img_str = base64.b64encode(buffer.read()).decode('utf-8')
        return img_str
    except Exception as e:
        st.error(f"Error processing image: {str(e)}")
        return None

def compare_faces_simple(img1_base64, img2_base64):
    """Simple face comparison using image hashing"""
    try:
        # Decode base64 images
        img1_data = base64.b64decode(img1_base64)
        img2_data = base64.b64decode(img2_base64)
        
        # Create image hashes
        hash1 = hashlib.md5(img1_data).hexdigest()
        hash2 = hashlib.md5(img2_data).hexdigest()
        
        # Simple comparison (for demo only - in production use proper face recognition)
        similarity = 100 if hash1 == hash2 else 30
        
        return similarity > 70, similarity
    except:
        return False, 0

# ========== SESSION STATE INIT ==========
if 'use_supabase' not in st.session_state:
    st.session_state.use_supabase = True

if 'local_students' not in st.session_state:
    st.session_state.local_students = []

if 'local_attendance' not in st.session_state:
    st.session_state.local_attendance = []

# ========== MAIN APP ==========
def main():
    # Initialize Supabase
    supabase = None
    if st.session_state.use_supabase:
        supabase = init_supabase()
        if supabase:
            setup_database(supabase)
    
    # ========== SIDEBAR ==========
    with st.sidebar:
        st.image("https://cdn-icons-png.flaticon.com/512/3135/3135715.png", width=80)
        st.title("🎓 Absensi Digital")
        
        st.divider()
        
        # Database selector
        st.session_state.use_supabase = st.toggle(
            "🌐 Gunakan Supabase Cloud",
            value=st.session_state.use_supabase,
            help="Simpan data di cloud atau lokal"
        )
        
        if supabase:
            st.success("✅ Cloud Connected")
            
            # Quick stats
            try:
                students_count = len(get_all_students(supabase))
                st.metric("Siswa Terdaftar", students_count)
                
                today_att = get_attendance_report(supabase, date.today(), date.today())
                st.metric("Absensi Hari Ini", len(today_att))
            except:
                pass
        else:
            st.info("📱 Mode Lokal")
            st.metric("Siswa", len(st.session_state.local_students))
            st.metric("Absensi", len(st.session_state.local_attendance))
        
        st.divider()
        
        # Quick actions
        if st.button("🔄 Refresh Data", use_container_width=True):
            st.rerun()
        
        if st.button("📊 Export Semua Data", use_container_width=True):
            if supabase:
                data = get_attendance_report(supabase)
                if data:
                    df = pd.DataFrame(data)
                    csv = df.to_csv(index=False)
                    st.download_button(
                        "📥 Download CSV",
                        data=csv,
                        file_name=f"absensi_full_{datetime.now().strftime('%Y%m%d')}.csv",
                        key="download_csv"
                    )
        
        st.divider()
        st.caption(f"v1.0 • {datetime.now().strftime('%d/%m/%Y')}")

    # ========== MAIN CONTENT ==========
    st.title("📱 Sistem Absensi Wajah Digital")
    st.markdown("**Dengan Supabase Cloud Database**")
    
    # Create tabs
    tab1, tab2, tab3, tab4 = st.tabs([
        "📸 Absensi", 
        "👥 Data Siswa", 
        "📊 Laporan", 
        "🔍 Verifikasi Wajah"
    ])
    
    # ========== TAB 1: ATTENDANCE ==========
    with tab1:
        st.header("Input Absensi")
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            # Get students list
            students = []
            if supabase:
                students = get_all_students(supabase)
            else:
                students = st.session_state.local_students
            
            if not students:
                st.warning("⚠️ Belum ada siswa terdaftar. Daftarkan dulu di tab **Data Siswa**.")
            else:
                # Student selection
                student_names = [s.get('nama', '') for s in students]
                selected_name = st.selectbox("Pilih Siswa:", student_names)
                
                if selected_name:
                    # Get selected student data
                    selected_student = next(s for s in students if s.get('nama') == selected_name)
                    
                    st.info(f"""
                    **Data Siswa:**
                    - NIM: {selected_student.get('nim', '')}
                    - Kelas: {selected_student.get('kelas', '')}
                    """)
                    
                    # Attendance photo
                    st.subheader("Foto Absensi")
                    attendance_photo = st.camera_input(
                        "Ambil foto wajah untuk absensi",
                        key="attendance_camera"
                    )
                    
                    # Status selection
                    status = st.radio(
                        "Status Kehadiran:",
                        ["Hadir", "Izin", "Sakit", "Alpha"],
                        horizontal=True
                    )
                    
                    # Confidence slider (if using face verification)
                    confidence = st.slider("Tingkat Keyakinan (%)", 0, 100, 85)
                    
                    # Submit button
                    if st.button("✅ Simpan Absensi", type="primary", use_container_width=True):
                        with st.spinner("Menyimpan data..."):
                            # Process photo
                            foto_base64 = None
                            if attendance_photo:
                                image = Image.open(attendance_photo)
                                foto_base64 = image_to_base64(image)
                            
                            # Save to database
                            success = False
                            if supabase:
                                success = save_attendance(
                                    supabase,
                                    selected_student.get('nim', ''),
                                    selected_student.get('nama', ''),
                                    selected_student.get('kelas', ''),
                                    status,
                                    foto_base64,
                                    confidence
                                )
                            else:
                                # Save locally
                                entry = {
                                    "timestamp": datetime.now().isoformat(),
                                    "nim": selected_student.get('nim', ''),
                                    "nama": selected_student.get('nama', ''),
                                    "kelas": selected_student.get('kelas', ''),
                                    "status": status,
                                    "confidence": confidence
                                }
                                st.session_state.local_attendance.append(entry)
                                success = True
                            
                            if success:
                                st.balloons()
                                st.success(f"✅ **{selected_name}** berhasil diabsen sebagai **{status}**!")
                                time.sleep(1)
                                st.rerun()
        
        with col2:
            st.subheader("Absensi Hari Ini")
            
            # Get today's attendance
            today_data = []
            if supabase:
                today_data = get_attendance_report(supabase, date.today(), date.today())
            else:
                today_str = date.today().isoformat()
                today_data = [
                    a for a in st.session_state.local_attendance
                    if a.get('timestamp', '').startswith(today_str)
                ]
            
            if today_data:
                df_today = pd.DataFrame(today_data)
                
                # Display summary
                col_a, col_b, col_c, col_d = st.columns(4)
                with col_a:
                    hadir = len(df_today[df_today['status'] == 'Hadir'])
                    st.metric("Hadir", hadir)
                with col_b:
                    izin = len(df_today[df_today['status'] == 'Izin'])
                    st.metric("Izin", izin)
                with col_c:
                    sakit = len(df_today[df_today['status'] == 'Sakit'])
                    st.metric("Sakit", sakit)
                with col_d:
                    alpha = len(df_today[df_today['status'] == 'Alpha'])
                    st.metric("Alpha", alpha)
                
                # Display table
                st.dataframe(
                    df_today[['nama', 'kelas', 'status', 'confidence']],
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.info("📝 Belum ada absensi hari ini")
    
    # ========== TAB 2: STUDENT DATA ==========
    with tab2:
        st.header("Manajemen Data Siswa")
        
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.subheader("Tambah Siswa Baru")
            
            with st.form("student_form"):
                nim = st.text_input("NIM *", max_chars=20)
                nama = st.text_input("Nama Lengkap *", max_chars=100)
                kelas = st.selectbox("Kelas *", ["XII IPA 1", "XII IPA 2", "XII IPA 3", "XII IPS 1", "XII IPS 2"])
                
                st.write("Foto Wajah (untuk verifikasi)")
                student_photo = st.file_uploader(
                    "Upload foto wajah",
                    type=['jpg', 'jpeg', 'png'],
                    key="student_photo"
                )
                
                if st.form_submit_button("📝 Daftarkan Siswa", type="primary"):
                    if nim and nama and kelas:
                        # Process photo
                        foto_base64 = None
                        if student_photo:
                            image = Image.open(student_photo)
                            foto_base64 = image_to_base64(image)
                        
                        # Save student
                        success = False
                        if supabase:
                            success = save_student(supabase, nim, nama, kelas, foto_base64)
                        else:
                            student_data = {
                                "nim": nim,
                                "nama": nama,
                                "kelas": kelas,
                                "foto_base64": foto_base64,
                                "created_at": datetime.now().isoformat()
                            }
                            st.session_state.local_students.append(student_data)
                            success = True
                        
                        if success:
                            st.success(f"✅ {nama} berhasil didaftarkan!")
                            time.sleep(1)
                            st.rerun()
                    else:
                        st.warning("⚠️ Harap isi semua field yang wajib (*)")
        
        with col2:
            st.subheader("Daftar Siswa Terdaftar")
            
            # Get students data
            students = []
            if supabase:
                students = get_all_students(supabase)
            else:
                students = st.session_state.local_students
            
            if students:
                # Convert to DataFrame
                df_students = pd.DataFrame(students)
                
                # Display without photo_base64 column (too long)
                display_cols = [col for col in df_students.columns if col != 'foto_base64']
                display_df = df_students[display_cols]
                
                st.dataframe(
                    display_df,
                    use_container_width=True,
                    hide_index=True
                )
                
                # Export button
                csv_data = display_df.to_csv(index=False)
                st.download_button(
                    "📥 Export Data Siswa",
                    data=csv_data,
                    file_name=f"data_siswa_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv"
                )
            else:
                st.info("📝 Belum ada siswa terdaftar")
    
    # ========== TAB 3: REPORTS ==========
    with tab3:
        st.header("Laporan & Analisis")
        
        # Date range filter
        col1, col2, col3 = st.columns([1, 1, 2])
        
        with col1:
            start_date = st.date_input("Dari Tanggal", value=date.today())
        with col2:
            end_date = st.date_input("Sampai Tanggal", value=date.today())
        
        # Filter button
        with col3:
            st.write("")  # Spacer
            if st.button("🔍 Filter Data", use_container_width=True):
                st.rerun()
        
        # Get filtered data
        attendance_data = []
        if supabase:
            attendance_data = get_attendance_report(supabase, start_date, end_date)
        else:
            attendance_data = [
                a for a in st.session_state.local_attendance
                if start_date.isoformat() <= a.get('timestamp', '').split('T')[0] <= end_date.isoformat()
            ]
        
        if attendance_data:
            df_report = pd.DataFrame(attendance_data)
            
            # Display stats
            st.subheader("Statistik")
            
            col_a, col_b, col_c = st.columns(3)
            with col_a:
                total = len(df_report)
                st.metric("Total Absensi", total)
            with col_b:
                unique_students = df_report['nama'].nunique()
                st.metric("Siswa Unik", unique_students)
            with col_c:
                attendance_rate = (len(df_report[df_report['status'] == 'Hadir']) / total * 100) if total > 0 else 0
                st.metric("Presentase Hadir", f"{attendance_rate:.1f}%")
            
            # Display data
            st.subheader("Data Absensi")
            display_cols = [col for col in df_report.columns if col != 'foto_base64']
            st.dataframe(
                df_report[display_cols],
                use_container_width=True,
                hide_index=True
            )
            
            # Chart
            st.subheader("Grafik Kehadiran")
            chart_data = df_report['status'].value_counts()
            st.bar_chart(chart_data)
            
            # Export options
            st.subheader("Export Data")
            col_x, col_y = st.columns(2)
            
            with col_x:
                csv_report = df_report[display_cols].to_csv(index=False)
                st.download_button(
                    "📥 Download CSV",
                    data=csv_report,
                    file_name=f"laporan_{start_date}_{end_date}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
            
            with col_y:
                # Excel export (via CSV)
                st.download_button(
                    "📊 Download Excel",
                    data=csv_report,
                    file_name=f"laporan_{start_date}_{end_date}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
        else:
            st.info(f"📝 Tidak ada data absensi dari {start_date} sampai {end_date}")
    
    # ========== TAB 4: FACE VERIFICATION ==========
    with tab4:
        st.header("Verifikasi Wajah")
        st.info("""
        **Fitur ini membandingkan foto absensi dengan foto terdaftar.**
        Untuk penggunaan produksi, gunakan library face recognition khusus.
        """)
        
        # Get students with photos
        students_with_photos = []
        if supabase:
            students = get_all_students(supabase)
            students_with_photos = [s for s in students if s.get('foto_base64')]
        else:
            students_with_photos = [s for s in st.session_state.local_students if s.get('foto_base64')]
        
        if len(students_with_photos) < 1:
            st.warning("⚠️ Belum ada siswa dengan foto terdaftar. Upload foto di tab Data Siswa.")
        else:
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("Foto Referensi (Terdaftar)")
                
                # Select student
                student_options = {s['nama']: s for s in students_with_photos}
                selected_student_name = st.selectbox(
                    "Pilih siswa referensi:",
                    list(student_options.keys())
                )
                
                if selected_student_name:
                    student = student_options[selected_student_name]
                    
                    # Display reference photo
                    if student.get('foto_base64'):
                        try:
                            img_data = base64.b64decode(student['foto_base64'])
                            image = Image.open(io.BytesIO(img_data))
                            st.image(image, caption=f"Foto {student['nama']}", width=250)
                        except:
                            st.warning("Foto referensi tidak valid")
            
            with col2:
                st.subheader("Foto untuk Verifikasi")
                
                # Upload test photo
                test_photo = st.file_uploader(
                    "Upload foto untuk verifikasi",
                    type=['jpg', 'jpeg', 'png'],
                    key="verify_photo"
                )
                
                if test_photo:
                    test_image = Image.open(test_photo)
                    st.image(test_image, caption="Foto untuk verifikasi", width=250)
                    
                    if st.button("🔍 Verifikasi Wajah", type="primary", use_container_width=True):
                        if student.get('foto_base64'):
                            # Convert test photo to base64
                            test_base64 = image_to_base64(test_image)
                            
                            # Compare faces
                            with st.spinner("Membandingkan wajah..."):
                                match, similarity = compare_faces_simple(
                                    student['foto_base64'],
                                    test_base64
                                )
                                
                                # Display result
                                if match:
                                    st.success(f"""
                                    ✅ **WAJAH COCOK!**
                                    
                                    **Detail:**
                                    - Nama: {student['nama']}
                                    - NIM: {student['nim']}
                                    - Kelas: {student['kelas']}
                                    - Similarity: {similarity:.1f}%
                                    """)
                                    st.balloons()
                                else:
                                    st.error(f"""
                                    ❌ **WAJAH TIDAK COCOK**
                                    
                                    Similarity: {similarity:.1f}%
                                    """)
    
    # ========== FOOTER ==========
    st.divider()
    
    col_left, col_center, col_right = st.columns([1, 2, 1])
    
    with col_center:
        st.caption(f"""
        **Sistem Absensi Wajah Digital v1.0**  
        Database: {'Supabase Cloud' if supabase else 'Lokal'} • 
        Total Data: {len(st.session_state.local_attendance) if not supabase else 'Cloud'} • 
        Update: {datetime.now().strftime('%H:%M:%S')}
        """)

# ========== RUN APP ==========
if __name__ == "__main__":
    main()

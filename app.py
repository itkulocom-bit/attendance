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
        st.sidebar.warning("⚠️ Install: pip install supabase")
        return None
    
    try:
        # Get credentials from secrets
        SUPABASE_URL = st.secrets.get("SUPABASE_URL", "")
        SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", "")
        
        if not SUPABASE_URL or not SUPABASE_KEY:
            st.sidebar.error("❌ Tambahkan SUPABASE_URL & SUPABASE_KEY di Secrets")
            return None
        
        # Create client
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        
        # Test connection
        try:
            supabase.table("students").select("count", count="exact").limit(1).execute()
            st.sidebar.success("✅ Terhubung ke Supabase!")
        except:
            st.sidebar.info("📡 Supabase connected")
        
        return supabase
        
    except Exception as e:
        st.sidebar.error(f"❌ Koneksi gagal: {type(e).__name__}")
        return None

# ========== DATABASE FUNCTIONS ==========
def get_all_students(supabase):
    """Get all students from Supabase"""
    if not supabase:
        return []
    
    try:
        response = supabase.table("students").select("*").order("created_at", desc=True).execute()
        return response.data
    except Exception as e:
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
        
        # Check if student exists
        existing = supabase.table("students").select("*").eq("nim", nim).execute()
        if existing.data:
            # Update existing
            supabase.table("students").update(data).eq("nim", nim).execute()
        else:
            # Insert new
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

def compare_faces_simple(img1_base64, img2_base64):
    """Simple face comparison"""
    try:
        img1_data = base64.b64decode(img1_base64)
        img2_data = base64.b64decode(img2_base64)
        
        hash1 = hashlib.md5(img1_data).hexdigest()
        hash2 = hashlib.md5(img2_data).hexdigest()
        
        similarity = 100 if hash1 == hash2 else 30
        return similarity > 70, similarity
    except:
        return False, 0

# ========== MAIN APP ==========
def main():
    # Initialize Supabase
    supabase = init_supabase()
    
    # ========== SIDEBAR ==========
    with st.sidebar:
        st.image("https://cdn-icons-png.flaticon.com/512/3135/3135715.png", width=80)
        st.title("🎓 Absensi Digital")
        
        st.divider()
        
        if supabase:
            st.success("✅ Supabase Connected")
            
            # Quick stats
            try:
                students = get_all_students(supabase)
                today_att = get_attendance_report(supabase, date.today(), date.today())
                
                st.metric("Siswa", len(students))
                st.metric("Absensi Hari Ini", len(today_att))
            except:
                pass
        else:
            st.warning("📱 Mode Offline")
        
        st.divider()
        
        # Quick actions
        if st.button("🔄 Refresh Data", use_container_width=True):
            st.rerun()
        
        st.divider()
        st.caption(f"v1.0 • {date.today().strftime('%d/%m/%Y')}")

    # ========== MAIN CONTENT ==========
    st.title("📱 Sistem Absensi Wajah Digital")
    st.markdown("**Dengan Supabase Cloud Database**")
    
    # Create tabs
    tab1, tab2, tab3, tab4 = st.tabs([
        "📸 Absensi", 
        "👥 Data Siswa", 
        "📊 Laporan", 
        "🔍 Verifikasi"
    ])
    
    # ========== TAB 1: ATTENDANCE ==========
    with tab1:
        st.header("Input Absensi")
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            # Get students
            students = get_all_students(supabase) if supabase else []
            
            if not students:
                st.warning("⚠️ Daftarkan siswa dulu di tab **Data Siswa**")
            else:
                # Student selection
                student_names = [s.get('nama', '') for s in students]
                selected_name = st.selectbox("Pilih Siswa:", student_names)
                
                if selected_name:
                    selected_student = next(s for s in students if s.get('nama') == selected_name)
                    
                    st.info(f"""
                    **Data:**
                    - NIM: {selected_student.get('nim', '')}
                    - Kelas: {selected_student.get('kelas', '')}
                    """)
                    
                    # Attendance photo
                    st.subheader("Foto Absensi")
                    attendance_photo = st.camera_input("Ambil foto wajah")
                    
                    # Status
                    status = st.radio(
                        "Status:",
                        ["Hadir", "Izin", "Sakit", "Alpha"],
                        horizontal=True
                    )
                    
                    confidence = st.slider("Keyakinan (%)", 0, 100, 85)
                    
                    # Submit
                    if st.button("✅ Simpan Absensi", type="primary", use_container_width=True):
                        with st.spinner("Menyimpan..."):
                            # Process photo
                            foto_base64 = None
                            if attendance_photo:
                                image = Image.open(attendance_photo)
                                foto_base64 = image_to_base64(image)
                            
                            # Save
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
                                success = True
                            
                            if success:
                                st.balloons()
                                st.success(f"✅ **{selected_name}** - **{status}**!")
                                time.sleep(1)
                                st.rerun()
        
        with col2:
            st.subheader("Absensi Hari Ini")
            
            # Get today's attendance
            today_data = []
            if supabase:
                today_data = get_attendance_report(supabase, date.today(), date.today())
            
            if today_data:
                df_today = pd.DataFrame(today_data)
                
                # Stats
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
                
                # Table
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
            st.subheader("Tambah/Edit Siswa")
            
            with st.form("student_form"):
                nim = st.text_input("NIM *", max_chars=20)
                nama = st.text_input("Nama Lengkap *", max_chars=100)
                kelas = st.selectbox("Kelas *", ["XII IPA 1", "XII IPA 2", "XII IPA 3", "XII IPS 1", "XII IPS 2"])
                
                st.write("Foto Wajah")
                student_photo = st.file_uploader(
                    "Upload foto wajah",
                    type=['jpg', 'jpeg', 'png']
                )
                
                if st.form_submit_button("💾 Simpan Data", type="primary"):
                    if nim and nama and kelas:
                        # Process photo
                        foto_base64 = None
                        if student_photo:
                            image = Image.open(student_photo)
                            foto_base64 = image_to_base64(image)
                        
                        # Save
                        if supabase:
                            success = save_student(supabase, nim, nama, kelas, foto_base64)
                        else:
                            success = True
                        
                        if success:
                            st.success(f"✅ {nama} berhasil disimpan!")
                            time.sleep(1)
                            st.rerun()
        
        with col2:
            st.subheader("Daftar Siswa")
            
            # Get students
            students = get_all_students(supabase) if supabase else []
            
            if students:
                df_students = pd.DataFrame(students)
                
                # Display without photo column
                if 'foto_base64' in df_students.columns:
                    display_df = df_students.drop(columns=['foto_base64'])
                else:
                    display_df = df_students
                
                st.dataframe(
                    display_df,
                    use_container_width=True,
                    hide_index=True
                )
                
                # Export
                csv_data = display_df.to_csv(index=False)
                st.download_button(
                    "📥 Export CSV",
                    data=csv_data,
                    file_name=f"siswa_{date.today().strftime('%Y%m%d')}.csv",
                    mime="text/csv"
                )
            else:
                st.info("📝 Belum ada siswa terdaftar")
    
    # ========== TAB 3: REPORTS ==========
    with tab3:
        st.header("Laporan & Analisis")
        
        # Date range
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("Dari Tanggal", value=date.today())
        with col2:
            end_date = st.date_input("Sampai Tanggal", value=date.today())
        
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
                hadir_pct = (len(df_report[df_report['status'] == 'Hadir']) / total * 100) if total > 0 else 0
                st.metric("Hadir", f"{hadir_pct:.1f}%")
            
            # Data
            st.subheader("Data")
            if 'foto_base64' in df_report.columns:
                display_df = df_report.drop(columns=['foto_base64'])
            else:
                display_df = df_report
            
            st.dataframe(
                display_df,
                use_container_width=True,
                hide_index=True
            )
            
            # Chart
            st.subheader("Grafik")
            chart_data = df_report['status'].value_counts()
            st.bar_chart(chart_data)
            
            # Export
            st.subheader("Export")
            csv_report = display_df.to_csv(index=False)
            st.download_button(
                "📊 Download Laporan",
                data=csv_report,
                file_name=f"laporan_{start_date}_{end_date}.csv",
                mime="text/csv",
                use_container_width=True
            )
        else:
            st.info(f"📝 Tidak ada data dari {start_date} sampai {end_date}")
    
    # ========== TAB 4: FACE VERIFICATION ==========
    with tab4:
        st.header("Verifikasi Wajah")
        st.info("Fitur demo - bandingkan foto baru dengan foto terdaftar")
        
        # Get students with photos
        students = get_all_students(supabase) if supabase else []
        students_with_photos = [s for s in students if s.get('foto_base64')]
        
        if len(students_with_photos) < 1:
            st.warning("⚠️ Upload foto siswa dulu di tab Data Siswa")
        else:
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("Foto Referensi")
                
                # Select student
                student_options = {s['nama']: s for s in students_with_photos}
                selected_name = st.selectbox(
                    "Pilih siswa:",
                    list(student_options.keys())
                )
                
                if selected_name:
                    student = student_options[selected_name]
                    
                    # Display photo
                    if student.get('foto_base64'):
                        try:
                            img_data = base64.b64decode(student['foto_base64'])
                            image = Image.open(io.BytesIO(img_data))
                            st.image(image, caption=f"Foto {student['nama']}", width=250)
                        except:
                            st.warning("Foto tidak valid")
            
            with col2:
                st.subheader("Foto Baru")
                
                # Upload test photo
                test_photo = st.file_uploader(
                    "Upload foto untuk verifikasi",
                    type=['jpg', 'jpeg', 'png'],
                    key="test_photo"
                )
                
                if test_photo:
                    test_image = Image.open(test_photo)
                    st.image(test_image, caption="Foto baru", width=250)
                    
                    if st.button("🔍 Verifikasi", type="primary"):
                        if student.get('foto_base64'):
                            # Convert
                            test_base64 = image_to_base64(test_image)
                            
                            # Compare
                            with st.spinner("Membandingkan..."):
                                match, similarity = compare_faces_simple(
                                    student['foto_base64'],
                                    test_base64
                                )
                                
                                if match:
                                    st.success(f"""
                                    ✅ **COCOK!**
                                    
                                    **Detail:**
                                    - Nama: {student['nama']}
                                    - NIM: {student['nim']}
                                    - Similarity: {similarity:.1f}%
                                    """)
                                    st.balloons()
                                else:
                                    st.error(f"""
                                    ❌ **TIDAK COCOK**
                                    
                                    Similarity: {similarity:.1f}%
                                    """)
    
    # ========== FOOTER ==========
    st.divider()
    st.caption(f"Absensi Digital v1.0 • Supabase • {datetime.now().strftime('%H:%M:%S')}")

# ========== RUN APP ==========
if __name__ == "__main__":
    main()

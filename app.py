import streamlit as st
import cv2
import numpy as np
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
from PIL import Image
import face_recognition
import tempfile
import os

# ========== CONFIGURATION ==========
st.set_page_config(
    page_title="Pintu Ujian - Face Verification",
    page_icon="🎓",
    layout="centered"
)

# ========== TITLE ==========
st.title("🎓 PINTU MASUK UJIAN")
st.markdown("**Hanya peserta terdaftar yang bisa masuk**")

# ========== INITIALIZE SESSION STATE ==========
if 'verified' not in st.session_state:
    st.session_state.verified = False
if 'verified_name' not in st.session_state:
    st.session_state.verified_name = ""
if 'attempts' not in st.session_state:
    st.session_state.attempts = []

# ========== GOOGLE SHEETS CONNECTION ==========
@st.cache_resource
def connect_to_sheets():
    # Download credentials from Streamlit secrets or local file
    try:
        # For Streamlit Cloud (using secrets)
        creds_dict = st.secrets["google_credentials"]
        creds = Credentials.from_service_account_info(creds_dict)
    except:
        # For local development
        import json
        with open('credentials.json') as f:
            creds_dict = json.load(f)
        creds = Credentials.from_service_account_info(creds_dict)
    
    client = gspread.authorize(creds)
    return client

# ========== LOAD REGISTERED STUDENTS ==========
def load_registered_students():
    try:
        client = connect_to_sheets()
        sheet = client.open("ExamAttendanceDB").worksheet("registered_students")
        records = sheet.get_all_records()
        
        # Convert to face encodings
        students = []
        for record in records:
            if record['Status'] == 'Active':
                # Download and encode face
                img_path = download_image(record['Foto_URL'])
                if img_path:
                    encoding = get_face_encoding(img_path)
                    if encoding is not None:
                        students.append({
                            'nim': record['NIM'],
                            'nama': record['Nama'],
                            'encoding': encoding,
                            'foto_url': record['Foto_URL']
                        })
        return students
    except Exception as e:
        st.error(f"Error loading students: {str(e)}")
        return []

# ========== FACE PROCESSING FUNCTIONS ==========
def download_image(url):
    """Download image from URL to temp file"""
    import requests
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            # Create temp file
            with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as f:
                f.write(response.content)
                return f.name
    except:
        pass
    return None

def get_face_encoding(image_path):
    """Extract face encoding from image"""
    try:
        image = face_recognition.load_image_file(image_path)
        encodings = face_recognition.face_encodings(image)
        if len(encodings) > 0:
            return encodings[0]
    except:
        pass
    return None

def compare_faces(known_encoding, test_encoding, threshold=0.6):
    """Compare two face encodings"""
    if known_encoding is None or test_encoding is None:
        return False, 0
    
    distance = face_recognition.face_distance([known_encoding], test_encoding)[0]
    similarity = (1 - distance) * 100
    return distance < threshold, similarity

# ========== VERIFICATION FUNCTION ==========
def verify_face(captured_image):
    """Compare captured face with registered students"""
    students = load_registered_students()
    if not students:
        st.error("Database siswa kosong atau error")
        return None, 0
    
    # Encode captured face
    test_encoding = get_face_encoding(captured_image)
    if test_encoding is None:
        st.error("Wajah tidak terdeteksi di foto")
        return None, 0
    
    # Compare with all registered students
    best_match = None
    best_similarity = 0
    
    for student in students:
        match, similarity = compare_faces(student['encoding'], test_encoding)
        if match and similarity > best_similarity:
            best_match = student
            best_similarity = similarity
    
    if best_match and best_similarity > 70:  # Threshold 70%
        return best_match, best_similarity
    else:
        return None, best_similarity

# ========== LOG ATTEMPT ==========
def log_attempt(nim, nama, status, confidence):
    """Log verification attempt to Google Sheets"""
    try:
        client = connect_to_sheets()
        sheet = client.open("ExamAttendanceDB").worksheet("attendance_log")
        
        sheet.append_row([
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            nim if nim else "-",
            nama if nama else "Unknown",
            status,
            f"{confidence:.1f}%"
        ])
    except Exception as e:
        st.error(f"Gagal menyimpan log: {str(e)}")

# ========== MAIN APP ==========
def main():
    # Sidebar for registered students
    with st.sidebar:
        st.header("📋 Peserta Terdaftar")
        students = load_registered_students()
        for student in students:
            st.write(f"**{student['nama']}** - {student['nim']}")
        
        st.divider()
        st.header("📊 Log Attempt")
        if st.session_state.attempts:
            for attempt in st.session_state.attempts[-5:]:  # Show last 5
                st.text(f"{attempt['time']}: {attempt['name']} - {attempt['status']}")
    
    # Main verification area
    if not st.session_state.verified:
        st.subheader("🔍 Verifikasi Wajah untuk Masuk")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # Camera input
            picture = st.camera_input(
                "Hadapkan wajah ke kamera",
                help="Pastikan cahaya cukup dan wajah terlihat jelas"
            )
            
            if picture:
                # Save captured image to temp file
                with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as f:
                    f.write(picture.getvalue())
                    temp_path = f.name
                
                # Verify face
                with st.spinner("Memverifikasi wajah..."):
                    result, confidence = verify_face(temp_path)
                    
                    # Clean up temp file
                    os.unlink(temp_path)
                    
                    if result:
                        # SUCCESS - Verified
                        st.session_state.verified = True
                        st.session_state.verified_name = result['nama']
                        
                        # Log successful attempt
                        log_attempt(result['nim'], result['nama'], "Verified", confidence)
                        st.session_state.attempts.append({
                            'time': datetime.now().strftime("%H:%M:%S"),
                            'name': result['nama'],
                            'status': '✅ Verified'
                        })
                        
                        st.rerun()
                    else:
                        # FAILED - Not recognized
                        st.error(f"⚠️ Wajah tidak dikenali (Kecocokan: {confidence:.1f}%)")
                        
                        # Log failed attempt
                        log_attempt(None, "Unknown", "Rejected", confidence)
                        st.session_state.attempts.append({
                            'time': datetime.now().strftime("%H:%M:%S"),
                            'name': "Unknown",
                            'status': '❌ Rejected'
                        })
        
        with col2:
            st.info("**Peserta yang bisa masuk:**")
            st.success("✅ Sastro")
            st.success("✅ Muda")
            st.success("✅ Jabal")
            st.error("❌ Orang lain")
            
            st.divider()
            st.caption("""
            **Instruksi:**
            1. Hadap kamera
            2. Tunggu verifikasi
            3. Jika berhasil, bisa masuk
            """)
    
    else:
        # SUCCESS SCREEN
        st.balloons()
        st.success(f"## ✅ SELAMAT DATANG, {st.session_state.verified_name}!")
        st.markdown("### Anda telah terverifikasi dan **BOLEH MASUK** ujian.")
        
        # Exam information
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Status", "TERVERIFIKASI")
        with col2:
            st.metric("Waktu Masuk", datetime.now().strftime("%H:%M"))
        with col3:
            st.metric("Kursi", "A-12")  # Could be from database
        
        st.divider()
        
        # Rules and instructions
        st.markdown("**Peraturan Ujian:**")
        st.markdown("""
        1. Tunjukkan ini kepada pengawas
        2. Duduk di kursi yang ditentukan
        3. Simpan HP di tas
        4. Waktu ujian: 120 menit
        """)
        
        # Reset button for next person
        if st.button("🔁 Verifikasi Peserta Berikutnya"):
            st.session_state.verified = False
            st.session_state.verified_name = ""
            st.rerun()

# ========== RUN APP ==========
if __name__ == "__main__":
    main()

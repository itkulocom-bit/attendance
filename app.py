import streamlit as st
import pandas as pd
from datetime import datetime, date
import time
from PIL import Image
import io
import base64
import os
import tempfile

# Supabase imports
try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False

# DeepFace for real face recognition
try:
    from deepface import DeepFace
    DEEPFACE_AVAILABLE = True
except ImportError:
    DEEPFACE_AVAILABLE = False

# ========== REAL FACE RECOGNITION ==========
def compare_faces_real(img1_base64, img2_base64, threshold=0.6):
    """
    Real face recognition using DeepFace
    Returns: (match: bool, similarity: float, distance: float)
    """
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
            # Use DeepFace to compare faces
            result = DeepFace.verify(
                img1_path=img1_path,
                img2_path=img2_path,
                model_name="Facenet",  # or "VGG-Face", "OpenFace"
                detector_backend="opencv",
                distance_metric="cosine",
                enforce_detection=False  # Continue even if no face detected
            )
            
            # Clean up temp files
            os.unlink(img1_path)
            os.unlink(img2_path)
            
            # Extract results
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
            
            st.error(f"DeepFace error: {str(e)[:100]}")
            return False, 0, 0
            
    except Exception as e:
        return False, 0, 0

def compare_faces_fast(img1_base64, img2_base64):
    """
    Faster alternative: Feature-based comparison
    """
    try:
        # Simple comparison using image features
        from PIL import Image
        import numpy as np
        
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
        
        # Calculate similarity (cosine similarity)
        dot_product = np.dot(arr1, arr2)
        norm1 = np.linalg.norm(arr1)
        norm2 = np.linalg.norm(arr2)
        
        if norm1 == 0 or norm2 == 0:
            return False, 0
        
        similarity = dot_product / (norm1 * norm2)
        similarity_percent = similarity * 100
        
        # Threshold for match (adjust based on testing)
        match = similarity_percent > 70
        
        return match, similarity_percent
        
    except:
        return False, 0

# ========== UPDATE ATTENDANCE FUNCTION ==========
def save_attendance_with_verification(supabase, student, attendance_photo, status):
    """
    Save attendance with face verification
    """
    if not student or not attendance_photo:
        return False, "Data tidak lengkap"
    
    try:
        # Get student's reference photo
        reference_photo = student.get('foto_base64')
        if not reference_photo:
            return False, "Siswa belum punya foto referensi"
        
        # Process attendance photo
        image = Image.open(attendance_photo)
        attendance_base64 = image_to_base64(image)
        
        # Perform face verification
        verification_result = False
        confidence = 0
        
        if DEEPFACE_AVAILABLE:
            # Use DeepFace for accurate verification
            match, confidence, distance = compare_faces_real(reference_photo, attendance_base64)
            verification_result = match
            method = "DeepFace"
        else:
            # Use fast method as fallback
            match, confidence = compare_faces_fast(reference_photo, attendance_base64)
            verification_result = match
            method = "FastMatch"
        
        # Log verification result
        st.info(f"""
        **Verifikasi Wajah ({method}):**
        - Status: {'✅ COCOK' if verification_result else '❌ TIDAK COCOK'}
        - Confidence: {confidence:.1f}%
        - Wajah: {student['nama']}
        """)
        
        # If face doesn't match, require confirmation
        if not verification_result:
            st.warning("⚠️ **PERINGATAN: Wajah tidak cocok dengan foto referensi!**")
            
            # Ask for confirmation
            col1, col2 = st.columns(2)
            with col1:
                force_save = st.checkbox("Tetap simpan (override verification)")
            with col2:
                if st.button("❌ Batalkan Absensi", type="secondary"):
                    return False, "Absensi dibatalkan"
            
            if not force_save:
                return False, "Verifikasi wajah gagal"
        
        # Save to database
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

# ========== UPDATE THE ATTENDANCE TAB ==========
# Dalam tab attendance, ganti bagian submit button:

"""
# GANTI bagian ini di dalam tab attendance:

if st.button("✅ Simpan Absensi", type="primary", use_container_width=True):
    with st.spinner("Memverifikasi wajah..."):
        # Panggil fungsi verifikasi
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
"""

# ========== ADD FACE ENROLLMENT VERIFICATION ==========
def verify_face_enrollment(image_base64):
    """
    Verify that uploaded face is valid (has clear face)
    """
    if not DEEPFACE_AVAILABLE:
        return True, "DeepFace tidak tersedia, skip verification"
    
    try:
        # Save to temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as f:
            img_data = base64.b64decode(image_base64)
            f.write(img_data)
            img_path = f.name
        
        # Analyze face
        try:
            # Detect face
            analysis = DeepFace.analyze(
                img_path=img_path,
                actions=['age', 'gender', 'emotion', 'race'],
                enforce_detection=True,
                detector_backend="opencv"
            )
            
            os.unlink(img_path)
            
            if isinstance(analysis, list) and len(analysis) > 0:
                # Face detected
                face_data = analysis[0]
                
                # Check face size and quality
                region = face_data.get('region', {})
                face_area = region.get('w', 0) * region.get('h', 0) if region else 0
                
                if face_area < 10000:  # Face too small
                    return False, "Wajah terlalu kecil, dekatkan ke kamera"
                
                # Check if looking straight
                emotion = face_data.get('dominant_emotion', 'neutral')
                if emotion in ['angry', 'disgust', 'fear']:
                    return False, "Ekspresi wajah tidak netral"
                
                return True, f"✅ Wajah terdeteksi ({emotion})"
            else:
                return False, "Wajah tidak terdeteksi"
                
        except Exception as e:
            if os.path.exists(img_path):
                os.unlink(img_path)
            
            if "Face could not be detected" in str(e):
                return False, "❌ Wajah tidak terdeteksi. Pastikan wajah jelas dan menghadap kamera"
            return False, f"Error: {str(e)[:100]}"
            
    except Exception as e:
        return False, f"Error: {str(e)[:100]}"

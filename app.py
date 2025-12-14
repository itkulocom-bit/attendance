# app.py - Versi tanpa face-recognition untuk deploy cepat
import streamlit as st
from supabase import create_client
import pandas as pd
from datetime import datetime
import base64

# Di app.py, tambahkan:
import sys
st.write(f"Python version: {sys.version}")

# ========== SIMPLE FACE COMPARE ==========
def simple_image_compare(img1_bytes, img2_bytes):
    """Simple comparison for MVP"""
    from PIL import Image
    import numpy as np
    
    try:
        # Open images
        img1 = Image.open(img1_bytes).convert('L').resize((50, 50))
        img2 = Image.open(img2_bytes).convert('L').resize((50, 50))
        
        # Convert to arrays
        arr1 = np.array(img1)
        arr2 = np.array(img2)
        
        # Calculate difference
        diff = np.abs(arr1 - arr2).mean()
        
        # Similarity (0-100)
        similarity = max(0, 100 - diff * 0.5)
        
        return similarity > 70, similarity
    except:
        return False, 0

# ========== MAIN APP ==========
def main():
    st.title("🎓 Absensi Sederhana (MVP)")
    
    # Database simulation (pakai Supabase atau CSV)
    use_supabase = st.sidebar.checkbox("Gunakan Supabase", value=False)
    
    if use_supabase:
        # Supabase setup
        url = st.secrets.get("SUPABASE_URL", "")
        key = st.secrets.get("SUPABASE_KEY", "")
        
        if url and key:
            supabase = create_client(url, key)
            st.success("✅ Terhubung ke Supabase")
        else:
            st.warning("⚠️ Supabase credentials belum diatur")
            use_supabase = False
    
    # Absensi manual dulu
    st.header("Absensi Manual")
    
    col1, col2 = st.columns(2)
    
    with col1:
        nama = st.text_input("Nama Siswa")
        nim = st.text_input("NIM")
        status = st.selectbox("Status", ["Hadir", "Izin", "Sakit", "Alpha"])
        
        if st.button("Simpan Absensi"):
            # Simpan ke CSV atau Supabase
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            if use_supabase:
                try:
                    data = {
                        "nama": nama,
                        "nim": nim,
                        "status": status,
                        "created_at": timestamp
                    }
                    supabase.table("attendance").insert(data).execute()
                    st.success("✅ Tersimpan di Supabase!")
                except Exception as e:
                    st.error(f"Error: {str(e)}")
            else:
                # Simpan ke CSV lokal
                import csv
                with open("attendance.csv", "a", newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow([timestamp, nim, nama, status])
                st.success("✅ Tersimpan di CSV lokal")
    
    with col2:
        st.header("Data Absensi")
        
        if use_supabase:
            try:
                data = supabase.table("attendance").select("*").execute()
                df = pd.DataFrame(data.data)
                st.dataframe(df)
            except:
                st.info("Belum ada data")
        else:
            # Baca dari CSV
            try:
                df = pd.read_csv("attendance.csv", 
                               names=['timestamp', 'nim', 'nama', 'status'])
                st.dataframe(df)
                
                # Download button
                csv = df.to_csv(index=False)
                st.download_button("📥 Download CSV", csv, "attendance.csv")
            except:
                st.info("Belum ada data absensi")

if __name__ == "__main__":
    main()

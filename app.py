import streamlit as st
import pandas as pd

st.set_page_config(page_title="Test Supabase", layout="centered")
st.title("🔗 Test Koneksi Supabase")

# ========== TEST CONNECTION ==========
st.header("1. Test Koneksi Supabase")

try:
    from supabase import create_client
    
    # Ambil credentials
    url = st.text_input("Supabase URL", placeholder="https://xxxxx.supabase.co")
    key = st.text_input("Supabase Key", type="password")
    
    if st.button("Test Koneksi") and url and key:
        with st.spinner("Menghubungkan..."):
            try:
                # Buat client
                supabase = create_client(url, key)
                
                # Test dengan query sederhana
                st.info("🧪 Testing connection...")
                
                # Coba akses students table
                try:
                    result = supabase.table("students").select("*").limit(1).execute()
                    st.success(f"✅ BERHASIL! Tabel 'students' ada dengan {len(result.data)} data")
                except Exception as table_error:
                    if "Could not find the table" in str(table_error):
                        st.warning("⚠️ Tabel 'students' belum ada. Buat dulu di SQL Editor.")
                    else:
                        st.error(f"❌ Error: {str(table_error)}")
                
                # Coba akses attendance table
                try:
                    result = supabase.table("attendance").select("*").limit(1).execute()
                    st.success(f"✅ Tabel 'attendance' ada dengan {len(result.data)} data")
                except:
                    st.warning("⚠️ Tabel 'attendance' belum ada")
                
                # Simpan ke secrets jika berhasil
                st.success("🎉 Koneksi Supabase BERHASIL!")
                st.code(f"""
                # Streamlit Secrets format:
                SUPABASE_URL = "{url}"
                SUPABASE_KEY = "{key}"
                """)
                
            except Exception as e:
                st.error(f"❌ Gagal koneksi: {str(e)}")
    
except ImportError:
    st.error("""
    ❌ Library supabase belum diinstall!
    
    Tambahkan di requirements.txt:
    supabase>=2.3.0
    
    Atau install manual:
    pip install supabase
    """)

# ========== SQL UNTUK BUAT TABEL ==========
st.header("2. SQL untuk Buat Tabel")

st.code("""
-- Table 1: students
CREATE TABLE IF NOT EXISTS students (
  id BIGSERIAL PRIMARY KEY,
  nim TEXT UNIQUE NOT NULL,
  nama TEXT NOT NULL,
  kelas TEXT NOT NULL,
  foto_base64 TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Table 2: attendance  
CREATE TABLE IF NOT EXISTS attendance (
  id BIGSERIAL PRIMARY KEY,
  nim TEXT NOT NULL,
  nama TEXT NOT NULL,
  kelas TEXT NOT NULL,
  status TEXT NOT NULL,
  foto_base64 TEXT,
  confidence FLOAT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Enable public access (untuk demo)
ALTER TABLE students ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow all" ON students FOR ALL USING (true);

ALTER TABLE attendance ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow all" ON attendance FOR ALL USING (true);
""")

st.info("""
**Cara buat tabel:**
1. Buka Supabase Dashboard
2. Klik "SQL Editor" di sidebar
3. Paste SQL di atas
4. Klik "Run"
""")

# ========== CEK SECRETS ==========
st.header("3. Cek Current Secrets")

try:
    secrets = st.secrets
    if hasattr(secrets, "SUPABASE_URL"):
        display_url = str(secrets.SUPABASE_URL).replace("https://", "").replace(".supabase.co", "[...]")
        st.success(f"✅ SUPABASE_URL: {display_url}")
    else:
        st.warning("⚠️ SUPABASE_URL tidak ada di secrets")
        
    if hasattr(secrets, "SUPABASE_KEY"):
        key_preview = str(secrets.SUPABASE_KEY)[:10] + "..." if len(str(secrets.SUPABASE_KEY)) > 10 else "***"
        st.success(f"✅ SUPABASE_KEY: {key_preview}")
    else:
        st.warning("⚠️ SUPABASE_KEY tidak ada di secrets")
        
except:
    st.info("ℹ️ Tidak ada secrets terdeteksi")

st.divider()
st.caption("Test Supabase Connection • Streamlit Cloud")

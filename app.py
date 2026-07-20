import streamlit as st
import geopandas as gpd
import folium
from streamlit_folium import folium_static
import pandas as pd

# Set Page Config for a premium look
st.set_page_config(
    page_title="WebGIS Monitoring TMU & RPTRA DKI Jakarta",
    page_icon="🗺️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling (CSS)
st.markdown("""
    <style>
    .main-title {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1E3A8A;
        margin-bottom: 0.5rem;
    }
    .sub-title {
        font-size: 1.1rem;
        color: #4B5563;
        margin-bottom: 2rem;
    }
    .card {
        background-color: #F3F4F6;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
        margin-bottom: 1.5rem;
    }
    .metric-title {
        font-size: 0.9rem;
        color: #6B7280;
        text-transform: uppercase;
        font-weight: bold;
    }
    .metric-value {
        font-size: 1.8rem;
        font-weight: bold;
        color: #1F2937;
    }
    </style>
""", unsafe_allow_html=True)

# App Title & Header
st.markdown('<div class="main-title">Peta Interaktif Monitoring Kapasitas Taman Makam Umum (TMU) dan Aksesibilitas RPTRA di DKI Jakarta</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">UAS Sistem Informasi Geografis (SIG) - Program Studi Sistem Informasi</div>', unsafe_allow_html=True)

# ----------------- DATA LOADING -----------------
@st.cache_data
def load_spatial_data():
    # Load raw GeoJSON layers
    gdf_rw = gpd.read_file("Batas_RW_Predictions.geojson")
    gdf_tmu = gpd.read_file("Lokasi_TMU.geojson")
    gdf_rptra = gpd.read_file("Lokasi_RPTRA.geojson")
    gdf_lahan = gpd.read_file("Lahan_Kosong_Pemkot.geojson")
    gdf_jalan = gpd.read_file("Jaringan_Jalan.geojson")
    
    # CALCULATE BUFFER EXCLUSION FOR TMU (500 Meters)
    # Project to UTM 48S (EPSG:32748) for accurate distance measurements in meters
    gdf_tmu_utm = gdf_tmu.to_crs(epsg=32748)
    gdf_tmu_buffer_utm = gdf_tmu_utm.copy()
    gdf_tmu_buffer_utm['geometry'] = gdf_tmu_utm.buffer(500)
    
    # Project back to WGS 84 (EPSG:4326) for mapping in Folium
    gdf_tmu_buffer = gdf_tmu_buffer_utm.to_crs(epsg=4326)
    
    return gdf_rw, gdf_tmu, gdf_rptra, gdf_lahan, gdf_jalan, gdf_tmu_buffer

try:
    gdf_rw, gdf_tmu, gdf_rptra, gdf_lahan, gdf_jalan, gdf_tmu_buffer = load_spatial_data()
except Exception as e:
    st.error(f"Error loading spatial data: {str(e)}. Please run generate_mock_data.py first.")
    st.stop()

# ----------------- SIDEBAR CONTROLS & FILTERS -----------------
st.sidebar.header("🛠️ Kontrol & Filter Peta")

# 1. Filter Wilayah Administrasi (based on RW Kecamatan mapping)
all_kecamatans = ["Semua"] + sorted(list(gdf_rw["Kecamatan"].dropna().unique()))
selected_kec = st.sidebar.selectbox("Filter Wilayah Kecamatan:", all_kecamatans)

# 2. Filter Status Kapasitas TMU
tmu_status_opts = ["Semua", "Tersedia (>30%)", "Sedang (10-30%)", "Kritis (<10%)"]
selected_tmu_status = st.sidebar.selectbox("Filter Status Kapasitas TMU:", tmu_status_opts)

# Apply filters to GeoDataFrames
filtered_tmu = gdf_tmu.copy()
filtered_rptra = gdf_rptra.copy()

# Simple spatial filtering mock logic based on coordinates for demonstration:
# In a real app we would check intersection with selected Kecamatan, 
# for simplicity we filter TMU and RPTRA inside selected Kecamatan's approximate boundary box
if selected_kec != "Semua":
    rw_in_kec = gdf_rw[gdf_rw["Kecamatan"] == selected_kec]
    minx, miny, maxx, maxy = rw_in_kec.total_bounds
    
    # Filter points within bounds
    filtered_tmu = gdf_tmu.cx[minx:maxx, miny:maxy]
    filtered_rptra = gdf_rptra.cx[minx:maxx, miny:maxy]
    filtered_tmu_buffer = gdf_tmu_buffer.cx[minx:maxx, miny:maxy]
    filtered_rw = rw_in_kec
else:
    filtered_rw = gdf_rw
    filtered_tmu_buffer = gdf_tmu_buffer

# Filter by TMU Capacity
if selected_tmu_status == "Tersedia (>30%)":
    filtered_tmu = filtered_tmu[filtered_tmu["Kapasitas"] > 30]
elif selected_tmu_status == "Sedang (10-30%)":
    filtered_tmu = filtered_tmu[(filtered_tmu["Kapasitas"] >= 10) & (filtered_tmu["Kapasitas"] <= 30)]
elif selected_tmu_status == "Kritis (<10%)":
    filtered_tmu = filtered_tmu[filtered_tmu["Kapasitas"] < 10]

# Sidebar Legend Info
st.sidebar.markdown("---")
st.sidebar.subheader("🎨 Legenda Kartografi")
st.sidebar.markdown("""
**Prioritas RPTRA Baru (Poligon RW):**
*   🟢 **Sangat Prioritas** (Ada Lahan, Kepadatan Anak Tinggi, Aman)
*   🟡 **Cukup Prioritas** (Ada Lahan, Kepadatan Anak Sedang, Aman)
*   🔴 **Tidak Prioritas** (Tidak ada Lahan, atau dekat Makam <500m)

**Kapasitas TMU (Poligon/Titik):**
*   🟢 **Tersedia** (> 30% kapasitas tersisa)
*   🟡 **Sedang** (10-30% kapasitas tersisa)
*   🔴 **Kritis** (< 10% kapasitas tersisa - penuh)

**Kondisi RPTRA (Titik):**
*   🔵 **Fasilitas Lengkap** (Kondisi Baik)
*   🟣 **Fasilitas Terbatas** (Kondisi Terbatas)

**Zona Eksklusi TMU:**
*   ⚠️ **Buffer Transparan 500m** (Zona Penyangga RPTRA)
""")

# ----------------- MAIN LAYOUT: MAP & STATS -----------------
# Metrics row
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.markdown(f"""
    <div class="card">
        <div class="metric-title">Total TMU Terpantau</div>
        <div class="metric-value">{len(filtered_tmu)}</div>
    </div>
    """, unsafe_allow_html=True)
with col2:
    critical_tmu = len(filtered_tmu[filtered_tmu["Kapasitas"] < 10])
    st.markdown(f"""
    <div class="card">
        <div class="metric-title">TMU Berstatus Kritis</div>
        <div class="metric-value" style="color: #DC2626;">{critical_tmu}</div>
    </div>
    """, unsafe_allow_html=True)
with col3:
    st.markdown(f"""
    <div class="card">
        <div class="metric-title">Total RPTRA</div>
        <div class="metric-value">{len(filtered_rptra)}</div>
    </div>
    """, unsafe_allow_html=True)
with col4:
    limited_rptra = len(filtered_rptra[filtered_rptra["Tipe_Fas"] == "Fasilitas Terbatas"])
    st.markdown(f"""
    <div class="card">
        <div class="metric-title">RPTRA Fasilitas Terbatas</div>
        <div class="metric-value" style="color: #7C3AED;">{limited_rptra}</div>
    </div>
    """, unsafe_allow_html=True)

# ----------------- FOLIUM MAP GENERATION -----------------
# Centering map on the centroid of the RW layer
map_center = [-6.235, 106.83]
m = folium.Map(location=map_center, zoom_start=13, tiles="CartoDB positron", control_scale=True)

# 1. Base Layer: Batas RW / Kelurahan (as Checkbox / Layer control)
fg_rw = folium.FeatureGroup(name="Prioritas Pembangunan RPTRA (Batas RW)", show=True)
for _, row in filtered_rw.iterrows():
    # Simple polygon drawing
    sim_geo = gpd.GeoSeries(row['geometry']).simplify(tolerance=0.0001)
    geo_j = sim_geo.to_json()
    
    # Ambil Prediksi_Prioritas dari row hasil Machine Learning
    prio = row.get('Prediksi_Prioritas', 0)
    if prio == 2:
        fill_color = '#10B981'  # Green (Sangat Prioritas)
        fill_opacity = 0.4
        label_prio = "Sangat Prioritas"
    elif prio == 1:
        fill_color = '#F59E0B'  # Yellow (Cukup Prioritas)
        fill_opacity = 0.3
        label_prio = "Cukup Prioritas"
    else:
        fill_color = '#EF4444'  # Red (Tidak Prioritas)
        fill_opacity = 0.1
        label_prio = "Tidak Prioritas"
        
    geo_j = folium.GeoJson(
        geo_j,
        style_function=lambda x, fc=fill_color, fo=fill_opacity: {
            'fillColor': fc,
            'color': '#9CA3AF',
            'weight': 1,
            'fillOpacity': fo
        }
    )
    folium.Popup(f"<b>Kecamatan:</b> {row['Kecamatan']}<br><b>RW:</b> {row['Nama_RW']}<br><b>Kepadatan Anak:</b> {row['Kpdn_Anak']} anak/km²<br><b>Prediksi Prioritas:</b> <b style='color:{fill_color};'>{label_prio}</b>").add_to(geo_j)
    geo_j.add_to(fg_rw)
fg_rw.add_to(m)

# 2. TMU Buffer Zone (500 meters)
fg_buffer = folium.FeatureGroup(name="Zona Penyangga TMU (500m)", show=True)
for _, row in filtered_tmu_buffer.iterrows():
    sim_geo = gpd.GeoSeries(row['geometry']).simplify(tolerance=0.0001)
    geo_j = sim_geo.to_json()
    geo_j = folium.GeoJson(
        geo_j,
        style_function=lambda x: {
            'fillColor': '#EF4444',
            'color': '#EF4444',
            'weight': 1,
            'fillOpacity': 0.15,
            'dashArray': '5, 5'
        }
    )
    folium.Popup(f"<b>Zona Eksklusi:</b> Penyangga 500m dari TMU").add_to(geo_j)
    geo_j.add_to(fg_buffer)
fg_buffer.add_to(m)

# 3. TMU Layer (Polygons/Marker)
fg_tmu = folium.FeatureGroup(name="Taman Makam Umum (TMU)", show=True)
for _, row in filtered_tmu.iterrows():
    # Determine color by capacity
    cap = row['Kapasitas']
    if cap > 30:
        color = '#10B981' # Green
        status_text = "Tersedia"
    elif cap >= 10:
        color = '#F59E0B' # Yellow / Orange
        status_text = "Sedang"
    else:
        color = '#EF4444' # Red
        status_text = "Kritis"
        
    sim_geo = gpd.GeoSeries(row['geometry']).simplify(tolerance=0.0001)
    geo_j = sim_geo.to_json()
    geo_j = folium.GeoJson(
        geo_j,
        style_function=lambda x, color=color: {
            'fillColor': color,
            'color': '#1E293B',
            'weight': 2,
            'fillOpacity': 0.7
        }
    )
    popup_content = f"""
    <div style="font-family: Arial, sans-serif; font-size: 12px; width: 200px;">
        <h4 style="margin: 0 0 5px 0; color: #1E3A8A;">{row['Nama_TMU']}</h4>
        <hr style="margin: 5px 0;">
        <b>Luas Area:</b> {row['Luas_Ha']} Ha<br>
        <b>Kapasitas Tersisa:</b> {row['Kapasitas']}% ({status_text})<br>
        <b>Tahun Berdiri:</b> {row['Thn_Berdir']}
    </div>
    """
    folium.Popup(popup_content, max_width=250).add_to(geo_j)
    geo_j.add_to(fg_tmu)
fg_tmu.add_to(m)

# 4. RPTRA Layer (Points)
fg_rptra = folium.FeatureGroup(name="Sebaran RPTRA", show=True)
for _, row in filtered_rptra.iterrows():
    # Determine color by facilities
    tipe = row['Tipe_Fas']
    color = '#2563EB' if tipe == "Fasilitas Lengkap" else '#8B5CF6' # Blue vs Purple
    
    # Get coordinates of Point
    coords = row['geometry'].coords[0] # [lon, lat]
    
    popup_content = f"""
    <div style="font-family: Arial, sans-serif; font-size: 12px; width: 220px;">
        <h4 style="margin: 0 0 5px 0; color: #1E3A8A;">{row['Nama_RPTRA']}</h4>
        <hr style="margin: 5px 0;">
        <b>Tipe Fasilitas:</b> {row['Tipe_Fas']}<br>
        <b>Fasilitas Utama:</b> {row['Fasilitas']}<br>
        <b>Kondisi:</b> {row['Kondisi']}
    </div>
    """
    
    folium.CircleMarker(
        location=[coords[1], coords[0]],
        radius=8,
        color='#1F2937',
        weight=1,
        fill=True,
        fill_color=color,
        fill_opacity=0.9,
        popup=folium.Popup(popup_content, max_width=250)
    ).add_to(fg_rptra)
fg_rptra.add_to(m)

# Add Layer Control to Toggle Layers
folium.LayerControl().add_to(m)

# Display Map in Streamlit
st.subheader("🗺️ Peta WebGIS Interaktif")
folium_static(m, width=1100, height=550)

# ----------------- EXECUTIVE SUMMARY & ANALYTICAL TEXT -----------------
st.markdown("---")
st.subheader("📝 Ringkasan Eksekutif Hasil Analisis Spasial")
st.markdown("""
Berdasarkan visualisasi spasial monitoring kapasitas Taman Makam Umum (TMU) dan aksesibilitas RPTRA di atas, ditemukan beberapa poin strategis untuk pengambilan keputusan:
1.  **Isu Overcapacity TMU**: Terdapat **2 TMU berstatus kritis** di Jakarta Selatan, yaitu **TMU Menteng Pulo** (kapasitas tersisa 5%) dan **TMU Kalibata** (kapasitas tersisa 8%). Lokasi ini membutuhkan intervensi segera berupa pembatasan pemakaman baru atau penyiapan lahan pemakaman alternatif di daerah penyangga.
2.  **Kesesuaian Lokasi RPTRA & Buffer Eksklusi**: Peta menunjukkan radius buffer eksklusi **500m** di sekeliling area TMU sebagai daerah penyangga lingkungan dan psikologis anak. Beberapa RPTRA seperti **RPTRA Dahlia** dan **RPTRA Tebet Kreatif** berada di sekitar perbatasan zona buffer TMU Menteng Pulo, yang menandakan pentingnya membatasi pembangunan RPTRA baru di wilayah barat laut Kecamatan Tebet.
3.  **Kebutuhan Sebaran Fasilitas**: Di Kecamatan **Tebet**, sebaran RPTRA dengan fasilitas lengkap sudah terdistribusi dengan baik, namun terdapat RPTRA dengan **fasilitas terbatas** (seperti *RPTRA Tebet Kreatif* dan *RPTRA Melati*) yang memerlukan penambahan fasilitas penunjang ramah anak (seperti perpustakaan interaktif atau ruang laktasi) untuk mengimbangi tingginya tingkat kepadatan penduduk anak di wilayah sekitarnya.
""")

# ----------------- DETAILS DATA TABLE -----------------
st.markdown("---")
st.subheader("📊 Tabel Detail Fasilitas")
tab1, tab2 = st.tabs(["Detail Taman Makam Umum (TMU)", "Detail Ruang Publik Terpadu Ramah Anak (RPTRA)"])

with tab1:
    df_tmu_display = pd.DataFrame(filtered_tmu.drop(columns='geometry'))
    st.dataframe(df_tmu_display, use_container_width=True)
    
with tab2:
    df_rptra_display = pd.DataFrame(filtered_rptra.drop(columns='geometry'))
    st.dataframe(df_rptra_display, use_container_width=True)

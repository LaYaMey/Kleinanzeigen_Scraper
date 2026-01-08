import streamlit as st
import pandas as pd
import json
import os
import gpxpy
import pgeocode
import numpy as np
import datetime
from scipy.spatial import cKDTree

# --- IMPORT FEATURE EXTRACTOR ---
from feature_extractor import enrich_dataframe

# --- CONFIGURATION ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FOLDER = os.path.join(SCRIPT_DIR, "..", "data")

# Initialize Geocoding (Germany)
nomi = pgeocode.Nominatim('de')
dist_calc = pgeocode.GeoDistance('de')

def get_json_files(folder):
    if not os.path.exists(folder):
        return []
    files = [f for f in os.listdir(folder) if f.endswith('.json')]
    return sorted(files)

@st.cache_data
def load_data(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if not data: return pd.DataFrame()
        df = pd.DataFrame(data)
        
        # 1. Standard Cleaning
        if 'Preis' in df.columns:
            df['Preis'] = df['Preis'].astype(str).str.replace(r'[^\d]', '', regex=True).replace('', '0').astype(int)
        
        if 'Date' in df.columns:
            df['Date'] = pd.to_datetime(df['Date'], format='%d.%m.%Y', errors='coerce')
        
        # 2. RUN HEURISTIC EXTRACTION
        df = enrich_dataframe(df)

        # 3. EXTRACT ZIP CODE (PLZ)
        if 'Place' in df.columns:
            df['PLZ'] = df['Place'].astype(str).str.extract(r'^(\d{5})')
        else:
            df['PLZ'] = None
        
        return df
    except Exception as e:
        st.error(f"Error loading {file_path}: {e}")
        return pd.DataFrame()

# --- HELPER: GPX PROCESSING ---
def parse_gpx_to_points(gpx_file):
    try:
        gpx = gpxpy.parse(gpx_file)
        points = []
        for track in gpx.tracks:
            for segment in track.segments:
                for point in segment.points:
                    points.append((point.latitude, point.longitude))
        if not points:
            for route in gpx.routes:
                for point in route.points:
                    points.append((point.latitude, point.longitude))
        return np.array(points)
    except Exception as e:
        st.error(f"Error parsing GPX: {e}")
        return np.array([])

# --- HELPER: GEOCODE ITEMS ---
@st.cache_data
def geocode_dataframe(df):
    if 'PLZ' not in df.columns or df.empty:
        return df
    
    unique_zips = df['PLZ'].dropna().unique()
    geo_results = nomi.query_postal_code(unique_zips)
    zip_map = geo_results.set_index('postal_code')[['latitude', 'longitude']].to_dict('index')
    
    def get_coords(plz):
        if plz in zip_map:
            d = zip_map[plz]
            return pd.Series([d['latitude'], d['longitude']])
        return pd.Series([None, None])

    df[['Item_Lat', 'Item_Lon']] = df['PLZ'].apply(get_coords)
    return df

# --- HELPER: DISTANCE TO ROUTE ---
def calculate_route_distance(df, route_points):
    valid_items = df.dropna(subset=['Item_Lat', 'Item_Lon'])
    if valid_items.empty or len(route_points) == 0:
        df['Route_Dist'] = None
        return df

    item_coords = valid_items[['Item_Lat', 'Item_Lon']].values
    tree = cKDTree(route_points)
    dists_deg, _ = tree.query(item_coords, k=1)
    
    # Approx conversion deg -> km (using 111km per degree roughly)
    dists_km = dists_deg * 111 

    df.loc[valid_items.index, 'Route_Dist'] = dists_km
    return df

# --- MAIN APP ---
st.set_page_config(layout="wide", page_title="Kleinanzeigen Explorer")

# Sidebar: File Selection
with st.sidebar:
    st.header("📂 Dataset Selection")
    available_files = get_json_files(DATA_FOLDER)
    if not available_files:
        st.error(f"No files in '{DATA_FOLDER}'")
        st.stop()
    selected_filename = st.selectbox("Choose a Dataset:", available_files)
    if st.button("🔄 Refresh Data"):
        st.cache_data.clear()
        st.rerun()
    st.divider()

if selected_filename is None:
    st.stop()
full_path = os.path.join(DATA_FOLDER, selected_filename)
df = load_data(full_path)

if df.empty:
    st.warning("File empty.")
    st.stop()

# --- PRE-PROCESS: LAT/LON ---
df = geocode_dataframe(df)

# --- SIDEBAR: LOCATION / ROUTE ---
with st.sidebar:
    st.header("📍 Location & Route")
    
    tab1, tab2 = st.tabs(["🏠 Zip Code", "🗺️ GPX Route"])
    
    # --- TAB 1: Single Zip ---
    with tab1:
        my_zip = st.text_input("Your Zip Code", max_chars=5)
        max_dist_zip = 0
        if my_zip and len(my_zip) == 5 and my_zip.isdigit():
            item_zips = df['PLZ'].fillna("").tolist()
            dists = dist_calc.query_postal_code(my_zip, item_zips)
            df['Dist_Zip'] = dists
            df['Dist_Zip'] = df['Dist_Zip'].fillna(9999).round(1)
            max_dist_zip = st.slider("Max Radius (km)", 0, 600, 100)
        else:
            if 'Dist_Zip' in df.columns: df.drop(columns=['Dist_Zip'], inplace=True)

    # --- TAB 2: GPX Route ---
    with tab2:
        uploaded_gpx = st.file_uploader("Upload Route (.gpx)", type=['gpx'])
        max_dist_route = 0
        
        if uploaded_gpx:
            route_pts = parse_gpx_to_points(uploaded_gpx)
            st.caption(f"Route loaded: {len(route_pts)} points")
            if len(route_pts) > 0:
                df = calculate_route_distance(df, route_pts)
                max_dist_route = st.slider("Max Detour (km)", 0, 200, 50)
        else:
            if 'Route_Dist' in df.columns: df.drop(columns=['Route_Dist'], inplace=True)

    st.markdown("---")

# --- SIDEBAR: VIEW & SORT ---
with st.sidebar:
    st.header("⚙️ View & Sort")
    
    # 1. Visible Columns
    all_cols = df.columns.tolist()
    # Removed 'ID' from defaults
    defaults = ['Preis', 'Artikelstitel', 'Ext_GPU', 'Ext_CPU', 'Place', 'Date', 'URL']
    
    if 'Route_Dist' in df.columns: defaults.insert(1, 'Route_Dist')
    if 'Dist_Zip' in df.columns: defaults.insert(1, 'Dist_Zip')
        
    default_cols = [c for c in defaults if c in all_cols]
    selected_columns = st.multiselect("Visible Columns:", all_cols, default=default_cols)
    
    # 2. Sorting
    st.subheader("Sorting")
    sort_options = ['Preis', 'Date', 'Place', 'Ext_GPU', 'Ext_CPU', 'Ext_RAM']
    
    if 'Route_Dist' in df.columns: sort_options.insert(0, 'Route_Dist')
    if 'Dist_Zip' in df.columns: sort_options.insert(0, 'Dist_Zip')
        
    sort_options = [c for c in sort_options if c in df.columns]
    
    c1, c2 = st.columns([2, 1])
    sort_1 = c1.selectbox("Sort By (1st)", ["None"] + sort_options, index=0)
    order_1 = c2.selectbox("Order 1", ["Asc", "Desc"], label_visibility="collapsed")
    
    sort_2 = "None"
    if sort_1 != "None":
        c3, c4 = st.columns([2, 1])
        remaining = [x for x in sort_options if x != sort_1]
        sort_2 = c3.selectbox("Sort By (2nd)", ["None"] + remaining, index=0)
        order_2 = c4.selectbox("Order 2", ["Asc", "Desc"], label_visibility="collapsed")

    st.markdown("---")
    
    # 3. Standard Filters
    st.subheader("Basic Filters")
    search_query = st.text_input("🔍 Quick Search", "")
    
    # Price
    max_price = int(df['Preis'].max()) if 'Preis' in df.columns else 3000
    SLIDER_MAX = ((max_price // 100) + 1) * 100 
    user_min, user_max = st.slider("Price Range (€)", 0, SLIDER_MAX, (0, SLIDER_MAX), 50)

    # Date
    start_date, end_date = None, None
    if 'Date' in df.columns and not df['Date'].dropna().empty:
        d_min_file = df['Date'].min().date()
        d_max_file = df['Date'].max().date()
        
        # Calculate Defaults (Today - 3 Months)
        today = datetime.date.today()
        target_start = today - datetime.timedelta(days=90)
        
        # Ensure defaults are within the bounds of the file (or logical)
        # Default Start: The later of (3 months ago) OR (First date in file)
        # If the file is super old (older than 3 months), we just show the start of file to avoid empty view?
        # User requested "From today to 3 months ago".
        
        default_start = max(d_min_file, target_start)
        # If the calculated start is after the file's end (i.e. file is old), reset to file start
        if default_start > d_max_file:
            default_start = d_min_file
            
        default_end = d_max_file

        st.write("📅 **Date Range**")
        c_d1, c_d2 = st.columns(2)
        start_date = c_d1.date_input("From", value=default_start, min_value=d_min_file, max_value=d_max_file)
        end_date = c_d2.date_input("To", value=default_end, min_value=d_min_file, max_value=d_max_file)

    st.markdown("---")

    # 4. Spec Filters
    st.subheader("Spec Filters")
    found_gpu = sorted(df['Ext_GPU'].dropna().unique())
    sel_gpu = st.multiselect("GPU Series", found_gpu)
    
    found_cpu = sorted(df['Ext_CPU'].dropna().unique())
    sel_cpu = st.multiselect("CPU Family", found_cpu)

# --- FILTER LOGIC ---
filtered_df = df.copy()

# Price
if 'Preis' in filtered_df.columns and user_max != SLIDER_MAX:
    filtered_df = filtered_df[(filtered_df['Preis'] >= user_min) & (filtered_df['Preis'] <= user_max)]
elif 'Preis' in filtered_df.columns:
    filtered_df = filtered_df[filtered_df['Preis'] >= user_min]

# Search
if search_query:
    mask = filtered_df.astype(str).apply(lambda row: row.str.contains(search_query, case=False).any(), axis=1)
    filtered_df = filtered_df[mask]

# Date
if start_date and end_date and 'Date' in filtered_df.columns:
    mask_date = (filtered_df['Date'].dt.date >= start_date) & (filtered_df['Date'].dt.date <= end_date)
    filtered_df = filtered_df[mask_date]

# Specs
if sel_gpu: filtered_df = filtered_df[filtered_df['Ext_GPU'].isin(sel_gpu)]
if sel_cpu: filtered_df = filtered_df[filtered_df['Ext_CPU'].isin(sel_cpu)]

# DISTANCE FILTERS
if 'Dist_Zip' in filtered_df.columns and max_dist_zip > 0:
    filtered_df = filtered_df[filtered_df['Dist_Zip'] <= max_dist_zip]

if 'Route_Dist' in filtered_df.columns and max_dist_route > 0:
    filtered_df = filtered_df[filtered_df['Route_Dist'] <= max_dist_route]

# SORTING
if sort_1 != "None":
    cols = [sort_1]
    ascs = [True if order_1 == "Asc" else False]
    if sort_2 != "None":
        cols.append(sort_2)
        ascs.append(True if order_2 == "Asc" else False)
    filtered_df = filtered_df.sort_values(by=cols, ascending=ascs)

# --- DISPLAY ---
st.title(f"📊 {selected_filename} ({len(filtered_df)} items)")

# Metric
c1, c2, c3, c4 = st.columns(4)
c1.metric("Total", len(df))
c2.metric("Filtered", len(filtered_df))
avg_price = filtered_df['Preis'].mean() if 'Preis' in filtered_df.columns and not filtered_df.empty else 0
c3.metric("Avg Price", f"{avg_price:.0f} €")

# Column Config
col_config = {
    "URL": st.column_config.LinkColumn("Link"),
    "Preis": st.column_config.NumberColumn("Price", format="%d €"),
    "Date": st.column_config.DateColumn("Date", format="DD.MM.YYYY"),
}
if 'Dist_Zip' in filtered_df.columns:
    col_config["Dist_Zip"] = st.column_config.NumberColumn("Dist (Home)", format="%.1f km")
if 'Route_Dist' in filtered_df.columns:
    col_config["Route_Dist"] = st.column_config.NumberColumn("Detour (Route)", format="%.1f km")

st.dataframe(
    filtered_df[selected_columns],
    width="stretch",
    hide_index=True,
    column_config=col_config
)
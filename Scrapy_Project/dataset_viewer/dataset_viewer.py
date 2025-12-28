import streamlit as st
import pandas as pd
import json
import os
import math

# --- IMPORT FEATURE EXTRACTOR ---
from feature_extractor import enrich_dataframe

# --- CONFIGURATION ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FOLDER = os.path.join(SCRIPT_DIR, "..", "data")

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
        
        # 2. RUN HEURISTIC EXTRACTION (New!)
        df = enrich_dataframe(df)
        
        return df
    except Exception as e:
        st.error(f"Error loading {file_path}: {e}")
        return pd.DataFrame()

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

# Sidebar: View Settings
with st.sidebar:
    st.header("⚙️ Filter Settings")
    
    # 1. Fields
    st.subheader("1. Show/Hide Fields")
    # Added Ext_* columns to the list
    all_cols = df.columns.tolist()
    default_cols = [c for c in ['ID', 'Preis', 'Artikelstitel', 'Ext_RAM', 'Ext_SSD', 'Ext_CPU', 'URL'] if c in all_cols]
    selected_columns = st.multiselect("Select columns:", all_cols, default=default_cols)
    
    st.markdown("---")
    
    # 2. Standard Filters
    st.subheader("2. Basic Filters")
    search_query = st.text_input("🔍 Quick Search", "")
    
    max_price = int(df['Preis'].max()) if 'Preis' in df.columns else 3000
    SLIDER_MAX = ((max_price // 100) + 1) * 100 
    user_min, user_max = st.slider("Price Range (€)", 0, SLIDER_MAX, (0, SLIDER_MAX), 50)

    st.markdown("---")

    # 3. DERIVED SPEC FILTERS (New!)
    st.subheader("3. Derived Specs (Heuristics)")
    
    # A. RAM FILTER
    # Get unique RAM values found in data, sort them
    found_ram = sorted([int(x) for x in df['Ext_RAM'].dropna().unique()])
    sel_ram = st.multiselect("RAM (GB)", found_ram, format_func=lambda x: f"{x} GB")
    
    # B. CPU FILTER
    found_cpu = sorted(df['Ext_CPU'].dropna().unique())
    sel_cpu = st.multiselect("CPU Family", found_cpu)
    
    # C. SSD FILTER (Min Size)
    found_ssd = sorted([int(x) for x in df['Ext_SSD'].dropna().unique()])
    if found_ssd:
        min_ssd_val = st.select_slider("Min Storage (GB)", options=[0] + found_ssd, value=0)
    else:
        min_ssd_val = 0

# --- MAIN LOGIC ---

filtered_df = df.copy()

# 1. Price
if 'Preis' in filtered_df.columns and user_max != SLIDER_MAX:
    filtered_df = filtered_df[(filtered_df['Preis'] >= user_min) & (filtered_df['Preis'] <= user_max)]
elif 'Preis' in filtered_df.columns:
    filtered_df = filtered_df[filtered_df['Preis'] >= user_min]

# 2. Text Search
if search_query:
    mask = filtered_df.astype(str).apply(lambda row: row.str.contains(search_query, case=False).any(), axis=1)
    filtered_df = filtered_df[mask]

# 3. Derived Filters
# Logic: If user selects specific RAM, only show rows WITH that RAM. Rows with "None" are hidden.
if sel_ram:
    filtered_df = filtered_df[filtered_df['Ext_RAM'].isin(sel_ram)]

if sel_cpu:
    filtered_df = filtered_df[filtered_df['Ext_CPU'].isin(sel_cpu)]

if min_ssd_val > 0:
    # Filter: Must have extracted SSD value AND it must be >= slider
    filtered_df = filtered_df[filtered_df['Ext_SSD'].notna() & (filtered_df['Ext_SSD'] >= min_ssd_val)]

# --- DISPLAY ---
st.title(f"📊 {selected_filename} ({len(filtered_df)} items)")

# Metrics
c1, c2, c3, c4 = st.columns(4)
c1.metric("Total", len(df))
c2.metric("Filtered", len(filtered_df))
avg_price = filtered_df['Preis'].mean() if 'Preis' in filtered_df.columns else 0
c3.metric("Avg Price", f"{avg_price:.0f} €")

# Heuristic Success Rate Metric
# How many rows have at least one extracted spec?
with_specs = filtered_df[['Ext_RAM', 'Ext_SSD', 'Ext_CPU']].dropna(how='all')
success_rate = (len(with_specs) / len(filtered_df) * 100) if not filtered_df.empty else 0
c4.metric("Specs Found", f"{success_rate:.0f}%")

st.dataframe(
    filtered_df[selected_columns],
    width="stretch",
    hide_index=True,
    column_config={
        "URL": st.column_config.LinkColumn("Link"),
        "Preis": st.column_config.NumberColumn("Price", format="%d €"),
        "Ext_RAM": st.column_config.NumberColumn("RAM", format="%d GB"),
        "Ext_SSD": st.column_config.NumberColumn("SSD", format="%d GB"),
        "Date": st.column_config.DateColumn("Date", format="DD.MM.YYYY"),
    }
)
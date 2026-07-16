import streamlit as st
import pandas as pd
from datetime import date

# --- App Title & Config ---
st.set_page_config(page_title="Gym Member Transfer Tool", layout="wide")
st.title("🏋️‍♂️ Gym Member Transfer Tool")
st.write(f"Report Period: **{date.today().strftime('%Y.%m')}**")

# --- Sidebar Inputs ---
st.sidebar.header("Settings")

gym_map = {
    'LHI': 'lehi',
    'MCK': 'millcreek',
    'SDY': 'sandy',
    'FTU': 'fort union',
    'TSQ': 'trolley square'
}

# Replace your hardcoded MoLoc with a dropdown
mo_loc = st.sidebar.selectbox("Select Current Location (MoLoc):", list(gym_map.keys()))

# --- File Uploaders ---
st.subheader("1. Upload Source Files")
col1, col2 = st.columns(2)

with col1:
    checkin_file = st.file_uploader("Upload Remote Check-in Percentage Report (.csv)", type=["csv"])
with col2:
    info_file = st.file_uploader("Upload Print Displayed Customer List (.csv)", type=["csv"])

# --- Processing Logic ---
if checkin_file and info_file:
    st.success("Both files uploaded successfully! Processing...")
    
    try:
        # Read the uploaded files directly from the browser cache
        checkin = pd.read_csv(checkin_file)
        m_info = pd.read_csv(info_file)

        # --- Your Pandas Clean up & Filtering Logic ---
        checkin = checkin.rename(columns=str.lower)
        
        # Clean remote percentage (handling strings/percentages safely)
        checkin['remote percentage'] = checkin['remote percentage'].astype(str).str.replace('%', '')
        checkin['remote percentage'] = pd.to_numeric(checkin['remote percentage']).round(2)

        m_info = m_info.rename(columns=str.lower)
        m_info = m_info[['name', 'type', 'subtype', 'status', 'billing', 'responsible party', 'dues']]

        # Filters
        subtype_filters = ['Individual', 'Family - 1', 'Family - 2', 'Family - 3+']
        m_info = m_info[
            (m_info['type'] == 'Member') & 
            (m_info['subtype'].isin(subtype_filters)) & 
            (m_info['status'] == 'OK') & 
            (m_info['billing'] == 'EFT')
        ]

        # Merge
        checkin_info = m_info.merge(checkin, left_on='name', right_on='customer')
        
        if 'type_y' in checkin_info.columns:
            checkin_info = checkin_info.drop(columns=['type_y', 'status_y'], errors='ignore')

        checkin_info = checkin_info[checkin_info['remote percentage'] >= 65].drop(columns='customer', errors='ignore')
        checkin_info = checkin_info[checkin_info['remote visits'] >= 6]
        checkin_info['% Remote'] = ((checkin_info['remote visits'] / checkin_info['total visits']) * 100).round(0)

        # --- Transfer Calculations ---
        current_gym = gym_map[mo_loc]
        comparison_gyms = [g for g in gym_map.values() if g != current_gym]

        checkin_info[comparison_gyms] = checkin_info[comparison_gyms].astype(float).fillna(0)
        max_vals = checkin_info[comparison_gyms].max(axis=1)
        ties = checkin_info[comparison_gyms].eq(max_vals, axis=0).sum(axis=1) > 1

        checkin_info['transfer location'] = checkin_info[comparison_gyms].idxmax(axis=1)
        checkin_info.loc[ties, 'transfer location'] = 'Investigate'

        # Responsible Party logic
        resp_party = checkin_info['responsible party']
        has_resp_party = resp_party.notnull()
        resp_party_trans = resp_party.isin(checkin_info['name'])
        
        output = checkin_info[has_resp_party == resp_party_trans]

        # Reorder columns
        cols = output.columns.tolist()
        cols = cols[-1:] + cols[:-1]
        output = output[cols]

        # --- Display Results ---
        st.subheader("2. Output Preview")
        st.dataframe(output)  # Interactive table in the browser
        st.metric(label="Total Members to Transfer", value=len(output))

        # --- Download Button ---
        # Convert dataframe to CSV bytes for browser download
        csv_data = output.to_csv(index=False).encode('utf-8')
        output_file_name = f"{mo_loc}_{date.today().strftime('%Y.%m')}_ToBeTransferred.csv"

        st.download_button(
            label="📥 Download Processed CSV File",
            data=csv_data,
            file_name=output_file_name,
            mime='text/csv',
        )

    except Exception as e:
        st.error(f"An error occurred while processing the files: {e}")
else:
    st.info("💡 Please upload both CSV files in the fields above to begin.")
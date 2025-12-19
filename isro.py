import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from skyfield.api import load, wgs84
import datetime

# -------------------------------------------------
# 1.  DARK THEME & STYLING
# -------------------------------------------------
st.set_page_config(page_title="ISRO 3D Mission Radar", layout="wide")

st.markdown("""
    <style>
    .main { background: radial-gradient(circle, #1b2735 0%, #080a0f 100%); color: #e0e0e0; }
    [data-testid="stMetricValue"] { 
        color: #00f9ff !important; 
        font-family: 'Courier New', monospace; 
        text-shadow: 0 0 12px rgba(0, 249, 255, 0.6); 
    }
    .intel-card {
        background: rgba(0, 249, 255, 0.07);
        border: 1px solid #00f9ff;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 0 20px rgba(0, 249, 255, 0.1);
    }
    .search-btn {
        display: inline-block;
        padding: 8px 16px;
        background-color: #4285F4;
        color: white;
        text-decoration: none;
        border-radius: 4px;
        font-weight: bold;
        font-size: 0.8rem;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("ISRO Satellites : 3D Live Radar")



# -------------------------------------------------
# 2. DATA ENGINE
# -------------------------------------------------
@st.cache_data
def load_csv_data():
    path = r"D:\Data Analysis Projects\Sentinel 2\satcat.csv"
    df = pd.read_csv(path)
    df.columns = [c.strip().upper() for c in df.columns]
    df["NORAD_CAT_ID"] = pd.to_numeric(df["NORAD_CAT_ID"], errors="coerce")
    df = df.dropna(subset=["NORAD_CAT_ID"])
    if "RCS" in df.columns:
        df["RCS"] = pd.to_numeric(df["RCS"], errors="coerce").fillna(1.0).clip(0.5, 5)
    return df

@st.cache_resource
def load_live_tle():
    return load.tle_file("https://celestrak.org/NORAD/elements/gp.php?GROUP=active&FORMAT=tle")

local_df = load_csv_data()
target_ids = set(local_df["NORAD_CAT_ID"].astype(int))
tle_sats = load_live_tle()
ts = load.timescale()
now = ts.now()

live_list, matched_tle_map = [], {}
for sat in tle_sats:
    if int(sat.model.satnum) in target_ids:
        subpoint = wgs84.subpoint(sat.at(now))
        live_list.append({
            "NAME": sat.name, "ID": int(sat.model.satnum),
            "LAT": subpoint.latitude.degrees, "LON": subpoint.longitude.degrees,
            "ALT": round(subpoint.elevation.km, 2)
        })
        matched_tle_map[sat.name] = sat

full_df = pd.merge(pd.DataFrame(live_list), local_df, left_on="ID", right_on="NORAD_CAT_ID", how="left")

# -------------------------------------------------
# 3. SIDEBAR & SELECTION 
# -------------------------------------------------
st.sidebar.markdown("### TARGETING SYSTEM")
selected = st.sidebar.selectbox("SELECT TARGET", ["ALL SATELLITES"] + sorted(full_df["NAME"].unique()))

# -------------------------------------------------
# 4. 3D VISUALIZATION ENGINE
# -------------------------------------------------
fig = go.Figure()

if selected != "ALL SATELLITES":
    sat_obj = matched_tle_map[selected]
    lats, lons = [], []
    base_dt = now.utc_datetime()
    for m in range(0, 100, 4):
        future_t = ts.from_datetime(base_dt + datetime.timedelta(minutes=m))
        pos = sat_obj.at(future_t).subpoint()
        lats.append(pos.latitude.degrees)
        lons.append(pos.longitude.degrees)
    fig.add_trace(go.Scattergeo(lat=lats, lon=lons, mode="lines", line=dict(width=2, color="#00f9ff"), opacity=0.4))

fig.add_trace(go.Scattergeo(
    lat=full_df["LAT"], lon=full_df["LON"], mode="markers",
    marker=dict(size=full_df["RCS"]*3, color=full_df["ALT"], colorscale="Viridis", showscale=True),
    text=full_df["NAME"]
))

if selected != "ALL SATELLITES":
    target = full_df[full_df["NAME"] == selected].iloc[0]
    fig.add_trace(go.Scattergeo(lat=[target["LAT"]], lon=[target["LON"]], mode="markers", 
                                marker=dict(size=18, color="#ff0044", symbol="circle-open", line=dict(width=3))))
    fig.update_geos(projection_rotation=dict(lon=target["LON"], lat=target["LAT"], roll=0))

fig.update_geos(projection_type="orthographic", showocean=True, oceancolor="#010914", showland=True, landcolor="#0a1a2f", bgcolor="rgba(0,0,0,0)")
fig.update_layout(height=600, margin=dict(l=0, r=0, t=0, b=0), paper_bgcolor="rgba(0,0,0,0)", showlegend=False)
st.plotly_chart(fig, use_container_width=True)




# -------------------------------------------------
# 5. INTELLIGENCE HUB
# -------------------------------------------------
if selected != "ALL SATELLITES":
    f = full_df[full_df["NAME"] == selected].iloc[0]
    
    st.markdown(f"### AI Intelligence Report: {selected}")
    
    col_brief, col_stats = st.columns([1.2, 0.8])
    
    with col_brief:
        # Calculate AI-style insights based on orbital physics
        inc = f.get('INCLINATION', 0)
        per = f.get('PERIOD', 0)
        
        # logic for mission guessing
        if inc > 90: mission_type = "Sun-Synchronous (Polar) - Likely Imaging/Remote Sensing"
        elif per > 1400: mission_type = "Geostationary - Likely Communication/Weather"
        else: mission_type = "Low Earth Orbit (LEO) - Likely Scientific/Experimental"

   
if selected != "ALL SATELLITES":
    f = full_df[full_df["NAME"] == selected].iloc[0]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("ALTITUDE", f"{f['ALT']} km")
    c2.metric("INCLINATION", f"{f.get('INCLINATION', 'N/A')}°")
    c3.metric("PERIOD", f"{f.get('PERIOD', 'N/A')} m")
    c4.metric("SIZE (RCS)", f"{f.get('RCS', 'N/A')}")

st.markdown(
    f"""
    <div class="footer">
        Developed by <span class="dev-credit">Shubham Wankhede</span> | 
        <span class="dev-credit">TISS 2025</span> | 
        Powered by ISRO Open Data & Skyfield API
    </div>
    """, 
    unsafe_allow_html=True
            )

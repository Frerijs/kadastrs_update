import os
import geopandas as gpd
import folium
from urllib.parse import urlencode
import numpy as np
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium
from shapely.geometry import Polygon, LineString, Point, MultiPolygon
import tempfile

# Papildu bibliotēkas
import ezdxf
from shapely.ops import linemerge, polygonize, unary_union
import datetime
import requests
from zoneinfo import ZoneInfo
from folium.plugins import Draw
from ezdxf.enums import TextHAlign
from folium import MacroElement
from jinja2 import Template
import base64
from arcgis2geojson import arcgis2geojson
import json

# Supabase konfigurācija (demonstrācijas vajadzībām)
supabase_url = "https://uhwbflqdripatfpbbetf.supabase.co"
supabase_key = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InVod2JmbHFkcmlwYXRmcGJiZXRmIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTczMDcxODE2MywiZXhwIjoyMDQ2Mjk0MTYzfQ."
    "78wsNZ4KBg2l6zeZ1ZknBBooe0PeLtJzRU-7eXo3WTk"
)

# Konstantas
APP_NAME = "Kadastrs"
APP_VERSION = "4.0"
APP_TYPE = "web"

# Tulkošanas vārdnīca
translations = {
    "Latviešu": {
        "radio_label": "Izvēlieties veidu, kā iegūt datus:",
        "methods": [
            "Augšupielādējiet iepriekš sagatavotu noslēgtas kontūras failu .DXF vai .SHP formātā",
            "Zīmējiet uz kartes noslēgtu kontūru",
            "Tikai ievadītajiem kadastra apzīmējumiem",
            "Ievadītajiem kadastra apzīmējumiem un pierobežniekiem"
        ],
        "title": "Kadastra apzīmējumu saraksta lejuplāde (ZV robežas un apzīmējumi)",
        "language_label": "Valoda / Language",
        "upload_instruction": "Augšupielādējiet slēgtu kontūru vai vairākas kontūras vienā no atbalstītajiem failu formātiem:",
        "upload_files_label": "Augšupielādējiet nepieciešamos failus:",
        "draw_instruction": "Zīmējiet noslēgtu kontūru uz kartes un nospiediet 'Iegūt datus' pogu.",
        "get_data_button": "Iegūt datus",
        "download_geojson": "*.GeoJSON",
        "download_shapefile": "*.SHP",
        "download_dxf": "*.DXF",
        "download_csv": "*.CSV",
        "download_all_csv": "*.XLSX (ekselis)",
        "download_all_excel": "*.CSV",
        "logout": "Iziet",  # Poga vairs netiks attēlota
        "success_logout": "Veiksmīgi izgājāt no konta.",
        "error_authenticate": "Kļūda autentificējot lietotāju: {status_code}",
        "error_login": "Nepareizs lietotājvārds vai parole.",
        "error_upload_dxf": "DXF failā netika atrastas derīgas ģeometrijas.",
        "error_upload_shp": "Netika atrasts .shp fails starp augšupielādētajiem failiem.",
        "error_no_data_download": "Nav pieejami dati lejupielādei.",
        "error_display_pdf": "Kļūda: {error}",
        "info_upload": "Lūdzu, augšupielādējiet failu ar poligonu.",
        "info_draw": "Lūdzu, uzzīmējiet poligonu uz kartes.",
        "info_enter_code": "Lūdzu, ievadiet vienu vai vairākus kadastra numurus, atdalot ar komatu.",
        "preparing_geojson": "1. Sagatavo GeoJSON failu...",
        "preparing_shapefile": "2. Sagatavo Shapefile ZIP failu...",
        "preparing_dxf": "3. Sagatavo DXF failu...",
        "preparing_csv": "4. Sagatavo CSV failu...",
        "preparing_all_csv": "5. Sagatavo VISU CSV failu...",
        "preparing_all_excel": "6. Sagatavo VISU EXCEL failu...",
        "warning_code_missing": "Kadastra numurs nav pieejama datos. Teksts netiks pievienots DXF failā.",
        "instructions": "Instrukcija",
        "search_address": "Meklēt pēc koda:",
        "search_button": "Meklēt",
        "search_error": "Neizdevās atrast ierakstu ar šo kodu.",
        "enter_codes_label": "Ievadiet kadastra numuru (us):",
        "process_codes_button": "Apstrādāt kodus",
        "error_no_codes_entered": "Nav ievadīti kadastra numuri. Lūdzu, ievadiet vienu vai vairākus kadastra numurus.",
        "error_no_data_found": "Nav atrasti dati ar norādītajiem kadastra numuriem.",
        "info_code_filter": "Dati tiek iegūti gan par norādītajiem kadastra numuriem un pieskarošajiem."
    },
    "English": {
        "radio_label": "Choose a method to obtain data:",
        "methods": [
            "Upload a pre-prepared closed contour file in .DXF or .SHP format",
            "Draw a closed contour on the map",
            "Enter one or more cadastral numbers and obtain data",
            "Enter one or more cadastral numbers and obtain data for both the specified cadastral numbers and adjacent ones"
        ],
        "title": "Download Cadastral Designation List (ZV Boundaries and Designations)",
        "language_label": "Language",
        "upload_instruction": "Upload a closed contour or multiple contours in one of the supported file formats:",
        "upload_files_label": "Upload the required files:",
        "draw_instruction": "Draw a closed contour on the map and press the 'Get Data' button.",
        "get_data_button": "Get Data",
        "download_geojson": "*.GeoJSON",
        "download_shapefile": "*.SHP",
        "download_dxf": "*.DXF",
        "download_csv": "*.CSV",
        "download_all_csv": "*.XLSX (ekselis)",
        "download_all_excel": "*.CSV",
        "logout": "Logout",
        "success_logout": "Successfully logged out of the account.",
        "error_authenticate": "Error authenticating user: {status_code}",
        "error_login": "Incorrect username or password.",
        "error_upload_dxf": "No valid geometries found in the DXF file.",
        "error_upload_shp": "No .shp file found among the uploaded files.",
        "error_no_data_download": "No data available for download.",
        "error_display_pdf": "Error: {error}",
        "info_upload": "Please upload a polygon file.",
        "info_draw": "Please draw a polygon on the map.",
        "info_enter_code": "Please enter one or more cadastral numbers, separated by commas.",
        "preparing_geojson": "1. Preparing GeoJSON file...",
        "preparing_shapefile": "2. Preparing Shapefile ZIP file...",
        "preparing_dxf": "3. Preparing DXF file...",
        "preparing_csv": "4. Preparing CSV file...",
        "preparing_all_csv": "5. Preparing ALL CSV files...",
        "preparing_all_excel": "6. Preparing ALL EXCEL files...",
        "warning_code_missing": "Cadastral number is not available in the data. The text will not be added to the DXF file.",
        "instructions": "Instructions",
        "search_address": "Search by code:",
        "search_button": "Search",
        "search_error": "Failed to find a record with this code.",
        "enter_codes_label": "Enter cadastral number(s):",
        "process_codes_button": "Process codes",
        "error_no_codes_entered": "No cadastral numbers entered. Please enter one or more cadastral numbers.",
        "error_no_data_found": "No data found for the specified cadastral numbers.",
        "info_code_filter": "Data is obtained for both the specified cadastral numbers and adjacent ones."
    }
}

st.set_page_config(
    page_title=translations["Latviešu"]["title"],
    layout="centered"
)

# Palielinām pogu fonta izmēru
st.markdown(
    """
    <style>
    div.stButton > button {
        font-size: 20px;
        padding: 10px 20px;
    }
    </style>
    """,
    unsafe_allow_html=True
)

language = st.sidebar.selectbox(
    translations["Latviešu"]["language_label"],
    ["Latviešu", "English"]
)

# =============================================================================
# Pielāgots Leaflet kontrolis (dzēš poligonus)
# =============================================================================
class CustomDeleteButton(MacroElement):
    _template = Template("""
        {% macro script(this, kwargs) %}
            L.Control.DeleteButton = L.Control.extend({
                options: { position: 'topleft' },
                onAdd: function(map) {
                    var container = L.DomUtil.create('div', 'leaflet-bar leaflet-control');
                    var button = L.DomUtil.create('a', 'leaflet-control-delete', container);
                    button.innerHTML = '&#128465;';
                    button.title = 'Dzēst visus poligonus';
                    button.style.fontSize = '18px';
                    button.style.textAlign = 'center';
                    button.style.lineHeight = '30px';
                    button.style.width = '30px';
                    button.style.height = '30px';
                    button.style.cursor = 'pointer';
                    L.DomEvent.disableClickPropagation(container);
                    L.DomEvent.on(button, 'click', function(e) {
                        e.preventDefault();
                        map.eachLayer(function(layer) {
                            if (layer instanceof L.FeatureGroup && layer.options.name === "Drawn Items") {
                                layer.clearLayers();
                            }
                        });
                    });
                    return container;
                }
            });
            map.addControl(new L.Control.DeleteButton());
        {% endmacro %}
    """)
    def __init__(self):
        super().__init__()

# =============================================================================
# Lietotāja autentifikācija (Supabase DEMO)
# =============================================================================
def authenticate(username, password):
    try:
        headers = {"apikey": supabase_key,
                   "Authorization": f"Bearer {supabase_key}",
                   "Content-Type": "application/json"}
        url = f"{supabase_url}/rest/v1/users"
        params = {"select": "*", "username": f"eq.{username}", "password": f"eq.{password}"}
        response = requests.get(url, headers=headers, params=params)
        if response.status_code == 200:
            data = response.json()
            return bool(data)
        else:
            st.error(translations[language]["error_authenticate"].format(status_code=response.status_code))
            return False
    except Exception as e:
        st.error(translations[language]["error_display_pdf"].format(error=str(e)))
        return False

def log_user_login(username):
    try:
        riga_tz = ZoneInfo('Europe/Riga')
        current_time = datetime.datetime.now(riga_tz).isoformat()
        data = {"username": username, "App": APP_NAME, "Ver": APP_VERSION, "app_type": APP_TYPE, "login_time": current_time}
        headers = {"apikey": supabase_key,
                   "Authorization": f"Bearer {supabase_key}",
                   "Content-Type": "application/json"}
        url = f"{supabase_url}/rest/v1/user_data"
        response = requests.post(url, json=data, headers=headers)
        if response.status_code not in [200, 201]:
            st.error(translations[language]["error_authenticate"].format(status_code=response.status_code) + f", {response.text}")
    except Exception as e:
        st.error(translations[language]["error_display_pdf"].format(error=str(e)))

def login():
    username = st.session_state.get('username', '').strip()
    password = st.session_state.get('password', '').strip()
    if not username or not password:
        st.error(translations[language]["error_login"])
    else:
        if authenticate(username, password):
            st.session_state.logged_in = True
            st.session_state.username_logged = username
            log_user_login(username)
        else:
            st.error(translations[language]["error_login"])

def show_login():
    st.title(translations[language]["title"])
    with st.form(key='login_form'):
        username = st.text_input("Lietotājvārds" if language == "Latviešu" else "Username", key='username')
        password = st.text_input("Parole" if language == "Latviešu" else "Password", type="password", key='password')
        st.form_submit_button(label=("Pieslēgties" if language == "Latviešu" else "Login"), on_click=login)
    st.markdown("<div style='text-align: center; margin-top: 20px; color: gray;'>© 2024 METRUM</div>", unsafe_allow_html=True)

# =============================================================================
# Meklēšana (ArcGIS FeatureServer) pēc "code" kolonnas
# =============================================================================
def geocode_address(address_text):
    # Šī funkcija veic vaicājumu ArcGIS FeatureServer, meklējot ierakstu, kura 'code' vērtība sakrīt ar ievadīto tekstu.
    if not address_text:
        return None, None, None, None
    try:
        arcgis_url_base = ("https://utility.arcgis.com/usrsvcs/servers/"
                           "4923f6b355934843b33aa92718520f12/rest/services/Hosted/"
                           "Kadastrs/FeatureServer/8/query")
        params = {
            'f': 'json',
            'where': f"code = '{address_text.strip()}'",
            'outFields': '*',
            'returnGeometry': 'true',
            'outSR': '3059'
        }
        query_url = f"{arcgis_url_base}?{urlencode(params)}"
        resp = requests.get(query_url)
        if resp.status_code != 200:
            st.error(f"ArcGIS REST query failed with status code {resp.status_code}")
            return None, None, None, None
        esri_data = resp.json()
        if 'features' not in esri_data or not esri_data['features']:
            st.error("Nav atrasts ieraksts ar šo kodu.")
            return None, None, None, None
        geojson_data = arcgis2geojson(esri_data)
        if 'features' not in geojson_data or not geojson_data['features']:
            st.error("Nav atrasts ieraksts ar šo kodu.")
            return None, None, None, None
        feature = geojson_data['features'][0]
        gdf = gpd.GeoDataFrame.from_features([feature], crs="EPSG:3059")
        centroid = gdf.geometry.centroid.iloc[0]
        return centroid.y, centroid.x, feature['geometry'], None
    except Exception as e:
        st.error(f"Kļūda kodu meklēšanā: {str(e)}")
        return None, None, None, None

# =============================================================================
# Attēlot kartē rezultātus (gan ievadīto poligonu, gan atlasītos poligonus)
# =============================================================================
def display_map_with_results():
    if 'joined_gdf' not in st.session_state or st.session_state['joined_gdf'].empty:
        st.warning(translations[language]["error_no_data_found"])
        return
    joined_gdf = st.session_state.joined_gdf.to_crs(epsg=4326)
    input_method = st.session_state.get('input_method', 'drawn')
    m = folium.Map(location=[56.946285, 24.105078], zoom_start=7)
    tooltip_field = ('Kadastra apzīmējums:' if language == "Latviešu" else "Cadastral identifier:")
    if input_method in ['upload', 'drawn']:
        if 'polygon_gdf' in st.session_state:
            polygon_gdf = st.session_state.polygon_gdf.to_crs(epsg=4326)
            folium.GeoJson(polygon_gdf,
                           name=('Ievadītais poligons' if language=="Latviešu" else 'Input polygon'),
                           style_function=lambda x: {'fillColor': 'none', 'color': 'red', 'weight': 3}).add_to(m)
        else:
            st.info("Nav saglabāts ievades poligons.")
    folium.GeoJson(joined_gdf,
                   name=('Atlasītie poligoni' if language == "Latviešu" else 'Selected polygons'),
                   tooltip=folium.GeoJsonTooltip(fields=['code'], aliases=[tooltip_field]),
                   style_function=lambda x: {'color': 'blue', 'fillOpacity': 0.1, 'weight': 2}).add_to(m)
    folium.LayerControl().add_to(m)
    if not joined_gdf.empty:
        bounds = joined_gdf.total_bounds
        m.fit_bounds([[bounds[1], bounds[0]], [bounds[3], bounds[2]]])
    st_folium(m, width=700, height=500, key='result_map')

# =============================================================================
# Lejupielādes pogas ar virsrakstiem
# =============================================================================
def display_download_buttons():
    if 'joined_gdf' not in st.session_state or st.session_state['joined_gdf'].empty:
        st.error(translations[language]["error_no_data_download"])
        return
    joined_gdf = st.session_state['joined_gdf']
    with tempfile.TemporaryDirectory() as tmp_output_dir:
        progress_bar = st.progress(0)
        progress_text = st.empty()
        base_file_name = st.session_state.get('base_file_name', 'ZV_dati_data')
        processing_date = st.session_state.get('processing_date', datetime.datetime.now().strftime('%Y%m%d'))
        file_name_prefix = f"{base_file_name}_ZV_dati_{processing_date}"
        
        # Kadastra pamatinformācija
        st.markdown("### Kadastra pamatinformācija (kadastra apzīmējums, robeža):")
        
        total_steps = 6
        current_step = 0
        try:
            progress_text.text(translations[language].get("preparing_geojson", "1. Sagatavo GeoJSON failu..."))
            geojson_str = joined_gdf.to_json()
            if not geojson_str:
                st.error(translations[language]["error_display_pdf"].format(error="Failed to generate GeoJSON data."))
            else:
                geojson_bytes = geojson_str.encode('utf-8')
                st.download_button(
                    label="*.GeoJSON",
                    data=geojson_bytes,
                    file_name=f'{file_name_prefix}.geojson',
                    mime='application/geo+json'
                )
            current_step += 1
            progress_bar.progress(current_step / total_steps)
        except Exception as e:
            st.error(translations[language]["error_display_pdf"].format(error=str(e)))
        try:
            progress_text.text(translations[language].get("preparing_shapefile", "2. Sagatavo Shapefile ZIP failu..."))
            shp_output_path = os.path.join(tmp_output_dir, f'{file_name_prefix}.shp')
            joined_gdf.to_file(shp_output_path, encoding='utf-8')
            cpg_path = os.path.join(tmp_output_dir, f'{file_name_prefix}.cpg')
            with open(cpg_path, 'w') as cpg_file:
                cpg_file.write('UTF-8')
            prj_path = os.path.join(tmp_output_dir, f'{file_name_prefix}.prj')
            crs = joined_gdf.crs
            with open(prj_path, 'w') as prj_file:
                prj_file.write(crs.to_wkt())
            import zipfile
            shp_zip_path = os.path.join(tmp_output_dir, f'{file_name_prefix}_shp.zip')
            with zipfile.ZipFile(shp_zip_path, 'w') as zipf:
                for ext in ['shp', 'shx', 'dbf', 'prj', 'cpg']:
                    file_path = os.path.join(tmp_output_dir, f'{file_name_prefix}.{ext}')
                    if os.path.exists(file_path):
                        zipf.write(file_path, arcname=f'{file_name_prefix}.{ext}')
            with open(shp_zip_path, 'rb') as f:
                shp_zip_bytes = f.read()
            st.download_button(
                label="*.SHP",
                data=shp_zip_bytes,
                file_name=f'{file_name_prefix}_shp.zip',
                mime='application/zip'
            )
            current_step += 1
            progress_bar.progress(current_step / total_steps)
        except Exception as e:
            st.error(translations[language]["error_display_pdf"].format(error=str(e)))
        try:
            progress_text.text(translations[language].get("preparing_dxf", "3. Sagatavo DXF failu..."))
            dxf_output_path = os.path.join(tmp_output_dir, f'{file_name_prefix}.dxf')
            doc = ezdxf.new(dxfversion='R2010')
            doc.encoding = 'utf-8'
            if 'KKParcel' not in doc.layers:
                doc.layers.new(name='KKParcel', dxfattribs={'color': 0, 'linetype': 'Continuous', 'true_color': 0x00FFFF, 'lineweight': 1})
            if 'KKParcel_txt' not in doc.layers:
                doc.layers.new(name='KKParcel_txt', dxfattribs={'color': 0, 'linetype': 'Continuous', 'true_color': 0x00FFFF, 'lineweight': 1})
            if 'Tahoma' not in doc.styles:
                try:
                    doc.styles.new('Tahoma', dxfattribs={'font': 'Tahoma.ttf'})
                except:
                    st.error(translations[language]["warning_code_missing"])
                    raise
            msp = doc.modelspace()
            if 'code' not in joined_gdf.columns:
                st.warning(translations[language]["warning_code_missing"])
            else:
                for idx, row in joined_gdf.iterrows():
                    geom = row['geometry']
                    code_text = row['code']
                    if geom.type == 'Polygon':
                        exterior_coords = list(geom.exterior.coords)
                        msp.add_lwpolyline(exterior_coords, dxfattribs={'layer': 'KKParcel', 'lineweight': 1}, close=True)
                        for interior in geom.interiors:
                            interior_coords = list(interior.coords)
                            msp.add_lwpolyline(interior_coords, dxfattribs={'layer': 'KKParcel', 'lineweight': 1}, close=True)
                        rep_point = geom.representative_point()
                        text = msp.add_text(text=code_text, dxfattribs={'insert': (rep_point.x, rep_point.y), 'height': 1, 'style': 'Tahoma', 'layer': 'KKParcel_txt', 'lineweight': 1})
                        text.dxf.halign = TextHAlign.LEFT
                    elif geom.type == 'MultiPolygon':
                        for poly in geom.geoms:
                            exterior_coords = list(poly.exterior.coords)
                            msp.add_lwpolyline(exterior_coords, dxfattribs={'layer': 'KKParcel', 'lineweight': 1}, close=True)
                            for interior in poly.interiors:
                                interior_coords = list(interior.coords)
                                msp.add_lwpolyline(interior_coords, dxfattribs={'layer': 'KKParcel', 'lineweight': 1}, close=True)
                            rep_point = poly.representative_point()
                            text = msp.add_text(text=code_text, dxfattribs={'insert': (rep_point.x, rep_point.y), 'height': 1, 'style': 'Tahoma', 'layer': 'KKParcel_txt', 'lineweight': 1})
                            text.dxf.halign = TextHAlign.LEFT
            doc.saveas(dxf_output_path)
            with open(dxf_output_path, 'rb') as f:
                dxf_bytes = f.read()
            if dxf_bytes:
                st.download_button(
                    label="*.DXF",
                    data=dxf_bytes,
                    file_name=f'{file_name_prefix}.dxf',
                    mime='application/dxf'
                )
            else:
                st.error(translations[language]["error_display_pdf"].format(error="Failed to generate DXF file."))
            current_step += 1
            progress_bar.progress(current_step / total_steps)
        except Exception as e:
            st.error(translations[language]["error_display_pdf"].format(error=str(e)))
        st.markdown("### Kadastra pilnā informācija:")
        try:
            progress_text.text(translations[language].get("preparing_all_csv", "5. Sagatavo VISU CSV failu..."))
            all_data_df = joined_gdf.copy()
            all_data_df['geometry'] = all_data_df['geometry'].apply(lambda g: g.wkt if g else None)
            csv_str_all = all_data_df.to_csv(index=False, encoding='utf-8')
            if not csv_str_all:
                st.error(translations[language]["error_display_pdf"].format(error="Failed to generate ALL CSV data."))
            else:
                csv_bytes_all = csv_str_all.encode('utf-8')
                st.download_button(
                    label="*.XLSX (ekselis)",
                    data=csv_bytes_all,
                    file_name=f'{file_name_prefix}_all.csv',
                    mime='text/csv'
                )
            current_step += 1
            progress_bar.progress(current_step / total_steps)
        except Exception as e:
            st.error(translations[language]["error_display_pdf"].format(error=str(e)))
        try:
            progress_text.text(translations[language].get("preparing_all_excel", "6. Sagatavo VISU EXCEL failu..."))
            import io
            xls_data_df = joined_gdf.copy()
            xls_data_df['geometry'] = xls_data_df['geometry'].apply(lambda g: g.wkt if g else None)
            output_excel = io.BytesIO()
            with pd.ExcelWriter(output_excel, engine='xlsxwriter') as writer:
                xls_data_df.to_excel(writer, sheet_name='VisiDati', index=False)
            excel_bytes = output_excel.getvalue()
            st.download_button(
                label="*.CSV",
                data=excel_bytes,
                file_name=f"{file_name_prefix}_all.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            current_step += 1
            progress_bar.progress(current_step / total_steps)
        except Exception as e:
            st.error(translations[language]["error_display_pdf"].format(error=str(e)))
        progress_text.empty()
        progress_bar.empty()

# =============================================================================
# Meklēšana (ArcGIS FeatureServer) pēc "code" kolonnas
# =============================================================================
def geocode_address(address_text):
    # Šī funkcija veic vaicājumu ArcGIS FeatureServer, meklējot ierakstu, kura 'code' vērtība sakrīt ar ievadīto tekstu.
    if not address_text:
        return None, None, None, None
    try:
        arcgis_url_base = ("https://utility.arcgis.com/usrsvcs/servers/"
                           "4923f6b355934843b33aa92718520f12/rest/services/Hosted/"
                           "Kadastrs/FeatureServer/8/query")
        params = {
            'f': 'json',
            'where': f"code = '{address_text.strip()}'",
            'outFields': '*',
            'returnGeometry': 'true',
            'outSR': '3059'
        }
        query_url = f"{arcgis_url_base}?{urlencode(params)}"
        resp = requests.get(query_url)
        if resp.status_code != 200:
            st.error(f"ArcGIS REST query failed with status code {resp.status_code}")
            return None, None, None, None
        esri_data = resp.json()
        if 'features' not in esri_data or not esri_data['features']:
            st.error("Nav atrasts ieraksts ar šo kodu.")
            return None, None, None, None
        geojson_data = arcgis2geojson(esri_data)
        if 'features' not in geojson_data or not geojson_data['features']:
            st.error("Nav atrasts ieraksts ar šo kodu.")
            return None, None, None, None
        feature = geojson_data['features'][0]
        gdf = gpd.GeoDataFrame.from_features([feature], crs="EPSG:3059")
        centroid = gdf.geometry.centroid.iloc[0]
        return centroid.y, centroid.x, feature['geometry'], None
    except Exception as e:
        st.error(f"Kļūda kodu meklēšanā: {str(e)}")
        return None, None, None, None

# =============================================================================
# Galvenā lietotnes saskarne
# =============================================================================
def show_main_app():
    direct_pdf_url = "https://drive.google.com/uc?export=download&id=1jUh4Uq9svZsnAWCkN6VQHW1C0kp1wLws"
    col1, col2 = st.columns([3, 1])
    with col1:
        pass
    with col2:
        st.markdown(f'''<a href="{direct_pdf_url}" target="_blank" style="float: right; font-size: 22px; color: #CE2F2C;">
                      <strong>{translations[language]["instructions"]}</strong></a>''', unsafe_allow_html=True)
    st.title(translations[language]["title"])
    default_location = [56.946285, 24.105078]
    
    # Sadaļa 1: "Izvēlieties veidu, kā iegūt datus:"
    st.markdown("### " + translations[language]["radio_label"])
    if st.button(translations[language]["methods"][0]):
        st.session_state['input_option'] = "upload"
    if st.button(translations[language]["methods"][1]):
        st.session_state['input_option'] = "draw"
    
    # Sadaļa 2: "Meklēt pēc kadastra apzīmējuma un iegūt datus:"
    st.markdown("### Meklēt pēc kadastra apzīmējuma un iegūt datus:")
    if st.button(translations[language]["methods"][2]):
        st.session_state['input_option'] = "code"
    if st.button(translations[language]["methods"][3]):
        st.session_state['input_option'] = "code_with_adjacent"
    
    if 'input_option' not in st.session_state:
        st.info("Lūdzu, izvēlieties kādu no opcijām augstāk!")
        return
    
    option = st.session_state['input_option']
    if option == "upload":
        map_placeholder = st.empty()
        st.markdown(f"""{translations[language]["upload_instruction"]}  
        * **DXF** (.dxf)  
        * **SHP** (.shp, .shx, .dbf, .prj)""")
        uploaded_files = st.file_uploader(translations[language]["upload_files_label"],
                                            type=["shp", "shx", "dbf", "prj", "dxf"],
                                            accept_multiple_files=True)
        if uploaded_files:
            with tempfile.TemporaryDirectory() as tmpdirname:
                for uploaded_file in uploaded_files:
                    file_path = os.path.join(tmpdirname, uploaded_file.name)
                    with open(file_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                dxf_files = [os.path.join(tmpdirname, f.name) for f in uploaded_files if f.name.lower().endswith('.dxf')]
                if dxf_files:
                    polygon_dxf = dxf_files[0]
                    polygon_gdf = read_dxf_to_geodataframe(polygon_dxf)
                    if polygon_gdf.empty:
                        st.error(translations[language]["error_upload_dxf"])
                        polygon_gdf = None
                    else:
                        base_file_name = os.path.splitext(os.path.basename(dxf_files[0]))[0]
                        st.session_state['base_file_name'] = base_file_name
                else:
                    required_extensions = ['.shp', '.shx', '.dbf']
                    uploaded_extensions = [os.path.splitext(f.name)[1].lower() for f in uploaded_files]
                    if all(ext in uploaded_extensions for ext in required_extensions):
                        shp_files = [os.path.join(tmpdirname, f.name) for f in uploaded_files if f.name.lower().endswith('.shp')]
                        if shp_files:
                            polygon_shp = shp_files[0]
                            polygon_gdf = gpd.read_file(polygon_shp)
                            base_file_name = os.path.splitext(os.path.basename(shp_files[0]))[0]
                            st.session_state['base_file_name'] = base_file_name
                        else:
                            st.error(translations[language]["error_upload_shp"])
                            polygon_gdf = None
                    else:
                        st.error(translations[language]["error_display_pdf"].format(
                            error="Please upload the polygon in one of the selected file formats: DXF or SHP."
                        ))
                        polygon_gdf = None
            if polygon_gdf is not None:
                st.session_state['polygon_gdf'] = polygon_gdf
                process_input(polygon_gdf, input_method='upload')
                if st.session_state.get('data_ready', False):
                    st.success("Dati veiksmīgi iegūti!")
            else:
                st.error(translations[language]["error_display_pdf"].format(error="Could not load polygon from file."))
                m = folium.Map(location=default_location, zoom_start=7)
                with map_placeholder:
                    st_folium(m, width=700, height=500, key='upload_map')
        else:
            st.info(translations[language]["info_upload"])
            m = folium.Map(location=default_location, zoom_start=7)
            st_folium(m, width=700, height=500, key='upload_map')
    elif option == "draw":
        st.info(translations[language]["draw_instruction"])
        if 'map_center' not in st.session_state:
            st.session_state['map_center'] = [56.946285, 24.105078]
        if 'found_geometry' not in st.session_state:
            st.session_state['found_geometry'] = None
        if 'found_bbox' not in st.session_state:
            st.session_state['found_bbox'] = None
        with st.form(key='draw_form'):
            # Tagad meklēšana tiek veikta pēc "code" (ArcGIS FeatureServer)
            address_text = st.text_input(label=translations[language]["search_address"], value="")
            search_col, data_col = st.columns([1, 1])
            with search_col:
                search_button = st.form_submit_button(label=translations[language]["search_button"])
            with data_col:
                submit_button = st.form_submit_button(label=translations[language]["get_data_button"])
            if search_button and address_text.strip():
                # Veicam meklēšanu pēc "code"
                y, x, geom, _ = geocode_address(address_text.strip())
                if y is not None and x is not None:
                    st.session_state['map_center'] = [y, x]
                    st.session_state['found_geometry'] = geom
                    st.session_state['found_bbox'] = None
                else:
                    st.warning(translations[language]["search_error"])
            current_lat, current_lon = st.session_state['map_center']
            m = folium.Map(location=[current_lat, current_lon], zoom_start=10)
            wms_url = "https://lvmgeoserver.lvm.lv/geoserver/ows"
            wms_layers = {'Ortofoto': {'layers': 'public:Orto_LKS'},
                          'Kadastra karte': {'layers': 'publicwfs:Kadastra_karte'}}
            add_wms_layer(map_obj=m, url=wms_url, name=('Ortofoto' if language == "Latviešu" else 'Orthophoto'),
                          layers=wms_layers['Ortofoto']['layers'], overlay=False, opacity=1.0)
            add_wms_layer(map_obj=m, url=wms_url, name=('Kadastra karte' if language == "Latviešu" else 'Cadastral map'),
                          layers=wms_layers['Kadastra karte']['layers'], overlay=True, opacity=0.5)
            if st.session_state["found_geometry"]:
                folium.GeoJson(data=st.session_state["found_geometry"],
                               name="Atrastais poligons (ArcGIS)",
                               style_function=lambda x: {"color": "green", "fillOpacity": 0.2}).add_to(m)
            drawnItems = folium.FeatureGroup(name="Drawn Items")
            drawnItems.add_to(m)
            draw = Draw(draw_options={'polyline': False, 'polygon': True, 'circle': False, 'rectangle': False,
                                        'marker': False, 'circlemarker': False},
                         edit_options={'edit': False, 'remove': True}, feature_group=drawnItems)
            draw.add_to(m)
            folium.LayerControl().add_to(m)
            m.get_root().add_child(CustomDeleteButton())
            map_key = f"draw_map_{current_lat:.5f}_{current_lon:.5f}"
            output = st_folium(m, width=700, height=500, key=map_key)
            if submit_button:
                if output and 'all_drawings' in output and output['all_drawings']:
                    last_drawing = output['all_drawings'][-1]
                    polygon_gdf = gpd.GeoDataFrame.from_features([last_drawing], crs='EPSG:4326')
                    st.session_state['polygon_gdf'] = polygon_gdf
                    process_input(polygon_gdf, input_method='drawn')
                    if st.session_state.get('data_ready', False):
                        st.success("Dati veiksmīgi iegūti!")
                        st.session_state['base_file_name'] = 'polygon'
                else:
                    st.error(translations[language]["info_draw"])
    elif option == "code":
        st.info(translations[language]["info_enter_code"])
        with st.form(key='code_form'):
            codes_input = st.text_input(label=translations[language]["enter_codes_label"], value="")
            process_codes = st.form_submit_button(label=translations[language]["process_codes_button"])
            if process_codes:
                if not codes_input.strip():
                    st.error(translations[language]["error_no_codes_entered"])
                else:
                    codes = [code.strip() for code in codes_input.split(',') if code.strip()]
                    if not codes:
                        st.error(translations[language]["error_no_codes_entered"])
                    else:
                        max_codes_in_filename = 5
                        display_codes = "_".join(codes) if len(codes) <= max_codes_in_filename else "_".join(codes[:max_codes_in_filename]) + f"_{len(codes)}_codi"
                        st.session_state['base_file_name'] = display_codes
                        process_input(codes, input_method='code')
        if st.session_state.get('data_ready', False) and st.session_state['input_method'] == 'code':
            display_map_with_results()
            display_download_buttons()
    elif option == "code_with_adjacent":
        st.info(translations[language]["info_code_filter"])
        with st.form(key='code_with_adjacent_form'):
            codes_input = st.text_input(label=translations[language]["enter_codes_label"], value="")
            process_codes = st.form_submit_button(label=translations[language]["process_codes_button"])
            if process_codes:
                if not codes_input.strip():
                    st.error(translations[language]["error_no_codes_entered"])
                else:
                    codes = [code.strip() for code in codes_input.split(',') if code.strip()]
                    if not codes:
                        st.error(translations[language]["error_no_codes_entered"])
                    else:
                        max_codes_in_filename = 5
                        display_codes = "_".join(codes) if len(codes) <= max_codes_in_filename else "_".join(codes[:max_codes_in_filename]) + f"_{len(codes)}_codi"
                        st.session_state['base_file_name'] = display_codes
                        process_input(codes, input_method='code_with_adjacent')
        if st.session_state.get('data_ready', False) and st.session_state['input_method'] == 'code_with_adjacent':
            display_map_with_results()
            display_download_buttons()
    if st.session_state.get('data_ready', False) and st.session_state['input_option'] not in ["code", "code_with_adjacent"]:
        display_map_with_results()
        display_download_buttons()
    
    st.markdown("<div style='text-align: center; margin-top: 20px; color: gray;'>© 2024 METRUM</div>", unsafe_allow_html=True)

# =============================================================================
# main() - Galvenā programma
# =============================================================================
def main():
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    if 'username_logged' not in st.session_state:
        st.session_state.username_logged = ''
    if not st.session_state.logged_in:
        show_login()
    else:
        show_main_app()

if __name__ == '__main__':
    main()

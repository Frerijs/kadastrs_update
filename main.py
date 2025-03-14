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
from shapely.ops import linemerge, polygonize, unary_union, transform
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
import shapely.geometry
from shapely.geometry import mapping
from pyproj import Transformer

# -------------------------------------------------------------------------
# ----------------------- Supabase konfigurācija ---------------------------
# -------------------------------------------------------------------------
supabase_url = "https://uhwbflqdripatfpbbetf.supabase.co"
supabase_key = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InVod2JmbHFkcmlwYXRmcGJiZXRmIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTczMDcxODE2MywiZXhwIjoyMDQ2Mjk0MTYzfQ."
    "78wsNZ4KBg2l6zeZ1ZknBBooe0PeLtJzRU-7eXo3WTk"
)

# -------------------------------------------------------------------------
# ----------------------- ArcGIS FeatureServer URL -------------------------
# -------------------------------------------------------------------------
arcgis_url_base = (
    "https://utility.arcgis.com/usrsvcs/servers/"
    "4923f6b355934843b33aa92718520f12/rest/services/Hosted/"
    "Kadastrs/FeatureServer/8/query"
)

# -------------------------------------------------------------------------
# --------------------------- Konstantes / Info ----------------------------
# -------------------------------------------------------------------------
APP_NAME = "Kadastrs"
APP_VERSION = "4.0"
APP_TYPE = "web"

# -------------------------------------------------------------------------
# ----------------------- Tulkošanas vārdnīca -----------------------------
# -------------------------------------------------------------------------
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
        "download_all_csv": "*.CSV",
        "download_all_excel": "*.XLSX (ekselis)",
        "logout": "Iziet",
        "success_logout": "Veiksmīgi izgājāt no konta.",
        "error_authenticate": "Kļūda autentificējot lietotāju: {status_code}",
        "error_login": "Nepareizs lietotājvārds vai parole.",
        "error_upload_dxf": "DXF failā netika atrastas derīgas ģeometrijas.",
        "error_upload_shp": "Netika atrasts .shp fails starp augšupielādētajiem failiem.",
        "error_no_data_download": "Nav pieejami dati lejupielādei.",
        "error_display_pdf": "Kļūda: {error}",
        "info_upload": "Lūdzu, augšupielādējiet failu ar poligonu.",
        "info_draw": "Lūdzu, uzzīmējiet poligonu uz kartes.",
        "info_enter_code": "Lūdzu, ievadiet vienu vai vairākus kadastra apzīmējumus, atdalot ar komatu. Vai augšupielādējiet *.txt failu ar atdalītājiem . , ; : vai atstarpe.",
        "preparing_geojson": "1. Sagatavo GeoJSON failu...",
        "preparing_shapefile": "2. Sagatavo Shapefile ZIP failu...",
        "preparing_dxf": "3. Sagatavo DXF failu...",
        "preparing_csv": "4. Sagatavo CSV failu...",
        "preparing_all_csv": "5. Sagatavo VISU CSV failu...",
        "preparing_all_excel": "6. Sagatavo VISU EXCEL failu...",
        "warning_code_missing": "Kadastra apzīmējums nav pieejams datos. Teksts netiks pievienots DXF failā.",
        "instructions": "Instrukcija",
        "search_address": "Meklēt adresi",
        "search_code": "Meklēšana (pēc kadastra apzīmējuma)",
        "search_button": "Meklēt",
        "search_error": "Neizdevās atrast datus pēc norādītā koda.",
        "enter_codes_label": "Ievadiet kadastra apzīmējumus (piemērs: 84960050005, 84960050049):",
        "process_codes_button": "Apstrādāt kodus",
        "error_no_codes_entered": "Nav ievadīti kadastra apzīmējumi. Lūdzu, ievadiet vienu vai vairākus kadastra apzīmējumus.",
        "error_no_data_found": "Nav atrasti dati ar norādītajiem kadastra numuriem.",
        "info_code_filter": "Dati tiek iegūti gan par norādītajiem kadastra apzīmējumiem, gan pierobežniekiem.",
        "upload_txt_label": "TXT fails ar kadastra apzīmējumiem (atdalītāji: . , ; : vai atstarpe)"
    },
    "English": {
        "radio_label": "Select the method to obtain data:",
        "methods": [
            "Upload a pre-prepared closed contour file in .DXF or .SHP format",
            "Draw a closed contour on the map",
            "Only for the entered cadastral numbers",
            "For the entered cadastral numbers and neighbors"
        ],
        "title": "Download of Cadastral Number List (ZV Boundaries and Designations)",
        "language_label": "Language / Valoda",
        "upload_instruction": "Upload a closed contour or multiple contours in one of the supported file formats:",
        "upload_files_label": "Upload the required files:",
        "draw_instruction": "Draw a closed contour on the map and click the 'Get Data' button.",
        "get_data_button": "Get Data",
        "download_geojson": "*.GeoJSON",
        "download_shapefile": "*.SHP",
        "download_dxf": "*.DXF",
        "download_csv": "*.CSV",
        "download_all_csv": "*.CSV",
        "download_all_excel": "*.XLSX (Excel)",
        "logout": "Logout",
        "success_logout": "Successfully logged out.",
        "error_authenticate": "Error authenticating user: {status_code}",
        "error_login": "Incorrect username or password.",
        "error_upload_dxf": "No valid geometries were found in the DXF file.",
        "error_upload_shp": "The .shp file was not found among the uploaded files.",
        "error_no_data_download": "No data available for download.",
        "error_display_pdf": "Error: {error}",
        "info_upload": "Please upload a file with a polygon.",
        "info_draw": "Please draw a polygon on the map.",
        "info_enter_code": "Please enter one or more cadastral numbers, separated by commas. Or upload a *.txt file with delimiters . , ; : or space.",
        "preparing_geojson": "1. Preparing the GeoJSON file...",
        "preparing_shapefile": "2. Preparing the Shapefile ZIP file...",
        "preparing_dxf": "3. Preparing the DXF file...",
        "preparing_csv": "4. Preparing the CSV file...",
        "preparing_all_csv": "5. Preparing the complete CSV file...",
        "preparing_all_excel": "6. Preparing the complete Excel file...",
        "warning_code_missing": "The cadastral number is not available in the data. The text will not be added to the DXF file.",
        "instructions": "Instructions",
        "search_address": "Search address",
        "search_code": "Search (by cadastral number)",
        "search_button": "Search",
        "search_error": "No data found for the provided code.",
        "enter_codes_label": "Enter cadastral numbers (e.g., 84960050005, 84960050049):",
        "process_codes_button": "Process codes",
        "error_no_codes_entered": "No cadastral numbers entered. Please enter one or more cadastral numbers.",
        "error_no_data_found": "No data found for the provided cadastral numbers.",
        "info_code_filter": "Data is obtained for both the provided cadastral numbers and their neighbors.",
        "upload_txt_label": "TXT file with cadastral numbers (delimiters: . , ; : or space)"
    }
}

# -------------------------------------------------------------------------
# --------------------- Streamlit lapas iestatījumi ------------------------
# -------------------------------------------------------------------------
st.set_page_config(
    page_title=translations["Latviešu"]["title"],
    layout="centered"
)

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

# -------------------------------------------------------------------------
# ----------------------- Palīgfunkcijas ----------------------------------
# -------------------------------------------------------------------------
def reproject_geometry(geom, src_crs="EPSG:3059", dst_crs="EPSG:4326"):
    """Pārvērš ģeometriju no EPSG:3059 uz EPSG:4326"""
    transformer = Transformer.from_crs(src_crs, dst_crs, always_xy=True)
    return transform(transformer.transform, geom)

def format_geojson_geometry(geom):
    """Pārvērš GeoJSON-līdzīgu objektu par derīgu shapely un atpakaļ par geojson mapping."""
    try:
        if isinstance(geom, dict) and "type" in geom and "coordinates" in geom:
            return geom
        shape_obj = shapely.geometry.shape(geom)
        return mapping(shape_obj)
    except Exception as e:
        st.error(f"Error formatting geometry: {e}")
        return None

# -------------------------------------------------------------------------
# --------------------- Leaflet kontrolis (dzēš poligonus) ----------------
# -------------------------------------------------------------------------
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

# -------------------------------------------------------------------------
# ------------------------ Autentifikācija ---------------------------------
# -------------------------------------------------------------------------
def authenticate(username, password):
    """Pamata Supabase DEMO lietotāju autentifikācija."""
    try:
        headers = {
            "apikey": supabase_key,
            "Authorization": f"Bearer {supabase_key}",
            "Content-Type": "application/json",
        }
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
    """Pieraksta lietotāja login Supabase DB (DEMO)."""
    try:
        riga_tz = ZoneInfo('Europe/Riga')
        current_time = datetime.datetime.now(riga_tz).isoformat()
        data = {
            "username": username,
            "App": APP_NAME,
            "Ver": APP_VERSION,
            "app_type": APP_TYPE,
            "login_time": current_time
        }
        headers = {
            "apikey": supabase_key,
            "Authorization": f"Bearer {supabase_key}",
            "Content-Type": "application/json"
        }
        url = f"{supabase_url}/rest/v1/user_data"
        response = requests.post(url, json=data, headers=headers)
        if response.status_code not in [200, 201]:
            st.error(
                translations[language]["error_authenticate"].format(status_code=response.status_code) +
                f", {response.text}"
            )
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
    """Attēlo login formu, ja lietotājs vēl nav ielogojies."""
    st.title(translations[language]["title"])
    with st.form(key='login_form'):
        username = st.text_input("Lietotājvārds" if language == "Latviešu" else "Username", key='username')
        password = st.text_input("Parole" if language == "Latviešu" else "Password", type="password", key='password')
        st.form_submit_button(label=("Pieslēgties" if language == "Latviešu" else "Login"), on_click=login)
    st.markdown("<div style='text-align: center; margin-top: 20px; color: gray;'>© 2024 METRUM</div>", unsafe_allow_html=True)

# -------------------------------------------------------------------------
# --------------------- PDF attēlošana (ja vajag) -------------------------
# -------------------------------------------------------------------------
def display_pdf(file_path):
    """Ja vajag, var rādīt PDF saturu iebūvētā rāmī."""
    try:
        with open(file_path, "rb") as f:
            base64_pdf = base64.b64encode(f.read()).decode('utf-8')
        pdf_display = f'''
            <iframe src="data:application/pdf;base64,{base64_pdf}" width="700" height="1000" type="application/pdf">
                <p>{translations[language]["error_display_pdf"].format(error="")} 
                <a href="data:application/pdf;base64,{base64_pdf}">{translations[language]["download_dxf"]}</a>.</p>
            </iframe>
        '''
        st.markdown(pdf_display, unsafe_allow_html=True)
    except FileNotFoundError:
        st.error(f"{translations[language]['error_display_pdf'].format(error='PDF file not found.')}: {file_path}")
    except Exception as e:
        st.error(translations[language]["error_display_pdf"].format(error=str(e)))

# -------------------------------------------------------------------------
# ------------------- ArcGIS vaicājuma palīgfunkcija -----------------------
# -------------------------------------------------------------------------
def fetch_arcgis_data_with_pagination(params, chunk_size=2000):
    """
    Veic atkārtotus pieprasījumus ArcGIS FeatureServer (līdz brīdim,
    kamēr netiek atgriezts viss rezultātu kopums).
    """
    all_features = []
    offset = 0

    while True:
        # Papildinām params ar paginācijas parametriem
        params["resultOffset"] = offset
        params["resultRecordCount"] = chunk_size

        query_url = f"{arcgis_url_base}?{urlencode(params)}"
        resp = requests.get(query_url)
        if resp.status_code != 200:
            st.error(f"ArcGIS REST query failed with status code {resp.status_code}")
            break

        data = resp.json()
        if "features" not in data:
            break

        features = data["features"]
        all_features.extend(features)

        # Ja serveris norāda, ka ir vairāk datu, turpinām palielinot offset
        if data.get("exceededTransferLimit"):
            offset += chunk_size
        else:
            break

    # Atgriežam vienu lielu GeoJSON-līdzīgu dict ar "features"
    data["features"] = all_features
    return data

# -------------------------------------------------------------------------
# --------------------- DXF -> GeoDataFrame --------------------------------
# -------------------------------------------------------------------------
def read_dxf_to_geodataframe(dxf_file_path):
    """Nolasa DXF failu un mēģina izveidot poligonu GDF no tajā esošajām ģeometrijām."""
    try:
        doc = ezdxf.readfile(dxf_file_path)
        msp = doc.modelspace()
        geometries = []

        def to_2d(coords):
            if isinstance(coords, tuple):
                return coords[0], coords[1]
            return [(x, y) for x, y, *_ in coords]

        for entity in msp:
            if entity.dxftype() == 'LINE':
                start = entity.dxf.start
                end = entity.dxf.end
                line = LineString([to_2d((start.x, start.y, start.z)), to_2d((end.x, end.y, end.z))])
                geometries.append(line)
            elif entity.dxftype() == 'LWPOLYLINE':
                points = [to_2d(point) for point in entity.get_points()]
                if entity.closed:
                    geometries.append(Polygon(points))
                else:
                    geometries.append(LineString(points))
            elif entity.dxftype() == 'POLYLINE':
                points = []
                for vertex in entity.vertices:
                    location = vertex.dxf.location
                    points.append(to_2d((location.x, location.y, location.z)))
                if entity.is_closed:
                    geometries.append(Polygon(points))
                else:
                    geometries.append(LineString(points))
            elif entity.dxftype() == 'CIRCLE':
                center = to_2d((entity.dxf.center.x, entity.dxf.center.y, entity.dxf.center.z))
                radius = entity.dxf.radius
                circle = Point(center).buffer(radius)
                geometries.append(circle)
            elif entity.dxftype() == 'ARC':
                center = entity.dxf.center
                radius = entity.dxf.radius
                start_angle = np.radians(entity.dxf.start_angle)
                end_angle = np.radians(entity.dxf.end_angle)
                theta = np.linspace(start_angle, end_angle, 100)
                arc_points = [(center.x + radius * np.cos(angle), center.y + radius * np.sin(angle)) for angle in theta]
                geometries.append(LineString(arc_points))
            elif entity.dxftype() == '3DFACE':
                vertices = [
                    (entity.dxf.vtx0.x, entity.dxf.vtx0.y, entity.dxf.vtx0.z),
                    (entity.dxf.vtx1.x, entity.dxf.vtx1.y, entity.dxf.vtx1.z),
                    (entity.dxf.vtx2.x, entity.dxf.vtx2.y, entity.dxf.vtx2.z)
                ]
                if entity.dxf.hasattr("vtx3"):
                    vertices.append((entity.dxf.vtx3.x, entity.dxf.vtx3.y, entity.dxf.vtx3.z))
                vertices_2d = to_2d(vertices)
                geometries.append(Polygon(vertices_2d))

        # Pārvēršam slēgtas līnijas par poligoniem
        converted_geometries = []
        for geom in geometries:
            if isinstance(geom, LineString) and geom.is_ring:
                converted_geometries.append(Polygon(geom.coords))
            else:
                converted_geometries.append(geom)
        geometries = converted_geometries

        # Apvienojam linijas, ja tādas ir, lai veidotos poligoni
        lines = [geom for geom in geometries if isinstance(geom, LineString)]
        if lines:
            multiline = linemerge(lines)
            polygons = list(polygonize(multiline))
            geometries.extend(polygons)

        polygons = [geom for geom in geometries if isinstance(geom, (Polygon, MultiPolygon))]
        if polygons:
            unified_geometry = unary_union(polygons)
        else:
            unified_geometry = None

        if unified_geometry:
            return gpd.GeoDataFrame(geometry=[unified_geometry], crs="EPSG:3059")
        else:
            st.error(translations[language]["error_upload_dxf"])
            return gpd.GeoDataFrame()

    except Exception as e:
        st.error(translations[language]["error_display_pdf"].format(error=str(e)))
        return gpd.GeoDataFrame()

# -------------------------------------------------------------------------
# -------------------- WMS slāņa pievienošana kartei -----------------------
# -------------------------------------------------------------------------
def add_wms_layer(map_obj, url, name, layers, overlay=True, opacity=1.0):
    """Pievieno WMS slāni folium kartei."""
    try:
        folium.WmsTileLayer(
            url=url,
            name=name,
            layers=layers,
            format='image/png',
            transparent=True,
            version='1.3.0',
            overlay=overlay,
            control=True,
            opacity=opacity
        ).add_to(map_obj)
    except Exception as e:
        st.error(f"Failed to add {name} layer: {e}")

# -------------------------------------------------------------------------
# ----------------------- Meklēšana pēc viena koda ------------------------
# -------------------------------------------------------------------------
def search_by_code(code_text):
    """Meklē konkrētu 'code' ArcGIS servisā, atgriež koordinātes, geojson un bounding box."""
    if not code_text:
        return None, None, None, None, None
    try:
        params = {
            'f': 'json',
            'outFields': '*',
            'returnGeometry': 'true',
            'outSR': '3059',
            'where': f"code = '{code_text}'"
        }
        data = fetch_arcgis_data_with_pagination(params, chunk_size=2000)
        if 'features' not in data or not data['features']:
            st.warning(translations[language]["search_error"])
            return None, None, None, None, None

        geojson_data = arcgis2geojson(data)
        if 'features' not in geojson_data or not geojson_data['features']:
            st.warning(translations[language]["search_error"])
            return None, None, None, None, None

        feature = geojson_data['features'][0]
        geometry = feature.get("geometry")
        if not geometry:
            return None, None, None, None, None

        # Formatējam -> shapely -> reprojekcija -> mapping
        formatted_geom = format_geojson_geometry(geometry)
        shape_obj = shapely.geometry.shape(formatted_geom)
        shape_reproj = reproject_geometry(shape_obj, src_crs="EPSG:3059", dst_crs="EPSG:4326")
        geojson_reproj = mapping(shape_reproj)
        centroid = shape_reproj.centroid
        bounds = shape_reproj.bounds  # (minx, miny, maxx, maxy)

        found_code = feature.get("properties", {}).get("code", None)
        return centroid.y, centroid.x, geojson_reproj, bounds, found_code

    except Exception as e:
        st.error(f"Error in search_by_code: {e}")
        return None, None, None, None, None

# -------------------------------------------------------------------------
# ---------- Palīgfunkcija .txt failu ar code sarakstu parsēšanai ---------
# -------------------------------------------------------------------------
def parse_uploaded_codes(txt_content: str) -> list:
    """
    TXT failā var būt kadastra kodi, atdalīti ar . , ; : vai atstarpēm.
    Pārveido visus atdalītājus uz komatu un sadala.
    """
    for delim in [".", ",", ";", ":", " "]:
        txt_content = txt_content.replace(delim, ",")
    codes = [c.strip() for c in txt_content.split(",") if c.strip()]
    return codes

# -------------------------------------------------------------------------
# -------- JAUNĀ Palīgfunkcija - chunk pieeja garam code sarakstam --------
# -------------------------------------------------------------------------
def fetch_code_features(codes_list, chunk_size=50):
    """
    Meklē kadastra apzīmējumus 'codes_list' ArcGIS servisā,
    sadalot tos pa gabaliņiem (chunk) ar izmēru 'chunk_size=50',
    lai nepārsniegtu ArcGIS atļauto limitu vienā pieprasījumā.
    (Ja vajag, var mainīt chunk_size.)
    """
    import math
    from arcgis2geojson import arcgis2geojson

    all_features_gdf = gpd.GeoDataFrame()
    total_codes = len(codes_list)
    chunks_count = math.ceil(total_codes / chunk_size)

    for i in range(chunks_count):
        start_idx = i * chunk_size
        end_idx = start_idx + chunk_size
        codes_chunk = codes_list[start_idx:end_idx]

        sanitized_codes = [code.strip().replace("'", "''") for code in codes_chunk]
        codes_str = ",".join([f"'{code}'" for code in sanitized_codes])

        params = {
            'f': 'json',
            'outFields': '*',
            'returnGeometry': 'true',
            'outSR': '3059',
            'where': f"code IN ({codes_str})"
        }

        # Izmantojam to pašu paginācijas funkciju, ja ArcGIS atgriež daudz ierakstu
        esri_data = fetch_arcgis_data_with_pagination(params, chunk_size=2000)
        if not esri_data.get('features'):
            continue

        geojson_data = arcgis2geojson(esri_data)
        if not geojson_data.get('features'):
            continue

        chunk_gdf = gpd.GeoDataFrame.from_features(geojson_data["features"])
        if chunk_gdf.crs is None:
            chunk_gdf.crs = "EPSG:3059"
        else:
            chunk_gdf = chunk_gdf.to_crs(epsg=3059)

        if all_features_gdf.empty:
            all_features_gdf = chunk_gdf
        else:
            all_features_gdf = pd.concat([all_features_gdf, chunk_gdf], ignore_index=True)

    if not all_features_gdf.empty:
        if 'objectid' in all_features_gdf.columns:
            all_features_gdf.drop_duplicates(subset=['objectid', 'code'], inplace=True, ignore_index=True)
        else:
            all_features_gdf.drop_duplicates(subset=['code'], inplace=True, ignore_index=True)

    return all_features_gdf

# -------------------------------------------------------------------------
# --------------------- process_input funkcija ----------------------------
# -------------------------------------------------------------------------
def process_input(input_data, input_method):
    """
    Galvenā funkcija, kas apstrādā ievadīto poligonu (upload/draw)
    vai kadastra kodus (code/code_with_adjacent) un pēc tam iegūst
    atbilstošos datus no ArcGIS FeatureServer.
    """
    try:
        progress_bar = st.progress(0)
        progress_text = st.empty()

        st.session_state['input_method'] = input_method
        progress_text.text(translations[language].get("preparing_geojson", "1. Sagatavo GeoJSON failu..."))

        # --- 1) Ja "upload" vai "drawn" -> Envelope meklēšana ---------------
        if input_method in ['upload', 'drawn']:
            polygon_gdf = input_data.to_crs(epsg=3059)
            minx, miny, maxx, maxy = polygon_gdf.total_bounds
            geometry = {
                "xmin": minx,
                "ymin": miny,
                "xmax": maxx,
                "ymax": maxy,
                "spatialReference": {"wkid": 3059}
            }
            params = {
                'f': 'json',
                'outFields': '*',
                'returnGeometry': 'true',
                'outSR': '3059',
                'spatialRel': 'esriSpatialRelIntersects',
                'where': '1=1',
                'geometry': json.dumps(geometry),
                'geometryType': 'esriGeometryEnvelope',
                'inSR': '3059',
                'outSR': '3059'
            }

            # Izmantojam paginācijas funkciju, lai iegūtu *visus* poligonus
            esri_data = fetch_arcgis_data_with_pagination(params, chunk_size=2000)
            progress_bar.progress(20)

            if not esri_data.get('features'):
                st.error(translations[language]["error_no_data_found"])
                st.session_state['data_ready'] = False
                return

            geojson_data = arcgis2geojson(esri_data)
            if not geojson_data.get('features'):
                st.error(translations[language]["error_no_data_found"])
                st.session_state['data_ready'] = False
                return

            arcgis_gdf = gpd.GeoDataFrame.from_features(geojson_data["features"])
            if arcgis_gdf.crs is None:
                arcgis_gdf.crs = "EPSG:3059"
            else:
                arcgis_gdf = arcgis_gdf.to_crs(epsg=3059)
            progress_bar.progress(40)

            # Filtrējam tikai tos, kas tiešām krustojas ar ielādēto poligonu
            input_union = unary_union(polygon_gdf.geometry)
            arcgis_gdf = arcgis_gdf[arcgis_gdf.geometry.apply(lambda g: g.intersects(input_union))]

            st.session_state['joined_gdf'] = arcgis_gdf
            st.session_state['data_ready'] = True
            current_time = datetime.datetime.now(ZoneInfo('Europe/Riga'))
            st.session_state['processing_date'] = current_time.strftime('%Y%m%d')

            progress_text.empty()
            progress_bar.progress(100)

        # --- 2) Ja "code" vai "code_with_adjacent" -> chunk pieeja -----------
        elif input_method in ['code', 'code_with_adjacent']:
            codes = input_data  # ievadītie + no .txt faila

            filtered_gdf = fetch_code_features(codes, chunk_size=50)
            progress_bar.progress(30)

            if filtered_gdf.empty:
                st.error(translations[language]["error_no_data_found"])
                st.session_state['data_ready'] = False
                return

            missing_codes = set(codes) - set(filtered_gdf['code'].unique())

            if input_method == 'code_with_adjacent':
                union_geometry = unary_union(filtered_gdf.geometry)
                bminx, bminy, bmaxx, bmaxy = union_geometry.bounds
                adjacent_params = {
                    'f': 'json',
                    'outFields': '*',
                    'returnGeometry': 'true',
                    'outSR': '3059',
                    'spatialRel': 'esriSpatialRelIntersects',
                    'geometry': json.dumps({
                        "xmin": bminx,
                        "ymin": bminy,
                        "xmax": bmaxx,
                        "ymax": bmaxy,
                        "spatialReference": {"wkid": 3059}
                    }),
                    'geometryType': 'esriGeometryEnvelope',
                    'inSR': '3059',
                    'outSR': '3059'
                }

                esri_adjacent_data = fetch_arcgis_data_with_pagination(adjacent_params, chunk_size=2000)
                if not esri_adjacent_data.get('features'):
                    st.error(translations[language]["error_no_data_found"])
                    st.session_state['data_ready'] = False
                    return

                geojson_adjacent_data = arcgis2geojson(esri_adjacent_data)
                adjacent_gdf = gpd.GeoDataFrame.from_features(geojson_adjacent_data)
                if adjacent_gdf.crs is None:
                    adjacent_gdf.crs = "EPSG:3059"
                else:
                    adjacent_gdf = adjacent_gdf.to_crs(epsg=3059)

                # Filtrējam tos, kas reāli pieskaras (touches) norādīto poligonu union
                adjacent_gdf = adjacent_gdf[adjacent_gdf.geometry.touches(union_geometry)]
                if adjacent_gdf.empty:
                    st.warning(translations[language]["error_no_data_found"])
                    st.session_state['data_ready'] = False
                    return

                combined_gdf = pd.concat([filtered_gdf, adjacent_gdf], ignore_index=True).drop_duplicates()
                joined_gdf = combined_gdf.reset_index(drop=True).fillna('')
            else:
                joined_gdf = filtered_gdf.copy()

            progress_bar.progress(60)

            if not joined_gdf.empty:
                invalid_geometries = ~joined_gdf.is_valid
                if invalid_geometries.any():
                    joined_gdf['geometry'] = joined_gdf['geometry'].buffer(0)

            max_codes_in_filename = 5
            if len(codes) > max_codes_in_filename:
                display_codes = "_".join(codes[:max_codes_in_filename]) + f"_{len(codes)}_codi"
            else:
                display_codes = "_".join(codes)
            st.session_state['base_file_name'] = display_codes

            if missing_codes:
                st.warning(
                    f"Nav atrasti dati ar norādītajiem kadastra apzīmējumiem: {', '.join(missing_codes)}"
                )

            current_time = datetime.datetime.now(ZoneInfo('Europe/Riga'))
            st.session_state['processing_date'] = current_time.strftime('%Y%m%d')
            st.session_state['joined_gdf'] = joined_gdf
            st.session_state['data_ready'] = True
            progress_text.empty()
            progress_bar.progress(100)

        else:
            st.error("Nepazīstams input_method!")
            st.session_state['data_ready'] = False

    except Exception as e:
        st.error(translations[language]["error_display_pdf"].format(error=str(e)))
        st.session_state['data_ready'] = False

# -------------------------------------------------------------------------
# --------------------- Kartes attēlošana ar rezultātiem ------------------
# -------------------------------------------------------------------------
def display_map_with_results():
    """Ja dati ir iegūti, attēlo tos kartē."""
    if 'joined_gdf' not in st.session_state or st.session_state['joined_gdf'].empty:
        st.warning(translations[language]["error_no_data_found"])
        return

    joined_gdf = st.session_state.joined_gdf.to_crs(epsg=4326)
    m = folium.Map(location=[56.946285, 24.105078], zoom_start=7)

    tooltip_field = ('Kadastra apzīmējums:' if language == "Latviešu" else "Cadastral identifier:")
    if 'polygon_gdf' in st.session_state:
        polygon_gdf = st.session_state.polygon_gdf.to_crs(epsg=4326)
        folium.GeoJson(
            polygon_gdf,
            name=('Ievadītais poligons' if language=="Latviešu" else 'Input polygon'),
            style_function=lambda x: {'fillColor': 'none', 'color': 'red', 'weight': 3}
        ).add_to(m)

    folium.GeoJson(
        joined_gdf,
        name=('Atlasītie poligoni' if language == "Latviešu" else 'Selected polygons'),
        tooltip=folium.GeoJsonTooltip(fields=['code'], aliases=[tooltip_field]),
        style_function=lambda x: {'color': 'blue', 'fillOpacity': 0.1, 'weight': 2}
    ).add_to(m)

    folium.LayerControl().add_to(m)

    if not joined_gdf.empty:
        bounds = joined_gdf.total_bounds  # (minx, miny, maxx, maxy)
        sw = [bounds[1], bounds[0]]
        ne = [bounds[3], bounds[2]]
        m.fit_bounds([sw, ne])

    st_folium(m, width=700, height=500, key='result_map')

# -------------------------------------------------------------------------
# ----------------------- Lejupielādes pogas ------------------------------
# -------------------------------------------------------------------------
def display_download_buttons():
    """Piedāvā lejupielādēt sagatavotos failus (GeoJSON, SHP, DXF, CSV, XLSX)."""
    if 'joined_gdf' not in st.session_state or st.session_state['joined_gdf'].empty:
        st.error(translations[language]["error_no_data_download"])
        return

    joined_gdf = st.session_state['joined_gdf']

    with tempfile.TemporaryDirectory() as tmp_output_dir:
        total_steps = 7
        current_step = 0
        progress_bar = st.progress(0)
        progress_text = st.empty()

        base_file_name = st.session_state.get('base_file_name', 'ZV_dati_data')
        processing_date = st.session_state.get('processing_date', datetime.datetime.now().strftime('%Y%m%d'))
        file_name_prefix = f"{base_file_name}_ZV_dati_{processing_date}"

        # --- 1) GEOJSON ---
        st.markdown("### Kadastra pamatinformācija (kadastra apzīmējums, robeža):")
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

        # --- 2) SHAPEFILE ZIP ---
        try:
            progress_text.text(translations[language].get("preparing_shapefile", "2. Sagatavo Shapefile ZIP failu..."))
            shp_output_path = os.path.join(tmp_output_dir, f'{file_name_prefix}.shp')
            joined_gdf.to_file(shp_output_path, encoding='utf-8')

            # Pievieno .cpg un .prj
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

        # --- 3) DXF ---
        try:
            progress_text.text(translations[language].get("preparing_dxf", "3. Sagatavo DXF failu..."))
            dxf_output_path = os.path.join(tmp_output_dir, f'{file_name_prefix}.dxf')
            doc = ezdxf.new(dxfversion='R2010')
            doc.encoding = 'utf-8'

            if 'KKParcel' not in doc.layers:
                doc.layers.new(name='KKParcel', dxfattribs={
                    'color': 0, 'linetype': 'Continuous', 'true_color': 0x00FFFF, 'lineweight': 1
                })
            if 'KKParcel_txt' not in doc.layers:
                doc.layers.new(name='KKParcel_txt', dxfattribs={
                    'color': 0, 'linetype': 'Continuous', 'true_color': 0x00FFFF, 'lineweight': 1
                })

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
                        text = msp.add_text(
                            text=code_text,
                            dxfattribs={
                                'insert': (rep_point.x, rep_point.y),
                                'height': 1,
                                'style': 'Tahoma',
                                'layer': 'KKParcel_txt',
                                'lineweight': 1
                            }
                        )
                        text.dxf.halign = TextHAlign.LEFT

                    elif geom.type == 'MultiPolygon':
                        for poly in geom.geoms:
                            exterior_coords = list(poly.exterior.coords)
                            msp.add_lwpolyline(exterior_coords, dxfattribs={'layer': 'KKParcel', 'lineweight': 1}, close=True)

                            for interior in poly.interiors:
                                interior_coords = list(interior.coords)
                                msp.add_lwpolyline(interior_coords, dxfattribs={'layer': 'KKParcel', 'lineweight': 1}, close=True)

                            rep_point = poly.representative_point()
                            text = msp.add_text(
                                text=code_text,
                                dxfattribs={
                                    'insert': (rep_point.x, rep_point.y),
                                    'height': 1,
                                    'style': 'Tahoma',
                                    'layer': 'KKParcel_txt',
                                    'lineweight': 1
                                }
                            )
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

        # --- 4) CSV failu ar atlasītajiem kodiem ---
        try:
            progress_text.text("4. Sagatavo CSV failu ar atlasītajiem kodiem...")
            if 'code' in joined_gdf.columns:
                codes_df = joined_gdf[['code']].drop_duplicates()
                csv_codes_str = codes_df.to_csv(index=False, encoding='utf-8')
                st.download_button(
                    label="*.CSV (Atlasītie kodi)",
                    data=csv_codes_str.encode('utf-8'),
                    file_name=f'{file_name_prefix}_codes.csv',
                    mime='text/csv'
                )
            else:
                st.warning("Nav atrasts 'code' lauks datos.")
            current_step += 1
            progress_bar.progress(current_step / total_steps)
        except Exception as e:
            st.error(translations[language]["error_display_pdf"].format(error=str(e)))

        st.markdown("### Kadastra pilnā informācija:")
        # --- 5) CSV (VISI dati) ---
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

        # --- 6) Excel (VISI dati) ---
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

# -------------------------------------------------------------------------
# ------------------- (Neizmantots) geocode_address ------------------------
# -------------------------------------------------------------------------
def geocode_address(address_text):
    return None, None, None, None

# -------------------------------------------------------------------------
# -------------------- Galvenā lietotnes saskarne -------------------------
# -------------------------------------------------------------------------
def show_main_app():
    direct_pdf_url = "https://drive.google.com/uc?export=download&id=1jUh4Uq9svZsnAWCkN6VQHW1C0kp1wLws"
    col1, col2 = st.columns([3, 1])
    with col1:
        pass
    with col2:
        st.markdown(
            f'''<a href="{direct_pdf_url}" target="_blank" style="float: right; font-size: 22px; color: #CE2F2C;">
                <strong>{translations[language]["instructions"]}</strong></a>''',
            unsafe_allow_html=True
        )

    st.title(translations[language]["title"])
    default_location = [56.946285, 24.105078]

    st.markdown("### " + translations[language]["radio_label"])
    if st.button(translations[language]["methods"][0]):
        st.session_state['input_option'] = "upload"
    if st.button(translations[language]["methods"][1]):
        st.session_state['input_option'] = "draw"
    if st.button(translations[language]["methods"][2]):
        st.session_state['input_option'] = "code"
    if st.button(translations[language]["methods"][3]):
        st.session_state['input_option'] = "code_with_adjacent"

    if 'input_option' not in st.session_state:
        st.info("Lūdzu, izvēlieties kādu no opcijām augstāk!")
        return

    option = st.session_state['input_option']

    # (1) Augšupielādē poligonu (DXF/SHP)
    if option == "upload":
        map_placeholder = st.empty()
        st.markdown(f"""{translations[language]["upload_instruction"]}  
        * **DXF** (.dxf)  
        * **SHP** (.shp, .shx, .dbf, .prj)""")

        uploaded_files = st.file_uploader(
            translations[language]["upload_files_label"],
            type=["shp", "shx", "dbf", "prj", "dxf"],
            accept_multiple_files=True
        )

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
                        st.error(
                            translations[language]["error_display_pdf"].format(
                                error="Please upload the polygon in one of the selected file formats: DXF or SHP."
                            )
                        )
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

    # (2) Zīmējam poligonu kartē
    elif option == "draw":
        st.info(translations[language]["draw_instruction"])

        if 'map_center' not in st.session_state:
            st.session_state['map_center'] = [56.946285, 24.105078]
        if 'found_geometry' not in st.session_state:
            st.session_state['found_geometry'] = None
        if 'found_bbox' not in st.session_state:
            st.session_state['found_bbox'] = None

        with st.form(key='draw_form'):
            code_text = st.text_input(label=translations[language].get("search_code", "Search by code"), value="")
            search_col, data_col = st.columns([1, 1])
            with search_col:
                search_button = st.form_submit_button(label=translations[language]["search_button"])
            with data_col:
                submit_button = st.form_submit_button(label=translations[language]["get_data_button"])

            if search_button and code_text.strip():
                lat, lon, poly_geojson, bbox, found_code = search_by_code(code_text.strip())
                if lat is not None and lon is not None:
                    st.session_state['map_center'] = [lat, lon]
                    st.session_state['found_geometry'] = poly_geojson
                    st.session_state['found_bbox'] = bbox
                    st.session_state['found_code'] = found_code
                else:
                    st.warning(translations[language]["search_error"])

            current_lat, current_lon = st.session_state['map_center']
            m = folium.Map(location=[current_lat, current_lon], zoom_start=10)

            wms_url = "https://lvmgeoserver.lvm.lv/geoserver/ows"
            wms_layers = {
                'Ortofoto': {'layers': 'public:Orto_LKS'},
                'Kadastra karte': {'layers': 'publicwfs:Kadastra_karte'}
            }

            add_wms_layer(
                map_obj=m,
                url=wms_url,
                name=('Ortofoto' if language == "Latviešu" else 'Orthophoto'),
                layers=wms_layers['Ortofoto']['layers'],
                overlay=False,
                opacity=1.0
            )
            add_wms_layer(
                map_obj=m,
                url=wms_url,
                name=('Kadastra karte' if language == "Latviešu" else 'Cadastral map'),
                layers=wms_layers['Kadastra karte']['layers'],
                overlay=True,
                opacity=0.5
            )

            if st.session_state["found_geometry"]:
                feature_collection = {
                    "type": "FeatureCollection",
                    "features": [
                        {
                            "type": "Feature",
                            "geometry": st.session_state["found_geometry"],
                            "properties": {"code": st.session_state.get("found_code", "N/A")}
                        }
                    ]
                }
                folium.GeoJson(
                    data=feature_collection,
                    name="Kad.apz.",
                    style_function=lambda x: {
                        "color": "green",
                        "fillColor": "yellow",
                        "fillOpacity": 0.4,
                        "weight": 2
                    }
                ).add_to(m)

                try:
                    shape_obj = shapely.geometry.shape(st.session_state["found_geometry"])
                    centroid = shape_obj.centroid
                    folium.Marker(
                        location=[centroid.y, centroid.x],
                        popup=f"Kad.apz.: {st.session_state.get('found_code', 'N/A')}",
                        icon=folium.Icon(color='red', icon='info-sign')
                    ).add_to(m)
                except Exception as e:
                    st.error(f"Error adding marker: {e}")

            if st.session_state["found_bbox"]:
                try:
                    minx, miny, maxx, maxy = map(float, st.session_state["found_bbox"])
                    m.fit_bounds([[miny, minx], [maxy, maxx]])
                except Exception as e:
                    st.error(f"Error fitting bounds: {e}")

            drawnItems = folium.FeatureGroup(name="Drawn Items")
            drawnItems.add_to(m)

            draw = Draw(
                draw_options={
                    'polyline': False, 'polygon': True, 'circle': False,
                    'rectangle': False, 'marker': False, 'circlemarker': False
                },
                edit_options={'edit': False, 'remove': True},
                feature_group=drawnItems
            )
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

    # (3) Tikai ievadītajiem kadastra kodiem
    elif option == "code":
        st.info(translations[language]["info_enter_code"])
        with st.form(key='code_form'):
            codes_input = st.text_input(label=translations[language]["enter_codes_label"], value="")
            uploaded_txt_file = st.file_uploader(
                translations[language]["upload_txt_label"],
                type=["txt"]
            )
            process_codes = st.form_submit_button(label=translations[language]["process_codes_button"])

            if process_codes:
                typed_codes = [code.strip() for code in codes_input.split(',') if code.strip()]
                uploaded_codes = []
                if uploaded_txt_file is not None:
                    content = uploaded_txt_file.read().decode("utf-8", errors="replace")
                    uploaded_codes = parse_uploaded_codes(content)
                all_codes = list(set(typed_codes + uploaded_codes))
                if not all_codes:
                    st.error(translations[language]["error_no_codes_entered"])
                else:
                    max_codes_in_filename = 5
                    if len(all_codes) > max_codes_in_filename:
                        display_codes = "_".join(all_codes[:max_codes_in_filename]) + f"_{len(all_codes)}_codi"
                    else:
                        display_codes = "_".join(all_codes)
                    st.session_state['base_file_name'] = display_codes
                    process_input(all_codes, input_method='code')

        if st.session_state.get('data_ready', False) and st.session_state['input_method'] == 'code':
            display_map_with_results()
            display_download_buttons()

    # (4) Ievadītajiem kodiem + pierobežnieki
    elif option == "code_with_adjacent":
        st.info(translations[language]["info_code_filter"])
        with st.form(key='code_with_adjacent_form'):
            codes_input = st.text_input(label=translations[language]["enter_codes_label"], value="")
            uploaded_txt_file = st.file_uploader(
                translations[language]["upload_txt_label"],
                type=["txt"]
            )
            process_codes = st.form_submit_button(label=translations[language]["process_codes_button"])

            if process_codes:
                typed_codes = [code.strip() for code in codes_input.split(',') if code.strip()]
                uploaded_codes = []
                if uploaded_txt_file is not None:
                    content = uploaded_txt_file.read().decode("utf-8", errors="replace")
                    uploaded_codes = parse_uploaded_codes(content)
                all_codes = list(set(typed_codes + uploaded_codes))
                if not all_codes:
                    st.error(translations[language]["error_no_codes_entered"])
                else:
                    max_codes_in_filename = 5
                    if len(all_codes) > max_codes_in_filename:
                        display_codes = "_".join(all_codes[:max_codes_in_filename]) + f"_{len(all_codes)}_codi"
                    else:
                        display_codes = "_".join(all_codes)
                    st.session_state['base_file_name'] = display_codes
                    process_input(all_codes, input_method='code_with_adjacent')

        if st.session_state.get('data_ready', False) and st.session_state['input_method'] == 'code_with_adjacent':
            display_map_with_results()
            display_download_buttons()

    # Ja dati jau gatavi (upload/draw variants)
    if st.session_state.get('data_ready', False) and st.session_state['input_option'] not in ["code", "code_with_adjacent"]:
        display_map_with_results()
        display_download_buttons()

    st.markdown("<div style='text-align: center; margin-top: 20px; color: gray;'>© 2024 METRUM</div>", unsafe_allow_html=True)

# -------------------------------------------------------------------------
# ------------------------------ main() -----------------------------------
# -------------------------------------------------------------------------
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

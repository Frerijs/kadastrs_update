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
from zoneinfo import ZoneInfo  # Pieejams Python 3.9 un jaunāk
from folium.plugins import Draw  # Importēt Draw spraudni
from ezdxf.enums import TextHAlign  # Importēt TextHAlign teksta izlīdzināšanai
from folium import MacroElement
from jinja2 import Template
import base64  # Jaunais imports PDF attēlošanai
import json  # Jaunais imports Esri JSON

# Supabase konfigurācija (Aizvietojiet ar savām faktiskajām vērtībām)
supabase_url = "https://uhwbflqdripatfpbbetf.supabase.co"
supabase_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InVod2JmbHFkcmlwYXRmcGJiZXRmIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTczMDcxODE2MywiZXhwIjoyMDQ2Mjk0MTYzfQ.78wsNZ4KBg2l6zeZ1ZknBBooe0PeLtJzRU-7eXo3WTk"  # Aizvietojiet ar drošu metodi


# Konstantas
APP_NAME = "Kadastrs"
APP_VERSION = "3.0"
APP_TYPE = "web"

# Tulkošanas vārdnīca
translations = {
    "Latviešu": {
        "radio_label": "Izvēlieties veidu, kā iegūt datus:",
        "methods": [
            'Augšupielādējiet iepriekš sagatavotu noslēgtas kontūras failu .DXF vai .SHP formātā',
            'Zīmējiet uz kartes noslēgtu kontūru'
        ],
        "title": "Kadastra apzīmējumu saraksta lejuplāde (ZV robežas un apzīmējumi)",
        "language_label": "Valoda / Language",
        "upload_instruction": "Augšupielādējiet slēgtu kontūru vai vairākas kontūras vienā no atbalstītajiem failu formātiem:",
        "upload_files_label": "Augšupielādējiet nepieciešamos failus:",
        "draw_instruction": "Zīmējiet noslēgtu kontūru uz kartes un nospiediet 'Iegūt datus' pogu.",
        "get_data_button": "Iegūt datus",
        "download_geojson": "Lejupielādēt datus GeoJSON formātā",
        "download_shapefile": "Lejupielādēt datus Shapefile formātā (ZIP)",
        "download_dxf": "Lejupielādēt datus DXF formātā",
        "download_csv": "Lejupielādēt zemes vienumu sarakstu CSV formātā",
        "logout": "Iziet",
        "success_logout": "Veiksmīgi izgājāt no konta.",
        "error_authenticate": "Kļūda autentificējot lietotāju: {status_code}",
        "error_login": "Nepareizs lietotājvārds vai parole.",
        "error_upload_dxf": "DXF failā netika atrastas derīgas ģeometrijas.",
        "error_upload_shp": "Netika atrasts .shp fails starp augšupielādētajiem failiem.",
        "error_no_data_download": "Nav pieejami dati lejupielādei.",
        "error_display_pdf": "Kļūda attēlojot PDF: {error}",
        "info_upload": "Lūdzu, augšupielādējiet failu ar poligonu.",
        "info_draw": "Lūdzu, uzzīmējiet poligonu uz kartes.",
        "preparing_geojson": "1. Sagatavo GeoJSON failu...",
        "preparing_shapefile": "2. Sagatavo Shapefile ZIP failu...",
        "preparing_dxf": "3. Sagatavo DXF failu...",
        "preparing_csv": "4. Sagatavo CSV failu...",
        "warning_code_missing": 'Kolonna "code" nav pieejama ArcGIS REST servisa datos. Teksts netiks pievienots DXF failā.',
        "instructions": "Instrukcija"
    },
    "English": {
        "radio_label": "Choose the way to get data:",
        "methods": [
            'Upload a previously prepared closed contour file in .DXF or .SHP format',
            'Draw a closed contour on the map'
        ],
        "title": "Download list of cadastral identifiers (ZV boundaries and identifiers)",
        "language_label": "Language / Valoda",
        "upload_instruction": "Upload a closed polygon or multiple polygons in one of the supported file formats:",
        "upload_files_label": "Upload the required files:",
        "draw_instruction": "Draw a closed polygon on the map and press the 'Get Data' button.",
        "get_data_button": "Get Data",
        "download_geojson": "Download data in GeoJSON format",
        "download_shapefile": "Download data in Shapefile format (ZIP)",
        "download_dxf": "Download data in DXF format",
        "download_csv": "Download cadastral units list in CSV format",
        "logout": "Logout",
        "success_logout": "Successfully logged out.",
        "error_authenticate": "Error authenticating user: {status_code}",
        "error_login": "Incorrect username or password.",
        "error_upload_dxf": "No valid geometries found in the DXF file.",
        "error_upload_shp": "No .shp file found among the uploaded files.",
        "error_no_data_download": "No data available for download.",
        "error_display_pdf": "Error displaying PDF: {error}",
        "info_upload": "Please upload the polygon file.",
        "info_draw": "Please draw a polygon on the map.",
        "preparing_geojson": "1. Preparing GeoJSON file...",
        "preparing_shapefile": "2. Preparing Shapefile ZIP file...",
        "preparing_dxf": "3. Preparing DXF file...",
        "preparing_csv": "4. Preparing CSV file...",
        "warning_code_missing": '"code" column is not available in ArcGIS REST service data. Text will not be added to the DXF file.',
        "instructions": "Instructions"
    }
}

# 1. Izsaucam st.set_page_config kā pirmo Streamlit komandu
st.set_page_config(page_title=translations["Latviešu"]["title"], layout="centered")

# 2. Pievienojam pielāgotu CSS, lai palielinātu radio pogu etiķetes
st.markdown(
    """
    <style>
    /* Palielina radio pogu etiķetes fonta izmēru */
    div[data-testid="stRadio"] label > div {
        font-size: 24px;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# Valodas izvēlne (Latviešu / Angļu)
language = st.sidebar.selectbox(translations["Latviešu"]["language_label"], ["Latviešu", "English"])

# Definēt CustomDeleteButton klasi
class CustomDeleteButton(MacroElement):
    """
    Pielāgots kontrolis ar atkritumu kastes ikonu, kas notīra visus uzzīmētos poligonus.
    """
    _template = Template("""
        {% macro script(this, kwargs) %}
            L.Control.DeleteButton = L.Control.extend({
                options: {
                    position: 'topleft'
                },
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

# Funkcija lietotāja autentifikācijai
def authenticate(username, password):
    try:
        headers = {
            "apikey": supabase_key,
            "Authorization": f"Bearer {supabase_key}",
            "Content-Type": "application/json",
        }
        url = f"{supabase_url}/rest/v1/users"
        params = {
            "select": "*",
            "username": f"eq.{username}",
            "password": f"eq.{password}",
        }
        response = requests.get(url, headers=headers, params=params)
        if response.status_code == 200:
            data = response.json()
            if data:
                return True
            else:
                return False
        else:
            st.error(translations[language]["error_authenticate"].format(status_code=response.status_code))
            return False
    except Exception as e:
        st.error(translations[language]["error_display_pdf"].format(error=str(e)))
        return False

# Funkcija lietotāja pieteikšanās reģistrēšanai
def log_user_login(username):
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
            st.error(translations[language]["error_authenticate"].format(status_code=response.status_code) + f", {response.text}")
    except Exception as e:
        st.error(translations[language]["error_display_pdf"].format(error=str(e)))

# Callback funkcija pieteikšanās formai
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
            # Noklusējuma izvēle pēc pieteikšanās
            st.session_state['input_option'] = translations[language]["methods"][1]  # 'Zīmējiet uz kartes noslēgtu kontūru' or 'Draw a closed contour on the map'
        else:
            st.error(translations[language]["error_login"])

# Funkcija, lai parādītu pieteikšanās formu
def show_login():
    st.title(translations[language]["title"])
    with st.form(key='login_form'):
        username = st.text_input("Lietotājvārds" if language=="Latviešu" else "Username", key='username')
        password = st.text_input("Parole" if language=="Latviešu" else "Password", type="password", key='password')
        submit_button = st.form_submit_button(label=("Pieslēgties" if language=="Latviešu" else "Login"), on_click=login)
    st.markdown("<div style='text-align: center; margin-top: 20px; color: gray;'>© 2024 METRUM</div>", unsafe_allow_html=True)

# Funkcija, kas attēlo PDF failu lietotnē
def display_pdf(file_path):
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

# Funkcija, kas parāda lejupielādes pogu un iespēju attēlot PDF
def display_instruction():
    direct_pdf_url = "https://drive.google.com/uc?export=download&id=1jUh4Uq9svZsnAWCkN6VQHW1C0kp1wLws"
    try:
        response = requests.get(direct_pdf_url)
        if response.status_code == 200:
            pdf_bytes = response.content
            st.download_button(
                label=translations[language]["download_geojson"],
                data=pdf_bytes,
                file_name=("Kadastra_instrukcija.pdf" if language=="Latviešu" else "Cadastral_instructions.pdf"),
                mime="application/pdf"
            )
            
            st.markdown("---")
            
            if st.button(translations[language]["instructions"]):
                base64_pdf = base64.b64encode(pdf_bytes).decode('utf-8')
                pdf_display = f'''
                    <iframe src="data:application/pdf;base64,{base64_pdf}" width="700" height="1000" type="application/pdf">
                        <p>{translations[language]["error_display_pdf"].format(error="")} 
                        <a href="data:application/pdf;base64,{base64_pdf}">{translations[language]["download_dxf"]}</a>.</p>
                    </iframe>
                '''
                st.markdown(pdf_display, unsafe_allow_html=True)
        else:
            st.error(translations[language]["error_display_pdf"].format(error="Failed to download PDF from Google Drive."))
    except Exception as e:
        st.error(translations[language]["error_display_pdf"].format(error=str(e)))

# Funkcija, lai nolasītu DXF failu un pārvērstu to GeoDataFrame
def read_dxf_to_geodataframe(dxf_file_path):
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
                num_segments = 100
                theta = np.linspace(start_angle, end_angle, num_segments)
                arc_points = [
                    (center.x + radius * np.cos(angle),
                     center.y + radius * np.sin(angle))
                    for angle in theta
                ]
                geometries.append(LineString(arc_points))
            elif entity.dxftype() == '3DFACE':
                vertices = [
                    (entity.dxf.vtx0.x, entity.dxf.vtx0.y, entity.dxf.vtx0.z),
                    (entity.dxf.vtx1.x, entity.dxf.vtx1.y, entity.dxf.vtx1.z),
                    (entity.dxf.vtx2.x, entity.dxf.vtx2.y, entity.dxf.vtx2.z),
                ]
                if entity.dxf.hasattr("vtx3"):
                    vertices.append((entity.dxf.vtx3.x, entity.dxf.vtx3.y, entity.dxf.vtx3.z))
                vertices_2d = to_2d(vertices)
                geometries.append(Polygon(vertices_2d))

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
            gdf = gpd.GeoDataFrame(geometry=[unified_geometry], crs="EPSG:3059")
            return gdf
        else:
            st.error(translations[language]["error_upload_dxf"])
            return gpd.GeoDataFrame()

    except Exception as e:
        st.error(translations[language]["error_display_pdf"].format(error=str(e)))
        return gpd.GeoDataFrame()

def add_wms_layer(map_obj, url, name, layers, overlay=True, opacity=1.0):
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
        st.error((f"Neizdevās pievienot {name} slāni: {e}" if language=="Latviešu" else f"Failed to add {name} layer: {e}"))

# *** GALVENĀ IZMAIŅA ŠAI FUNKCIJAI ***
# Funkcija, lai apstrādātu poligonu un iegūtu datus no ArcGIS REST servisa
def process_polygon(polygon_gdf, input_method):
    try:
        progress_bar = st.progress(0)
        progress_text = st.empty()

        st.session_state['input_method'] = input_method

        progress_text.text(translations[language].get("preparing_geojson", "1. Preparing GeoJSON file..."))

        # ArcGIS REST servisa konfigurācija
        # Izvēlieties pareizu slāņa id, piemēram, 8 ("Zemes vienības")
        layer_id = 8  # Aizvietojiet ar nepieciešamo slāņa id
        arcgis_base_url = f"https://utility.arcgis.com/usrsvcs/servers/4923f6b355934843b33aa92718520f12/rest/services/Hosted/Kadastrs/FeatureServer/{layer_id}/query"
        # Layer 8, var pielāgot atbilstoši jūsu servisa struktūrai

        polygon_gdf = polygon_gdf.to_crs(epsg=4326)  # ArcGIS REST parasti lieto WGS84
        progress_bar.progress(10)

        # Pārveidojiet shapely ģeometriju uz Esri JSON
        def shapely_to_esri_json(geom):
            if geom.type == 'Polygon':
                rings = [list(geom.exterior.coords)]
                for interior in geom.interiors:
                    rings.append(list(interior.coords))
                return {
                    "rings": rings,
                    "spatialReference": {"wkid": 4326}
                }
            elif geom.type == 'MultiPolygon':
                rings = []
                for poly in geom.geoms:
                    rings.append(list(poly.exterior.coords))
                    for interior in poly.interiors:
                        rings.append(list(interior.coords))
                return {
                    "rings": rings,
                    "spatialReference": {"wkid": 4326}
                }
            else:
                raise ValueError("Unsupported geometry type.")

        # Pieņemot, ka polygon_gdf satur tikai vienu poligonu
        polygon_esri_json = shapely_to_esri_json(polygon_gdf.geometry.iloc[0])
        progress_bar.progress(20)

        # Parametri ArcGIS REST query
        params = {
            'geometry': json.dumps(polygon_esri_json),
            'geometryType': 'esriGeometryPolygon',
            'spatialRel': 'esriSpatialRelIntersects',
            'outFields': '*',
            'returnGeometry': 'true',
            'f': 'geojson'
        }

        # Debug: izdrukājiet parametrus, lai pārbaudītu
        # st.write("ArcGIS REST Query Parameters:", params)

        # Veikt pieprasījumu
        response = requests.get(arcgis_base_url, params=params)
        progress_bar.progress(30)

        if response.status_code == 200:
            try:
                arcgis_data = response.json()
            except json.JSONDecodeError as jde:
                st.error(translations[language]["error_display_pdf"].format(error=f"JSON Decode Error: {jde}"))
                arcgis_data = None

            if arcgis_data and 'features' in arcgis_data and arcgis_data['features']:
                arcgis_gdf = gpd.GeoDataFrame.from_features(arcgis_data['features'])
                arcgis_gdf = arcgis_gdf.set_crs(epsg=4326).to_crs(epsg=3059)
                progress_bar.progress(50)

                # Apvieno ar ievadīto poligonu, ja nepieciešams
                joined_gdf = gpd.sjoin(arcgis_gdf, polygon_gdf, how='inner', predicate='intersects')
                progress_bar.progress(80)

                joined_gdf = joined_gdf.reset_index(drop=True).fillna('')

                for col in joined_gdf.columns:
                    if col != 'geometry':
                        if not pd.api.types.is_string_dtype(joined_gdf[col]):
                            joined_gdf[col] = joined_gdf[col].astype(str)

                invalid_geometries = ~joined_gdf.is_valid
                if invalid_geometries.any():
                    joined_gdf['geometry'] = joined_gdf['geometry'].buffer(0)
                progress_bar.progress(100)

                st.session_state['joined_gdf'] = joined_gdf
                st.session_state['polygon_gdf'] = polygon_gdf

                current_time = datetime.datetime.now(ZoneInfo('Europe/Riga'))
                processing_date = current_time.strftime('%Y%m%d')
                st.session_state['processing_date'] = processing_date

                st.session_state['data_ready'] = True
            else:
                st.error(translations[language]["error_display_pdf"].format(error="No 'features' in ArcGIS REST response."))
        else:
            st.error(translations[language]["error_display_pdf"].format(error=f"ArcGIS REST query failed with status code {response.status_code}"))

        progress_text.empty()
        progress_bar.empty()

    except Exception as e:
        st.error(translations[language]["error_display_pdf"].format(error=str(e)))

# Funkcija, lai parādītu karti ar rezultātiem
def display_map_with_results():
    if 'joined_gdf' not in st.session_state:
        st.error("Dati nav pieejami kartes attēlošanai.")
        return

    joined_gdf = st.session_state.joined_gdf.to_crs(epsg=4326)
    polygon_gdf = st.session_state.polygon_gdf.to_crs(epsg=4326)
    input_method = st.session_state.get('input_method', 'drawn')

    m = folium.Map(location=[56.946285, 24.105078], zoom_start=7)

    tooltip_field = 'Kadastra apzīmējums:' if language=="Latviešu" else "Cadastral identifier:"

    if input_method == 'upload':
        folium.GeoJson(
            joined_gdf,
            name=('Kadastra dati' if language=="Latviešu" else 'Cadastral data'),
            tooltip=folium.GeoJsonTooltip(fields=['code'], aliases=[tooltip_field]),
            style_function=lambda x: {'color': 'blue', 'fillOpacity': 0.1}
        ).add_to(m)

        folium.GeoJson(
            polygon_gdf,
            name=('Ievadītais poligons' if language=="Latviešu" else 'Input polygon'),
            style_function=lambda x: {'fillColor': 'none', 'color': 'red'}
        ).add_to(m)
    else:
        folium.GeoJson(
            polygon_gdf,
            name=('Ievadītais poligons' if language=="Latviešu" else 'Input polygon'),
            style_function=lambda x: {'fillColor': 'none', 'color': 'red'}
        ).add_to(m)

        folium.GeoJson(
            joined_gdf,
            name=('Kadastra dati' if language=="Latviešu" else 'Cadastral data'),
            tooltip=folium.GeoJsonTooltip(fields=['code'], aliases=[tooltip_field]),
            style_function=lambda x: {'color': 'blue', 'fillOpacity': 0.1}
        ).add_to(m)

    folium.LayerControl().add_to(m)

    if not joined_gdf.empty:
        bounds = joined_gdf.total_bounds
        m.fit_bounds([[bounds[1], bounds[0]], [bounds[3], bounds[2]]])
    elif not polygon_gdf.empty:
        bounds = polygon_gdf.total_bounds
        m.fit_bounds([[bounds[1], bounds[0]], [bounds[3], bounds[2]]])

    st_folium(m, width=700, height=500, key='result_map')

# Funkcija, lai parādītu lejupielādes pogas
def display_download_buttons():
    if st.session_state.get('joined_gdf') is None or st.session_state['joined_gdf'].empty:
        st.error(translations[language]["error_no_data_download"])
        return

    joined_gdf = st.session_state['joined_gdf']
    with tempfile.TemporaryDirectory() as tmp_output_dir:
        progress_bar = st.progress(0)
        progress_text = st.empty()

        base_file_name = st.session_state.get('base_file_name', 'ZV_dati_data')
        processing_date = st.session_state.get('processing_date', datetime.datetime.now().strftime('%Y%m%d'))
        file_name_prefix = f"{base_file_name}_ZV_dati_{processing_date}"

        total_steps = 4
        current_step = 0

        # GeoJSON
        try:
            progress_text.text(translations[language].get("preparing_geojson", "1. Preparing GeoJSON file..."))
            geojson_str = joined_gdf.to_json()
            if not geojson_str:
                st.error(translations[language]["error_display_pdf"].format(error="Failed to generate GeoJSON data."))
            else:
                geojson_bytes = geojson_str.encode('utf-8')
                st.download_button(
                    label=translations[language]["download_geojson"],
                    data=geojson_bytes,
                    file_name=f'{file_name_prefix}.geojson',
                    mime='application/geo+json'
                )
            current_step += 1
            progress_bar.progress(current_step / total_steps)
        except Exception as e:
            st.error(translations[language]["error_display_pdf"].format(error=str(e)))

        # Shapefile
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
                label=translations[language]["download_shapefile"],
                data=shp_zip_bytes,
                file_name=f'{file_name_prefix}_shp.zip',
                mime='application/zip'
            )
            current_step += 1
            progress_bar.progress(current_step / total_steps)
        except Exception as e:
            st.error(translations[language]["error_display_pdf"].format(error=str(e)))

        # DXF
        try:
            progress_text.text(translations[language].get("preparing_dxf", "3. Sagatavo DXF failu..."))
            dxf_output_path = os.path.join(tmp_output_dir, f'{file_name_prefix}.dxf')
            doc = ezdxf.new(dxfversion='R2010')
            doc.encoding = 'utf-8'

            if 'KKParcel' not in doc.layers:
                doc.layers.new(name='KKParcel', dxfattribs={
                    'color': 0,
                    'linetype': 'Continuous',
                    'true_color': 0x00FFFF,
                    'lineweight': 1,
                })

            if 'KKParcel_txt' not in doc.layers:
                doc.layers.new(name='KKParcel_txt', dxfattribs={
                    'color': 0,
                    'linetype': 'Continuous',
                    'true_color': 0x00FFFF,
                    'lineweight': 1,
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
                        msp.add_lwpolyline(exterior_coords, dxfattribs={
                            'layer': 'KKParcel',
                            'lineweight': 1,
                        }, close=True)
                        for interior in geom.interiors:
                            interior_coords = list(interior.coords)
                            msp.add_lwpolyline(interior_coords, dxfattribs={
                                'layer': 'KKParcel',
                                'lineweight': 1,
                            }, close=True)
                        rep_point = geom.representative_point()
                        text = msp.add_text(
                            text=code_text,
                            dxfattribs={
                                'insert': (rep_point.x, rep_point.y),
                                'height': 1,
                                'style': 'Tahoma',
                                'layer': 'KKParcel_txt',
                                'lineweight': 1,
                            }
                        )
                        text.dxf.halign = TextHAlign.LEFT

                    elif geom.type == 'MultiPolygon':
                        for poly in geom.geoms:
                            exterior_coords = list(poly.exterior.coords)
                            msp.add_lwpolyline(exterior_coords, dxfattribs={
                                'layer': 'KKParcel',
                                'lineweight': 1,
                            }, close=True)
                            for interior in poly.interiors:
                                interior_coords = list(interior.coords)
                                msp.add_lwpolyline(interior_coords, dxfattribs={
                                    'layer': 'KKParcel',
                                    'lineweight': 1,
                                }, close=True)
                            rep_point = poly.representative_point()
                            text = msp.add_text(
                                text=code_text,
                                dxfattribs={
                                    'insert': (rep_point.x, rep_point.y),
                                    'height': 1,
                                    'style': 'Tahoma',
                                    'layer': 'KKParcel_txt',
                                    'lineweight': 1,
                                }
                            )
                            text.dxf.halign = TextHAlign.LEFT

            doc.saveas(dxf_output_path)

            with open(dxf_output_path, 'rb') as f:
                dxf_bytes = f.read()

            if dxf_bytes:
                st.download_button(
                    label=translations[language]["download_dxf"],
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

        # CSV
        try:
            progress_text.text(translations[language].get("preparing_csv", "4. Sagatavo CSV failu..."))
            if 'code' in joined_gdf.columns:
                code_series = joined_gdf['code'].drop_duplicates()
                code_df = code_series.to_frame()
                csv_str = code_df.to_csv(index=False, encoding='utf-8')
                if not csv_str:
                    st.error(translations[language]["error_display_pdf"].format(error="Failed to generate CSV data."))
                else:
                    csv_bytes = csv_str.encode('utf-8')
                    st.download_button(
                        label=translations[language]["download_csv"],
                        data=csv_bytes,
                        file_name=f'{file_name_prefix}.csv',
                        mime='text/csv',
                    )
            else:
                st.warning(translations[language]["warning_code_missing"])
            current_step += 1
            progress_bar.progress(current_step / total_steps)
        except Exception as e:
            st.error(translations[language]["error_display_pdf"].format(error=str(e)))

        progress_text.empty()
        progress_bar.empty()

def show_main_app():
    direct_pdf_url = "https://drive.google.com/uc?export=download&id=1jUh4Uq9svZsnAWCkN6VQHW1C0kp1wLws"
    col1, col2 = st.columns([3, 1])
    with col1:
        pass
    with col2:
        st.markdown(
            f'''
            <a href="{direct_pdf_url}" target="_blank" style="float: right; font-size: 22px; color: #CE2F2C;"><strong>{translations[language]["instructions"]}</strong></a>
            ''',
            unsafe_allow_html=True
        )

    st.title(translations[language]["title"])

    default_location = [56.946285, 24.105078]

    # Izmantojot tulkošanas karti, iegūstam radio pogu etiķeti un opcijas
    radio_label = translations[language]["radio_label"]
    methods = translations[language]["methods"]

    # Noklusējuma vērtības
    if 'input_option' not in st.session_state:
        st.session_state['input_option'] = methods[1]  # 'Zīmējiet uz kartes noslēgtu kontūru' or 'Draw a closed contour on the map'
    if 'previous_option' not in st.session_state:
        st.session_state['previous_option'] = methods[1]

    # Ievades metodes
    input_option = st.radio(
        label=radio_label,
        options=methods,
        index=1 if st.session_state['input_option'] == methods[1] else 0
    )

    # Ja atšķiras no iepriekšējās, notīram starpstāvokļus
    if st.session_state['previous_option'] != input_option:
        keys_to_reset = ['joined_gdf', 'polygon_gdf', 'data_ready', 'base_file_name', 'processing_date', 'input_method']
        for key in keys_to_reset:
            if key in st.session_state:
                del st.session_state[key]
        st.session_state['previous_option'] = input_option

    # Saglabājam 'input_option' jaunajā st.session_state
    st.session_state['input_option'] = input_option

    # Parādām atbilstošo sadaļu
    if st.session_state['input_option'] == translations[language]["methods"][0]:
        map_placeholder = st.empty()

        st.markdown(
            f"""
            {translations[language]["upload_instruction"]}  
            * **DXF** (.dxf)  
            * **SHP** (.shp, .shx, .dbf, .prj)
            """
        )

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
                        st.error(translations[language]["error_display_pdf"].format(error="Please upload the polygon in one of the selected file formats: DXF or SHP."))

            if 'polygon_gdf' in locals() and polygon_gdf is not None:
                process_polygon(polygon_gdf, input_method='upload')
                st.session_state['data_ready'] = True
            else:
                st.error(translations[language]["error_display_pdf"].format(error="Could not load polygon from file."))
                m = folium.Map(location=default_location, zoom_start=7)
                with map_placeholder:
                    st_folium(m, width=700, height=500, key='upload_map')
        else:
            st.info(translations[language]["info_upload"])
            m = folium.Map(location=default_location, zoom_start=7)
            with st.empty():
                st_folium(m, width=700, height=500, key='upload_map')

    else:
        # Šeit pakeitām st.write uz st.info
        st.info(
            translations[language]["draw_instruction"]
        )

        wms_url = "https://lvmgeoserver.lvm.lv/geoserver/ows"
        wms_layers = {
            'Ortofoto': {'layers': 'public:Orto_LKS'},
            'Kadastra karte': {'layers': 'publicwfs:Kadastra_karte'}
        }

        with st.form(key='draw_form'):
            m = folium.Map(location=default_location, zoom_start=10)

            add_wms_layer(
                map_obj=m,
                url=wms_url,
                name=('Ortofoto' if language=="Latviešu" else 'Orthophoto'),
                layers=wms_layers['Ortofoto']['layers'],
                overlay=False,
                opacity=1.0
            )

            add_wms_layer(
                map_obj=m,
                url=wms_url,
                name=('Kadastra karte' if language=="Latviešu" else 'Cadastral map'),
                layers=wms_layers['Kadastra karte']['layers'],
                overlay=True,
                opacity=0.5
            )

            drawnItems = folium.FeatureGroup(name="Drawn Items")
            drawnItems.add_to(m)

            draw = Draw(
                draw_options={
                    'polyline': False,
                    'polygon': True,
                    'circle': False,
                    'rectangle': False,
                    'marker': False,
                    'circlemarker': False,
                },
                edit_options={
                    'edit': False,
                    'remove': True,
                },
                feature_group=drawnItems
            )
            draw.add_to(m)

            folium.LayerControl().add_to(m)

            m.get_root().add_child(CustomDeleteButton())

            output = st_folium(m, width=700, height=500, key='draw_map')

            submit_button = st.form_submit_button(label=translations[language]["get_data_button"])

            if submit_button:
                if output and 'all_drawings' in output and output['all_drawings']:
                    last_drawing = output['all_drawings'][-1]
                    polygon_gdf = gpd.GeoDataFrame.from_features([last_drawing], crs='EPSG:4326')
                    process_polygon(polygon_gdf, input_method='drawn')
                    st.session_state['data_ready'] = True
                    st.session_state['base_file_name'] = 'polygon'
                else:
                    st.error(translations[language]["info_draw"])

    # Ja dati apstrādāti, attēlojam rezultātus un lejupielādes pogas
    if st.session_state.get('data_ready', False):
        display_map_with_results()
        display_download_buttons()

    if st.button(translations[language]["logout"]):
        st.session_state.clear()
        st.success(translations[language]["success_logout"])

    st.markdown("<div style='text-align: center; margin-top: 20px; color: gray;'>© 2024 METRUM</div>", unsafe_allow_html=True)

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

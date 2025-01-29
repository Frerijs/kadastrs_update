import streamlit as st
import folium
from streamlit_folium import st_folium
import requests
import geopandas as gpd
from shapely.geometry import Polygon
from folium.plugins import Draw
import tempfile
from urllib.parse import urlencode
from arcgis2geojson import arcgis2geojson

# -- Mūsu WMS / ArcGIS parametri (piemēram)
WMS_URL = "https://lvmgeoserver.lvm.lv/geoserver/ows"
ARCGIS_URL_BASE = (
    "https://utility.arcgis.com/usrsvcs/servers/"
    "4923f6b355934843b33aa92718520f12/rest/services/Hosted/"
    "Kadastrs/FeatureServer/8/query"
)

st.set_page_config("Kadastrs - piemērs", layout="wide")

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
        st.warning(f"Neizdevās pievienot {name} slāni: {e}")

def get_data_by_code(search_code):
    """
    Vienkāršota funkcija, kas meklē ArcGIS servisā pēc code='...'
    """
    if not search_code:
        return gpd.GeoDataFrame()  # ja tukšs, uzreiz atgriežam tukšu

    # 1) Būvējam vaicājumu
    params = {
        'f': 'json',
        'where': f"code='{search_code}'",
        'outFields': '*',
        'returnGeometry': 'true',
        'outSR': '3059'
    }
    query_url = f"{ARCGIS_URL_BASE}?{urlencode(params)}"

    # 2) Sūtot pieprasījumu ArcGIS servisam
    resp = requests.get(query_url)

    # 3) Ja radās HTTP kļūda:
    if resp.status_code != 200:
        st.error(f"ArcGIS REST query failed: {resp.status_code}")
        return gpd.GeoDataFrame()

    # 4) Iegūstam JSON no atbildes
    esri_data = resp.json()

    # 5) Vai ir 'error' lauks atbildē (ArcGIS var atgriezt kļūdas ziņu)?
    if "error" in esri_data:
        msg = esri_data["error"].get("message", "Unknown ArcGIS error")
        st.error(f"ArcGIS atgrieza kļūdu: {msg}")
        return gpd.GeoDataFrame()

    # 6) Konvertējam uz GeoJSON
    geojson_data = arcgis2geojson(esri_data)

    # 7) Pārbaudām, vai geojson_data satur lauku "features"
    if "features" not in geojson_data:
        st.warning("ArcGIS neatgrieza nevienu ģeometriju (nav 'features').")
        return gpd.GeoDataFrame()

    # 8) Beidzot veidojam GeoDataFrame
    gdf = gpd.GeoDataFrame.from_features(geojson_data["features"])

    # 9) Ja vajag, iestatām CRS
    if gdf.empty:
        # Ja ArcGIS kaut ko atgriezis, bet 0 objektus
        st.warning(f"ArcGIS neatgrieza nevienu ierakstu atbilstoši code='{search_code}'.")
        return gpd.GeoDataFrame()

    # Pieņemam, ka orģināli EPSG:3059
    if gdf.crs is None:
        gdf.crs = "EPSG:3059"
    else:
        gdf = gdf.to_crs("EPSG:3059")

    return gdf


def get_data_by_polygon(polygon_gdf):
    """
    Vienkāršota funkcija, kas meklē ArcGIS servisā pēc poligona (BBOX).
    """
    if polygon_gdf.empty:
        return gpd.GeoDataFrame()
    # Pieņemam, ka polygon_gdf jau EPSG:4326, pārveidojam uz 3059
    poly_3059 = polygon_gdf.to_crs(epsg=3059)
    minx, miny, maxx, maxy = poly_3059.total_bounds
    params = {
        'f': 'json',
        'where': '1=1',
        'outFields': '*',
        'returnGeometry': 'true',
        'geometry': f'{minx},{miny},{maxx},{maxy}',
        'geometryType': 'esriGeometryEnvelope',
        'inSR': '3059',
        'outSR': '3059',
        'spatialRel': 'esriSpatialRelIntersects',
    }
    query_url = f"{ARCGIS_URL_BASE}?{urlencode(params)}"
    resp = requests.get(query_url)
    if resp.status_code != 200:
        st.error(f"ArcGIS REST query failed: {resp.status_code}")
        return gpd.GeoDataFrame()
    esri_data = resp.json()
    geojson_data = arcgis2geojson(esri_data)
    gdf = gpd.GeoDataFrame.from_features(geojson_data["features"])
    if gdf.crs is None:
        gdf.crs = "EPSG:3059"
    else:
        gdf = gdf.to_crs(epsg=3059)
    # tagad sjoin, lai iegūtu reāli pārklājošos
    joined = gpd.sjoin(gdf, poly_3059, how='inner', predicate='intersects')
    return joined

def show_gdf_on_map(gdf, center=[56.946285, 24.105078]):
    """
    Vienkārši attēlo gdf uz folium kartes.
    """
    if gdf.empty:
        st.warning("Nav atrasts neviens ieraksts!")
        return
    gdf_4326 = gdf.to_crs(epsg=4326)
    m = folium.Map(location=center, zoom_start=9)
    folium.GeoJson(
        gdf_4326,
        name='Atrastie dati',
        tooltip=folium.GeoJsonTooltip(fields=['code'], aliases=['Kadastra apz.:']),
        style_function=lambda x: {'color': 'blue', 'fillOpacity': 0.1}
    ).add_to(m)
    folium.LayerControl().add_to(m)

    # Iezūmojam uz rezultātu robežām
    bounds = gdf_4326.total_bounds
    m.fit_bounds([[bounds[1], bounds[0]], [bounds[3], bounds[2]]])
    st_folium(m, width=700, height=450)

# ---------------------------
# Galvenā lietotnes plūsma
# ---------------------------

st.title("Kadastra meklēšanas piemērs")
choice = st.radio(
    "Izvēlieties darbību:",
    ["Meklēt pēc kadastra numura", "Zīmēt poligonu uz kartes"]
)

if choice == "Meklēt pēc kadastra numura":
    st.info("Šeit netiek izmantota nekāda poligona zīmēšana. Vienkārši meklējam pēc code='...'")
    code_input = st.text_input("Ievadiet code:")
    if st.button("Meklēt"):
        result_gdf = get_data_by_code(code_input)
        show_gdf_on_map(result_gdf)

else:
    st.info("Šeit var zīmēt poligonu. Meklējam ArcGIS pēc poligona pārklājuma.")
    with st.form("draw_polygon_form"):
        m = folium.Map(location=[56.946285, 24.105078], zoom_start=8)
        # Pievienojam WMS (orto + Kadastra karte)
        add_wms_layer(
            m, WMS_URL, "Ortofoto", "public:Orto_LKS", overlay=False, opacity=1.0
        )
        add_wms_layer(
            m, WMS_URL, "Kadastra karte", "publicwfs:Kadastra_karte", overlay=True, opacity=0.5
        )

        draw = Draw(
            draw_options={
                'polyline': False,
                'polygon': True,
                'circle': False,
                'rectangle': False,
                'marker': False,
                'circlemarker': False,
            },
            edit_options={'edit': False, 'remove': True}
        )
        draw.add_to(m)
        st_data = st_folium(m, width=700, height=450)

        submit_poly = st.form_submit_button("Iegūt datus")

    if submit_poly:
        # pārbaudām, vai ir uzzīmēts poligons
        if "all_drawings" in st_data and st_data["all_drawings"]:
            # ņemam pēdējo zīmējumu
            last_drawing = st_data["all_drawings"][-1]
            poly_gdf = gpd.GeoDataFrame.from_features([last_drawing], crs="EPSG:4326")
            result_gdf = get_data_by_polygon(poly_gdf)
            show_gdf_on_map(result_gdf)
        else:
            st.warning("Nav uzzīmēts neviens poligons!")

import requests
import streamlit as st

st.title("Adrešu meklēšana")

def nominatim_search(query):
    """Atgriež Nominatim rezultātu sarakstu (label, lat, lon) pēc dotā query."""
    url = "https://nominatim.openstreetmap.org/search"
    params = {
        "format": "json",
        "limit": 5,  # cik ieteikumus atgriezt
        "q": query
    }
    try:
        r = requests.get(url, params=params)
        results = r.json()
        out = []
        for item in results:
            label = item["display_name"]
            lat = float(item["lat"])
            lon = float(item["lon"])
            out.append((label, lat, lon))
        return out
    except:
        return []

def on_text_change():
    query = st.session_state.address_text.strip()
    if not query:
        st.session_state.suggestions = []
        return
    suggestions = nominatim_search(query)
    st.session_state.suggestions = suggestions

# sagatavojam mainīgos, lai saglabātu starprezultātus
if "address_text" not in st.session_state:
    st.session_state.address_text = ""
if "suggestions" not in st.session_state:
    st.session_state.suggestions = []

# Teksta ievade ar on_change
st.text_input(
    "Ievadiet adresi",
    key="address_text",
    on_change=on_text_change
)

# Parādām selectbox ar ieteikumiem
if st.session_state.suggestions:
    # veidojam label sarakstu (lai selectbox redz tikai tekstu)
    select_labels = [x[0] for x in st.session_state.suggestions]
    choice = st.selectbox("Ieteikumi:", select_labels)
    st.write(f"**Jūsu izvēle**: {choice}")

    # atrod lat/lon
    chosen_item = next((x for x in st.session_state.suggestions if x[0] == choice), None)
    if chosen_item:
        st.write(f"Platums (lat): {chosen_item[1]}, Garums (lon): {chosen_item[2]}")

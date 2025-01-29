import streamlit as st
import requests

def search_address(q):
    if not q:
        return []
    url = "https://nominatim.openstreetmap.org/search"
    headers = {"User-Agent": "MyStreamlitApp/1.0 (myemail@domain.com)"}
    params = {
        "q": q,
        "format": "json",
        "limit": 5
    }
    try:
        # Sūtām pieprasījumu
        r = requests.get(url, headers=headers, params=params, timeout=10)
        
        # DIAGNOSTIKA
        st.write("DEBUG | Status code:", r.status_code)
        st.write("DEBUG | Response text:", r.text)
        
        r.raise_for_status()  # ja status_code != 200 => Exception
        data = r.json()
        return data
    except Exception as e:
        st.warning(f"Kļūda: {e}")
        return []

st.title("Meklēt ar Nominatim")

address_input = st.text_input("Ievadiet vietu:")
if st.button("Meklēt"):
    results = search_address(address_input)
    if results:
        st.write(f"Atrasti {len(results)} rezultāti.")
        for place in results:
            st.write(f"**{place.get('display_name')}**",
                     f" => lat: {place.get('lat')}, lon: {place.get('lon')}")
    else:
        st.write("Nekas netika atrasts vai atgriezts tukšs saraksts.")

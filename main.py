import streamlit as st
import requests

st.title("Adrešu meklēšana ar Nominatim (piemērs)")

def nominatim_search(query):
    """
    Atgriež Nominatim rezultātu sarakstu (label, lat, lon) pēc dotā query.
    Pievērš uzmanību pareizai "User-Agent" galvenes norādei!
    """
    url = "https://nominatim.openstreetmap.org/search"
    params = {
        "format": "json",
        "limit": 5,
        "q": query
    }
    # OBLIGĀTI norādām lietotāja aģentu, citādi Nominatim var bloķēt pieprasījumu
    headers = {
        "User-Agent": "MyStreamlitApp/1.0 (myemail@domain.com)"  
    }
    try:
        r = requests.get(url, params=params, headers=headers, timeout=10)
        r.raise_for_status()  # pacelt kļūdu, ja nav 200
        data = r.json()
        results = []
        for item in data:
            label = item.get("display_name")
            lat = float(item.get("lat"))
            lon = float(item.get("lon"))
            results.append((label, lat, lon))
        return results
    except Exception as e:
        st.warning(f"Kļūda meklēšanā: {e}")
        return []

# Teksta ievade un poga
address = st.text_input("Ievadiet vietas nosaukumu (piem., 'Talsi'):")
if st.button("Meklēt"):
    if address.strip():
        # Veicam meklēšanu
        suggestions = nominatim_search(address.strip())
        if suggestions:
            st.write("Rezultāti:")
            for (label, lat, lon) in suggestions:
                st.write(f"**{label}**  [lat={lat}, lon={lon}]")
        else:
            st.write("Nekas netika atrasts.")
    else:
        st.warning("Ievadiet kādu atslēgvārdu!")

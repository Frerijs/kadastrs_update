import streamlit as st
import requests

def nominatim_search(q):
    url = "https://nominatim.openstreetmap.org/search"
    params = {"format":"json", "limit":5, "q": q}
    headers = {"User-Agent": "MyStreamlitApp/1.0 (myemail@domain.com)"}
    r = requests.get(url, params=params, headers=headers)
    st.write("DEBUG status code:", r.status_code)
    st.write("DEBUG text:", r.text)
    r.raise_for_status()
    return r.json()

address = st.text_input("Ievadiet vietu:")
if st.button("Meklēt"):
    results = nominatim_search(address.strip())
    st.write(results)

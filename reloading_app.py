import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# App Konfiguration
st.set_page_config(page_title="Reloading Log", page_icon="🎯", layout="wide")

# --- VERBINDUNG ---
conn = st.connection("gsheets", type=GSheetsConnection)

# DEINE SPEZIFISCHE TABELLEN-URL
SHEET_URL = "https://docs.google.com/spreadsheets/d/1qEUbTNszbjXmFYi4V9LaXMt6mxKSwe1jfOi7zqX8LHY/edit"

def load_data():
    try:
        # Lädt das Blatt "Ladedaten"
        data = conn.read(spreadsheet=SHEET_URL, worksheet="Ladedaten", ttl=0)
        return data.dropna(how="all")
    except Exception:
        return pd.DataFrame(columns=["Datum", "Kaliber", "Geschoss", "Pulver", "Ladung_gr", "OAL_mm", "Notizen"])

st.title("🎯 Wiederlade-Datenbank")

# --- EINGABE IN DER SIDEBAR ---
with st.sidebar:
    st.header("📝 Neuer Eintrag")
    with st.form("reload_form", clear_on_submit=True):
        datum = st.date_input("Datum", datetime.now())
        kaliber = st.text_input("Kaliber", placeholder="z.B. .308 Win")
        geschoss = st.text_input("Geschoss", placeholder="Typ / Gewicht")
        pulver = st.text_input("Pulver")
        ladung = st.number_input("Ladung (Grains)", step=0.1, format="%.1f")
        oal = st.number_input("OAL (mm)", step=0.01, format="%.2f")
        notizen = st.text_area("Notizen")
        
        if st.form_submit_button("💾 Speichern"):
            current_df = load_data()
            new_entry = pd.DataFrame([{
                "Datum": str(datum),
                "Kaliber": kaliber,
                "Geschoss": geschoss,
                "Pulver": pulver,
                "Ladung_gr": float(ladung),
                "OAL_mm": float(oal),
                "Notizen": notizen
            }])
            updated_df = pd.concat([current_df, new_entry], ignore_index=True)
            conn.update(spreadsheet=SHEET_URL, worksheet="Ladedaten", data=updated_df)
            st.cache_data.clear()
            st.success("Gespeichert!")
            st.rerun()

# --- DATEN ANZEIGEN ---
df = load_data()
if not df.empty:
    st.dataframe(df.iloc[::-1], use_container_width=True)
else:
    st.info("Noch keine Daten vorhanden.")

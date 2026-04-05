import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# App Konfiguration
st.set_page_config(page_title="Reloading Log Professional", page_icon="🎯", layout="wide")

# --- VERBINDUNG ---
conn = st.connection("gsheets", type=GSheetsConnection)
SHEET_URL = "https://docs.google.com/spreadsheets/d/1qEUbTNszbjXmFYi4V9LaXMt6mxKSwe1jfOi7zqX8LHY/edit"

# --- HELFER: DATEN AUS REATERN LADEN ---
def get_list(sheet_name):
    try:
        df = conn.read(spreadsheet=SHEET_URL, worksheet=sheet_name, ttl=3600)
        return df.iloc[:, 0].dropna().tolist() # Nimmt die erste Spalte jedes Reiters
    except:
        return []

# Laden der Dropdown-Listen für die Eingabemaske
list_kaliber = get_list("Kaliber")
list_geschosse = get_list("Geschosse")
list_pulver = get_list("Pulver")
list_zuender = get_list("Zünder")
list_huelsen = get_list("Hülsen")

def load_main_data():
    df = conn.read(spreadsheet=SHEET_URL, worksheet="Ladedatum", ttl=0)
    return df.dropna(how="all")

# --- HAUPTBEREICH ---
st.title("🎯 Wiederlade-Logbuch")

# Daten laden
df_main = load_main_data()

# --- SIDEBAR: NEUE LADUNG ---
with st.sidebar:
    st.header("📝 Neue Ladung erfassen")
    with st.form("entry_form", clear_on_submit=True):
        f_date = st.date_input("Ladedatum", datetime.now())
        f_stueck = st.number_input("Stück", min_value=1, step=1, value=50)
        f_kal = st.selectbox("Kaliber", list_kaliber)
        f_ges = st.selectbox("Geschoss", list_geschosse)
        f_pul = st.selectbox("Pulver", list_pulver)
        f_grain = st.number_input("Grain", step=0.1, format="%.1f")
        f_oal = st.number_input("OAL", step=0.1, format="%.1f")
        f_crimp = st.text_input("Crimp", value="factory leicht")
        f_zuen = st.selectbox("Zünder", list_zuender)
        f_huel = st.selectbox("Hülsen", list_huelsen)
        f_anm = st.text_input("Anmerkung")
        
        if st.form_submit_button("💾 Speichern"):
            # Gesamtzahl berechnen (letzter Wert + neue Stück)
            current_total = df_main["Gesamt"].iloc[-1] if not df_main.empty else 0
            new_total = current_total + f_stueck
            
            new_row = pd.DataFrame([{
                "Ladedatum": f_date.strftime("%d.%m.%Y"),
                "Stück": f_stueck,
                "Kaliber": f_kal,
                "Geschoss": f_ges,
                "Pulver": f_pul,
                "Grain": f_grain,
                "OAL": f_oal,
                "Crimp": f_crimp,
                "Zünder": f_zuen,
                "Hülsen": f_huel,
                "Anmerkung": f_anm,
                "Gesamt": int(new_total)
            }])
            
            updated_df = pd.concat([df_main, new_row], ignore_index=True)
            conn.update(spreadsheet=SHEET_URL, worksheet="Ladedatum", data=updated_df)
            st.cache_data.clear()
            st.success(f"Gespeichert! Gesamtstand: {new_total}")
            st.rerun()

# --- DASHBOARD ---
if not df_main.empty:
    # Metriken oben
    m1, m2, m3 = st.columns(3)
    total_produced = df_main["Gesamt"].iloc[-1]
    m1.metric("Gesamtproduktion", f"{int(total_produced)} Schuss")
    m2.metric("Letzte Ladung", f"{df_main['Stück'].iloc[-1]}x {df_main['Kaliber'].iloc[-1]}")
    m3.metric("Einträge", len(df_main))

    # Filter
    st.divider()
    filter_kal = st.multiselect("Kaliber filtern", options=list_kaliber, default=[])
    
    display_df = df_main
    if filter_kal:
        display_df = df_main[df_main["Kaliber"].isin(filter_kal)]

    # Tabelle (Neueste zuerst)
    st.dataframe(display_df.iloc[::-1], use_container_width=True, hide_index=True)
    
else:
    st.info("Keine Daten im Reiter 'Ladedatum' gefunden.")

# --- LÖSCH-MODUS ---
with st.expander("🛠️ Admin / Korrektur"):
    if st.button("🗑️ Letzte Zeile löschen"):
        if not df_main.empty:
            conn.update(spreadsheet=SHEET_URL, worksheet="Ladedatum", data=df_main[:-1])
            st.cache_data.clear()
            st.rerun()

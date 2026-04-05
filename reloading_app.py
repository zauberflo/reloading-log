import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# App Konfiguration
st.set_page_config(page_title="Reloading Log Professional", page_icon="🎯", layout="wide")

# --- VERBINDUNG ---
conn = st.connection("gsheets", type=GSheetsConnection)

# DEINE TABELLEN-URL
SHEET_URL = "https://docs.google.com/spreadsheets/d/1qEUbTNszbjXmFYi4V9LaXMt6mxKSwe1jfOi7zqX8LHY/edit"

# --- HELFER: DATEN LADEN ---
def get_list(sheet_name):
    try:
        # Nutzt spreadsheet=URL um Secrets zu erzwingen
        df = conn.read(spreadsheet=SHEET_URL, worksheet=sheet_name, ttl=3600)
        return df.iloc[:, 0].dropna().tolist()
    except Exception as e:
        # Falls ein Reiter fehlt, geben wir eine leere Liste zurück, damit die App nicht abstürzt
        return []

def load_main_data():
    try:
        df = conn.read(spreadsheet=SHEET_URL, worksheet="Ladedatum", ttl=0)
        return df.dropna(how="all")
    except Exception:
        return pd.DataFrame()

# --- DATEN INITIALISIEREN (WICHTIG: Vor der Sidebar!) ---
list_kaliber = get_list("Kaliber")
list_geschosse = get_list("Geschosse")
list_pulver = get_list("Pulver")
list_zuender = get_list("Zünder")
list_huelsen = get_list("Hülsen")

df_main = load_main_data()

# --- HAUPTBEREICH ---
st.title("🎯 Wiederlade-Logbuch")

# --- SIDEBAR: NEUE LADUNG ---
with st.sidebar:
    st.header("📝 Neue Ladung erfassen")
    with st.form("entry_form", clear_on_submit=True):
        f_date = st.date_input("Ladedatum", datetime.now())
        f_stueck = st.number_input("Stück", min_value=1, step=1, value=50)
        
        # Hier nutzen wir jetzt die oben definierten Listen
        f_kal = st.selectbox("Kaliber", list_kaliber if list_kaliber else ["Keine Daten"])
        f_ges = st.selectbox("Geschoss", list_geschosse if list_geschosse else ["Keine Daten"])
        f_pul = st.selectbox("Pulver", list_pulver if list_pulver else ["Keine Daten"])
        
        f_grain = st.number_input("Grain", step=0.1, format="%.1f")
        f_oal = st.number_input("OAL", step=0.1, format="%.1f")
        f_crimp = st.text_input("Crimp", value="factory leicht")
        
        f_zuen = st.selectbox("Zünder", list_zuender if list_zuender else ["Keine Daten"])
        f_huel = st.selectbox("Hülsen", list_huelsen if list_huelsen else ["Keine Daten"])
        
        f_anm = st.text_input("Anmerkung")
        
        if st.form_submit_button("💾 Speichern"):
            # Gesamtzahl berechnen
            current_total = 0
            if not df_main.empty and "Gesamt" in df_main.columns:
                current_total = pd.to_numeric(df_main["Gesamt"]).iloc[-1]
            
            new_total = current_total + f_stueck
            
            new_row = pd.DataFrame([{
                "Ladedatum": f_date.strftime("%d.%m.%Y"),
                "Stück": int(f_stueck),
                "Kaliber": f_kal,
                "Geschoss": f_ges,
                "Pulver": f_pul,
                "Grain": float(f_grain),
                "OAL": float(f_oal),
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

# --- DASHBOARD ANZEIGE ---
if not df_main.empty:
    # Metriken oben
    m1, m2, m3 = st.columns(3)
    
    # Sicherstellen, dass Gesamt existiert
    if "Gesamt" in df_main.columns:
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
    st.info("Warte auf Daten aus 'Ladedatum'...")

# --- LÖSCH-MODUS ---
with st.expander("🛠️ Admin / Korrektur"):
    if st.button("🗑️ Letzte Zeile löschen"):
        if not df_main.empty:
            conn.update(spreadsheet=SHEET_URL, worksheet="Ladedatum", data=df_main[:-1])
            st.cache_data.clear()
            st.rerun()

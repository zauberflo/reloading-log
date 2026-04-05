import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# App Konfiguration
st.set_page_config(page_title="Reloading Log Professional", page_icon="🎯", layout="wide")

# --- VERBINDUNG ---
conn = st.connection("gsheets", type=GSheetsConnection)
SHEET_URL = "https://docs.google.com/spreadsheets/d/1qEUbTNszbjXmFYi4V9LaXMt6mxKSwe1jfOi7zqX8LHY/edit"

# --- HELFER: DATEN LADEN ---
def get_list(sheet_name):
    """Holt die Daten aus den Referenz-Tabellenblättern (Geschosse, Pulver, etc.)"""
    try:
        df = conn.read(spreadsheet=SHEET_URL, worksheet=sheet_name, ttl=0)
        # Wir nehmen die erste Spalte und entfernen leere Zellen
        return df.iloc[:, 0].dropna().unique().tolist()
    except:
        return []

def load_main_data():
    """Lädt das Haupt-Tabellenblatt 'Ladedaten'"""
    try:
        df = conn.read(spreadsheet=SHEET_URL, worksheet="Ladedaten", ttl=0)
        return df.dropna(how="all")
    except Exception as e:
        st.error(f"Fehler beim Laden des Blattes 'Ladedaten': {e}")
        return pd.DataFrame()

# --- DATEN INITIALISIEREN ---
# Hier laden wir die Listen für die Dropdowns aus deinen anderen Tabellenblättern
list_kaliber = get_list("Kaliber")
list_geschosse = get_list("Geschosse")
list_pulver = get_list("Pulver")
list_zuender = get_list("Zünder")
list_huelsen = get_list("Hülsen")

df_main = load_main_data()

st.title("🎯 Wiederlade-Logbuch")

# --- SIDEBAR ---
with st.sidebar:
    # --- TEIL 1: NEUE LADUNG ERFASSEN ---
    st.header("📝 Neue Ladung erfassen")
    with st.form("entry_form", clear_on_submit=True):
        f_date = st.date_input("Ladedatum", datetime.now())
        f_stueck = st.number_input("Stück", min_value=1, value=50)
        f_kal = st.selectbox("Kaliber", list_kaliber if list_kaliber else ["-"])
        f_ges = st.selectbox("Geschoss", list_geschosse if list_geschosse else ["-"])
        f_pul = st.selectbox("Pulver", list_pulver if list_pulver else ["-"])
        f_grain = st.number_input("Grain", step=0.1, format="%.1f")
        f_oal = st.number_input("OAL", step=0.1, format="%.1f")
        f_crimp = st.text_input("Crimp", value="leicht")
        f_zuen = st.selectbox("Zünder", list_zuender if list_zuender else ["-"])
        f_huel = st.selectbox("Hülsen", list_huelsen if list_huelsen else ["-"])
        f_anm = st.text_input("Anmerkung")
        
        if st.form_submit_button("💾 Ladung Speichern"):
            # Gesamtzahl automatisch berechnen
            current_total = 0
            if not df_main.empty and "Gesamt" in df_main.columns:
                try:
                    current_total = pd.to_numeric(df_main["Gesamt"]).max()
                except: 
                    current_total = 0
            
            new_total = current_total + f_stueck
            
            new_row = pd.DataFrame([{
                "Ladedatum": f_date.strftime("%d.%m.%Y"),
                "Stück": int(f_stueck),
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
            
            updated = pd.concat([df_main, new_row], ignore_index=True)
            conn.update(spreadsheet=SHEET_URL, worksheet="Ladedaten", data=updated)
            st.cache_data.clear()
            st.success("Erfolgreich gespeichert!")
            st.rerun()

    st.divider()
    
    # --- TEIL 2: NEUE ARTEN HINZUFÜGEN ---
    st.header("🆕 Stammdaten ergänzen")
    # Hier wählst du aus, in welches Tabellenblatt der neue Eintrag soll
    cat = st.selectbox("Kategorie", ["Kaliber", "Geschosse", "Pulver", "Zünder", "Hülsen"])
    new_val = st.text_input(f"Neuer Name für {cat}")
    
    if st.button(f"➕ Zu {cat} hinzufügen"):
        if new_val:
            current_items = get_list(cat)
            if new_val not in current_items:
                # Erstellt ein DataFrame mit dem neuen Wert für das entsprechende Blatt
                new_df = pd.DataFrame({cat: current_items + [new_val]})
                conn.update(spreadsheet=SHEET_URL, worksheet=cat, data=new_df)
                st.cache_data.clear()
                st.success(f"'{new_val}' wurde hinzugefügt!")
                st.rerun()
            else:
                st.warning("Eintrag existiert bereits.")

# --- DASHBOARD ANZEIGE ---
if not df_main.empty:
    # Metriken (Gesamtzahlen)
    m1, m2, m3 = st.columns(3)
    if "Gesamt" in df_main.columns:
        total = pd.to_numeric(df_main["Gesamt"]).max()
        m1.metric("Gesamtproduktion", f"{int(total)} Schuss")
    m2.metric("Einträge", len(df_main))
    m3.metric("Letztes Kaliber", df_main["Kaliber"].iloc[-1] if "Kaliber" in df_main.columns else "-")

    st.divider()
    
    # Filterfunktion
    filter_kal = st.multiselect("Kaliber filtern", options=list_kaliber)
    display_df = df_main
    if filter_kal:
        display_df = df_main[df_main["Kaliber"].isin(filter_kal)]

    # Tabelle anzeigen (neueste Einträge oben)
    st.dataframe(display_df.iloc[::-1], use_container_width=True, hide_index=True)
else:
    st.info("Das Tabellenblatt 'Ladedaten' ist leer oder wurde nicht gefunden.")

# Admin Bereich zum Löschen
with st.expander("🛠️ Administration"):
    if st.button("🗑️ Letzten Eintrag löschen"):
        if not df_main.empty:
            conn.update(spreadsheet=SHEET_URL, worksheet="Ladedaten", data=df_main[:-1])
            st.cache_data.clear()
            st.rerun()

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
    try:
        # Hier nutzen wir einen kurzen Cache von 10 Min für die Stammdaten
        df = conn.read(spreadsheet=SHEET_URL, worksheet=sheet_name, ttl=600)
        return [str(x).strip() for x in df.iloc[:, 0].dropna().unique().tolist()]
    except:
        return []

def load_main_data():
    try:
        # Ladedaten ohne Cache (ttl=0), damit neue Einträge sofort da sind
        df = conn.read(spreadsheet=SHEET_URL, worksheet="Ladedaten", ttl=0)
        
        if df is None:
            return pd.DataFrame()
        
        # Entferne komplett leere Zeilen/Spalten
        df = df.dropna(how="all")
        
        if df.empty:
            return df

        # Alle Textspalten bereinigen
        for col in df.select_dtypes(include=['object']).columns:
            df[col] = df[col].astype(str).str.strip()
        
        # Spalte 'Gesamt' ignorieren, falls sie in Google Sheets noch existiert
        if "Gesamt" in df.columns:
            df = df.drop(columns=["Gesamt"])
            
        return df
    except Exception as e:
        # Zeige den echten Fehler an, falls Google nicht antwortet
        st.error(f"⚠️ Verbindung zu Google Sheets unterbrochen: {e}")
        return None 

# --- DATEN INITIALISIEREN ---
list_kaliber = get_list("Kaliber")
list_geschosse = get_list("Geschosse")
list_pulver = get_list("Pulver")
list_zuender = get_list("Zünder")
list_huelsen = get_list("Hülsen")

df_main = load_main_data()

st.title("🎯 Wiederlade-Logbuch")

# --- SIDEBAR ---
with st.sidebar:
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
            new_row = pd.DataFrame([{
                "Ladedatum": f_date.strftime("%d.%m.%Y"),
                "Stück": int(f_stueck), "Kaliber": f_kal, "Geschoss": f_ges,
                "Pulver": f_pul, "Grain": f_grain, "OAL": f_oal,
                "Crimp": f_crimp, "Zünder": f_zuen, "Hülsen": f_huel, "Anmerkung": f_anm
            }])
            # Wir hängen die neue Zeile an die bestehenden Daten an
            updated = pd.concat([df_main, new_row], ignore_index=True) if df_main is not None else new_row
            conn.update(spreadsheet=SHEET_URL, worksheet="Ladedaten", data=updated)
            st.cache_data.clear()
            st.rerun()

    st.divider()
    st.header("🆕 Stammdaten ergänzen")
    cat = st.selectbox("Kategorie", ["Kaliber", "Geschosse", "Pulver", "Zünder", "Hülsen"])
    new_val = st.text_input(f"Neuer Name für {cat}")
    
    if st.button(f"➕ Zu {cat} hinzufügen"):
        if new_val:
            current_items = get_list(cat)
            if new_val.strip() not in current_items:
                new_df = pd.DataFrame({cat: current_items + [new_val.strip()]})
                conn.update(spreadsheet=SHEET_URL, worksheet=cat, data=new_df)
                st.cache_data.clear()
                st.rerun()

# --- HAUPTBEREICH ---
# Wenn df_main None ist, gab es einen Verbindungsfehler
if df_main is None:
    st.warning("Verbindung wird neu aufgebaut... Bitte Seite aktualisieren.")
elif not df_main.empty:
    # Filter
    available_kaliber = sorted(df_main["Kaliber"].unique().tolist())
    filter_kal = st.multiselect("🔍 Nach Kaliber filtern", options=available_kaliber)
    
    display_df = df_main.copy()
    if filter_kal:
        display_df = display_df[display_df["Kaliber"].isin(filter_kal)]

    # Metriken
    m1, m2, m3 = st.columns(3)
    
    total_sum = 0
    if "Stück" in display_df.columns:
        total_sum = pd.to_numeric(display_df["Stück"], errors='coerce').fillna(0).sum()
    
    m1.metric("Schuss (gefiltert)", f"{int(total_sum)}")
    m2.metric("Einträge", len(display_df))
    
    last_cal = "-"
    if not display_df.empty and "Kaliber" in display_df.columns:
        last_cal = str(display_df["Kaliber"].iloc[-1])
    m3.metric("Letztes Kaliber", last_cal)

    st.divider()
    
    if not display_df.empty:
        st.dataframe(display_df.iloc[::-1], use_container_width=True, hide_index=True)
    else:
        st.info("Keine Daten für diesen Filter.")
else:
    st.info("Das Tabellenblatt 'Ladedaten' scheint leer zu sein oder wurde nicht geladen.")

with st.expander("🛠️ Administration"):
    if st.button("🗑️ Letzten Eintrag löschen"):
        if df_main is not None and not df_main.empty:
            conn.update(spreadsheet=SHEET_URL, worksheet="Ladedaten", data=df_main[:-1])
            st.cache_data.clear()
            st.rerun()

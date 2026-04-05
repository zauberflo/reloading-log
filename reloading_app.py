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
    """Holt Stammdaten (Pulver, Geschosse etc.) mit 10 Min Cache"""
    try:
        df = conn.read(spreadsheet=SHEET_URL, worksheet=sheet_name, ttl=600)
        return [str(x).strip() for x in df.iloc[:, 0].dropna().unique().tolist()]
    except:
        return []

def load_main_data():
    """Lädt Ladedaten mit kurzem Cache gegen Google-Sperren"""
    try:
        # ttl=20 verhindert, dass schnelles Filtern zu viele Google-Anfragen sendet
        df = conn.read(spreadsheet=SHEET_URL, worksheet="Ladedaten", ttl=20)
        
        if df is None:
            return pd.DataFrame()
        
        # Leere Zeilen entfernen
        df = df.dropna(how="all")
        
        if df.empty:
            return df

        # Alle Textspalten von Leerzeichen bereinigen
        for col in df.select_dtypes(include=['object']).columns:
            df[col] = df[col].astype(str).str.strip()
        
        # Alte Gesamt-Spalte ignorieren
        if "Gesamt" in df.columns:
            df = df.drop(columns=["Gesamt"])
            
        return df
    except Exception as e:
        if "429" in str(e):
            st.error("⚠️ Google Limit erreicht. Bitte 30 Sekunden warten und Seite neu laden.")
        else:
            st.error(f"⚠️ Fehler beim Laden: {e}")
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
            
            # Neue Daten an bestehende anfügen
            updated = pd.concat([df_main, new_row], ignore_index=True) if df_main is not None and not df_main.empty else new_row
            conn.update(spreadsheet=SHEET_URL, worksheet="Ladedaten", data=updated)
            
            # Cache sofort löschen, damit neuer Eintrag sichtbar wird
            st.cache_data.clear()
            st.success("Erfolgreich gespeichert!")
            st.rerun()

    st.divider()
    st.header("🆕 Stammdaten ergänzen")
    cat = st.selectbox("Kategorie", ["Kaliber", "Geschosse", "Pulver", "Zünder", "Hülsen"])
    new_val = st.text_input(f"Neuer Name für {cat}")
    
    if st.button(f"➕ Zu {cat} hinzufügen"):
        if new_val:
            current_items = get_list(cat)
            val_clean = new_val.strip()
            if val_clean not in current_items:
                new_df = pd.DataFrame({cat: current_items + [val_clean]})
                conn.update(spreadsheet=SHEET_URL, worksheet=cat, data=new_df)
                st.cache_data.clear()
                st.rerun()

# --- HAUPTBEREICH ---
if df_main is None:
    st.warning("Verbindung wird neu aufgebaut... Bitte 10 Sekunden warten.")
elif not df_main.empty:
    # Filter
    # Wir ziehen die Kaliber direkt aus den aktuellen Ladedaten für maximale Konsistenz
    available_kaliber = sorted(df_main["Kaliber"].unique().tolist())
    filter_kal = st.multiselect("🔍 Nach Kaliber filtern", options=available_kaliber)
    
    display_df = df_main.copy()
    if filter_kal:
        display_df = display_df[display_df["Kaliber"].isin(filter_kal)]

    # Metriken
    m1, m2, m3 = st.columns(3)
    
    # Summe der Stückzahl (reagiert auf Filter)
    total_sum = 0
    if "Stück" in display_df.columns:
        total_sum = pd.to_numeric(display_df["Stück"], errors='coerce').fillna(0).sum()
    
    m1.metric("Schuss (gefiltert)", f"{int(total_sum)}")
    m2.metric("Einträge", len(display_df))
    
    # Letztes Kaliber sicher auslesen
    last_cal = "-"
    if not display_df.empty and "Kaliber" in display_df.columns:
        last_cal = str(display_df["Kaliber"].iloc[-1])
    m3.metric("Letztes Kaliber", last_cal)

    st.divider()
    
    # Tabelle anzeigen
    if not display_df.empty:
        st.dataframe(display_df.iloc[::-1], use_container_width=True, hide_index=True)
    else:
        st.info("Keine Daten für diesen Filter gefunden.")
else:
    st.info("Das Tabellenblatt 'Ladedaten' ist leer oder wurde noch nicht geladen.")

# Administration
with st.expander("🛠️ Administration"):
    if st.button("🗑️ Letzten Eintrag löschen"):
        if df_main is not None and not df_main.empty:
            conn.update(spreadsheet=SHEET_URL, worksheet="Ladedaten", data=df_main[:-1])
            st.cache_data.clear()
            st.rerun()

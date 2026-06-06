import streamlit as st
import pandas as pd
from datetime import datetime
import json

# WICHTIG: Für den Permanentspeicher nutzen wir eine kleine HTML/JS-Komponente
from streamlit_javascript import st_javascript

# Seiteneinstellungen für Smartphones optimieren
st.set_page_config(page_title="T212 Ultimate Assistent", page_icon="🛡️", layout="centered")

st.title("🛡️ T212 Strategie-Zentrale")
st.markdown("---")

# Basis-Konfiguration Ihrer 20k-Strategie
tages_zins_netto = 6.50    
schaltpunkt = 1875.00       

# ---------------------------------------------------------
# PERSISTENTER LOCAL-STORAGE VIA JAVASCRIPT
# ---------------------------------------------------------
# Hilfsfunktionen zum Laden und Speichern auf dem Smartphone-Speicher
def load_local_data(key, default_value):
    js_code = f"localStorage.getItem('{key}')"
    result = st_javascript(js_code)
    if result is None or result == "null" or result == "":
        return default_value
    try:
        return json.loads(result)
    except:
        return default_value

def save_local_data(key, value):
    js_code = f"localStorage.setItem('{key}', '{json.dumps(value)}')"
    st_javascript(js_code)

# Daten live vom Smartphone abrufen (falls leer, Standardwerte setzen)
stored_log = load_local_data("t212_logbuch", [])
stored_pie_wert = load_local_data("t212_letzter_pie", 10.00)
stored_puffer = load_local_data("t212_aktueller_puffer", 1000.00)
stored_ausgesetzt = load_local_data("t212_gestern_ausgesetzt", "Nein")

# In den Session-State für die aktuelle Ansicht spiegeln
if 'logbuch' not in st.session_state: st.session_state.logbuch = stored_log
if 'letzter_pie_wert' not in st.session_state: st.session_state.letzter_pie_wert = stored_pie_wert
if 'aktueller_puffer' not in st.session_state: st.session_state.aktueller_puffer = stored_puffer
if 'gestern_ausgesetzt' not in st.session_state: st.session_state.gestern_ausgesetzt = stored_ausgesetzt

# ---------------------------------------------------------
# TAB 1: TÄGLICHE ENTSCHEIDUNG (16:00 UHR)
# ---------------------------------------------------------
st.header("🕒 Täglicher Invest-Check (16:00)")

tages_perf = st.number_input(
    "Tagesperformance des Pies im Depot (in %):", 
    value=0.0, step=0.1, format="%.2f"
)

gestern_ausgesetzt = st.radio(
    "Haben Sie GESTERN 0 EUR investiert?",
    ("Nein", "Ja"), 
    index=1 if st.session_state.gestern_ausgesetzt == "Ja" else 0,
    horizontal=True
)

st.subheader("Action für heute:")
empfohlener_betrag = 0.0
neuer_aussetzer_status = "Nein"

if tages_perf > 1.0:
    if gestern_ausgesetzt == "Ja":
        st.warning(f"Markt ist stark (+{tages_perf}%), aber die Sicherheits-Sperre greift.")
        st.info(f"➡️ HEUTE: NORMAL **{tages_zins_netto:.2f} EUR** manuell einzahlen.")
        empfohlener_betrag = tages_zins_netto
    else:
        st.success(f"Markt ist stark (+{tages_perf}%) und Sie haben gestern investiert.")
        st.info("➡️ HEUTE: **0.00 EUR** investieren. Pulver trocken halten!")
        empfohlener_betrag = 0.0
        neuer_aussetzer_status = "Ja"
elif tages_perf < -1.0:
    st.error(f"Markt ist schwach ({tages_perf}%). Rabatt-Tag!")
    st.info(f"➡️ HEUTE: DOPPELT **{tages_zins_netto * 2:.2f} EUR** manuell einzahlen.")
    empfohlener_betrag = tages_zins_netto * 2
else:
    st.info(f"Markt ist neutral ({tages_perf}%).")
    st.info(f"➡️ HEUTE: NORMAL **{tages_zins_netto:.2f} EUR** manuell einzahlen.")
    empfohlener_betrag = tages_zins_netto

if st.button("Tägliche Aktion im Smartphone-Speicher sichern"):
    neuer_eintrag = {
        "Datum": datetime.now().strftime("%d.%m.%Y %H:%M"),
        "Typ": "Tägliches Invest",
        "Betrag (EUR)": empfohlener_betrag,
        "Markt-Perf": f"{tages_perf:+.1f}%",
        "Puffer-Stand": st.session_state.aktueller_puffer
    }
    st.session_state.logbuch.append(neuer_eintrag)
    st.session_state.gestern_ausgesetzt = neuer_aussetzer_status
    
    # Auf dem Handy einfrieren
    save_local_data("t212_logbuch", st.session_state.logbuch)
    save_local_data("t212_gestern_ausgesetzt", neuer_aussetzer_status)
    st.success("💾 Dauerhaft auf Ihrem Gerät gespeichert!")
    st.rerun()

st.markdown("---")

# =========================================================
# TAB 2: REBALANCING-CHECK
# =========================================================
st.header("🔄 Großes Rebalancing")
show_rebalance = st.checkbox("Großen Rebalancing-Check öffnen")

if show_rebalance:
    letzter_wert = st.number_input(
        "Bezugswert (nach LETZTER Rebalancing-Aktion in EUR):", 
        value=float(st.session_state.letzter_pie_wert), step=5.0
    )
    aktueller_wert = st.number_input("AKTUELLER Gesamtwert des Pies (in EUR):", value=letzter_wert, step=5.0)
    aktueller_puffer = st.number_input(
        "Aktueller Stand des Puffers im Kern (in EUR):", 
        value=float(st.session_state.aktueller_puffer), step=10.0
    )

    abweichung = (aktueller_wert - letzter_wert) / letzter_wert
    st.metric(label="Kursbewegung seit letztem Trigger", value=f"{abweichung*100:+.2f}%")

    action_triggered = False
    puffer_veraenderung = 0.0
    neuer_fixpunkt = letzter_wert

    if letzter_wert < schaltpunkt:
        st.subheader("Status: PHASE 1 - AKKUMULATION")
        if abweichung <= -0.10:
            st.error("🚨 TRIGGER ERREICHT: Verlust-Limit durchbrochen!")
            puffer_veraenderung = -aktueller_wert if aktueller_puffer >= aktueller_wert else -aktueller_puffer
            neuer_fixpunkt = aktueller_wert * 2
            action_triggered = True
        elif abweichung >= 0.10:
            st.success("🎉 TRIGGER ERREICHT: Gewinn-Limit überschritten!")
            puffer_veraenderung = aktueller_wert * 0.25
            neuer_fixpunkt = aktueller_wert - puffer_veraenderung
            action_triggered = True
    else:
        st.subheader("Status: PHASE 2 - REIFE-PHASE")
        if abweichung <= -0.10:
            st.error("🚨 TRIGGER ERREICHT: Verlust-Limit durchbrochen (Sicherheitsmodus)!")
            puffer_veraenderung = -(aktueller_puffer * 0.25)
            neuer_fixpunkt = aktueller_wert + (aktueller_puffer * 0.25)
            action_triggered = True
        elif abweichung >= 0.10:
            st.success("🎉 TRIGGER ERREICHT: Gewinn-Limit überschritten!")
            puffer_veraenderung = aktueller_wert * 0.25
            neuer_fixpunkt = aktueller_wert - puffer_veraenderung
            action_triggered = True

    if action_triggered:
        if st.button("Rebalancing ausführen & Werte auf Handy einfrieren"):
            st.session_state.aktueller_puffer = aktueller_puffer + puffer_veraenderung
            st.session_state.letzter_pie_wert = neuer_fixpunkt
            
            neuer_eintrag = {
                "Datum": datetime.now().strftime("%d.%m.%Y %H:%M"),
                "Typ": "🔄 REBALANCING",
                "Betrag (EUR)": puffer_veraenderung,
                "Markt-Perf": f"{abweichung*100:+.1f}%",
                "Puffer-Stand": st.session_state.aktueller_puffer
            }
            st.session_state.logbuch.append(neuer_eintrag)
            
            # Alle geänderten Daten auf dem Handy sichern
            save_local_data("t212_logbuch", st.session_state.logbuch)
            save_local_data("t212_aktueller_puffer", st.session_state.aktueller_puffer)
            save_local_data("t212_letzter_pie", st.session_state.letzter_pie_wert)
            
            st.success("💾 Alle Systemparameter dauerhaft upgedatet!")
            st.rerun()

st.markdown("---")

# =========================================================
# TAB 3: DAS HISTORISCHE LOGBUCH
# =========================================================
st.header("📋 Ihr Strategie-Logbuch")
if st.session_state.logbuch:
    df_log = pd.DataFrame(st.session_state.logbuch)
    st.dataframe(df_log, use_container_width=True)
    
    if st.button("⚠️ Logbuch komplett löschen"):
        save_local_data("t212_logbuch", [])
        save_local_data("t212_letzter_pie", 10.00)
        save_local_data("t212_aktueller_puffer", 1000.00)
        st.success("Reset erfolgreich!")
        st.rerun()
else:
    st.info("Noch keine Einträge auf diesem Gerät vorhanden.")

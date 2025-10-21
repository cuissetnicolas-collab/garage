import streamlit as st
import pandas as pd
from io import BytesIO

# ==========================
# 🔐 AUTHENTIFICATION
# ==========================
if "login" not in st.session_state:
    st.session_state["login"] = False

def login(username, password):
    users = {
        "aurore": {"password": "12345", "name": "Aurore Demoulin"},
        "laure.froidefond": {"password": "Laure2019$", "name": "Laure Froidefond"},
        "bruno": {"password": "Toto1963$", "name": "Toto El Gringo"},
    }
    if username in users and password == users[username]["password"]:
        st.session_state["login"] = True
        st.session_state["username"] = username
        st.session_state["name"] = users[username]["name"]
        st.success(f"Bienvenue {st.session_state['name']} 👋")
        st.rerun()
    else:
        st.error("❌ Identifiants incorrects")

if not st.session_state["login"]:
    st.title("🔑 Connexion espace expert-comptable")
    username = st.text_input("Identifiant")
    password = st.text_input("Mot de passe", type="password")
    if st.button("Connexion"):
        login(username, password)
    st.stop()

# ==========================
# ⚙️ APPLICATION
# ==========================
st.title("📘 Générateur d'écritures comptables (ventes)")

uploaded_file = st.file_uploader("📂 Importer le fichier TXT des ventes", type=["txt"])

if uploaded_file:
    journal = st.text_input("📒 Journal", value="VT")
    date_ecriture = st.date_input("📅 Date d'écriture")

    # Lecture du fichier TXT
    lines = uploaded_file.read().decode("utf-8").splitlines()
    data = [l.split(",") for l in lines if l.strip()]

    ecritures = []

    for parts in data:
        if len(parts) < 11:
            continue  # ligne incomplète

        # Extraction des champs
        date_raw = parts[1]
        code_compte = parts[3].strip()
        libelle_facture = parts[5].replace('"', '').strip()
        num_facture = parts[6].replace('"', '').strip()
        montant = float(parts[7])
        sens = parts[8].strip().upper()

        # Conversion date JJMMYY → JJ/MM/20YY
        date_str = f"{date_raw[:2]}/{date_raw[2:4]}/20{date_raw[4:6]}"

        # Extraction du nom client à partir du libellé
        nom_client = ""
        if "Fact:" in libelle_facture:
            try:
                nom_client = libelle_facture.split("Fact:")[1].split(" ", 1)[1]
            except IndexError:
                nom_client = "Client inconnu"

        # Génération du compte client 411 + initiales
        code_alpha = ''.join(c for c in nom_client if c.isalpha()).upper()
        code_alpha = code_alpha[:1] if code_alpha else "X"
        compte_client = f"411{code_alpha}00000"

        # Détermination du compte utilisé
        compte = compte_client if code_compte.startswith("0113") else code_compte

        # Libellé final
        libelle_final = f"Facture {num_facture} - {nom_client}"

        # Sens débit / crédit
        debit = montant if sens == "D" else 0.0
        credit = montant if sens == "C" else 0.0

        ecritures.append({
            "Date": date_str,
            "Journal": journal,
            "Numéro de compte": compte,
            "Libellé": libelle_final,
            "Montant au débit": debit,
            "Montant au crédit": credit,
        })

    # Conversion en DataFrame
    df = pd.DataFrame(ecritures)

    # ✅ Contrôle du nombre de lignes par facture
    nb_lignes = len(df)
    st.info(f"{nb_lignes} lignes d’écritures générées.")

    # ✅ Aperçu des écritures
    st.subheader("👀 Aperçu des écritures")
    st.dataframe(df, use_container_width=True)

    # ✅ Contrôle équilibre
    total_debit = df["Montant au débit"].sum()
    total_credit = df["Montant au crédit"].sum()
    diff = round(total_debit - total_credit, 2)

    if abs(diff) < 0.01:
        st.success(f"✅ Écritures équilibrées (Débit = Crédit = {total_debit:.2f} €)")
    else:
        st.error(f"⚠️ Écart de {diff:.2f} € entre le débit et le crédit")

    # ✅ Export Excel
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Ecritures")
    buffer.seek(0)

    st.download_button(
        label="📥 Télécharger le fichier Excel",
        data=buffer,
        file_name="Ecritures_PennyLane.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

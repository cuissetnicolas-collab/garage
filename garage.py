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

    # Lecture du fichier TXT
    lines = uploaded_file.read().decode("utf-8").splitlines()
    data = [l.split(",") for l in lines if l.strip()]

    ecritures = []

    for parts in data:
        if len(parts) < 11:
            continue  # ligne incomplète

        code_journal = parts[2].strip().upper()
        
        # ⚠️ Ne prendre que les lignes VE
        if code_journal != "VE":
            continue

        date_raw = parts[1].strip()
        code_compte = parts[3].strip()
        libelle_facture = parts[5].replace('"', '').strip()
        num_facture = parts[6].replace('"', '').strip()
        montant = float(parts[7])
        sens = parts[8].strip().upper()

        # Conversion date JJMMYY → JJ/MM/20YY
        date_str = f"{date_raw[:2]}/{date_raw[2:4]}/20{date_raw[4:6]}"

        # Extraction du nom client depuis le libellé
        nom_client = ""
        if "Fact:" in libelle_facture:
            try:
                nom_client = libelle_facture.split("Fact:")[1].split(" ", 1)[1]
            except IndexError:
                nom_client = "Client inconnu"
        else:
            nom_client = "Client inconnu"

        # 🔄 Normalisation des comptes standards
        compte_remap = {
            "70600000": "706000000",
            "70700000": "707000000",
            "44571000": "445710090",
        }

        # Détermination du compte comptable
        if code_compte in compte_remap:
            compte = compte_remap[code_compte]
        else:
            # Compte client alphabétique
            code_alpha = ''.join(c for c in nom_client if c.isalpha()).upper()
            code_alpha = code_alpha[:1] if code_alpha else "X"
            compte = f"411{code_alpha}00000"

        # Libellé clair
        libelle_final = f"Facture {num_facture} - {nom_client}"

        # Sens
        debit = montant if sens == "D" else 0.0
        credit = montant if sens == "C" else 0.0

        ecritures.append({
            "Date": date_str,
            "Journal": journal,
            "Numéro de compte": compte,
            "Libellé": libelle_final,
            "Montant au débit": debit,
            "Montant au crédit": credit,
            "Facture": num_facture,
            "Client": nom_client
        })

    # Conversion en DataFrame
    df = pd.DataFrame(ecritures)

    # ✅ Aperçu principal
    st.subheader("👀 Aperçu des écritures")
    st.dataframe(df[["Date", "Journal", "Numéro de compte", "Libellé", "Montant au débit", "Montant au crédit"]], use_container_width=True)

    # ✅ Contrôle d'équilibre
    total_debit = df["Montant au débit"].sum()
    total_credit = df["Montant au crédit"].sum()
    diff = round(total_debit - total_credit, 2)

    if abs(diff) < 0.01:
        st.success(f"✅ Écritures équilibrées (Débit = Crédit = {total_debit:.2f} €)")
    else:
        st.error(f"⚠️ Écart de {diff:.2f} € entre le débit et le crédit")

    # ✅ Aperçu groupé par facture/client
    st.subheader("📊 Totaux par facture et client")
    df_group = df.groupby(["Facture", "Client"], as_index=False).agg({
        "Montant au débit": "sum",
        "Montant au crédit": "sum"
    })
    df_group["Équilibre"] = df_group["Montant au débit"] - df_group["Montant au crédit"]
    st.dataframe(df_group, use_container_width=True)

    # ✅ Export Excel avec deux onglets
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Ecritures")
        df_group.to_excel(writer, index=False, sheet_name="Totaux")
    buffer.seek(0)

    st.download_button(
        label="📥 Télécharger le fichier Excel PennyLane",
        data=buffer,
        file_name="Ecritures_PennyLane.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

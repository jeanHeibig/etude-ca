import os

import streamlit as st

from analysis import main

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

application = get_wsgi_application()
from django.contrib.auth import authenticate


# Set Streamlit config
st.set_page_config(
    page_title="Analyse CA - Solstice Lab",
    page_icon=":bar_chart:",
    layout="centered",
    menu_items={
        'Get Help': 'https://www.solstice-lab.com/contact',
        'About': """
            # Analyse du Chiffre d'Affaires
            
            Détail des différences de CA entre deux périodes.  
            [Solstice Lab](https://www.solstice-lab.com/)
        """
    }
)

def check_password():
    """Returns `True` if the user had a correct password."""

    def password_entered():
        """Checks whether a password entered by the user is correct."""
        user = authenticate(
            username=st.session_state["username"], password=st.session_state["password"]
        )

        if user is not None:
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # don't store username + password
            del st.session_state["username"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state or not st.session_state["password_correct"]:
        # Password not correct, show input + error.
        st.text_input("Username", on_change=password_entered, key="username")
        st.text_input(
            "Password", type="password", on_change=password_entered, key="password"
        )
        if st.session_state["username"] and st.session_state["password"]:
            st.error("User not known or password incorrect")
        return False
    else:
        # Password correct.
        return True

if check_password():
    def local_css(file_name):
        with open(file_name) as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

    local_css("style.css")

    # Title
    st.title("Analyse du Chiffre d'Affaires")

    sales_file = st.sidebar.file_uploader("Veuillez entrer le fichier des ventes", type="csv",
        help="""
            Doit contenir les colonnes :
            1. *Year* : l'année
            2. *Reference* : le code produit
            3. *Currency* : le code de la devise locale (ex. EUR ou USD, etc.)
            4. *Price* : le prix **en devise locale**
            5. *Quantity* : la quantité de produits vendus sur l'année
        """
    )
    if sales_file is None:
        # We use a default file with fake data if no file is given by the user.
        sales_file = "default.csv"

    fx_file = st.sidebar.file_uploader("Taux de change personnalisés", type="csv",
        help="""
            Le ficher doit contenir une ligne d'entête avec le nom des colonnes :
            1. *Year* : l'année du taux de conversion pour la ligne
            2. *EUR* ou *USD* ou autre code devise : n'importe quel code devise correspondant au code du fichier des ventes
            3. *etc.* : autant d'autres codes devises que nécessaire

            Les valeurs doivent correspondre au cours de l'euro en devise locale, et non la réciproque. Si vous ne spécifiez pas de taux de change personnalisés,
            nous utilisons les taux du 1er janvier de l'année,
            tels que définis sur https://www.exchangerates.org.uk/ et https://www.xe.com/.
        """)
    if fx_file is None:
        # We use a reference file with 12 currencies from 2019 to 2022.
        fx_file = "fx_rate.csv"

    main(sales_file, fx_file)

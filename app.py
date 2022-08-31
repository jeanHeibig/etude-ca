import streamlit as st

from analysis import main


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

# Title
st.title("Analyse du Chiffre d'Affaires")

col1, col2 = st.columns(2)
uploaded_file = col1.file_uploader("Veuillez entrer le fichier des ventes", type="csv",
    help="""
        Doit contenir les colonnes :
        1. *Year* : l'année
        2. *Reference* : le code produit
        3. *Currency* : le code de la devise locale (ex. EUR ou USD, etc.)
        4. *Price* : le prix **en devise locale**
        5. *Quantity* : la quantité de produits vendus sur l'année
    """
)
if uploaded_file is None:
    # We use a default file with fake data if no file is given by the user.
    uploaded_file = "test_real.csv"
fx_file = col2.file_uploader("Taux de change personnalisés", type="csv",
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

main(uploaded_file, fx_file)

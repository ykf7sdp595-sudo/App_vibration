import io
import csv
from pathlib import Path
from scipy.signal import find_peaks

import pandas as pd
import streamlit as st
import plotly.express as px

st.set_page_config(page_title="Lecteur CSV d'essais", layout="wide")
st.title("Lecteur CSV — données d'essais")
st.caption("Import, exploration, filtrage et tracé de courbes à partir d'un fichier CSV.")

@st.cache_data(show_spinner=False)
def load_csv(file_bytes: bytes, filename: str) -> pd.DataFrame:
    """Essaie plusieurs encodages et séparateurs courants."""
    last_error = None
    # "\t" dans le code Python représente une vraie tabulation.
    # On teste aussi les séparateurs courants sans passer de séparateur multi-caractères.
    for encoding in ("utf-8-sig", "cp1252", "latin-1"):
        for sep in (",", ";", "\t", "|"):
            try:
                df = pd.read_csv(
                    io.BytesIO(file_bytes),
                    encoding=encoding,
                    sep=sep,
                    engine="c",
                    low_memory=False,
                    on_bad_lines="error",
                )
                # Ignore les essais qui n'ont pas correctement séparé les colonnes.
                if len(df.columns) > 1:
                    df.columns = [str(c).strip() for c in df.columns]
                    return df
            except Exception as exc:
                last_error = exc

    # Dernier recours : laisse Python détecter le séparateur à partir d'un échantillon.
    for encoding in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            sample = file_bytes[:65536].decode(encoding, errors="replace")
            dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
            df = pd.read_csv(
                io.BytesIO(file_bytes),
                encoding=encoding,
                sep=dialect.delimiter,
                engine="python",
                on_bad_lines="warn",
            )
            if len(df.columns) > 1:
                df.columns = [str(c).strip() for c in df.columns]
                return df
        except Exception as exc:
            last_error = exc

    raise ValueError(
        "Impossible de lire ce CSV. Vérifie son séparateur, son encodage "
        f"et la cohérence des lignes. Détail : {last_error}"
    )

uploaded = st.file_uploader("Choisir un fichier CSV", type=["csv", "txt"])

if uploaded is None:
    st.info("Importe un fichier CSV pour commencer. Le fichier est traité dans cette session.")
    st.markdown("""
    **Fonctions disponibles**
    - Tableau interactif avec tri et recherche via les filtres de colonnes.
    - Filtrage numérique sur les colonnes choisies.
    - Courbes avec choix libre des axes X et Y.
    - Statistiques descriptives et export des données filtrées.
    """)
    st.stop()

try:
    df = load_csv(uploaded.getvalue(), uploaded.name)
except Exception as exc:
    st.error(str(exc))
    st.stop()

if df.empty:
    st.warning("Le fichier ne contient aucune ligne.")
    st.stop()

# Convertit en numérique les colonnes qui semblent être des nombres,
# sans écraser les colonnes contenant réellement du texte.
for col in df.columns:
    if df[col].dtype == "object":
        converted = pd.to_numeric(df[col].astype(str).str.replace(",", ".", regex=False), errors="coerce")
        if converted.notna().mean() >= 0.85:
            df[col] = converted

numeric_cols = df.select_dtypes(include="number").columns.tolist()

m1, m2, m3, m4 = st.columns(4)
m1.metric("Lignes", f"{len(df):,}".replace(",", " "))
m2.metric("Colonnes", len(df.columns))
m3.metric("Colonnes numériques", len(numeric_cols))
m4.metric("Valeurs manquantes", f"{int(df.isna().sum().sum()):,}".replace(",", " "))

with st.sidebar:
    st.header("Options")
    st.write(f"**Fichier :** {uploaded.name}")
    selected_columns = st.multiselect(
        "Colonnes à afficher",
        options=df.columns.tolist(),
        default=df.columns.tolist(),
    )
    st.divider()
    st.subheader("Filtres numériques")
    filter_cols = st.multiselect(
        "Colonnes à filtrer",
        options=numeric_cols,
        default=[],
        help="Chaque filtre conserve les lignes comprises entre les deux bornes.",
    )

filtered = df.copy()
for col in filter_cols:
    series = pd.to_numeric(filtered[col], errors="coerce")
    finite = series.dropna()
    if finite.empty:
        continue
    low, high = float(finite.min()), float(finite.max())
    if low == high:
        st.sidebar.caption(f"{col} : valeur constante ({low:g})")
        continue
    chosen = st.sidebar.slider(
        col,
        min_value=low,
        max_value=high,
        value=(low, high),
        key=f"filter_{col}",
    )
    filtered = filtered[series.between(chosen[0], chosen[1])]

tab_data, tab_plot, tab_stats = st.tabs(["Données", "Courbes", "Statistiques"])

with tab_data:
    st.subheader("Tableau des données")
    search_text = st.text_input("Recherche textuelle dans les lignes", placeholder="Ex. : une valeur ou un terme")
    view = filtered
    if search_text:
        mask = view.astype(str).apply(
            lambda col: col.str.contains(search_text, case=False, na=False, regex=False)
        ).any(axis=1)
        view = view[mask]
    cols_to_show = [c for c in selected_columns if c in view.columns]
    if not cols_to_show:
        st.warning("Sélectionne au moins une colonne dans la barre latérale.")
    else:
        st.caption(f"{len(view):,} ligne(s) affichée(s) après filtrage.".replace(",", " "))
        st.dataframe(view[cols_to_show], use_container_width=True, height=520)
    csv_bytes = filtered.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        "Télécharger les données filtrées (CSV)",
        data=csv_bytes,
        file_name=f"{Path(uploaded.name).stem}_filtre.csv",
        mime="text/csv",
    )

with tab_plot:
    st.subheader("Tracer une ou plusieurs séries")
    if len(numeric_cols) < 2:
        st.warning("Il faut au moins deux colonnes numériques pour tracer une courbe.")
    else:
        default_x = "Frequency" if "Frequency" in numeric_cols else numeric_cols[0]
        x_col = st.selectbox(
            "Axe X",
            options=numeric_cols,
            index=numeric_cols.index(default_x),
        )
        default_y = [
            c for c in ("Demand1 (G²/Hz)", "Control1 (G²/Hz)", "Channel 1 (G RMS)")
            if c in numeric_cols and c != x_col
        ]
        if not default_y:
            default_y = [c for c in numeric_cols if c != x_col][:1]
        y_cols = st.multiselect(
            "Série(s) sur l'axe Y",
            options=[c for c in numeric_cols if c != x_col],
            default=default_y,
        )
        log_x = st.checkbox("Échelle logarithmique sur X", value=False)
        log_y = st.checkbox("Échelle logarithmique sur Y", value=False)
        max_global = st.checkbox("Afficher le maximum global de chaque série", value=False)
        min_global = st.checkbox("Afficher le minimum global de chaque série", value=False)
        max_local = st.checkbox("Afficher les maxima locaux de chaque série", value=False)
        min_local = st.checkbox("Afficher les minima locaux de chaque série", value=False)
        max_points = st.slider("Nombre maximal de points affichés", 1000, 30000, 10000, step=1000)
        
        if y_cols:
            plot_df = filtered[[x_col] + y_cols].dropna(subset=[x_col]).copy()
            plot_df = plot_df.sort_values(x_col)
            if len(plot_df) > max_points:
                # Échantillonnage régulier pour garder une interface réactive.
                step = max(1, len(plot_df) // max_points)
                plot_df = plot_df.iloc[::step]
            if log_x:
                plot_df = plot_df[plot_df[x_col] > 0]
            if log_y:
                for c in y_cols:
                    plot_df = plot_df[plot_df[c] > 0]
            if plot_df.empty:
                st.warning("Aucun point exploitable avec ces filtres et échelles.")
            else:
                fig = px.line(plot_df, x=x_col, y=y_cols)
                if log_x:
                    fig.update_xaxes(type="log")
                if log_y:
                    fig.update_yaxes(type="log")
                st.plotly_chart(fig, use_container_width=True)
                st.caption(f"{len(plot_df):,} points tracés.".replace(",", " "))
        else:
            st.info("Choisis au moins une série Y.")

with tab_stats:
    st.subheader("Statistiques descriptives")
    if numeric_cols:
        st.dataframe(filtered[numeric_cols].describe().T, use_container_width=True)
    st.subheader("Valeurs manquantes par colonne")
    missing = filtered.isna().sum().rename("Valeurs manquantes").to_frame()
    missing["Pourcentage"] = (filtered.isna().mean() * 100).round(2)
    st.dataframe(missing, use_container_width=True)

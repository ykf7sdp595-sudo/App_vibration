import hashlib
from pathlib import Path

import pandas as pd
import streamlit as st
import plotly.express as px
from chart_controls import draw_chart

from plotting import reduce_plot_points
from csv_reader import read_csv_robust, convert_numeric_columns
from column_registry import build_column_registry
from sweeps import candidate_pairs, compatible_pairs, analyze_sweep
import plotly.graph_objects as go
from specialized_tabs import (ui_vibrations, ui_chocs, ui_psd,
                              plot_axis_controls, apply_plot_axis_controls)

st.set_page_config(page_title="Lecteur CSV d'essais", page_icon="📈", layout="wide")
st.title("📈 Vibrations — données d'essais")
st.caption("Import, exploration, filtrage et tracé de courbes à partir de plusieurs fichiers CSV.")
with st.expander("👋 Premiers pas", expanded=False):
    st.markdown("1. Importez un ou plusieurs fichiers dans le volet latéral.\n"
                "2. Choisissez un fichier puis une analyse.\n"
                "3. Utilisez les réglages sous chaque graphique et l’appareil photo pour exporter en PNG.")

@st.cache_data(show_spinner=False, max_entries=16)
def load_csv(file_bytes: bytes, filename: str):
    """Lecture sans perte silencieuse de lignes, avec diagnostic des irrégularités."""
    df, report = read_csv_robust(file_bytes)
    df = convert_numeric_columns(df)
    return df, report, build_column_registry(df, report)

def render_file(uploaded, namespace, import_diagnostics):
    """Analyse indépendante : aucune concaténation des essais ni état partagé."""
    file_digest = hashlib.sha256(uploaded.getvalue()).hexdigest()
    try:
        df, csv_report, registry = load_csv(uploaded.getvalue(), uploaded.name)
    except Exception as exc:
        st.error(str(exc))
        return

    if df.empty:
        st.warning("Le fichier ne contient aucune ligne.")
        return

    st.caption(f"CSV : {csv_report['encoding']} ; séparateur : {csv_report['delimiter']!r} ; "
               f"{csv_report['data_rows']} lignes conservées.")
    if csv_report['extra_empty_rows']:
        import_diagnostics.append(f"{uploaded.name} : {csv_report['extra_empty_rows']} ligne(s) contiennent des champs finaux vides supplémentaires, ignorés sans supprimer de ligne.")
    if csv_report['short_rows']:
        import_diagnostics.append(f"{uploaded.name} : {csv_report['short_rows']} ligne(s) plus courtes que l'en-tête : cellules manquantes laissées vides (aucune valeur inventée).")
    if csv_report['extra_nonempty_rows']:
        import_diagnostics.append(f"{uploaded.name} : {csv_report['extra_nonempty_rows']} ligne(s) contiennent des champs supplémentaires non vides, conservés dans des colonnes dédiées. Vérifier leur alignement avant toute analyse scientifique.")
    if csv_report['duplicate_headers']:
        st.info(f"{csv_report['duplicate_headers']} en-tête(s) répété(s) : "
                "les colonnes ont été distinguées par leur position, sans fusion.")

    # Les groupes CSV peuvent avoir 2000, 4096 ou 7572 valeurs utiles.
    # On évalue la conversion uniquement sur les cellules présentes.
    numeric_cols = df.select_dtypes(include="number").columns.tolist()

    active_view = st.radio("Analyse", ["SWEEPS", "VIBRATIONS", "CHOCS", "PSD", "Courbe libre"], horizontal=True, key=namespace + ("active_view"))
    primary_chart_slot = st.container()

    # Étape 2 : registre informatif uniquement, sans changer les sélections actuelles.
    with st.expander("Registre des colonnes et unités", expanded=False):
        st.caption("Indices à partir de 0 · noms bruts conservés · unités non devinées. "
                   "Les groupes sont reconnus par des séquences d'en-têtes exactes.")
        st.dataframe(pd.DataFrame(registry).drop(columns=["colonne_interne"]),
                     width="stretch", hide_index=True)
        warnings = [c for c in registry if c["statut_unité"] in ("ambiguë", "alerte_encodage")]
        if warnings:
            st.warning("Unité ambiguë ou encodage suspect : " +
                       ", ".join(f"[{c['index']}] {c['nom_brut']}" for c in warnings))


    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Lignes", f"{len(df):,}".replace(",", " "))
    m2.metric("Colonnes", len(df.columns))
    m3.metric("Colonnes numériques", len(numeric_cols))
    m4.metric("Valeurs manquantes", f"{int(df.isna().sum().sum()):,}".replace(",", " "))

    with st.expander("Filtres du fichier", expanded=False):
        st.header("Options")
        st.write(f"**Fichier :** {uploaded.name}")
        st.subheader("Filtres numériques")
        filter_cols = st.multiselect(
            "Colonnes à filtrer",
            options=numeric_cols,
            default=[],
            help="Chaque filtre conserve les lignes comprises entre les deux bornes.",
            key=namespace + "filter_columns")

        filtered = df
        for col in filter_cols:
            series = pd.to_numeric(filtered[col], errors="coerce")
            finite = series.dropna()
            if finite.empty:
                continue
            low, high = float(finite.min()), float(finite.max())
            if low == high:
                st.caption(f"{col} : valeur constante ({low:g})")
                continue
            chosen = st.slider(
                col,
                min_value=low,
                max_value=high,
                value=(low, high),
                   key=namespace + (f"filter_{col}"),
            )
            filtered = filtered[series.between(chosen[0], chosen[1])]

    if active_view == "SWEEPS":
        st.subheader("SWEEPS — fréquence en fonction du temps")
        pairs = candidate_pairs(df, registry)
        ready = compatible_pairs(df, registry)
        if not pairs:
            st.info("Aucun couple temps/fréquence déclaré trouvé dans ce CSV. L’onglet Courbe libre reste disponible.")
        else:
            # Les couples compatibles sont proposés d'abord ; les autres restent
            # sélectionnables pour afficher un refus explicite et traçable.
            ordered = ready + [pair for pair in pairs if pair not in ready]
            def describe_pair(pair):
                t, f = pair
                return (f"Temps [{t}] {registry[t]['nom_brut']}  /  "
                        f"Fréquence [{f}] {registry[f]['nom_brut']}")
            pair = st.selectbox("Couple temps / fréquence", ordered,
                                format_func=describe_pair, key=namespace + ("sweeps_pair"))
            t_idx, f_idx = pair
            result = analyze_sweep(df, registry, t_idx, f_idx)
            if not result.ok:
                st.warning(result.message)
            else:
                tr, fr = result.time, result.frequency
                assert tr is not None and fr is not None
                t_unit = registry[t_idx]['unité_normalisée']
                f_unit = registry[f_idx]['unité_normalisée']
                is_reference_setpoint = registry[f_idx]['rôle_proposé'] == 'fréquence de consigne (confirmée profil)'
                y_title = ("Setpoint frequency (" if is_reference_setpoint else "Frequency (") + f_unit + ")"
                st.caption(f"{len(tr):,} points · ordre d'acquisition conservé · "
                           f"temps [{t_idx}], fréquence [{f_idx}]".replace(',', ' '))
                axis_options=plot_axis_controls(
                    f"Sweep — {registry[t_idx]['nom_brut']} / {registry[f_idx]['nom_brut']}",
                    registry[t_idx]['nom_brut'],y_title,tr,fr,
                    f"sweeps_axis_{t_idx}_{f_idx}",
                    log_x_default=False,log_y_default=True, namespace=namespace)
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=tr, y=fr, mode="lines", name=y_title))
                apply_plot_axis_controls(fig,axis_options)
                fig.update_layout(hovermode="closest")
                draw_chart(fig, key=namespace + "sweeps_chart", chart_slot=primary_chart_slot)
                a, b, c = st.columns(3)
                a.metric("Fréquence minimale", f"{fr.min():g} {f_unit}")
                b.metric("Fréquence maximale", f"{fr.max():g} {f_unit}")
                c.metric("Changements de sens", result.n_reversals)
                st.caption(f"Pas Δt : {result.dt_min:g} à {result.dt_max:g} {t_unit} · "
                           f"df/dt : {result.rate_min:g} à {result.rate_max:g} Hz/min · "
                           f"vitesse logarithmique : {result.octave_rate_min:g} à "
                           f"{result.octave_rate_max:g} octaves/min (indicateurs dérivés)")
                if result.dt_max is not None and result.dt_min is not None and result.dt_max > result.dt_min * 1.01:
                    st.info("Le pas de temps varie ; aucune interpolation ni rééchantillonnage n'est appliqué.")
                if result.n_reversals:
                    st.info("La fréquence comporte des changements de sens : tracé dans l'ordre du fichier, sans tri.")
                import json
                st.download_button('Exporter les paramètres SWEEPS (JSON)',
                    data=json.dumps({'source':'CSV','temps':registry[t_idx]['nom_brut'],
                        'temps_index':t_idx,'frequence':registry[f_idx]['nom_brut'],
                        'frequence_index':f_idx,'points':len(tr),'unite_temps':t_unit,
                        'unite_frequence':f_unit,
                        'axe_logarithmique':axis_options['log_y']},
                        ensure_ascii=False,indent=2),file_name='sweeps_parametres.json',
                        mime='application/json',key=namespace + ('sweeps_export'))

    if active_view == "VIBRATIONS":
        ui_vibrations(df, registry, csv_report, namespace=namespace, chart_slot=primary_chart_slot)

    if active_view == "CHOCS":
        ui_chocs(df, registry, csv_report, namespace=namespace, chart_slot=primary_chart_slot)

    if active_view == "PSD":
        ui_psd(df, registry, csv_report, namespace=namespace, chart_slot=primary_chart_slot)

    if active_view == "Courbe libre":
        st.subheader("Tracer une ou plusieurs séries")
        if len(numeric_cols) < 2:
            st.warning("Il faut au moins deux colonnes numériques pour tracer une courbe.")
        else:
            default_x = "Frequency" if "Frequency" in numeric_cols else numeric_cols[0]
            x_col = st.selectbox(
                "Axe X",
                options=numeric_cols,
                index=numeric_cols.index(default_x),
                key=namespace + "free_x")
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
                key=namespace + "free_y")
        
            max_points = st.slider("Nombre maximal de points affichés", 1000, 30000, 10000, step=1000, key=namespace + "free_max_points")

            if y_cols:
                axis_options=plot_axis_controls(
                    f"Free plot — {x_col} / {', '.join(y_cols)}",
                    x_col,', '.join(y_cols),filtered[x_col].to_numpy(),
                    [filtered[col].to_numpy() for col in y_cols],
                    'free_axis_'+file_digest[:12]+'_'+str(numeric_cols.index(x_col)), namespace=namespace)
                plot_df = filtered[[x_col] + y_cols].dropna(subset=[x_col]).copy()
                plot_df = plot_df.sort_values(x_col)
                if axis_options['log_x']:
                    plot_df = plot_df[plot_df[x_col] > 0]
                if axis_options['log_y']:
                    for c in y_cols:
                        plot_df = plot_df[plot_df[c] > 0]
                original_count = len(plot_df)
                try:
                    plot_df = reduce_plot_points(plot_df, y_cols, max_points)
                except ValueError as exc:
                    st.warning(str(exc))
                    plot_df = plot_df.iloc[:0]
                if original_count > len(plot_df):
                    st.caption("Affichage réduit avec conservation des extrema par intervalle ; calculs et export utilisent les données complètes.")
                if plot_df.empty:
                    st.warning("Aucun point exploitable avec ces filtres et échelles.")
                else:
                    fig = px.line(plot_df, x=x_col, y=y_cols)
                    apply_plot_axis_controls(fig,axis_options)
                    draw_chart(fig, key=namespace + "free_chart", chart_slot=primary_chart_slot)
                    st.caption(f"{len(plot_df):,} points tracés.".replace(",", " "))
            else:
                st.info("Choisis au moins une série Y.")

    # Export conservé après suppression de l'onglet « Données ».
    if st.button("Préparer l’export CSV", key=namespace + "prepare_export"):
        csv_bytes = filtered.to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            "Télécharger les données filtrées (CSV)", data=csv_bytes,
            file_name=f"{Path(uploaded.name).stem}_filtre.csv", mime="text/csv",
            on_click="ignore",
            key=namespace + "download_csv")


with st.sidebar:
    st.header("📂 Fichiers de mesures")
    uploaded_files = st.file_uploader(
        "Choisir un ou plusieurs fichiers CSV", type=["csv", "txt"],
        accept_multiple_files=True,
    )
    st.caption("Sélectionnez plusieurs fichiers pour comparer les essais.")
    import_diagnostics_slot = st.container()
    st.divider()
    st.caption("🔒 Données traitées localement · Réglages temporaires.")

# Nom + contenu + occurrence distinguent aussi les noms et contenus identiques.
file_entries = []
occurrences = {}
for uploaded in uploaded_files:
    digest = hashlib.sha256(
        uploaded.name.encode("utf-8") + b"\0" + uploaded.getvalue()
    ).hexdigest()
    occurrence = occurrences.get(digest, 0) + 1
    occurrences[digest] = occurrence
    file_entries.append((uploaded, f"csv_{digest}_{occurrence}_"))

active_namespaces = tuple(namespace for _, namespace in file_entries)
for key in list(st.session_state):
    if isinstance(key, str) and key.startswith("csv_") and not key.startswith(active_namespaces):
        del st.session_state[key]

if not file_entries:
    st.info("👈 Importez un ou plusieurs CSV dans le volet latéral pour commencer.")
    st.stop()

st.caption(f"{len(file_entries)} fichier(s) importé(s) · analyses et exports indépendants par fichier.")
tabs = st.tabs([f"{index}. {uploaded.name}" for index, (uploaded, _) in enumerate(file_entries, 1)])
import_diagnostics = []
for tab, (uploaded, namespace) in zip(tabs, file_entries):
    with tab:
        st.subheader(uploaded.name)
        render_file(uploaded, namespace, import_diagnostics)

if import_diagnostics:
    with import_diagnostics_slot:
        with st.expander(f"⚠️ Informations d’import ({len(import_diagnostics)})", expanded=False):
            for diagnostic in import_diagnostics:
                st.warning(diagnostic)

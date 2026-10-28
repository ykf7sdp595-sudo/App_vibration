import os
import sys
import streamlit as st
import numpy as np
import skrf as rf
import plotly.graph_objects as go
from PIL import Image

# Configuration de la page Streamlit
st.set_page_config(
    page_title="Banc de Qualification RF, TDR & Œil - Nicomatic",
    page_icon="📊",
    layout="wide"
)

# --- CHARGEMENT DES FICHIERS ---
@st.cache_data
def charger_base_donnees_complete(dossier_principal):
    donnees_projets = {}
    if not os.path.exists(dossier_principal):
        return donnees_projets
        
    for racine, sous_dossiers, fichiers in os.walk(dossier_principal):
        for fichier in fichiers:
            if fichier.endswith((".s1p", ".s2p", ".s4p")):
                chemin_complet = os.path.join(racine, fichier)
                nom_gamme = os.path.basename(racine)
                nom_fichier = os.path.splitext(fichier)[0]
                cle_unique = f"{nom_gamme} / {nom_fichier}"
                
                try:
                    reseau = rf.Network(chemin_complet)
                    donnees_projets[cle_unique] = {
                        'freq': reseau.f / 1e9,          # Fréquence en GHz
                        'nb_ports': reseau.number_of_ports,
                        's_db': reseau.s_db,             # Magnitude en dB
                        's_complex': reseau.s            # Matrice complexe (magnitude + phase pour TDR / Oeil)
                    }
                except Exception as e:
                    print(f"Erreur {fichier}: {e}")
    return donnees_projets

if getattr(sys, 'frozen', False):
    dossier_exe = os.path.dirname(sys.executable)
    chemin_relatif = os.path.join(dossier_exe, "High-speed_Fichiers SNP_CSV")
    if os.path.exists(chemin_relatif):
        dossier_principal = chemin_relatif
    else:
        dossier_principal = r"X:\Tests & Mesures\Technique\Infos techniques\High-speed_Fichiers SNP_CSV"
    logo_path = os.path.join(dossier_exe, "logo.png")
else:
    dossier_principal = r"X:\Tests & Mesures\Technique\Infos techniques\High-speed_Fichiers SNP_CSV"
    logo_path = "logo.png"

with st.spinner("Chargement des fichiers S-parameters..."):
    base_donnees = charger_base_donnees_complete(dossier_principal)

NICOMATIC_BLUE = "#0095D9"

# Mapping des indices pour les modes mixtes (standard Ceyear / BBAL)
mapping_indices_mixte = {
    "Sdd11": (0, 0), "Sdc11": (0, 1), "Sdd12": (0, 2), "Sdc12": (0, 3),
    "Scd11": (1, 0), "Scc11": (1, 1), "Scd12": (1, 2), "Scc12": (1, 3),
    "Sdd21": (2, 0), "Sdc21": (2, 1), "Sdd22": (2, 2), "Sdc22": (2, 3),
    "Scd21": (3, 0), "Scc21": (3, 1), "Scd22": (3, 2), "Scc22": (3, 3),
}

# ==============================================================================
# BARRE LATÉRALE : SÉLECTION GLOBALE, MATH, VISIBILITÉ, COULEURS & LISSAGE
# ==============================================================================
st.sidebar.header("⚙️ Sélection & Courbes")

# 1. Sélection des connecteurs
liste_connecteurs = list(base_donnees.keys())
connecteurs_selectionnes = st.sidebar.multiselect(
    "Choisir les connecteurs :", 
    liste_connecteurs,
    default=liste_connecteurs[:2] if len(liste_connecteurs) >= 2 else liste_connecteurs
)

# 2. Choix dynamique des paramètres S (Single-Ended & Mode Mixte unifiés)
parametres_standard = [f"S{i}{j}" for i in range(1, 5) for j in range(1, 5)]
parametres_mixtes = [
    "Sdd11", "Sdd12", "Sdd21", "Sdd22",
    "Sdc11", "Sdc12", "Sdc21", "Sdc22",
    "Scd11", "Scd12", "Scd21", "Scd22",
    "Scc11", "Scc12", "Scc21", "Scc22"
]
tous_les_parametres = parametres_standard + parametres_mixtes

parametres_selectionnes = st.sidebar.multiselect(
    "Paramètres S à tracer (Standard ou Mode Mixte) :",
    tous_les_parametres,
    default=["Sdd11", "Sdd21"] if "Sdd21" in tous_les_parametres else ["S21"]
)

# Génération de la liste de base de toutes les courbes standard disponibles
courbes_disponibles_base = []
for nom in connecteurs_selectionnes:
    info = base_donnees[nom]
    nb_ports = info['nb_ports']
    for param in parametres_selectionnes:
        if param.startswith("S") and len(param) == 3:
            i, j = int(param[1]), int(param[2])
            if i <= nb_ports and j <= nb_ports:
                courbes_disponibles_base.append(f"{nom} [{param}]")
        elif param.startswith(("Sdd", "Sdc", "Scd", "Scc")) and nb_ports >= 2:
            courbes_disponibles_base.append(f"{nom} [{param}]")

# 3. Gestion Dynamique des Courbes Mathématiques (Récursives)
st.sidebar.markdown("---")
st.sidebar.markdown("### 🧮 Menu Opérations Mathématiques")
if "custom_curves" not in st.session_state:
    st.session_state.custom_curves = {}

options_math_sources = courbes_disponibles_base + [f"Math: {k}" for k in st.session_state.custom_curves.keys()]

with st.sidebar.expander("➕ Créer une courbe mathématique"):
    nom_nouvelle_courbe = st.text_input("Nom de la nouvelle courbe", value="Delta_Courbe")
    
    if options_math_sources:
        c_src1 = st.selectbox("Courbe 1 (A)", options=options_math_sources, key="math_c1")
        operation = st.selectbox("Opération", ["Soustraction (A - B)", "Addition (A + B)", "Multiplication (A * B)", "Division (A / B)"], key="math_op")
        c_src2 = st.selectbox("Courbe 2 (B)", options=options_math_sources, key="math_c2")
        
        if st.button("Calculer et Ajouter la Courbe"):
            if nom_nouvelle_courbe.strip():
                st.session_state.custom_curves[nom_nouvelle_courbe.strip()] = {
                    "c1": c_src1,
                    "op": operation,
                    "c2": c_src2
                }
                st.success(f"Courbe '{nom_nouvelle_courbe}' créée !")
                st.rerun()
            else:
                st.error("Veuillez entrer un nom valide.")

if st.session_state.custom_curves:
    if st.sidebar.button("🗑️ Effacer toutes les courbes math."):
        st.session_state.custom_curves = {}
        st.rerun()

toutes_les_courbes_potentielles = courbes_disponibles_base + [f"Math: {k}" for k in st.session_state.custom_curves.keys()]

# 4. Visibilité des Courbes
st.sidebar.markdown("---")
st.sidebar.markdown("### 👁️ Visibilité des Courbes")
if "courbes_visibles" not in st.session_state:
    st.session_state.courbes_visibles = []

if "known_curves" not in st.session_state:
    st.session_state.known_curves = []

for c in toutes_les_courbes_potentielles:
    if c not in st.session_state.known_curves:
        st.session_state.known_curves.append(c)
        st.session_state.courbes_visibles.append(c)

st.session_state.courbes_visibles = [c for c in st.session_state.courbes_visibles if c in toutes_les_courbes_potentielles]

courbes_visibles_selectionnees = st.sidebar.multiselect(
    "Courbes actives à afficher :",
    options=toutes_les_courbes_potentielles,
    default=st.session_state.courbes_visibles
)
st.session_state.courbes_visibles = courbes_visibles_selectionnees

# 5. Style & Couleurs des Courbes
st.sidebar.markdown("---")
st.sidebar.markdown("### 🎨 Style & Couleurs")
afficher_marqueurs = st.sidebar.checkbox("Afficher tous les points (maillage)", value=False)
mode_trace = "lines+markers" if afficher_marqueurs else "lines"

if "curve_colors" not in st.session_state:
    st.session_state.curve_colors = {}

default_colors_palette = ["#0095D9", "#FF5733", "#2ECC71", "#9B59B6", "#F1C40F", "#E74C3C", "#1ABC9C"]
with st.sidebar.expander("🎨 Modifier les couleurs des courbes"):
    for idx, nom_c in enumerate(toutes_les_courbes_potentielles):
        if nom_c not in st.session_state.curve_colors:
            st.session_state.curve_colors[nom_c] = default_colors_palette[idx % len(default_colors_palette)]
        st.session_state.curve_colors[nom_c] = st.color_picker(
            f"{nom_c}", 
            value=st.session_state.curve_colors[nom_c], 
            key=f"col_{nom_c}"
        )

# 6. Menu Lissage (Smooth) - S'applique en RF et en TDR
st.sidebar.markdown("---")
st.sidebar.markdown("### 📈 Menu Lissage (Smooth)")
if "smooth_list" not in st.session_state:
    st.session_state.smooth_list = []

col_add_s, col_clr_s = st.sidebar.columns(2)
if col_add_s.button("➕ Ajout Lissage"):
    st.session_state.smooth_list.append({
        "pourcentage": 5.0,
        "courbes": toutes_les_courbes_potentielles.copy()
    })
if col_clr_s.button("🗑️ Effacer Lissage"):
    st.session_state.smooth_list = []

smooth_configures = []
for idx, s in enumerate(st.session_state.smooth_list):
    st.sidebar.markdown(f"**Lissage {idx + 1}**")
    pourcentage = st.sidebar.slider("Pourcentage (%)", min_value=1.0, max_value=30.0, value=float(s["pourcentage"]), step=1.0, key=f"smooth_pct_{idx}")
    s_curves = st.sidebar.multiselect("Courbes cibles (Lissage)", options=toutes_les_courbes_potentielles, default=[c for c in s["courbes"] if c in toutes_les_courbes_potentielles], key=f"curves_s_{idx}")
    
    if st.sidebar.button(f"❌ Supprimer Lissage {idx + 1}", key=f"del_s_{idx}"):
        st.session_state.smooth_list.pop(idx)
        st.rerun()
        
    smooth_configures.append({
        "pourcentage": pourcentage,
        "courbes": s_curves
    })


# ==============================================================================
# FONCTIONS D'EXTRACTION ET DE CALCULS PHYSIQUES (RF, TDR IFFT, OEIL)
# ==============================================================================
def get_curve_data(nom_courbe, connecteurs_sel, params_sel, db_dict, depth=0):
    """
    Retourne (freq_ghz, y_db, s_complex) pour n'importe quelle courbe standard ou mathématique,
    même si son paramètre S n'est pas coché dans la barre latérale.
    """
    if depth > 10:
        return None, None, None
        
    if nom_courbe.startswith("Math: "):
        key_math = nom_courbe.replace("Math: ", "")
        if key_math in st.session_state.custom_curves:
            cfg = st.session_state.custom_curves[key_math]
            freq_a, y_a, cplx_a = get_curve_data(cfg["c1"], connecteurs_sel, params_sel, db_dict, depth + 1)
            freq_b, y_b, cplx_b = get_curve_data(cfg["c2"], connecteurs_sel, params_sel, db_dict, depth + 1)
            
            if freq_a is not None and freq_b is not None:
                y_b_interp = np.interp(freq_a, freq_b, y_b)
                if "Soustraction" in cfg["op"]:
                    y_res = y_a - y_b_interp
                elif "Addition" in cfg["op"]:
                    y_res = y_a + y_b_interp
                elif "Multiplication" in cfg["op"]:
                    y_res = y_a * y_b_interp
                elif "Division" in cfg["op"]:
                    y_res = np.divide(y_a, y_b_interp, out=np.zeros_like(y_a), where=y_b_interp!=0)
                else:
                    y_res = y_a - y_b_interp
                    
                if cplx_a is not None:
                    phase_a = np.unwrap(np.angle(cplx_a))
                    cplx_res = (10 ** (y_res / 20.0)) * np.exp(1j * phase_a)
                else:
                    cplx_res = (10 ** (y_res / 20.0)).astype(complex)
                return freq_a, y_res, cplx_res
        return None, None, None
    
    # Extraction directe par analyse du nom "Connecteur [Param]"
    if " [" in nom_courbe and nom_courbe.endswith("]"):
        nom_conn, param_part = nom_courbe.rsplit(" [", 1)
        param = param_part[:-1]
        if nom_conn in db_dict:
            info = db_dict[nom_conn]
            freq = info['freq']
            s_db = info['s_db']
            s_cplx = info['s_complex']
            nb_ports = info['nb_ports']
            
            if param.startswith("S") and len(param) == 3:
                i, j = int(param[1]), int(param[2])
                if i <= nb_ports and j <= nb_ports:
                    return freq, s_db[:, i - 1, j - 1].copy(), s_cplx[:, i - 1, j - 1].copy()
            elif param in mapping_indices_mixte and nb_ports >= 2:
                r_idx, c_idx = mapping_indices_mixte[param]
                if r_idx < s_db.shape[1] and c_idx < s_db.shape[2]:
                    return freq, s_db[:, r_idx, c_idx].copy(), s_cplx[:, r_idx, c_idx].copy()
    return None, None, None


def calculer_points_marqueur(x_arr, y_arr, m_cfg, unite_x="GHz", unite_y="dB"):
    """
    Calcule les points (x, y) d'un marqueur selon son mode :
    - Franchissement de niveau / Impédance
    - Par Fréquence / Position
    - Minimum (Min), Maximum (Max) ou Min & Max simultanés (sur toute la courbe ou dans une plage [x_min, x_max])
    Retourne une liste de tuples : (label_point, desc_cible, x_val, y_val, color_marker)
    """
    m_type = m_cfg["type"]
    vals = m_cfg["valeurs"]
    num_base = m_cfg["numero"]
    points_trouves = []

    if "Minimum" in m_type or "Maximum" in m_type or "Min & Max" in m_type:
        # Si l'utilisateur a saisi 2 valeurs (ex: "1, 10"), on filtre dans cette plage
        if len(vals) >= 2:
            x_min_search, x_max_search = min(vals[0], vals[1]), max(vals[0], vals[1])
            masque = (x_arr >= x_min_search) & (x_arr <= x_max_search)
            plage_str = f"[{x_min_search} - {x_max_search} {unite_x}]"
        else:
            masque = np.ones_like(x_arr, dtype=bool)
            plage_str = f"Toute la courbe"

        if not np.any(masque):
            return points_trouves

        indices_masque = np.where(masque)[0]
        y_sub = y_arr[masque]

        if "Minimum" in m_type or "Min & Max" in m_type:
            idx_min = indices_masque[int(np.argmin(y_sub))]
            lbl = f"{num_base}_Min" if "Min & Max" in m_type else f"{num_base} (Min)"
            points_trouves.append((lbl, f"Min ({plage_str})", float(x_arr[idx_min]), float(y_arr[idx_min]), "#00E676"))

        if "Maximum" in m_type or "Min & Max" in m_type:
            idx_max = indices_masque[int(np.argmax(y_sub))]
            lbl = f"{num_base}_Max" if "Min & Max" in m_type else f"{num_base} (Max)"
            points_trouves.append((lbl, f"Max ({plage_str})", float(x_arr[idx_max]), float(y_arr[idx_max]), "#FF1744"))

    else:
        for v_idx, cible in enumerate(vals):
            num_m = f"{num_base}.{v_idx + 1}" if len(vals) > 1 else num_base
            if "Franchissement" in m_type:
                signs = np.sign(y_arr - cible)
                crossings = np.where(np.diff(signs))[0]
                idx_trouve = int(crossings[0]) if len(crossings) > 0 else int(np.abs(y_arr - cible).argmin())
                cible_str = f"{cible} {unite_y}"
            else:
                idx_trouve = int(np.abs(x_arr - cible).argmin())
                cible_str = f"{cible} {unite_x}"

            points_trouves.append((num_m, cible_str, float(x_arr[idx_trouve]), float(y_arr[idx_trouve]), "red"))

    return points_trouves


def calculer_tdr_lowpass_step(freq_ghz, s_complex, z0=50.0, beta_window=6.0, n_fft=16384):
    """
    Reconstruit la réponse indicielle Low-Pass Step (Gamma(t) et Impédance Z(t))
    calibrée exactement sur l'échelle d'impédance VNA Ceyear.
    """
    f_hz = freq_ghz * 1e9
    if len(f_hz) < 2:
        return None, None, None
        
    df = f_hz[1] - f_hz[0]
    if df <= 0:
        df = (f_hz[-1] - f_hz[0]) / max(1, len(f_hz) - 1)
        
    f_grid = np.arange(0.0, f_hz[-1] + df * 0.5, df)
    n_freq = len(f_grid)
    
    mag = np.abs(s_complex)
    phase_unwrap = np.unwrap(np.angle(s_complex))
    
    mag_interp = np.interp(f_grid, f_hz, mag)
    phase_interp = np.interp(f_grid, f_hz, phase_unwrap)
    
    dc_sign = 1.0 if np.real(s_complex[0]) >= 0 else -1.0
    s_grid = mag_interp * np.exp(1j * phase_interp)
    s_grid[0] = mag[0] * dc_sign
    
    half_win = np.kaiser(2 * n_freq, beta_window)[n_freq:]
    s_windowed = s_grid * half_win
    
    n_fft_actual = max(n_fft, 2 ** int(np.ceil(np.log2(4 * n_freq))))
    
    h_t = np.fft.irfft(s_windowed, n=n_fft_actual)
    h_unit = np.fft.irfft(half_win, n=n_fft_actual)
    norm_factor = np.sum(h_unit)
    if abs(norm_factor) < 1e-12:
        norm_factor = 1.0
        
    gamma_step = np.cumsum(h_t[:n_fft_actual // 2]) / norm_factor
    gamma_clipped = np.clip(gamma_step, -0.98, 0.98)
    
    z_t = z0 * (1.0 + gamma_clipped) / (1.0 - gamma_clipped)
    
    dt_s = 1.0 / (n_fft_actual * df)
    t_ns = np.arange(len(z_t)) * dt_s * 1e9
    
    return t_ns, z_t, gamma_step


def generer_prbs7(n_symbols, modulation="NRZ", vpp=1.0):
    """Génère une séquence PRBS-7 déterministe bien équilibrée."""
    lfsr = [1, 0, 1, 0, 1, 1, 1]
    bits = []
    n_bits_needed = n_symbols * (2 if modulation == "PAM-4" else 1)
    for _ in range(n_bits_needed):
        new_bit = lfsr[6] ^ lfsr[5]
        bits.append(lfsr[6])
        lfsr = [new_bit] + lfsr[:6]
    bits = np.array(bits)
    
    if modulation == "PAM-4":
        b_msb = bits[0::2]
        b_lsb = bits[1::2]
        idx = b_msb * 2 + (b_msb ^ b_lsb)
        levels = np.array([-0.5, -1.0 / 6.0, 1.0 / 6.0, 0.5]) * vpp
        return levels[idx]
    else:
        return (bits.astype(float) - 0.5) * vpp


def mesurer_rise_fall_rx(traces, dt_ps, low_level, high_level, norm_factor_edge="20% - 80%"):
    """
    Mesure les temps de montée (Rise Time) et de descente (Fall Time) réels sur les traces Rx
    entre les seuils choisis (20%-80% ou 10%-90%).
    """
    amp = high_level - low_level
    if amp <= 1e-6:
        return 0.0, 0.0
        
    if "10%" in norm_factor_edge:
        v_low_th = low_level + 0.10 * amp
        v_high_th = low_level + 0.90 * amp
    else:
        v_low_th = low_level + 0.20 * amp
        v_high_th = low_level + 0.80 * amp
        
    rise_times = []
    fall_times = []
    sps_est = traces.shape[1] // 2
    win_s, win_e = int(0.15 * sps_est), int(0.85 * sps_est)
    
    for tr in traces:
        seg = tr[win_s:win_e]
        if seg[0] < v_low_th and seg[-1] > v_high_th:
            idx_l = np.where(seg >= v_low_th)[0]
            idx_h = np.where(seg >= v_high_th)[0]
            if len(idx_l) > 0 and len(idx_h) > 0 and idx_h[0] > idx_l[0]:
                i1 = idx_l[0]
                t1 = (i1 - 1 + (v_low_th - seg[i1 - 1]) / max(1e-12, seg[i1] - seg[i1 - 1])) * dt_ps if i1 > 0 else 0.0
                i2 = idx_h[0]
                t2 = (i2 - 1 + (v_high_th - seg[i2 - 1]) / max(1e-12, seg[i2] - seg[i2 - 1])) * dt_ps if i2 > 0 else i2 * dt_ps
                if t2 > t1:
                    rise_times.append(t2 - t1)
        elif seg[0] > v_high_th and seg[-1] < v_low_th:
            idx_h = np.where(seg <= v_high_th)[0]
            idx_l = np.where(seg <= v_low_th)[0]
            if len(idx_h) > 0 and len(idx_l) > 0 and idx_l[0] > idx_h[0]:
                i1 = idx_h[0]
                t1 = (i1 - 1 + (seg[i1 - 1] - v_high_th) / max(1e-12, seg[i1 - 1] - seg[i1])) * dt_ps if i1 > 0 else 0.0
                i2 = idx_l[0]
                t2 = (i2 - 1 + (seg[i2 - 1] - v_low_th) / max(1e-12, seg[i2 - 1] - seg[i2])) * dt_ps if i2 > 0 else i2 * dt_ps
                if t2 > t1:
                    fall_times.append(t2 - t1)
                    
    tr_rx = float(np.median(rise_times)) if len(rise_times) > 0 else 0.0
    tf_rx = float(np.median(fall_times)) if len(fall_times) > 0 else 0.0
    return tr_rx, tf_rx


def simuler_diagramme_oeil(
    freq_ghz, y_db, s_complex,
    modulation="NRZ", bitrate_gbps=10.0, vpp=1.0,
    tr_ps=15.0, tf_ps=15.0, convention_edge="20% - 80%",
    rj_ps=0.0, noise_mv=0.0, n_symbols=400,
    mode_phase="Phase minimale causale (Standard VNA)"
):
    """
    Simule la transmission PRBS avec temps de montée (Rise Time tr_ps) et temps de descente
    (Fall Time tf_ps) indépendants, puis extrait le diagramme de l'oeil et ses métriques.
    """
    bits_per_symbol = 2 if modulation == "PAM-4" else 1
    symbol_rate_gbaud = bitrate_gbps / bits_per_symbol
    t_sym_s = 1.0 / (symbol_rate_gbaud * 1e9)
    t_sym_ps = t_sym_s * 1e12
    
    sps = 64
    dt_s = t_sym_s / sps
    dt_ps = dt_s * 1e12
    
    symbols = generer_prbs7(n_symbols, modulation=modulation, vpp=vpp)
    tx_ideal = np.repeat(symbols, sps)
    n_total = len(tx_ideal)
    
    edge_divisor = 2.5631 if "10%" in convention_edge else 1.6832
    sigma_r_s = max(dt_s * 0.6, (tr_ps * 1e-12) / edge_divisor)
    sigma_f_s = max(dt_s * 0.6, (tf_ps * 1e-12) / edge_divisor)
    
    half_k = 4 * sps
    t_kern = np.arange(-half_k, half_k + 1) * dt_s
    
    gauss_kern_r = np.exp(-0.5 * (t_kern / sigma_r_s) ** 2)
    gauss_kern_r /= np.sum(gauss_kern_r)
    
    gauss_kern_f = np.exp(-0.5 * (t_kern / sigma_f_s) ** 2)
    gauss_kern_f /= np.sum(gauss_kern_f)
    
    pad_len = half_k + sps
    tx_padded = np.concatenate([
        np.full(pad_len, tx_ideal[0]),
        tx_ideal,
        np.full(pad_len, tx_ideal[-1])
    ])
    diffs = np.diff(tx_padded, prepend=tx_padded[0])
    diffs_pos = np.maximum(diffs, 0.0)
    diffs_neg = np.minimum(diffs, 0.0)
    
    slope_pos = np.convolve(diffs_pos, gauss_kern_r, mode='same')
    slope_neg = np.convolve(diffs_neg, gauss_kern_f, mode='same')
    
    tx_wave_padded = tx_padded[0] + np.cumsum(slope_pos + slope_neg)
    tx_wave = tx_wave_padded[pad_len : pad_len + n_total]
    
    rng = np.random.default_rng(42)
    if rj_ps > 0:
        t_axis = np.arange(n_total) * dt_s
        jitter_s = np.repeat(rng.normal(0, rj_ps * 1e-12, size=n_symbols), sps)
        jitter_s = np.convolve(jitter_s, 0.5 * (gauss_kern_r + gauss_kern_f), mode='same')
        tx_wave = np.interp(t_axis + jitter_s, t_axis, tx_wave)
        
    freqs_sim_ghz = np.fft.rfftfreq(n_total, d=dt_s) / 1e9
    X_f = np.fft.rfft(tx_wave)
    
    mag_lin = 10.0 ** (y_db / 20.0)
    dc_mag = min(1.0, float(mag_lin[0]))
    mag_sim = np.interp(freqs_sim_ghz, freq_ghz, mag_lin, left=dc_mag, right=mag_lin[-1])
    mag_sim[0] = dc_mag
    
    if "minimale" in mode_phase:
        mag_two_sided = np.concatenate([mag_sim, mag_sim[-2:0:-1]])
        log_mag = np.log(np.maximum(mag_two_sided, 1e-5))
        cepstrum = np.fft.ifft(log_mag)
        w_cep = np.zeros(n_total)
        w_cep[0] = 1.0
        w_cep[1:n_total // 2] = 2.0
        w_cep[n_total // 2] = 1.0
        H_two_sided = np.exp(np.fft.fft(cepstrum * w_cep))
        H_f = H_two_sided[:len(freqs_sim_ghz)]
    else:
        s_norm = s_complex * np.exp(-1j * np.angle(s_complex[0]))
        phase_unwrap = np.unwrap(np.angle(s_norm))
        slope = float(np.sum(freq_ghz * phase_unwrap) / np.maximum(1e-12, np.sum(freq_ghz ** 2)))
        phase_disp = phase_unwrap - slope * freq_ghz
        phase_sim = np.interp(freqs_sim_ghz, freq_ghz, phase_disp, left=0.0, right=phase_disp[-1])
        phase_sim[0] = 0.0
        H_f = mag_sim * np.exp(1j * phase_sim)
        
    rx_wave = np.fft.irfft(X_f * H_f, n=n_total)
    
    if noise_mv > 0:
        rx_wave += rng.normal(0, noise_mv * 1e-3, size=n_total)
        
    best_lag = 0
    best_corr = -1e18
    slice_ref = tx_ideal[sps * 8 : -sps * 8]
    for lag in range(-sps, 3 * sps):
        shifted_rx = np.roll(rx_wave, -lag)[sps * 8 : -sps * 8]
        c_val = float(np.dot(shifted_rx, slice_ref))
        if c_val > best_corr:
            best_corr = c_val
            best_lag = lag
            
    rx_centered = np.roll(rx_wave, -best_lag + (sps // 2))
    
    seg_len = 2 * sps
    n_traces = (n_total // sps) - 16
    traces = []
    for k in range(8, 8 + n_traces):
        start_idx = k * sps
        seg = rx_centered[start_idx : start_idx + seg_len]
        if len(seg) == seg_len:
            traces.append(seg)
    traces = np.array(traces)
    
    t_ui = np.linspace(0.0, 2.0, seg_len)
    t_ps_axis = t_ui * t_sym_ps
    
    search_start, search_end = int(0.75 * sps), int(1.25 * sps)
    best_sample_idx = sps
    
    if modulation == "NRZ":
        best_eh = -1e9
        for idx_c in range(search_start, search_end):
            vals = traces[:, idx_c]
            v_mid_est = 0.5 * (np.max(vals) + np.min(vals))
            v_high = vals[vals >= v_mid_est]
            v_low = vals[vals < v_mid_est]
            if len(v_high) > 5 and len(v_low) > 5:
                eh_cand = float(np.min(v_high) - np.max(v_low))
                if eh_cand > best_eh:
                    best_eh = eh_cand
                    best_sample_idx = idx_c
                    
        sample_vals = traces[:, best_sample_idx]
        v_mid_est = 0.5 * (np.max(sample_vals) + np.min(sample_vals))
        v_high = sample_vals[sample_vals >= v_mid_est]
        v_low = sample_vals[sample_vals < v_mid_est]
        
        mu_1 = float(np.mean(v_high)) if len(v_high) > 0 else vpp / 2.0
        mu_0 = float(np.mean(v_low)) if len(v_low) > 0 else -vpp / 2.0
        sig_1 = float(np.std(v_high)) if len(v_high) > 0 else 1e-6
        sig_0 = float(np.std(v_low)) if len(v_low) > 0 else 1e-6
        
        min_1 = float(np.min(v_high)) if len(v_high) > 0 else mu_1
        max_0 = float(np.max(v_low)) if len(v_low) > 0 else mu_0
        
        eye_amplitude = max(1e-6, mu_1 - mu_0)
        eye_height = max(0.0, min_1 - max_0)
        open_factor_pct = max(0.0, (eye_height / eye_amplitude) * 100.0)
        q_factor = eye_amplitude / max(1e-6, sig_1 + sig_0)
        snr_db = 20.0 * np.log10(max(1e-3, q_factor))
        
        tr_rx_ps, tf_rx_ps = mesurer_rise_fall_rx(traces, dt_ps, mu_0, mu_1, convention_edge)
        
        v_th = 0.5 * (mu_1 + mu_0)
        cross_times_ps = []
        win_start = int(0.15 * sps)
        win_end = int(0.85 * sps)
        for tr in traces:
            sub = tr[win_start:win_end] - v_th
            crossings = np.where(np.diff(np.sign(sub)) != 0)[0]
            if len(crossings) == 1:
                c_i = crossings[0] + win_start
                y1, y2 = tr[c_i] - v_th, tr[c_i + 1] - v_th
                frac = -y1 / (y2 - y1) if abs(y2 - y1) > 1e-12 else 0.0
                cross_times_ps.append((c_i + frac) * dt_ps)
                
        if len(cross_times_ps) > 2:
            jitter_rms_ps = float(np.std(cross_times_ps))
            jitter_pp_ps = float(np.max(cross_times_ps) - np.min(cross_times_ps))
        else:
            jitter_rms_ps = 0.0
            jitter_pp_ps = 0.0
            
        eye_width_ps = max(0.0, t_sym_ps - jitter_pp_ps)
        eye_width_ui = eye_width_ps / t_sym_ps
        
        details_yeux = [{
            "Sous-Œil": "Œil Unique (NRZ)",
            "Hauteur d'Œil (mV)": round(eye_height * 1e3, 2),
            "Eye Opening Factor (%)": round(open_factor_pct, 1),
            "Largeur d'Œil (ps / UI)": f"{round(eye_width_ps, 2)} ps ({round(eye_width_ui, 3)} UI)",
            f"Rise Time Rx ({convention_edge})": f"{round(tr_rx_ps, 2)} ps",
            f"Fall Time Rx ({convention_edge})": f"{round(tf_rx_ps, 2)} ps",
            "Jitter PP (ps)": round(jitter_pp_ps, 2),
            "Jitter RMS (ps)": round(jitter_rms_ps, 2),
            "Facteur Q / SNR (dB)": f"{round(q_factor, 2)} ({round(snr_db, 1)} dB)"
        }]
        
        mask_coords = {
            "t_center_ps": best_sample_idx * dt_ps,
            "t_center_ui": t_ui[best_sample_idx],
            "eyes": [(max_0, min_1, eye_width_ps, eye_width_ui)]
        }
        
        metrics = {
            "eye_height_mv": eye_height * 1e3,
            "eye_width_ps": eye_width_ps,
            "eye_width_ui": eye_width_ui,
            "open_factor_pct": open_factor_pct,
            "jitter_pp_ps": jitter_pp_ps,
            "jitter_rms_ps": jitter_rms_ps,
            "tr_rx_ps": tr_rx_ps,
            "tf_rx_ps": tf_rx_ps,
            "snr_db": snr_db,
            "rlm_pct": 100.0,
            "symbol_rate_gbaud": symbol_rate_gbaud,
            "details_yeux": details_yeux,
            "mask_coords": mask_coords
        }
        
    else:
        sample_vals_center = traces[:, sps]
        v_span = np.max(sample_vals_center) - np.min(sample_vals_center)
        v_center = 0.5 * (np.max(sample_vals_center) + np.min(sample_vals_center))
        
        best_eh_mid = -1e9
        for idx_c in range(search_start, search_end):
            vals = traces[:, idx_c]
            v_pos = vals[(vals >= v_center) & (vals < v_center + 0.33 * v_span)]
            v_neg = vals[(vals < v_center) & (vals > v_center - 0.33 * v_span)]
            if len(v_pos) > 3 and len(v_neg) > 3:
                eh_cand = float(np.min(v_pos) - np.max(v_neg))
                if eh_cand > best_eh_mid:
                    best_eh_mid = eh_cand
                    best_sample_idx = idx_c
                    
        sample_vals = traces[:, best_sample_idx]
        th_mid = float(np.median(sample_vals))
        th_low = float(np.median(sample_vals[sample_vals < th_mid]))
        th_high = float(np.median(sample_vals[sample_vals >= th_mid]))
        
        l0 = sample_vals[sample_vals < th_low]
        l1 = sample_vals[(sample_vals >= th_low) & (sample_vals < th_mid)]
        l2 = sample_vals[(sample_vals >= th_mid) & (sample_vals < th_high)]
        l3 = sample_vals[sample_vals >= th_high]
        
        mu = [
            float(np.mean(l0)) if len(l0) > 0 else -0.5 * vpp,
            float(np.mean(l1)) if len(l1) > 0 else -vpp / 6.0,
            float(np.mean(l2)) if len(l2) > 0 else vpp / 6.0,
            float(np.mean(l3)) if len(l3) > 0 else 0.5 * vpp
        ]
        sig = [
            float(np.std(l0)) if len(l0) > 0 else 1e-6,
            float(np.std(l1)) if len(l1) > 0 else 1e-6,
            float(np.std(l2)) if len(l2) > 0 else 1e-6,
            float(np.std(l3)) if len(l3) > 0 else 1e-6
        ]
        
        tr_rx_ps, tf_rx_ps = mesurer_rise_fall_rx(traces, dt_ps, mu[0], mu[3], convention_edge)
        
        v_mid = (mu[0] + mu[3]) / 2.0
        es1 = (mu[1] - v_mid) / ((mu[0] - v_mid) / 3.0) if abs(mu[0] - v_mid) > 1e-6 else 1.0
        es2 = (mu[2] - v_mid) / ((mu[3] - v_mid) / 3.0) if abs(mu[3] - v_mid) > 1e-6 else 1.0
        rlm = min(3.0 * es1, 3.0 * es2, 2.0 - 3.0 * es1, 2.0 - 3.0 * es2)
        rlm_pct = max(0.0, min(100.0, rlm * 100.0))
        
        noms_yeux = ["Œil Inférieur (L0-L1)", "Œil Central (L1-L2)", "Œil Supérieur (L2-L3)"]
        clusters = [(l0, l1, mu[0], mu[1], sig[0], sig[1]),
                    (l1, l2, mu[1], mu[2], sig[1], sig[2]),
                    (l2, l3, mu[2], mu[3], sig[2], sig[3])]
        
        details_yeux = []
        eh_list, of_list, ew_ps_list, jpp_list, jrms_list, snr_list, mask_eyes = [], [], [], [], [], [], []
        
        win_start = int(0.15 * sps)
        win_end = int(0.85 * sps)
        
        for nom_o, (c_bot, c_top, m_bot, m_top, s_bot, s_top) in zip(noms_yeux, clusters):
            max_bot = float(np.max(c_bot)) if len(c_bot) > 0 else m_bot
            min_top = float(np.min(c_top)) if len(c_top) > 0 else m_top
            eh_sub = max(0.0, min_top - max_bot)
            amp_sub = max(1e-6, m_top - m_bot)
            of_sub = max(0.0, (eh_sub / amp_sub) * 100.0)
            q_sub = amp_sub / max(1e-6, s_bot + s_top)
            snr_sub = 20.0 * np.log10(max(1e-3, q_sub))
            
            tr_sub, tf_sub = mesurer_rise_fall_rx(traces, dt_ps, m_bot, m_top, convention_edge)
            
            v_th_sub = 0.5 * (m_bot + m_top)
            c_times = []
            for tr in traces:
                sub = tr[win_start:win_end] - v_th_sub
                crossings = np.where(np.diff(np.sign(sub)) != 0)[0]
                if len(crossings) == 1:
                    c_i = crossings[0] + win_start
                    y1, y2 = tr[c_i] - v_th_sub, tr[c_i + 1] - v_th_sub
                    frac = -y1 / (y2 - y1) if abs(y2 - y1) > 1e-12 else 0.0
                    c_times.append((c_i + frac) * dt_ps)
            if len(c_times) > 2:
                j_rms = float(np.std(c_times))
                j_pp = float(np.max(c_times) - np.min(c_times))
            else:
                j_rms, j_pp = 0.0, 0.0
                
            ew_ps = max(0.0, t_sym_ps - j_pp)
            ew_ui = ew_ps / t_sym_ps
            
            eh_list.append(eh_sub)
            of_list.append(of_sub)
            ew_ps_list.append(ew_ps)
            jpp_list.append(j_pp)
            jrms_list.append(j_rms)
            snr_list.append(snr_sub)
            mask_eyes.append((max_bot, min_top, ew_ps, ew_ui))
            
            details_yeux.append({
                "Sous-Œil": nom_o,
                "Hauteur d'Œil (mV)": round(eh_sub * 1e3, 2),
                "Eye Opening Factor (%)": round(of_sub, 1),
                "Largeur d'Œil (ps / UI)": f"{round(ew_ps, 2)} ps ({round(ew_ui, 3)} UI)",
                f"Rise Time Rx ({convention_edge})": f"{round(tr_sub if tr_sub > 0 else tr_rx_ps, 2)} ps",
                f"Fall Time Rx ({convention_edge})": f"{round(tf_sub if tf_sub > 0 else tf_rx_ps, 2)} ps",
                "Jitter PP (ps)": round(j_pp, 2),
                "Jitter RMS (ps)": round(j_rms, 2),
                "Facteur Q / SNR (dB)": f"{round(q_sub, 2)} ({round(snr_sub, 1)} dB)"
            })
            
        mask_coords = {
            "t_center_ps": best_sample_idx * dt_ps,
            "t_center_ui": t_ui[best_sample_idx],
            "eyes": mask_eyes
        }
        
        metrics = {
            "eye_height_mv": float(np.min(eh_list)) * 1e3,
            "eye_width_ps": float(np.min(ew_ps_list)),
            "eye_width_ui": float(np.min(ew_ps_list)) / t_sym_ps,
            "open_factor_pct": float(np.mean(of_list)),
            "jitter_pp_ps": float(np.max(jpp_list)),
            "jitter_rms_ps": float(np.mean(jrms_list)),
            "tr_rx_ps": tr_rx_ps,
            "tf_rx_ps": tf_rx_ps,
            "snr_db": float(np.min(snr_list)),
            "rlm_pct": rlm_pct,
            "symbol_rate_gbaud": symbol_rate_gbaud,
            "details_yeux": details_yeux,
            "mask_coords": mask_coords
        }
        
    return t_ui, t_ps_axis, traces, metrics


# ==============================================================================
# EN-TÊTE PRINCIPAL ET ONGLETS DE L'APPLICATION
# ==============================================================================
col_logo, col_titre = st.columns([1, 6])
with col_logo:
    if os.path.exists(logo_path):
        st.image(logo_path, width=140)
with col_titre:
    st.title("📊 Banc de Qualification - RF, TDR & Diagramme de l'Œil")

st.markdown(f"*{len(base_donnees)} fichiers S-parameters chargés depuis la base de données.*")

tab_rf, tab_tdr, tab_eye = st.tabs([
    "📊 1. Analyse RF (S-Parameters)",
    "⏱️ 2. Mode TDR & Impédance Z(t)",
    "👁️ 3. Diagramme de l'Œil (NRZ / PAM-4)"
])


# ==============================================================================
# ONGLET 1 : ANALYSE RF (S-PARAMETERS, MARQUEURS RF INCL. MIN/MAX & LIMITES RF)
# ==============================================================================
with tab_rf:
    with st.expander("⚙️ Configuration RF : Marqueurs (Niveau, Fréquence, Min/Max), Limites & Échelles", expanded=False):
        col_rf_m, col_rf_l, col_rf_z = st.columns(3)
        
        # --- Marqueurs RF ---
        with col_rf_m:
            st.markdown("#### 📍 Marqueurs RF")
            if "markers_list" not in st.session_state:
                st.session_state.markers_list = []
            c_am, c_cm = st.columns(2)
            if c_am.button("➕ Ajout Marqueur RF"):
                st.session_state.markers_list.append({
                    "type": "Franchissement de niveau (dB)",
                    "valeurs_str": "-10.0",
                    "courbes": toutes_les_courbes_potentielles.copy()
                })
            if c_cm.button("🗑️ Effacer Marqueurs RF"):
                st.session_state.markers_list = []

            modes_marqueurs_rf = [
                "Franchissement de niveau (dB)",
                "Par Fréquence (GHz)",
                "Minimum (Min)",
                "Maximum (Max)",
                "Min & Max simultanés"
            ]

            marqueurs_rf_cfg = []
            for idx, m in enumerate(st.session_state.markers_list):
                st.markdown(f"**Marqueur M{idx + 1}**")
                idx_mode_rf = modes_marqueurs_rf.index(m["type"]) if m.get("type") in modes_marqueurs_rf else 0
                m_type = st.selectbox("Mode", modes_marqueurs_rf, index=idx_mode_rf, key=f"rf_type_m_{idx}")
                m["type"] = m_type

                if "Min" in m_type or "Max" in m_type:
                    m_vals_str = st.text_input(
                        "Plage de fréquence optionnelle Min, Max (GHz)",
                        value=m.get("valeurs_str", "") if m.get("valeurs_str") != "-10.0" else "",
                        key=f"rf_vals_m_{idx}",
                        help="Laisse vide pour chercher sur toute la courbe, ou tape ex: 1, 10 pour chercher entre 1 et 10 GHz"
                    )
                else:
                    m_vals_str = st.text_input(
                        "Valeurs (séparées par des virgules)",
                        value=m.get("valeurs_str", "-10.0"),
                        key=f"rf_vals_m_{idx}",
                        help="Ex: 1, 5, 10 ou -3, -10"
                    )
                m["valeurs_str"] = m_vals_str

                m_curves = st.multiselect("Courbes cibles", options=toutes_les_courbes_potentielles, default=[c for c in m["courbes"] if c in toutes_les_courbes_potentielles], key=f"rf_curves_m_{idx}")
                if st.button(f"❌ Supprimer M{idx + 1}", key=f"rf_del_m_{idx}"):
                    st.session_state.markers_list.pop(idx)
                    st.rerun()

                parsed_vals = []
                for v in m_vals_str.replace("/", ",").split(","):
                    if v.strip():
                        try:
                            parsed_vals.append(float(v.strip()))
                        except ValueError:
                            pass
                marqueurs_rf_cfg.append({"numero": f"M{idx + 1}", "type": m_type, "valeurs": parsed_vals, "courbes": m_curves})

        # --- Limites Multi-Secteurs RF ---
        with col_rf_l:
            st.markdown("#### 📐 Limites Multi-Secteurs RF")
            if "limits_list" not in st.session_state:
                st.session_state.limits_list = []
            c_al, c_cl = st.columns(2)
            if c_al.button("➕ Ajout Limite RF"):
                st.session_state.limits_list.append({
                    "afficher_ligne": True,
                    "courbes": toutes_les_courbes_potentielles.copy(),
                    "secteurs": [{"f_min": 0.0, "f_max": 10.0, "seuil": -3.0, "operateur": "Inférieur ou égal (<=)"}]
                })
            if c_cl.button("🗑️ Effacer Limites RF"):
                st.session_state.limits_list = []

            limites_rf_cfg = []
            for idx, l in enumerate(st.session_state.limits_list):
                st.markdown(f"**Règle Limite L{idx + 1}**")
                l["afficher_ligne"] = st.checkbox("Afficher sur le graphe RF", value=l.get("afficher_ligne", True), key=f"rf_show_l_{idx}")
                l["courbes"] = st.multiselect("Courbes cibles", options=toutes_les_courbes_potentielles, default=[c for c in l["courbes"] if c in toutes_les_courbes_potentielles], key=f"rf_curves_l_{idx}")
                
                sec_del = []
                for s_idx, sec in enumerate(l["secteurs"]):
                    sc1, sc2 = st.columns(2)
                    sec["f_min"] = sc1.number_input("Min (GHz)", value=float(sec["f_min"]), step=0.5, key=f"rf_fmin_{idx}_{s_idx}")
                    sec["f_max"] = sc2.number_input("Max (GHz)", value=float(sec["f_max"]), step=0.5, key=f"rf_fmax_{idx}_{s_idx}")
                    sc3, sc4 = st.columns(2)
                    sec["seuil"] = sc3.number_input("Seuil (dB)", value=float(sec["seuil"]), step=0.5, key=f"rf_seuil_{idx}_{s_idx}")
                    sec["operateur"] = sc4.selectbox("Condition", ["Inférieur ou égal (<=)", "Supérieur ou égal (>=)"], index=0 if sec["operateur"]=="Inférieur ou égal (<=)" else 1, key=f"rf_op_{idx}_{s_idx}")
                    if st.button(f"🗑️ Suppr. secteur {s_idx + 1}", key=f"rf_del_sec_{idx}_{s_idx}"):
                        sec_del.append(s_idx)
                for s_idx in reversed(sec_del):
                    l["secteurs"].pop(s_idx)
                    st.rerun()
                if st.button(f"➕ Ajouter secteur à L{idx + 1}", key=f"rf_add_sec_{idx}"):
                    l["secteurs"].append({"f_min": 10.0, "f_max": 20.0, "seuil": -3.0, "operateur": "Inférieur ou égal (<=)"})
                    st.rerun()
                if st.button(f"❌ Supprimer Règle L{idx + 1}", key=f"rf_del_l_{idx}"):
                    st.session_state.limits_list.pop(idx)
                    st.rerun()
                limites_rf_cfg.append({"numero": f"L{idx + 1}", "afficher_ligne": l["afficher_ligne"], "courbes": l["courbes"], "secteurs": l["secteurs"]})

        # --- Échelles & Options RF ---
        with col_rf_z:
            st.markdown("#### 🔍 Échelles & Affichage RF")
            afficher_graphique_rf = st.checkbox("Afficher le Graphique RF", value=True)
            afficher_tab_m_rf = st.checkbox("Afficher le Tableau des Marqueurs RF", value=True)
            afficher_tab_l_rf = st.checkbox("Afficher le Tableau Pass / Fail RF", value=True)
            st.markdown("---")
            activer_zoom_rf = st.checkbox("Définir les échelles RF manuellement", value=False)
            freq_min_rf, freq_max_rf = 0.0, 20.0
            db_min_rf, db_max_rf = -60.0, 5.0
            if activer_zoom_rf:
                freq_min_rf = st.number_input("Fréquence Min (GHz)", value=0.0, key="rf_xmin")
                freq_max_rf = st.number_input("Fréquence Max (GHz)", value=20.0, key="rf_xmax")
                db_min_rf = st.number_input("Magnitude Min (dB)", value=-60.0, key="rf_ymin")
                db_max_rf = st.number_input("Magnitude Max (dB)", value=5.0, key="rf_ymax")

    if connecteurs_selectionnes and parametres_selectionnes:
        fig_rf = go.Figure()
        tableau_marqueurs_rf = []
        tableau_limites_rf = []
        limites_rf_deja_tracees = set()

        for nom_courbe_actuelle in st.session_state.courbes_visibles:
            freq, y_vals, _ = get_curve_data(nom_courbe_actuelle, connecteurs_selectionnes, parametres_selectionnes, base_donnees)
            if freq is not None and y_vals is not None:
                for s_cfg in smooth_configures:
                    if nom_courbe_actuelle in s_cfg["courbes"]:
                        fenetre = max(1, int(len(y_vals) * (s_cfg["pourcentage"] / 100.0)))
                        if fenetre % 2 == 0:
                            fenetre += 1
                        if fenetre > 1:
                            y_vals = np.convolve(y_vals, np.ones(fenetre) / fenetre, mode='same')

                couleur_courbe = st.session_state.curve_colors.get(nom_courbe_actuelle, "#0095D9")
                fig_rf.add_trace(go.Scatter(
                    x=freq, y=y_vals, mode=mode_trace,
                    marker=dict(size=4, color=couleur_courbe) if afficher_marqueurs else None,
                    line=dict(color=couleur_courbe),
                    name=nom_courbe_actuelle
                ))

                # Marqueurs RF (Niveau, Fréquence, Min, Max, Min & Max)
                for m_cfg in marqueurs_rf_cfg:
                    if nom_courbe_actuelle in m_cfg["courbes"]:
                        pts = calculer_points_marqueur(freq, y_vals, m_cfg, unite_x="GHz", unite_y="dB")
                        for lbl_m, desc_cible, f_tr, val_tr, col_m in pts:
                            fig_rf.add_trace(go.Scatter(
                                x=[f_tr], y=[val_tr], mode="markers+text",
                                marker=dict(size=12, symbol="x", color=col_m),
                                text=[lbl_m], textposition="top center",
                                name=f"{lbl_m} ({nom_courbe_actuelle})"
                            ))
                            tableau_marqueurs_rf.append({
                                "Marqueur": lbl_m,
                                "Connecteur / Paramètre": nom_courbe_actuelle,
                                "Mode": m_cfg["type"],
                                "Cible / Plage": desc_cible,
                                "Fréquence Réelle (GHz)": round(f_tr, 4),
                                "Valeur Mesurée (dB)": round(val_tr, 2)
                            })

                # Limites RF
                for l_cfg in limites_rf_cfg:
                    if nom_courbe_actuelle in l_cfg["courbes"]:
                        num_l = l_cfg["numero"]
                        regles_globales_pass = True
                        for sec in l_cfg["secteurs"]:
                            f_min_l, f_max_l, seuil_l, op_l = sec["f_min"], sec["f_max"], sec["seuil"], sec["operateur"]
                            cle_trace = (num_l, f_min_l, f_max_l, seuil_l)
                            if l_cfg["afficher_ligne"] and cle_trace not in limites_rf_deja_tracees:
                                fig_rf.add_trace(go.Scatter(
                                    x=[f_min_l, f_max_l], y=[seuil_l, seuil_l], mode="lines",
                                    line=dict(color="red", width=2, dash="dash"),
                                    name=f"Limite {num_l} ({f_min_l}-{f_max_l} GHz)"
                                ))
                                limites_rf_deja_tracees.add(cle_trace)

                            masque = (freq >= f_min_l) & (freq <= f_max_l)
                            if np.any(masque):
                                y_bande = y_vals[masque]
                                is_pass_sec = np.all(y_bande <= seuil_l) if op_l == "Inférieur ou égal (<=)" else np.all(y_bande >= seuil_l)
                                if not is_pass_sec:
                                    regles_globales_pass = False

                        tableau_limites_rf.append({
                            "Limite": num_l,
                            "Connecteur / Paramètre": nom_courbe_actuelle,
                            "Secteurs (GHz / Seuils)": " | ".join([f"[{s['f_min']}-{s['f_max']}GHz : {s['seuil']}dB]" for s in l_cfg["secteurs"]]),
                            "Statut Global": "✅ PASS" if regles_globales_pass else "❌ FAIL"
                        })

        layout_rf = dict(
            title="Comparatif Global S-Parameters, Opérations Math, Lissage & Limites",
            xaxis_title="Fréquence (GHz)", yaxis_title="Magnitude (dB)",
            hovermode="x unified", showlegend=True, height=680
        )
        if activer_zoom_rf:
            layout_rf["xaxis"] = dict(range=[freq_min_rf, freq_max_rf])
            layout_rf["yaxis"] = dict(range=[db_min_rf, db_max_rf])
        fig_rf.update_layout(**layout_rf)

        if afficher_graphique_rf:
            st.plotly_chart(fig_rf, use_container_width=True)
        if afficher_tab_m_rf and tableau_marqueurs_rf:
            st.markdown("### 📋 Tableau Récapitulatif des Marqueurs RF")
            st.dataframe(tableau_marqueurs_rf, use_container_width=True)
        if afficher_tab_l_rf and tableau_limites_rf:
            st.markdown("### 🚦 Résultats des Tests de Limites RF (Pass / Fail)")
            st.dataframe(tableau_limites_rf, use_container_width=True)
    else:
        st.info("Veuillez sélectionner au moins un connecteur et un paramètre S dans la barre latérale.")


# ==============================================================================
# ONGLET 2 : MODE TDR & PROFIL D'IMPÉDANCE Z(t) (AVEC MARQUEURS MIN/MAX & LIMITES)
# ==============================================================================
with tab_tdr:
    st.markdown("### ⏱️ Réflectométrie Temporelle (Low-Pass Step TDR) & Profil d'Impédance")
    
    col_tdr_p1, col_tdr_p2, col_tdr_p3, col_tdr_p4 = st.columns(4)
    z0_ref = col_tdr_p1.number_input("Impédance de référence Z0 (Ω)", value=100.0 if any("Sdd" in p for p in parametres_selectionnes) else 50.0, step=5.0, help="50 Ω en Single-Ended, 100 Ω en paire différentielle (Sdd)")
    axe_x_tdr_mode = col_tdr_p2.selectbox("Axe Horizontal TDR", ["Temps aller-retour (ns)", "Distance physique (mm)"])
    vp_pct = col_tdr_p3.slider("Vitesse de propagation Vp (% de c)", min_value=30.0, max_value=100.0, value=66.0, step=1.0)
    beta_kaiser = col_tdr_p4.slider("Fenêtrage IFFT (Lissage Step Kaiser β)", min_value=0.0, max_value=14.0, value=6.0, step=0.5)
    
    unite_x_tdr = "mm" if "Distance" in axe_x_tdr_mode else "ns"

    with st.expander("⚙️ Configuration TDR : Marqueurs Impédance (incl. Min/Max), Limites (Ω) & Échelles", expanded=True):
        col_tdr_m, col_tdr_l, col_tdr_z = st.columns(3)
        
        # --- Marqueurs TDR ---
        with col_tdr_m:
            st.markdown("#### 📍 Marqueurs TDR")
            if "tdr_markers_list" not in st.session_state:
                st.session_state.tdr_markers_list = []
            c_tam, c_tcm = st.columns(2)
            if c_tam.button("➕ Ajout Marqueur TDR"):
                st.session_state.tdr_markers_list.append({
                    "type": "Min & Max simultanés (Ω)",
                    "valeurs_str": "",
                    "courbes": toutes_les_courbes_potentielles.copy()
                })
            if c_tcm.button("🗑️ Effacer Marqueurs TDR"):
                st.session_state.tdr_markers_list = []

            modes_marqueurs_tdr = [
                f"Par Position ({unite_x_tdr})",
                "Franchissement d'Impédance (Ω)",
                "Minimum (Min Ω)",
                "Maximum (Max Ω)",
                "Min & Max simultanés (Ω)"
            ]

            marqueurs_tdr_cfg = []
            for idx, m in enumerate(st.session_state.tdr_markers_list):
                st.markdown(f"**Marqueur TDR T{idx + 1}**")
                idx_mode_tdr = modes_marqueurs_tdr.index(m["type"]) if m.get("type") in modes_marqueurs_tdr else 0
                m_type = st.selectbox("Mode", modes_marqueurs_tdr, index=idx_mode_tdr, key=f"tdr_type_m_{idx}")
                m["type"] = m_type

                if "Min" in m_type or "Max" in m_type:
                    m_vals_str = st.text_input(
                        f"Plage de recherche optionnelle Min, Max ({unite_x_tdr})",
                        value=m.get("valeurs_str", ""),
                        key=f"tdr_vals_m_{idx}",
                        help=f"Laisse vide pour chercher sur toute la courbe, ou tape ex: 0.1, 0.8 ({unite_x_tdr})"
                    )
                else:
                    m_vals_str = st.text_input(
                        "Valeurs (séparées par des virgules)",
                        value=m.get("valeurs_str", "0.38"),
                        key=f"tdr_vals_m_{idx}",
                        help="Ex: 0.38, 0.64 ou 65, 100"
                    )
                m["valeurs_str"] = m_vals_str

                m_curves = st.multiselect("Courbes cibles", options=toutes_les_courbes_potentielles, default=[c for c in m["courbes"] if c in toutes_les_courbes_potentielles], key=f"tdr_curves_m_{idx}")
                if st.button(f"❌ Supprimer T{idx + 1}", key=f"tdr_del_m_{idx}"):
                    st.session_state.tdr_markers_list.pop(idx)
                    st.rerun()
                parsed_vals = []
                for v in m_vals_str.replace("/", ",").split(","):
                    if v.strip():
                        try:
                            parsed_vals.append(float(v.strip()))
                        except ValueError:
                            pass
                marqueurs_tdr_cfg.append({"numero": f"T{idx + 1}", "type": m_type, "valeurs": parsed_vals, "courbes": m_curves})

        # --- Limites Multi-Secteurs TDR ---
        with col_tdr_l:
            st.markdown("#### 📐 Limites TDR & Pass/Fail (Ω)")
            if "tdr_limits_list" not in st.session_state:
                st.session_state.tdr_limits_list = []
            c_tal, c_tcl = st.columns(2)
            if c_tal.button("➕ Ajout Limite TDR"):
                st.session_state.tdr_limits_list.append({
                    "afficher_ligne": True,
                    "courbes": toutes_les_courbes_potentielles.copy(),
                    "secteurs": [
                        {"x_min": 0.0, "x_max": 1.0 if unite_x_tdr == "ns" else 150.0, "seuil": z0_ref + 15.0, "operateur": "Inférieur ou égal (<=)"},
                        {"x_min": 0.0, "x_max": 1.0 if unite_x_tdr == "ns" else 150.0, "seuil": z0_ref - 15.0, "operateur": "Supérieur ou égal (>=)"}
                    ]
                })
            if c_tcl.button("🗑️ Effacer Limites TDR"):
                st.session_state.tdr_limits_list = []

            limites_tdr_cfg = []
            for idx, l in enumerate(st.session_state.tdr_limits_list):
                st.markdown(f"**Règle TDR TL{idx + 1}**")
                l["afficher_ligne"] = st.checkbox("Afficher sur le graphe TDR", value=l.get("afficher_ligne", True), key=f"tdr_show_l_{idx}")
                l["courbes"] = st.multiselect("Courbes cibles", options=toutes_les_courbes_potentielles, default=[c for c in l["courbes"] if c in toutes_les_courbes_potentielles], key=f"tdr_curves_l_{idx}")
                
                sec_del = []
                for s_idx, sec in enumerate(l["secteurs"]):
                    sc1, sc2 = st.columns(2)
                    sec["x_min"] = sc1.number_input(f"Min ({unite_x_tdr})", value=float(sec["x_min"]), step=0.1 if unite_x_tdr=="ns" else 5.0, key=f"tdr_xmin_{idx}_{s_idx}")
                    sec["x_max"] = sc2.number_input(f"Max ({unite_x_tdr})", value=float(sec["x_max"]), step=0.1 if unite_x_tdr=="ns" else 5.0, key=f"tdr_xmax_{idx}_{s_idx}")
                    sc3, sc4 = st.columns(2)
                    sec["seuil"] = sc3.number_input("Seuil (Ω)", value=float(sec["seuil"]), step=1.0, key=f"tdr_seuil_{idx}_{s_idx}")
                    sec["operateur"] = sc4.selectbox("Condition", ["Inférieur ou égal (<=)", "Supérieur ou égal (>=)"], index=0 if sec["operateur"]=="Inférieur ou égal (<=)" else 1, key=f"tdr_op_{idx}_{s_idx}")
                    if st.button(f"🗑️ Suppr. secteur {s_idx + 1}", key=f"tdr_del_sec_{idx}_{s_idx}"):
                        sec_del.append(s_idx)
                for s_idx in reversed(sec_del):
                    l["secteurs"].pop(s_idx)
                    st.rerun()
                if st.button(f"➕ Ajouter secteur à TL{idx + 1}", key=f"tdr_add_sec_{idx}"):
                    l["secteurs"].append({"x_min": 0.0, "x_max": 1.0 if unite_x_tdr=="ns" else 150.0, "seuil": z0_ref + 10.0, "operateur": "Inférieur ou égal (<=)"})
                    st.rerun()
                if st.button(f"❌ Supprimer Règle TL{idx + 1}", key=f"tdr_del_l_{idx}"):
                    st.session_state.tdr_limits_list.pop(idx)
                    st.rerun()
                limites_tdr_cfg.append({"numero": f"TL{idx + 1}", "afficher_ligne": l["afficher_ligne"], "courbes": l["courbes"], "secteurs": l["secteurs"]})

        # --- Échelles manuelles TDR ---
        with col_tdr_z:
            st.markdown("#### 🔍 Échelles & Affichage TDR")
            afficher_tab_m_tdr = st.checkbox("Afficher le Tableau des Marqueurs TDR", value=True)
            afficher_tab_l_tdr = st.checkbox("Afficher le Tableau Pass / Fail TDR", value=True)
            st.markdown("---")
            activer_zoom_tdr = st.checkbox("Définir les échelles TDR manuellement", value=True)
            x_min_tdr_def, x_max_tdr_def = (0.0, 1.0) if unite_x_tdr == "ns" else (0.0, 150.0)
            z_min_tdr, z_max_tdr = max(0.0, z0_ref - 50.0), z0_ref + 50.0
            if activer_zoom_tdr:
                x_min_tdr = st.number_input(f"Axe X Min ({unite_x_tdr})", value=x_min_tdr_def, step=0.1 if unite_x_tdr=="ns" else 10.0, key="tdr_zoom_xmin")
                x_max_tdr = st.number_input(f"Axe X Max ({unite_x_tdr})", value=x_max_tdr_def, step=0.1 if unite_x_tdr=="ns" else 10.0, key="tdr_zoom_xmax")
                z_min_tdr = st.number_input("Impédance Min (Ω)", value=float(z_min_tdr), step=5.0, key="tdr_zoom_ymin")
                z_max_tdr = st.number_input("Impédance Max (Ω)", value=float(z_max_tdr), step=5.0, key="tdr_zoom_ymax")

    if connecteurs_selectionnes and parametres_selectionnes:
        fig_tdr = go.Figure()
        tableau_marqueurs_tdr = []
        tableau_limites_tdr = []
        limites_tdr_deja_tracees = set()

        fig_tdr.add_hline(y=z0_ref, line_dash="dot", line_color="gray", annotation_text=f"Z0 = {z0_ref} Ω")

        for nom_courbe_actuelle in st.session_state.courbes_visibles:
            freq, _, s_cplx = get_curve_data(nom_courbe_actuelle, connecteurs_selectionnes, parametres_selectionnes, base_donnees)
            if freq is not None and s_cplx is not None:
                t_ns, z_vals, _ = calculer_tdr_lowpass_step(freq, s_cplx, z0=z0_ref, beta_window=beta_kaiser)
                if t_ns is not None:
                    c_mm_per_ns = 299.792458 * (vp_pct / 100.0)
                    x_tdr = (t_ns * c_mm_per_ns / 2.0) if unite_x_tdr == "mm" else t_ns

                    for s_cfg in smooth_configures:
                        if nom_courbe_actuelle in s_cfg["courbes"]:
                            fenetre = max(1, int(len(z_vals) * (s_cfg["pourcentage"] / 100.0) * 0.25))
                            if fenetre % 2 == 0:
                                fenetre += 1
                            if fenetre > 1:
                                z_vals = np.convolve(z_vals, np.ones(fenetre) / fenetre, mode='same')

                    couleur_courbe = st.session_state.curve_colors.get(nom_courbe_actuelle, "#0095D9")
                    fig_tdr.add_trace(go.Scatter(
                        x=x_tdr, y=z_vals, mode=mode_trace,
                        marker=dict(size=4, color=couleur_courbe) if afficher_marqueurs else None,
                        line=dict(color=couleur_courbe, width=2),
                        name=f"{nom_courbe_actuelle} [TDR]"
                    ))

                    # 1. Marqueurs TDR (Position, Franchissement, Min, Max, Min & Max)
                    # En mode Min/Max sans plage saisie, si le zoom TDR est actif, on cherche dans la fenêtre visible
                    x_search_arr, z_search_arr = x_tdr, z_vals
                    if activer_zoom_tdr:
                        mask_vis = (x_tdr >= x_min_tdr) & (x_tdr <= x_max_tdr)
                        if np.any(mask_vis):
                            x_search_arr, z_search_arr = x_tdr[mask_vis], z_vals[mask_vis]

                    for m_cfg in marqueurs_tdr_cfg:
                        if nom_courbe_actuelle in m_cfg["courbes"]:
                            pts_tdr = calculer_points_marqueur(x_search_arr, z_search_arr, m_cfg, unite_x=unite_x_tdr, unite_y="Ω")
                            for lbl_m, desc_cible, x_tr, z_tr, col_m in pts_tdr:
                                fig_tdr.add_trace(go.Scatter(
                                    x=[x_tr], y=[z_tr], mode="markers+text",
                                    marker=dict(size=12, symbol="x", color=col_m),
                                    text=[lbl_m], textposition="top center",
                                    name=f"{lbl_m} ({nom_courbe_actuelle})"
                                ))
                                tableau_marqueurs_tdr.append({
                                    "Marqueur TDR": lbl_m,
                                    "Courbe": nom_courbe_actuelle,
                                    "Mode": m_cfg["type"],
                                    "Cible / Plage": desc_cible,
                                    f"Position ({unite_x_tdr})": round(x_tr, 4),
                                    "Impédance Mesurée (Ω)": round(z_tr, 2)
                                })

                    # 2. Limites Multi-Secteurs TDR
                    for l_cfg in limites_tdr_cfg:
                        if nom_courbe_actuelle in l_cfg["courbes"]:
                            num_l = l_cfg["numero"]
                            regles_globales_pass = True
                            z_min_mes, z_max_mes = None, None
                            for sec in l_cfg["secteurs"]:
                                x_min_l, x_max_l, seuil_l, op_l = sec["x_min"], sec["x_max"], sec["seuil"], sec["operateur"]
                                cle_trace = (num_l, x_min_l, x_max_l, seuil_l)
                                if l_cfg["afficher_ligne"] and cle_trace not in limites_tdr_deja_tracees:
                                    fig_tdr.add_trace(go.Scatter(
                                        x=[x_min_l, x_max_l], y=[seuil_l, seuil_l], mode="lines",
                                        line=dict(color="red", width=2, dash="dash"),
                                        name=f"Limite {num_l} ({seuil_l} Ω)"
                                    ))
                                    limites_tdr_deja_tracees.add(cle_trace)

                                masque = (x_tdr >= x_min_l) & (x_tdr <= x_max_l)
                                if np.any(masque):
                                    z_bande = z_vals[masque]
                                    z_min_mes = float(np.min(z_bande)) if z_min_mes is None else min(z_min_mes, float(np.min(z_bande)))
                                    z_max_mes = float(np.max(z_bande)) if z_max_mes is None else max(z_max_mes, float(np.max(z_bande)))
                                    is_pass_sec = np.all(z_bande <= seuil_l) if op_l == "Inférieur ou égal (<=)" else np.all(z_bande >= seuil_l)
                                    if not is_pass_sec:
                                        regles_globales_pass = False

                            tableau_limites_tdr.append({
                                "Limite TDR": num_l,
                                "Courbe": nom_courbe_actuelle,
                                f"Secteurs ({unite_x_tdr} / Ω)": " | ".join([f"[{s['x_min']}-{s['x_max']}{unite_x_tdr} : {s['seuil']}Ω]" for s in l_cfg["secteurs"]]),
                                "Z Min / Z Max Zone (Ω)": f"{round(z_min_mes, 2)} Ω / {round(z_max_mes, 2)} Ω" if z_min_mes is not None else "N/A",
                                "Statut Global": "✅ PASS" if regles_globales_pass else "❌ FAIL"
                            })

        layout_tdr = dict(
            title=f"Profil d'Impédance TDR Low-Pass Step (Z0 = {z0_ref} Ω)",
            xaxis_title=axe_x_tdr_mode,
            yaxis_title="Impédance Z (Ω)",
            hovermode="x unified", showlegend=True, height=650
        )
        if activer_zoom_tdr:
            layout_tdr["xaxis"] = dict(range=[x_min_tdr, x_max_tdr])
            layout_tdr["yaxis"] = dict(range=[z_min_tdr, z_max_tdr])
        fig_tdr.update_layout(**layout_tdr)

        st.plotly_chart(fig_tdr, use_container_width=True)

        if afficher_tab_m_tdr and tableau_marqueurs_tdr:
            st.markdown("### 📋 Tableau Récapitulatif des Marqueurs TDR")
            st.dataframe(tableau_marqueurs_tdr, use_container_width=True)
        if afficher_tab_l_tdr and tableau_limites_tdr:
            st.markdown("### 🚦 Résultats des Tests de Limites d'Impédance TDR (Pass / Fail)")
            st.dataframe(tableau_limites_tdr, use_container_width=True)


# ==============================================================================
# ONGLET 3 : DIAGRAMME DE L'ŒIL (NRZ & PAM-4, RISE/FALL TIME MANUELS, JITTER)
# ==============================================================================
with tab_eye:
    st.markdown("### 👁️ Reconstruction du Diagramme de l'Œil & Analyse de Jitter")

    courbes_oeil_disponibles = []
    for nom in connecteurs_selectionnes:
        nb_p = base_donnees[nom]['nb_ports']
        if nb_p >= 4:
            for p_trans in ["Sdd21", "Sdd12", "S21", "S12"]:
                c_label = f"{nom} [{p_trans}]"
                if c_label not in courbes_oeil_disponibles:
                    courbes_oeil_disponibles.append(c_label)
        elif nb_p >= 2:
            for p_trans in ["S21", "S12"]:
                c_label = f"{nom} [{p_trans}]"
                if c_label not in courbes_oeil_disponibles:
                    courbes_oeil_disponibles.append(c_label)

    for c_pot in toutes_les_courbes_potentielles:
        if c_pot not in courbes_oeil_disponibles:
            courbes_oeil_disponibles.append(c_pot)

    if courbes_oeil_disponibles:
        col_e1, col_e2, col_e3, col_e4 = st.columns(4)
        courbe_canal_eye = col_e1.selectbox("Courbe Canal (Transmission Sdd21 / S21) :", options=courbes_oeil_disponibles, index=0)
        mode_modulation = col_e2.selectbox("Format de Modulation :", ["NRZ", "PAM-4"])
        debit_gbps = col_e3.number_input("Débit Binaire (Gbps) :", min_value=0.5, max_value=224.0, value=10.0, step=1.0)
        axe_x_eye_mode = col_e4.selectbox("Unité Temporelle de l'Œil :", ["Intervalle Unitaire (UI)", "Temps (ps)"])

        col_rf1, col_rf2, col_rf3, col_rf4 = st.columns(4)
        tr_tx_ps = col_rf1.number_input("🔼 Rise Time Tx (ps) :", min_value=0.5, max_value=500.0, value=15.0, step=1.0, help="Temps de montée injecté sur les transitions montantes")
        tf_tx_ps = col_rf2.number_input("🔽 Fall Time Tx (ps) :", min_value=0.5, max_value=500.0, value=15.0, step=1.0, help="Temps de descente injecté sur les transitions descendantes")
        convention_edge_eye = col_rf3.selectbox("Convention Rise / Fall Time :", ["20% - 80%", "10% - 90%"])
        vpp_tx = col_rf4.number_input("Amplitude Différentielle Tx Vpp (V) :", min_value=0.1, max_value=5.0, value=1.0, step=0.1)

        if any(refl in courbe_canal_eye for refl in ["11]", "22]", "33]", "44]"]):
            st.warning("⚠️ Attention : tu as sélectionné un paramètre de réflexion (Return Loss). Pour un Diagramme de l'Œil, sélectionne plutôt une courbe de transmission comme **Sdd21** ou **S21**.")

        with st.expander("⚙️ Paramètres Avancés : Jitter Tx, Bruit, Phase, Masque & Échelles Manuelles de l'Œil", expanded=False):
            ce_p1, ce_p2, ce_p3 = st.columns(3)
            rj_tx_ps = ce_p1.slider("Jitter Aléatoire Tx injecté RJ (ps RMS)", min_value=0.0, max_value=10.0, value=0.0, step=0.2)
            noise_rx_mv = ce_p2.slider("Bruit B.A.G. ajouté (mV RMS)", min_value=0.0, max_value=50.0, value=0.0, step=1.0)
            nb_symboles_sim = ce_p3.select_slider("Nombre de symboles PRBS simulés", options=[200, 300, 400, 600, 800], value=400)

            ce_z1, ce_z2, ce_z3 = st.columns(3)
            mode_phase_eye = ce_z1.selectbox("Modèle de phase du canal", ["Phase minimale causale (Standard VNA)", "Phase brute mesurée (sans retard moyen)"])
            afficher_masque_oeil = ce_z2.checkbox("Afficher le losange d'ouverture d'œil", value=True)
            activer_zoom_eye = ce_z3.checkbox("Définir les échelles de l'Œil manuellement", value=False)

            if activer_zoom_eye:
                cz1, cz2, cz3, cz4 = st.columns(4)
                x_min_eye = cz1.number_input("Temps Min", value=0.0, key="eye_xmin")
                x_max_eye = cz2.number_input("Temps Max", value=2.0 if "UI" in axe_x_eye_mode else round(2000.0 / (debit_gbps / (2 if mode_modulation=="PAM-4" else 1)), 1), key="eye_xmax")
                y_min_eye = cz3.number_input("Tension Min (V)", value=-float(vpp_tx) * 0.7, step=0.1, key="eye_ymin")
                y_max_eye = cz4.number_input("Tension Max (V)", value=float(vpp_tx) * 0.7, step=0.1, key="eye_ymax")

        freq_e, y_db_e, s_cplx_e = get_curve_data(courbe_canal_eye, connecteurs_selectionnes, parametres_selectionnes, base_donnees)

        if freq_e is not None and s_cplx_e is not None:
            t_ui, t_ps, traces_eye, metrics_eye = simuler_diagramme_oeil(
                freq_e, y_db_e, s_cplx_e,
                modulation=mode_modulation,
                bitrate_gbps=debit_gbps,
                vpp=vpp_tx,
                tr_ps=tr_tx_ps,
                tf_ps=tf_tx_ps,
                convention_edge=convention_edge_eye,
                rj_ps=rj_tx_ps,
                noise_mv=noise_rx_mv,
                n_symbols=nb_symboles_sim,
                mode_phase=mode_phase_eye
            )

            k1, k2, k3, k4, k5, k6 = st.columns(6)
            k1.metric("Eye Opening Factor", f"{metrics_eye['open_factor_pct']:.1f} %")
            k2.metric("Hauteur d'Œil (Min)", f"{metrics_eye['eye_height_mv']:.1f} mV")
            k3.metric("Largeur d'Œil", f"{metrics_eye['eye_width_ps']:.2f} ps", f"{metrics_eye['eye_width_ui']:.2f} UI")
            k4.metric("Rise / Fall Rx mesurés", f"{metrics_eye['tr_rx_ps']:.1f} / {metrics_eye['tf_rx_ps']:.1f} ps", f"Tx: {tr_tx_ps:.0f}/{tf_tx_ps:.0f} ps")
            k5.metric("Jitter PP / RMS", f"{metrics_eye['jitter_pp_ps']:.2f} ps", f"RMS: {metrics_eye['jitter_rms_ps']:.2f} ps")
            if mode_modulation == "PAM-4":
                k6.metric("Linéarité RLM (PAM-4)", f"{metrics_eye['rlm_pct']:.1f} %", f"{metrics_eye['symbol_rate_gbaud']:.1f} GBaud")
            else:
                k6.metric("SNR / Qualité", f"{metrics_eye['snr_db']:.1f} dB", f"{metrics_eye['symbol_rate_gbaud']:.1f} GBaud")

            x_axis_eye = t_ui if "UI" in axe_x_eye_mode else t_ps
            unite_eye_str = "UI" if "UI" in axe_x_eye_mode else "ps"

            n_tr, seg_l = traces_eye.shape
            x_concat = np.tile(np.append(x_axis_eye, np.nan), n_tr)
            y_concat = np.column_stack([traces_eye, np.full(n_tr, np.nan)]).ravel()

            couleur_eye = st.session_state.curve_colors.get(courbe_canal_eye, "#00D2FF")
            fig_eye = go.Figure()

            fig_eye.add_trace(go.Scattergl(
                x=x_concat, y=y_concat,
                mode="lines",
                line=dict(color=couleur_eye, width=1.2),
                opacity=0.35,
                name=f"Traces {mode_modulation} ({debit_gbps} Gbps | tr={tr_tx_ps}ps, tf={tf_tx_ps}ps)"
            ))

            if afficher_masque_oeil:
                m_info = metrics_eye["mask_coords"]
                t_c = m_info["t_center_ui"] if "UI" in axe_x_eye_mode else m_info["t_center_ps"]
                for idx_eye, (v_bot, v_top, ew_ps_sub, ew_ui_sub) in enumerate(m_info["eyes"]):
                    if v_top > v_bot:
                        half_w = (ew_ui_sub * 0.35) if "UI" in axe_x_eye_mode else (ew_ps_sub * 0.35)
                        v_mid_sub = 0.5 * (v_bot + v_top)
                        diamond_x = [t_c - half_w, t_c, t_c + half_w, t_c, t_c - half_w]
                        diamond_y = [v_mid_sub, v_top, v_mid_sub, v_bot, v_mid_sub]
                        fig_eye.add_trace(go.Scatter(
                            x=diamond_x, y=diamond_y,
                            mode="lines+markers",
                            fill="toself",
                            fillcolor="rgba(255, 50, 50, 0.22)",
                            line=dict(color="#FF3333", width=2),
                            name=f"Ouverture Œil {idx_eye + 1}" if mode_modulation == "PAM-4" else "Ouverture de l'Œil"
                        ))

            layout_eye = dict(
                title=f"Diagramme de l'Œil {mode_modulation} à {debit_gbps} Gbps (tr={tr_tx_ps} ps, tf={tf_tx_ps} ps) — {courbe_canal_eye}",
                xaxis_title=f"Temps ({unite_eye_str})",
                yaxis_title="Tension Différentielle (V)",
                showlegend=True,
                height=650
            )
            if activer_zoom_eye:
                layout_eye["xaxis"] = dict(range=[x_min_eye, x_max_eye])
                layout_eye["yaxis"] = dict(range=[y_min_eye, y_max_eye])
            fig_eye.update_layout(**layout_eye)

            st.plotly_chart(fig_eye, use_container_width=True)

            st.markdown("### 📋 Tableau Détaillé des Mesures du Diagramme de l'Œil")
            st.dataframe(metrics_eye["details_yeux"], use_container_width=True)
    else:
        st.info("Veuillez sélectionner au moins un connecteur dans la barre latérale.")
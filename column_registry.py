"""Registre descriptif des colonnes d'essais, sans calcul scientifique.

Les unités proviennent des en-têtes ou d'un profil confirmé, jamais de
la magnitude des valeurs. Les positions sont en base zéro.
"""
import re
from dataclasses import asdict, dataclass

import pandas as pd


# Aucune normalisation Unicode NFKC : elle effacerait la distinction G² / G2.
def normalize_unit(raw: str) -> str:
    value = raw.strip().replace('\u00a0', ' ').replace('\u202f', ' ')
    value = value.replace('µ', 'u').replace('μ', 'u').replace('·', '*')
    value = value.replace('²', '^2').replace('³', '^3').replace('⁻¹', '^-1')
    value = re.sub(r'\*\*([23])', r'^\1', value)
    value = re.sub(r'\s+', '', value)
    return value


@dataclass(frozen=True)
class UnitInfo:
    unit: str
    normalized: str
    dimension: str
    status: str


def parse_unit(header: str) -> UnitInfo:
    """Extrait uniquement une unité terminale entre parenthèses.

    Les signes (+)/(-) sont des limites, pas des unités.
    """
    if 'Â²' in header or 'Â³' in header:
        return UnitInfo('', '', 'inconnue', 'alerte_encodage')
    nested = re.search(r'\(((?:\(m/s(?:²|\^2)\)(?:²|\^2)/Hz))\)\s*$', header, re.I)
    if nested:
        raw = nested.group(1)
        norm = normalize_unit(raw)
        return UnitInfo(raw, norm, 'PSD_accélération', 'déclarée')
    match = re.search(r'\(([^()]*)\)\s*$', header)
    # Inclut notamment (m/s²)²/Hz et (m/s^2)^2/Hz en fin de nom.
    if not match:
        special = re.search(r'(\(m/s(?:²|\^2)\)(?:²|\^2)/Hz)\s*$', header, re.I)
        if special:
            raw = special.group(1)
        else:
            return UnitInfo('', '', 'inconnue', 'non_déclarée')
    else:
        raw = match.group(1).strip()
        if raw in ('+', '-'):
            return UnitInfo('', '', 'inconnue', 'non_déclarée')
    norm = normalize_unit(raw)
    if re.fullmatch(r'(?i:g)2/Hz', norm):
        return UnitInfo(raw, norm, 'inconnue', 'ambiguë')
    dimensions = {
        'Hz': 'fréquence', 'kHz': 'fréquence',
        's': 'temps', 'ms': 'temps', 'min': 'temps', 'h': 'temps',
        'G': 'accélération', 'g': 'accélération', 'mg': 'accélération',
        'm/s^2': 'accélération', 'm/s': 'vitesse', 'mm': 'déplacement',
        'rad': 'phase', 'Volts': 'tension', 'V': 'tension',
        'G^2/Hz': 'PSD_accélération', 'g^2/Hz': 'PSD_accélération',
        '(m/s^2)^2/Hz': 'PSD_accélération', 'm^3': 'volume',
    }
    dimension = dimensions.get(norm)
    return UnitInfo(raw, norm, dimension or 'inconnue', 'déclarée' if dimension else 'inconnue')


# Séquences de reconnaissance du profil de référence. Les positions absolues
# ne sont jamais obligatoires ; elles servent seulement à distinguer les groupes.
ANCHORS = {
    'A — profil': ('Frequency (Hz)', 'Demand1 (G)', 'Control1 (G)', 'Abort1(+)', 'Tol1(+)'),
    'B — historique': ('Time (min)', 'Frequency (Hz)', 'Demand1 (G)', 'Control1 (G)'),
    'C — temporel': ('Time (ms)', 'Fixe1 (G)', 'Goute 2 (G)', 'Goute 3 (G)', 'Goute 4 (G)'),
}


def _anchor_positions(headers):
    matches = {}
    for group, sequence in ANCHORS.items():
        starts = [i for i in range(len(headers) - len(sequence) + 1)
                  if tuple(headers[i:i + len(sequence)]) == sequence]
        if len(starts) == 1:
            matches[group] = starts[0]
    return matches


def _role(header, dimension):
    if header.startswith('Frequency (') and dimension == 'fréquence':
        return 'axe fréquence'
    if header.startswith('Time (') and dimension == 'temps':
        return 'axe temps'
    if header.startswith(('Abort', 'Tol', 'Velocity Abort', 'Velocity Tol',
                          'Displacement Abort', 'Displacement Tol')):
        return 'limite'
    if dimension == 'PSD_accélération':
        return 'PSD fournie (candidate)'
    if header.startswith('Demand'):
        return 'consigne (candidate)'
    if header.startswith('Control'):
        return 'contrôle (candidat)'
    if dimension == 'accélération':
        return 'voie accélération (candidate)'
    return 'non déterminé'


def build_column_registry(df: pd.DataFrame, csv_report: dict) -> list[dict]:
    """Retourne le registre, sans modifier le dataframe ni déduire de fs.

    Le profil est validé par un ensemble d'en-têtes contigus, exacts et uniques,
    puis par la concordance du support avec l'axe local.
    """
    headers = tuple(csv_report['original_headers'])
    anchors = _anchor_positions(headers)
    order = sorted((start, group) for group, start in anchors.items())
    starts = {group: start for start, group in order}
    registered = []
    supports = [frozenset(df.index[df.iloc[:, i].notna()]) for i in range(len(df.columns))]
    for idx, col in enumerate(df.columns):
        raw = headers[idx] if idx < len(headers) else col
        unit = parse_unit(raw)
        group = 'non déterminé'
        for j, (start, name) in enumerate(order):
            stop = order[j + 1][0] if j + 1 < len(order) else len(headers)
            if start <= idx < stop:
                group = name
                break
        # Un groupe n'est assigné que si sa série a le support de son axe.
        if group != 'non déterminé':
            anchor_idx = starts[group]
            anchor_support = supports[anchor_idx]
            if idx >= len(headers) or supports[idx] != anchor_support:
                group = 'non déterminé'
        # Si seul C est reconnu, aucun groupe n'est présumé avant son ancre.
        if idx >= len(headers):
            group = 'hors en-tête'
        if group == 'A — profil' and raw in ('Abort1(+)', 'Tol1(+)', 'Tol1(-)', 'Abort1(-)'):
            # Unité validée dans le seul profil de référence, jamais globalement.
            unit = UnitInfo('G', 'G', 'accélération', 'confirmée_profil')
        count = len(supports[idx])
        series = df.iloc[:, idx]
        numeric = pd.to_numeric(series, errors='coerce')
        finite = numeric.dropna()
        role = _role(raw, unit.dimension)
        if group == 'B — historique' and idx == starts[group] + 1 and raw == 'Frequency (Hz)':
            role = 'fréquence de consigne (confirmée profil)'
        confidence = 'confirmée_profil' if group != 'non déterminé' and group != 'hors en-tête' else 'candidate'
        if unit.status in ('ambiguë', 'alerte_encodage', 'inconnue'):
            confidence = 'non fiable'
        registered.append({
            'index': idx, 'colonne_interne': col, 'nom_brut': raw,
            'unité': unit.unit or 'non déclarée', 'unité_normalisée': unit.normalized,
            'statut_unité': unit.status, 'dimension': unit.dimension,
            'groupe': group, 'valeurs_présentes': count,
            'minimum': float(finite.min()) if len(finite) else None,
            'maximum': float(finite.max()) if len(finite) else None,
            'abscisse': (f"[{starts[group]}] {headers[starts[group]]}"
                          if group in starts and idx != starts[group] else 'à déterminer'),
            'rôle_proposé': role, 'confiance': confidence,
            'trous_internes': (max(supports[idx]) - min(supports[idx]) + 1 - count) if count else 0,
        })
    return registered

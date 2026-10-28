"""Sélection et contrôle d'un balayage fréquence/temps, sans modifier les mesures."""
from dataclasses import dataclass
import numpy as np
import pandas as pd

TIME_UNITS = {'s', 'ms', 'min', 'h'}
FREQ_UNITS = {'Hz', 'kHz'}


@dataclass(frozen=True)
class SweepResult:
    ok: bool
    message: str
    time_index: int
    frequency_index: int
    time: np.ndarray | None = None
    frequency: np.ndarray | None = None
    n_reversals: int = 0
    dt_min: float | None = None
    dt_max: float | None = None
    rate_min: float | None = None
    rate_max: float | None = None
    octave_rate_min: float | None = None
    octave_rate_max: float | None = None
    log_frequency_suggested: bool = False


def candidate_pairs(df: pd.DataFrame, registry: list[dict]) -> list[tuple[int, int]]:
    """Paires possibles en conservant les indices, y compris les noms dupliqués."""
    times = [r for r in registry if r['dimension'] == 'temps'
             and r['unité_normalisée'] in TIME_UNITS and r['statut_unité'] == 'déclarée']
    freqs = [r for r in registry if r['dimension'] == 'fréquence'
             and r['unité_normalisée'] in FREQ_UNITS and r['statut_unité'] == 'déclarée']
    return [(t['index'], f['index']) for t in times for f in freqs]


def compatible_pairs(df: pd.DataFrame, registry: list[dict]) -> list[tuple[int, int]]:
    return [(t, f) for t, f in candidate_pairs(df, registry)
            if df.iloc[:, t].notna().equals(df.iloc[:, f].notna())
            and int(df.iloc[:, t].notna().sum()) >= 2]


def _constant_ratio(frequency: np.ndarray) -> bool:
    """Détection conservatrice d'une grille entière à rapport constant."""
    if len(frequency) < 4 or not np.all(np.diff(frequency) > 0):
        return False
    ratios = frequency[1:] / frequency[:-1]
    return bool(np.allclose(ratios, np.median(ratios), rtol=1e-3, atol=0))


def analyze_sweep(df: pd.DataFrame, registry: list[dict], time_index: int,
                  frequency_index: int) -> SweepResult:
    def fail(msg):
        return SweepResult(False, msg, time_index, frequency_index)

    records = {r['index']: r for r in registry}
    t = records.get(time_index)
    f = records.get(frequency_index)
    if t is None or f is None:
        return fail('Colonne absente du fichier.')
    if t['dimension'] != 'temps' or t['unité_normalisée'] not in TIME_UNITS or t['statut_unité'] != 'déclarée':
        return fail('Axe temps : unité déclarée s, ms, min ou h requise.')
    if f['dimension'] != 'fréquence' or f['unité_normalisée'] not in FREQ_UNITS or f['statut_unité'] != 'déclarée':
        return fail('Axe fréquence : unité déclarée Hz ou kHz requise.')
    time_s = df.iloc[:, time_index]
    freq_s = df.iloc[:, frequency_index]
    if not time_s.notna().equals(freq_s.notna()):
        return fail('Supports de lignes différents : ce temps et cette fréquence ne forment pas un couple exploitable.')
    if int(time_s.notna().sum()) < 2:
        return fail('Deux points communs au minimum sont nécessaires.')
    # Toute valeur texte ou infinie entraîne un refus explicite, sans suppression silencieuse.
    try:
        time = pd.to_numeric(time_s.dropna(), errors='raise').to_numpy(dtype=float)
        frequency = pd.to_numeric(freq_s.dropna(), errors='raise').to_numpy(dtype=float)
    except (ValueError, TypeError):
        return fail('Données non numériques dans le balayage.')
    if not (np.isfinite(time).all() and np.isfinite(frequency).all()):
        return fail('Valeurs non finies dans le balayage.')
    dt = np.diff(time)
    if not np.all(dt > 0):
        return fail('Temps non strictement croissant : doublon ou retour en arrière ; tracé refusé.')
    if not np.all(frequency > 0):
        return fail('La fréquence doit être strictement positive ; tracé refusé.')
    dfreq = np.diff(frequency)
    signs = np.sign(dfreq)
    signs = signs[signs != 0]
    reversals = int(np.sum(signs[1:] != signs[:-1]))
    # Indicateurs dérivés en Hz/min et octaves/min ; axes et mesures inchangés.
    minutes_per_unit = {"ms": 1 / 60000, "s": 1 / 60, "min": 1, "h": 60}[t["unité_normalisée"]]
    hz_per_unit = {"Hz": 1, "kHz": 1000}[f["unité_normalisée"]]
    dt_minutes = dt * minutes_per_unit
    local_rate = dfreq * hz_per_unit / dt_minutes
    octave_rate = np.log2(frequency[1:] / frequency[:-1]) / dt_minutes
    return SweepResult(
        True, '', time_index, frequency_index, time, frequency,
        n_reversals=reversals,
        dt_min=float(np.min(dt)), dt_max=float(np.max(dt)),
        rate_min=float(np.min(local_rate)), rate_max=float(np.max(local_rate)),
        octave_rate_min=float(np.min(octave_rate)), octave_rate_max=float(np.max(octave_rate)),
        log_frequency_suggested=_constant_ratio(frequency),
    )

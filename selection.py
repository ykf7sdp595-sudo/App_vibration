"""Sélections par indices, unités et supports, non par nombre fixe de colonnes."""
import numpy as np
import pandas as pd
from science import ScientificError, validate_sampling


def same_support(df, i, j):
    return df.iloc[:,i].notna().equals(df.iloc[:,j].notna())

def frequency_candidates(registry):
    return [r['index'] for r in registry if r['dimension']=='fréquence' and r['statut_unité']=='déclarée']

def acceleration_candidates(df,registry,freq_index):
    return [r['index'] for r in registry
            if r['dimension']=='accélération' and r['statut_unité'] in ('déclarée','confirmée_profil')
            and same_support(df,freq_index,r['index'])]

def validate_frequency_plot(df, registry, freq_idx, series_indices):
    if not series_indices:
        raise ScientificError('Sélectionner au moins une accélération.')
    if freq_idx not in frequency_candidates(registry):
        raise ScientificError('Axe fréquence invalide.')
    f=pd.to_numeric(df.iloc[:,freq_idx].dropna(),errors='raise').to_numpy(dtype=float)
    if len(f)<2 or not np.isfinite(f).all() or np.any(f<=0):
        raise ScientificError('Fréquences non finies, nulles ou négatives.')
    units=set()
    ys={}
    for i in series_indices:
        if i not in acceleration_candidates(df,registry,freq_idx):
            raise ScientificError(f'Colonne [{i}] incompatible avec la fréquence [{freq_idx}].')
        units.add(registry[i]['unité_normalisée'])
        y=pd.to_numeric(df.iloc[:,i].dropna(),errors='raise').to_numpy(dtype=float)
        if not np.isfinite(y).all():
            raise ScientificError(f'Valeurs non finies dans la colonne [{i}].')
        ys[i]=y
    if len(units)>1:
        raise ScientificError('Unités différentes : sélectionner une seule unité Y, sans conversion implicite.')
    return f,ys,units.pop()

def time_candidates(registry):
    return [r['index'] for r in registry if r['dimension']=='temps' and r['statut_unité']=='déclarée']

def time_acceleration_candidates(df,registry,time_idx):
    return [r['index'] for r in registry if r['dimension']=='accélération' and r['statut_unité']=='déclarée'
            and same_support(df,time_idx,r['index'])]

def signal_time_series(df,registry,time_idx,channel_idx):
    if time_idx not in time_candidates(registry) or channel_idx not in time_acceleration_candidates(df,registry,time_idx):
        raise ScientificError('Temps et accélération incompatibles.')
    t=pd.to_numeric(df.iloc[:,time_idx].dropna(),errors='raise').to_numpy(dtype=float)
    x=pd.to_numeric(df.iloc[:,channel_idx].dropna(),errors='raise').to_numpy(dtype=float)
    return t,x

def infer_known_test_type(registry):
    groups={r['groupe'] for r in registry}
    if 'A — profil' in groups and 'B — historique' in groups:
        return 'sinus'
    return 'inconnu'

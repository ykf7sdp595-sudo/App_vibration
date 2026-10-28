"""Réduction réservée à l'affichage ; ne pas utiliser pour les calculs."""
import numpy as np


def reduce_plot_points(frame, columns, limit):
    """Garde les extrémités et les min/max de chaque série par intervalle.

    La sélection est commune aux séries, sans interpolation. Elle ne garantit
    pas de conserver chaque pic local. Les lignes manquantes sont conservées
    pour ne pas relier des segments séparés ; elles comptent dans la limite.
    """
    if limit < 2 or not columns:
        raise ValueError('Au moins deux points et une série sont requis.')
    if len(frame) <= limit:
        return frame
    values = frame[columns].to_numpy(dtype=float)
    missing = np.flatnonzero(~np.isfinite(values).all(axis=1))
    keep = set(missing.tolist()) | {0, len(frame)-1}
    budget = limit - len(keep)
    bins = budget // (2 * len(columns))
    if bins < 1:
        # Trop de discontinuités : refuser plutôt que les masquer.
        raise ValueError('Trop de valeurs manquantes pour cette limite d’affichage ; augmentez la limite ou réduisez la sélection.')
    for chunk in np.array_split(np.arange(len(frame)), bins):
        for col in range(len(columns)):
            valid = chunk[np.isfinite(values[chunk, col])]
            if len(valid):
                keep.add(int(valid[np.argmin(values[valid, col])]))
                keep.add(int(valid[np.argmax(values[valid, col])]))
    return frame.iloc[sorted(keep)]

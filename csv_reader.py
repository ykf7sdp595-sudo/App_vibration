"""Lecture CSV conservatrice : aucune ligne ni donnée non vide ignorée silencieusement.

Ce module ne déduit ni unités, ni type d'essai, ni fréquence d'échantillonnage.
"""

import csv
import io
import re
from collections import Counter

import pandas as pd


DELIMITERS = (",", ";", "\t", "|")
ENCODINGS = ("utf-8-sig", "cp1252", "latin-1")


def _unique_names(headers):
    """Conserve le premier nom, suffixe les occurrences suivantes par position."""
    used = set()
    names = []
    for index, raw in enumerate(headers, start=1):
        base = raw.strip() or f"Colonne sans nom {index}"
        name = base
        if name in used:
            name = f"{base} [colonne {index}]"
        while name in used:
            name += "_"
        used.add(name)
        names.append(name)
    return names


def _decode(file_bytes):
    for encoding in ENCODINGS:
        try:
            return file_bytes.decode(encoding, errors="strict"), encoding
        except UnicodeDecodeError:
            pass
    raise ValueError("Encodage CSV non reconnu.")


def _choose_delimiter(text):
    """Détermine le séparateur depuis la première ligne CSV non vide."""
    candidates = []
    for delimiter in DELIMITERS:
        reader = csv.reader(io.StringIO(text, newline=""), delimiter=delimiter, strict=True)
        try:
            first = next(reader)
        except StopIteration:
            raise ValueError("Le fichier CSV est vide.")
        except csv.Error:
            continue
        candidates.append((len(first), delimiter))
    count, delimiter = max(candidates, key=lambda item: item[0])
    if count < 2:
        raise ValueError("Séparateur CSV non reconnu (au moins deux colonnes attendues).")
    return delimiter


def read_csv_robust(file_bytes: bytes):
    """Retourne (DataFrame, rapport) en conservant chaque enregistrement lu.

    Champs finaux supplémentaires vides : tolérés et comptabilisés.
    Champs supplémentaires non vides : conservés dans des colonnes dédiées.
    Lignes courtes : complétées par des cellules vides, sans interpolation.
    Les noms originaux et leurs indices restent accessibles dans le rapport.
    """
    if not file_bytes:
        raise ValueError("Le fichier CSV est vide.")
    text, encoding = _decode(file_bytes)
    delimiter = _choose_delimiter(text)
    reader = csv.reader(io.StringIO(text, newline=""), delimiter=delimiter, strict=True)
    try:
        headers = next(reader)
        if not headers or not any(h.strip() for h in headers):
            raise ValueError("L'en-tête CSV est vide.")
        width = len(headers)
        rows = []
        time_positions = [i for i, h in enumerate(headers) if h.strip().startswith("Time (")]
        time_digits = {i: 0 for i in time_positions}
        time_resolutions = {i: [] for i in time_positions}
        extra_empty_rows = 0
        extra_nonempty_rows = 0
        short_rows = 0
        max_nonempty_extra = 0
        for row in reader:
            for i in time_positions:
                resolution = None
                if i < len(row):
                    value = row[i].strip()
                    match = re.fullmatch(r'[+-]?(?:\d+(?:\.(\d+))?|\.(\d+))(?:[eE]([+-]?\d+))?', value)
                    if match:
                        decimals = len(match.group(1) or match.group(2) or '') - int(match.group(3) or 0)
                        time_digits[i] = max(time_digits[i], decimals)
                        resolution = 10.0**(-decimals)
                time_resolutions[i].append(resolution)
            # csv.reader peut renvoyer une ligne vide sous forme [] ; la conserver.
            if len(row) < width:
                short_rows += 1
                row = row + [""] * (width - len(row))
            elif len(row) > width:
                extras = row[width:]
                if any(value.strip() for value in extras):
                    extra_nonempty_rows += 1
                    max_nonempty_extra = max(max_nonempty_extra, len(extras))
                else:
                    extra_empty_rows += 1
            rows.append(row)
    except csv.Error as exc:
        raise ValueError(f"CSV mal formé à proximité de la ligne {reader.line_num} : {exc}") from exc

    names = _unique_names(headers)
    extra_names = []
    for i in range(max_nonempty_extra):
        name = f"Champ supplémentaire {width + i + 1} (hors en-tête)"
        while name in names or name in extra_names:
            name += "_"
        extra_names.append(name)
    cleaned = []
    for row in rows:
        values = row[:width]
        extras = row[width:]
        # Champs finaux vides ignorés uniquement au-delà de l'en-tête.
        cleaned.append(values + (extras[:max_nonempty_extra] + [""] * max(0, max_nonempty_extra - len(extras))))
    df = pd.DataFrame(cleaned, columns=names + extra_names)
    df = df.replace("", float("nan"))
    report = {
        "encoding": encoding,
        "delimiter": delimiter,
        "data_rows": len(rows),
        "header_count": width,
        "original_headers": tuple(headers),
        "duplicate_headers": sum(n - 1 for n in Counter(headers).values() if n > 1),
        "extra_empty_rows": extra_empty_rows,
        "extra_nonempty_rows": extra_nonempty_rows,
        "short_rows": short_rows,
        "extra_columns": tuple(extra_names),
        "time_precision": {i: 10.0**(-digits) for i, digits in time_digits.items()},
        "time_written_resolution": {i: tuple(values) for i, values in time_resolutions.items()},
    }
    return df, report


def convert_numeric_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Convertit les colonnes numériques, même courtes dans un CSV multi-groupes.

    Les cellules vides n'entrent pas dans le taux de conversion ; si une
    valeur non vide n'est pas numérique, on conserve toute la colonne en texte.
    Aucun point de mesure n'est interpolé ni supprimé.
    """
    converted_df = df.copy()
    for column in converted_df.columns:
        series = converted_df[column]
        # Pandas 3.x peut inférer le dtype texte « str » au lieu de « object ».
        # Ignorer seulement les colonnes déjà numériques, pas les colonnes texte.
        if pd.api.types.is_numeric_dtype(series):
            continue
        present = series.notna() & series.astype("string").str.strip().ne("").fillna(False)
        if not bool(present.any()):
            continue
        numeric = pd.to_numeric(
            series.astype("string").str.replace(",", ".", regex=False),
            errors="coerce",
        )
        if bool(numeric[present].notna().all()):
            converted_df[column] = numeric
    return converted_df

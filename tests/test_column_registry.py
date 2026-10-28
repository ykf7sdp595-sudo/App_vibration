import sys
import unittest
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from column_registry import build_column_registry, normalize_unit, parse_unit
from csv_reader import convert_numeric_columns, read_csv_robust


class ColumnRegistryTests(unittest.TestCase):
    def test_explicit_unicode_superscripts(self):
        for header in ('PSD (G²/Hz)', 'PSD (G^2/Hz)', 'PSD (G**2/Hz)'):
            self.assertEqual(parse_unit(header).dimension, 'PSD_accélération')
        self.assertEqual(parse_unit('Signal (m/s²)').dimension, 'accélération')
        self.assertEqual(parse_unit('Volume (m³)').dimension, 'volume')
        self.assertEqual(parse_unit('PSD ((m/s²)²/Hz)').dimension, 'PSD_accélération')

    def test_ambiguous_corrupt_and_undefined(self):
        self.assertEqual(parse_unit('PSD (G2/Hz)').status, 'ambiguë')
        self.assertEqual(parse_unit('Signal (Â²)').status, 'alerte_encodage')
        self.assertEqual(parse_unit('Abort1(+)').status, 'non_déclarée')
        self.assertEqual(parse_unit('Drive').status, 'non_déclarée')
        self.assertEqual(parse_unit('Signal (foo)').status, 'inconnue')

    def test_nonbreaking_spaces_and_micro(self):
        self.assertEqual(normalize_unit(' G² / Hz\u00a0'), 'G^2/Hz')
        self.assertEqual(normalize_unit('µm'), normalize_unit('μm'))

    def test_short_variable_file_and_duplicate_headers(self):
        raw = b'"Frequency (Hz)","Demand1 (G)","Frequency (Hz)"\n1,2,3\n2,3,4\n'
        frame, report = read_csv_robust(raw)
        frame = convert_numeric_columns(frame)
        reg = build_column_registry(frame, report)
        self.assertEqual(len(reg), 3)
        self.assertEqual([r['index'] for r in reg], [0, 1, 2])
        self.assertNotEqual(reg[0]['colonne_interne'], reg[2]['colonne_interne'])
        self.assertEqual(reg[0]['dimension'], 'fréquence')
        self.assertEqual(reg[1]['dimension'], 'accélération')
        self.assertTrue(all(x['groupe'] == 'non déterminé' for x in reg))

    def test_internal_missing_and_structural(self):
        raw = b'"Time (ms)","Fixe1 (G)"\n0,1\n1,\n2,3\n3,\n'
        frame, report = read_csv_robust(raw)
        reg = build_column_registry(convert_numeric_columns(frame), report)
        self.assertEqual(reg[1]['valeurs_présentes'], 2)
        self.assertEqual(reg[1]['trous_internes'], 1)
        self.assertEqual(reg[1]['groupe'], 'non déterminé')

    def test_reference_csv(self):
        source = Path('/mnt/data/csv_test_sin.csv')
        if not source.is_file():
            self.skipTest('CSV de référence non présent dans ce poste')
        frame, report = read_csv_robust(source.read_bytes())
        registry = build_column_registry(convert_numeric_columns(frame), report)
        self.assertEqual(len(registry), 66)
        self.assertEqual(registry[0]['groupe'], 'A — profil')
        self.assertEqual(registry[36]['groupe'], 'B — historique')
        self.assertEqual(registry[61]['groupe'], 'C — temporel')
        self.assertEqual(registry[37]['rôle_proposé'], 'fréquence de consigne (confirmée profil)')
        self.assertEqual(registry[3]['statut_unité'], 'confirmée_profil')
        self.assertEqual(registry[61]['valeurs_présentes'], 4096)
        self.assertEqual(registry[62]['abscisse'], '[61] Time (ms)')
        self.assertEqual(registry[0]['valeurs_présentes'], 2000)
        self.assertEqual(registry[36]['valeurs_présentes'], 7572)


if __name__ == '__main__':
    unittest.main()

import sys
import unittest
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from csv_reader import convert_numeric_columns, read_csv_robust
from column_registry import build_column_registry
from sweeps import candidate_pairs, compatible_pairs, analyze_sweep


def parsed(csv_text):
    df, report = read_csv_robust(csv_text.encode('utf-8'))
    df = convert_numeric_columns(df)
    return df, build_column_registry(df, report)


class SweepsTests(unittest.TestCase):
    def test_reference_csv(self):
        source = Path('/mnt/data/csv_test_sin.csv')
        if not source.is_file():
            self.skipTest('CSV de référence absent')
        df, report = read_csv_robust(source.read_bytes())
        df = convert_numeric_columns(df)
        reg = build_column_registry(df, report)
        self.assertIn((36, 37), compatible_pairs(df, reg))
        self.assertNotIn((61, 37), compatible_pairs(df, reg))
        self.assertNotIn((36, 0), compatible_pairs(df, reg))
        result = analyze_sweep(df, reg, 36, 37)
        self.assertTrue(result.ok, result.message)
        self.assertEqual(len(result.time), 7572)
        self.assertEqual(result.n_reversals, 23)
        self.assertAlmostEqual(result.frequency.max(), 2000)
        self.assertTrue(np.array_equal(result.frequency, df.iloc[:, 37].dropna().to_numpy()))
        self.assertFalse(analyze_sweep(df, reg, 61, 37).ok)

    def test_short_csv_no_fixed_positions(self):
        df, reg = parsed('Time (s),Frequency (Hz)\n0,10\n1,20\n2,10\n')
        self.assertEqual(candidate_pairs(df, reg), [(0, 1)])
        result = analyze_sweep(df, reg, 0, 1)
        self.assertTrue(result.ok)
        self.assertEqual(result.n_reversals, 1)
        self.assertEqual(result.rate_max, 600.0)
        self.assertEqual(result.rate_min, -600.0)

    def test_reject_time_duplicates_or_backwards(self):
        for times in ('0,10\n1,20\n1,30\n', '0,10\n2,20\n1,30\n'):
            df, reg = parsed('Time (min),Frequency (Hz)\n' + times)
            self.assertFalse(analyze_sweep(df, reg, 0, 1).ok)

    def test_supports_not_compatible(self):
        df, reg = parsed('Time (ms),Frequency (Hz)\n0,10\n1,\n2,30\n')
        self.assertNotIn((0, 1), compatible_pairs(df, reg))
        self.assertIn('Supports', analyze_sweep(df, reg, 0, 1).message)

    def test_zero_negative_or_nonfinite_rejected(self):
        for freq in ('0', '-10', 'inf'):
            df, reg = parsed('Time (s),Frequency (Hz)\n0,10\n1,' + freq + '\n')
            self.assertFalse(analyze_sweep(df, reg, 0, 1).ok)

    def test_log_frequency_constant_ratio(self):
        df, reg = parsed('Time (s),Frequency (Hz)\n0,10\n1,20\n2,40\n3,80\n')
        self.assertTrue(analyze_sweep(df, reg, 0, 1).log_frequency_suggested)

    def test_missing_headers_and_short_series(self):
        df, reg = parsed('Temps,Frequency (Hz)\n0,1\n1,2\n')
        self.assertEqual(candidate_pairs(df, reg), [])
        df, reg = parsed('Time (s),Frequency (Hz)\n0,10\n')
        self.assertFalse(analyze_sweep(df, reg, 0, 1).ok)


if __name__ == '__main__':
    unittest.main()

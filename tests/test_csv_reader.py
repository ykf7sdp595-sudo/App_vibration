import csv
import io
import unittest
import pandas as pd
from pathlib import Path

from csv_reader import read_csv_robust, convert_numeric_columns


class TestCsvReader(unittest.TestCase):
    def test_shorter_file_and_short_row(self):
        df, report = read_csv_robust(b"Time (ms);Accel (G)\n0;1\n1\n2;3\n")
        self.assertEqual(df.shape, (3, 2))
        self.assertEqual(report["short_rows"], 1)
        self.assertTrue(df.iloc[1, 1] != df.iloc[1, 1])

    def test_extra_empty(self):
        df, report = read_csv_robust(b"x,y\n1,2\n3,4,\n")
        self.assertEqual(df.shape, (2, 2))
        self.assertEqual(report["extra_empty_rows"], 1)

    def test_extra_nonempty_preserved(self):
        df, report = read_csv_robust(b"x,y\n1,2,abc\n3,4\n")
        self.assertEqual(df.shape, (2, 3))
        self.assertEqual(df.iloc[0, 2], "abc")
        self.assertEqual(report["extra_nonempty_rows"], 1)

    def test_duplicate_headers_kept_separate(self):
        df, report = read_csv_robust(b"Time (ms),Accel (G),Accel (G)\n0,1,2\n")
        self.assertEqual(df.shape, (1, 3))
        self.assertNotEqual(df.columns[1], df.columns[2])
        self.assertEqual(report["original_headers"][2], "Accel (G)")

    def test_malformed_quoted_csv_is_rejected(self):
        with self.assertRaises(ValueError):
            read_csv_robust(b'x,y\n"unclosed,2\n')

    def test_sparse_numeric_columns_are_detected(self):
        df, _ = read_csv_robust(b"freq,short,notes\n1,2,ok\n2,,other\n3,,third\n4,,fourth\n")
        result = convert_numeric_columns(df)
        self.assertEqual(result.select_dtypes(include="number").shape[1], 2)
        self.assertEqual(float(result["short"].iloc[0]), 2.0)
        self.assertTrue(pd.isna(result["short"].iloc[1]))
        self.assertEqual(result["notes"].iloc[0], "ok")

    def test_pandas_string_dtype_numeric_is_detected(self):
        # Reproduit le dtype texte utilisé par Pandas 3.x.
        df = pd.DataFrame({
            "Frequency (Hz)": pd.Series(["5", "5.5", None], dtype="str"),
            "Demand1 (G)": pd.Series(["0.07", "0.08", None], dtype="str"),
            "Commentaire": pd.Series(["début", "fin", None], dtype="str"),
        })
        result = convert_numeric_columns(df)
        self.assertEqual(len(result.select_dtypes(include="number").columns), 2)
        self.assertEqual(float(result["Frequency (Hz)"].iloc[1]), 5.5)
        self.assertTrue(pd.isna(result["Demand1 (G)"].iloc[2]))
        self.assertEqual(result["Commentaire"].iloc[0], "début")

    def test_mixed_text_numeric_is_not_silently_coerced(self):
        df, _ = read_csv_robust(b"time,value\n0,1\n1,ERROR\n2,3\n")
        result = convert_numeric_columns(df)
        self.assertEqual(result["value"].iloc[1], "ERROR")
        self.assertNotIn("value", result.select_dtypes(include="number").columns)

    def test_reference_csv(self):
        path = Path(__file__).resolve().parents[2] / "csv_test_sin.csv"
        if not path.exists():
            self.skipTest("CSV de référence absent")
        df, report = read_csv_robust(path.read_bytes())
        self.assertEqual(df.shape, (7572, 66))
        self.assertEqual(report["extra_empty_rows"], 3476)
        self.assertEqual(report["extra_nonempty_rows"], 0)
        self.assertEqual(report["data_rows"], 7572)
        converted = convert_numeric_columns(df)
        self.assertEqual(len(converted.select_dtypes(include="number").columns), 66)
        self.assertEqual(converted["Frequency (Hz)"].notna().sum(), 2000)
        self.assertEqual(converted["Time (ms)"].notna().sum(), 4096)


if __name__ == "__main__":
    unittest.main()

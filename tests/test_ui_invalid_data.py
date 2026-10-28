import unittest
from streamlit.testing.v1 import AppTest

class InvalidDataTests(unittest.TestCase):
    def check_view(self, function, csv):
        code=f'''from csv_reader import read_csv_robust, convert_numeric_columns
from column_registry import build_column_registry
from specialized_tabs import {function}
df, report = read_csv_robust({csv!r})
df = convert_numeric_columns(df)
{function}(df, build_column_registry(df, report), report)
'''
        app=AppTest.from_string(code).run()
        self.assertFalse(app.exception)
        self.assertTrue(app.warning)

    def test_chocs_rejects_text_without_crash(self):
        self.check_view('ui_chocs',b'Time (s),Channel (G)\n0,1\n1,bad\n')

    def test_psd_rejects_text_without_crash(self):
        self.check_view('ui_psd','Frequency (Hz),PSD (G²/Hz)\n1,1\n2,bad\n'.encode())

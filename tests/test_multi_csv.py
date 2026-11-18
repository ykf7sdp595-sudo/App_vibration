"""Integration tests with an uploader stub (AppTest cannot upload files)."""
from pathlib import Path
import unittest

from streamlit.testing.v1 import AppTest


APP = Path(__file__).with_name('multi_csv_app.py')
CSV = b'Time (s),Frequency (Hz),Channel (G)\n0,1,1\n1,2,-2\n2,3,1\n'


class MultiCsvTests(unittest.TestCase):
    def app(self, files):
        app = AppTest.from_file(str(APP), default_timeout=30)
        app.session_state['test_files'] = files
        return app.run()

    def test_identical_files_all_views_and_independent_settings(self):
        app = self.app([('essai.csv', CSV), ('essai.csv', CSV)])
        self.assertFalse(app.exception)
        self.assertEqual(len(app.tabs), 2)
        for view in ('VIBRATIONS', 'CHOCS', 'PSD', 'Courbe libre', 'SWEEPS'):
            for radio in app.radio:
                if radio.label == 'Analyse':
                    radio.set_value(view)
            app.run()
            self.assertFalse(app.exception, view)
        radios = [r for r in app.radio if r.label == 'Analyse']
        radios[0].set_value('Courbe libre').run()
        self.assertEqual([r.value for r in app.radio if r.label == 'Analyse'],
                         ['Courbe libre', 'SWEEPS'])
        filters = [m for m in app.multiselect if m.label == 'Colonnes à filtrer']
        filters[0].set_value(['Channel (G)']).run()
        self.assertEqual([m.value for m in app.multiselect if m.label == 'Colonnes à filtrer'],
                         [['Channel (G)'], []])
        app.slider(key=filters[0].key.removesuffix('filter_columns') + 'filter_Channel (G)').set_value((0.0, 1.0)).run()
        app.button[0].click().run()
        self.assertFalse(app.exception)
        self.assertEqual(len(app.get('download_button')), 2)  # filtered CSV + second file SWEEPS

    def test_invalid_file_does_not_stop_next_file(self):
        app = self.app([('vide.csv', b''), ('valide.csv', CSV)])
        self.assertFalse(app.exception)
        self.assertTrue(app.error)
        self.assertEqual(len(app.radio), 1)
        self.assertEqual(len(app.metric), 7)

    def test_removal_preserves_remaining_file_and_cleans_state(self):
        app = self.app([('a.csv', CSV), ('b.csv', CSV)])
        app.radio[1].set_value('Courbe libre').run()
        removed_key = app.radio[0].key
        app.session_state['test_files'] = [('b.csv', CSV)]
        app.run()
        self.assertFalse(app.exception)
        self.assertEqual(len(app.tabs), 1)
        self.assertEqual(app.radio[0].value, 'Courbe libre')
        self.assertNotIn(removed_key, app.session_state)
        app.session_state['test_files'] = []
        app.run()
        self.assertFalse(app.exception)
        self.assertEqual(len(app.tabs), 0)

    def test_multiple_psd_series_per_file(self):
        csv = 'Frequency (Hz),PSD (G²/Hz),PSD (G²/Hz)\n1,1,2\n2,2,3\n3,3,4\n'.encode()
        app = self.app([('a.csv', csv), ('b.csv', csv)])
        for radio in app.radio:
            radio.set_value('PSD')
        app.run()
        self.assertFalse(app.exception)
        self.assertEqual(len(app.get('plotly_chart')), 4)
        nodes = list(app.tabs[0])
        order = [('graph' if node.type == 'plotly_chart' else 'axes') for node in nodes
                 if node.type == 'plotly_chart' or
                 (node.type == 'expander' and 'Titre et axes du graphique' in node.label)]
        self.assertEqual(order, ['graph', 'axes', 'graph', 'axes'])

    def test_graph_before_its_options_and_legends_below(self):
        app = self.app([('essai.csv', CSV)])
        self.assertFalse(app.exception)
        nodes = list(app.tabs[0])
        chart_index = next(i for i, node in enumerate(nodes) if node.type == 'plotly_chart')
        axis_index = next(i for i, node in enumerate(nodes) if node.type == 'expander' and 'Titre et axes du graphique' in node.label)
        self.assertLess(chart_index, axis_index)
        self.assertTrue(all(not node.proto.expanded for node in nodes if node.type == 'expander'))
        import json
        legend = json.loads(app.get('plotly_chart')[0].proto.spec)['layout']['legend']
        self.assertEqual(legend['orientation'], 'h')
        self.assertLess(legend['y'], 0)

    def test_import_diagnostics_are_in_sidebar(self):
        csv = b'Time (s),Frequency (Hz),Channel (G)\n0,1\n1,2,3\n'
        app = self.app([('essai.csv', csv)])
        self.assertFalse(app.exception)
        self.assertTrue(any('Informations d’import' in panel.label for panel in app.sidebar.expander))
        self.assertTrue(any('plus courtes' in item.value for item in app.sidebar.warning))

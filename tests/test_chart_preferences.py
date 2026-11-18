import json
from pathlib import Path
import unittest

import plotly.graph_objects as go
from streamlit.testing.v1 import AppTest
from specialized_tabs import _analysis_labels, apply_plot_axis_controls


class ChartPreferencesTests(unittest.TestCase):
    def test_scales_and_colors_survive_removing_all_curves(self):
        app = AppTest.from_file(str(Path(__file__).with_name('multi_csv_app.py')), default_timeout=30)
        app.session_state['test_files'] = [('test.csv',
            b'Time (s),Frequency (Hz),Channel (G),Channel 2 (G)\n1,10,1,2\n2,20,3,4\n3,30,2,3\n')]
        app.run()
        scales = [s for s in app.selectbox if s.label.startswith('Échelle')]
        self.assertEqual([s.value for s in scales], ['Linéaire', 'Logarithmique'])
        app.radio[0].set_value('VIBRATIONS').run()
        for s in app.selectbox:
            if s.label == 'Fréquence' and s.value is None:
                s.set_value(1)
        app.run()
        self.assertFalse(app.exception)
        scales = [s for s in app.selectbox if s.label.startswith('Échelle')]
        self.assertEqual([s.value for s in scales], ['Logarithmique', 'Logarithmique'])
        scales[0].set_value('Linéaire').run()
        app.color_picker[0].set_value('#123456').run()
        series = next(m for m in app.multiselect if m.label == 'Accélérations')
        initial = list(series.value)
        series.set_value([2, 3]).run()
        self.assertEqual(next(s for s in app.selectbox if s.label == 'Échelle horizontale').value, 'Linéaire')
        next(m for m in app.multiselect if m.label == 'Accélérations').set_value([]).run()
        next(m for m in app.multiselect if m.label == 'Accélérations').set_value(initial).run()
        self.assertFalse(app.exception)
        self.assertEqual(next(s for s in app.selectbox if s.label == 'Échelle horizontale').value, 'Linéaire')
        self.assertEqual(app.color_picker[0].value, '#123456')
        spec = json.loads(app.get('plotly_chart')[0].proto.spec)
        self.assertEqual(spec['data'][0]['line']['color'], '#123456')

    def test_annotation_anchor_on_log_axes_and_nonpositive_values(self):
        fig = go.Figure()
        _analysis_labels(fig, [dict(frequency=100, amplitude=10, index=1),
                              dict(frequency=0, amplitude=-1, index=2)], 'G')
        apply_plot_axis_controls(fig, dict(title='Test', x_title='Hz', y_title='G',
            log_x=True, log_y=True, show_grid=True, x_range=None, y_range=None))
        annotation = fig.layout.annotations[0]
        self.assertEqual((annotation.x, annotation.y), (2, 1))
        self.assertTrue(annotation.showarrow)
        self.assertEqual(annotation.axref, 'pixel')
        self.assertFalse(fig.layout.annotations[1].visible)

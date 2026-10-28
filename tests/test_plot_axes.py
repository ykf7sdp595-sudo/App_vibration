import sys
import unittest
from pathlib import Path

import plotly.graph_objects as go

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from specialized_tabs import apply_plot_axis_controls


class PlotAxisTests(unittest.TestCase):
    def test_title_scales_ranges_and_grid_are_applied(self):
        figure=go.Figure()
        options={
            'title':'Spectre de test',
            'x_title':'Fréquence (Hz)',
            'y_title':'Accélération (G)',
            'log_x':True,
            'log_y':False,
            'show_grid':True,
            'x_range':(1.0,1000.0),
            'y_range':(-2.0,4.0),
        }

        apply_plot_axis_controls(figure,options)

        self.assertEqual(figure.layout.title.text,'Spectre de test')
        self.assertEqual(figure.layout.xaxis.type,'log')
        self.assertEqual(list(figure.layout.xaxis.range),[0.0,3.0])
        self.assertEqual(figure.layout.xaxis.title.text,'Fréquence (Hz)')
        self.assertEqual(figure.layout.yaxis.type,'linear')
        self.assertEqual(list(figure.layout.yaxis.range),[-2.0,4.0])
        self.assertEqual(figure.layout.yaxis.title.text,'Accélération (G)')
        self.assertTrue(figure.layout.xaxis.showgrid)
        self.assertTrue(figure.layout.yaxis.showgrid)


if __name__=='__main__':
    unittest.main()

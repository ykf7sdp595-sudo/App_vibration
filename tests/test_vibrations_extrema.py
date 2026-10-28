import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from vibrations import find_vibration_extrema,find_vibration_peaks


class VibrationExtremaTests(unittest.TestCase):
    def test_detects_local_maximum(self):
        result=find_vibration_peaks(np.arange(5),np.array([0,1,4,1,0]))
        self.assertEqual(len(result['peaks']),1)
        self.assertEqual(result['peaks'][0]['index'],2)
        self.assertEqual(result['peaks'][0]['frequency'],2.0)
        self.assertEqual(result['peaks'][0]['amplitude'],4.0)

    def test_repeated_frequencies_keep_sample_association(self):
        result=find_vibration_peaks(
            np.array([10,20,20,10,30]),np.array([0,3,0,1,0]))
        self.assertEqual([peak['index'] for peak in result['peaks']],[1,3])
        self.assertEqual([peak['frequency'] for peak in result['peaks']],[20.0,10.0])
        self.assertEqual([peak['amplitude'] for peak in result['peaks']],[3.0,1.0])

    def test_detects_local_minimum(self):
        result=find_vibration_extrema(np.arange(5),np.array([4,1,-2,1,4]))
        self.assertEqual(len(result['local_minima']),1)
        self.assertEqual(result['local_minima'][0]['index'],2)
        self.assertEqual(result['local_minima'][0]['amplitude'],-2.0)

    def test_minimum_prominence_filters_peaks(self):
        result=find_vibration_peaks(
            np.arange(7),np.array([0,2,0,1,0,4,0]),prominence=2.5)
        self.assertEqual([peak['index'] for peak in result['peaks']],[5])
        self.assertEqual(result['peaks'][0]['prominence'],4.0)

    def test_global_extrema_include_complete_valid_curve(self):
        result=find_vibration_extrema(
            np.arange(8),np.array([0,2,0,1,0,4,0,-3]))
        self.assertEqual(result['minimum']['index'],7)
        self.assertEqual(result['minimum']['amplitude'],-3.0)
        self.assertEqual(result['maximum']['index'],5)
        self.assertEqual(result['maximum']['amplitude'],4.0)

    def test_missing_values_split_local_peak_segments(self):
        values=np.array([0,3,0,np.nan,0,4,0])
        peaks=find_vibration_peaks(np.arange(7),values)
        extrema=find_vibration_extrema(np.arange(7),values)
        self.assertEqual(peaks['excluded'],1)
        self.assertEqual([peak['index'] for peak in peaks['peaks']],[1,5])
        self.assertEqual(extrema['excluded'],1)
        self.assertEqual(extrema['maximum']['index'],5)
        self.assertEqual([peak['index'] for peak in extrema['local_maxima']],[1,5])

    def test_constant_signal_has_no_local_peaks(self):
        values=np.ones(8)
        self.assertEqual(find_vibration_peaks(np.arange(8),values)['peaks'],[])
        extrema=find_vibration_extrema(np.arange(8),values)
        self.assertEqual(extrema['local_maxima'],[])
        self.assertEqual(extrema['local_minima'],[])
        self.assertEqual(extrema['minimum']['index'],0)
        self.assertEqual(extrema['maximum']['index'],0)

    def test_too_short_segments_have_no_local_peaks(self):
        result=find_vibration_peaks([1,2],[3,4])
        self.assertEqual(result['peaks'],[])
        self.assertEqual(result['short_segments'],1)


if __name__=='__main__':
    unittest.main()

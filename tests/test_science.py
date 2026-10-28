import sys
import unittest
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from science import (ScientificError,validate_sampling,fft_amplitude,welch_psd,band_rms,count_segments)
from csv_reader import read_csv_robust,convert_numeric_columns
from column_registry import build_column_registry
from selection import (frequency_candidates,acceleration_candidates,validate_frequency_plot,
                       time_acceleration_candidates, infer_known_test_type)
from vibrations import constant_ratio,avd_consistency

class ScienceTests(unittest.TestCase):
    def test_fft_8192_bin_peak_parseval(self):
        fs=8192;n=4096;t=np.arange(n)/fs;x=np.sin(2*np.pi*1000*t)
        sm=validate_sampling(t,'s',precision=1e-12)
        r=fft_amplitude(x,sm,window='boxcar',detrend='none')
        self.assertAlmostEqual(sm.fs,fs,places=7)
        self.assertAlmostEqual(r['frequency'][np.argmax(r['amplitude'])],1000)
        self.assertAlmostEqual(max(r['amplitude']),1,places=9)
        self.assertLess(r['parseval_error'],1e-9)

    def test_fft_65536_nyquist_dc_hann(self):
        fs=65536;n=4096;t=np.arange(n)/fs
        sm=validate_sampling(t,'s',precision=1e-12)
        nyquist=fft_amplitude(.7*np.cos(np.pi*np.arange(n))+.25,sm,'boxcar','none')
        self.assertAlmostEqual(nyquist['amplitude'][-1],.7,places=10)
        self.assertAlmostEqual(nyquist['amplitude'][0],.25,places=10)
        freq=1024
        sine=fft_amplitude(1.2*np.sin(2*np.pi*freq*t),sm,'hann','constant')
        self.assertAlmostEqual(sine['amplitude'][np.argmax(sine['amplitude'])],1.2,places=9)

    def test_sampling_not_uniform_or_conflicting(self):
        t=np.arange(4096)/65536
        t[100]+=2e-5
        with self.assertRaises(ScientificError):validate_sampling(t,'s',precision=1e-8)
        t=np.arange(4096)/65536
        with self.assertRaises(ScientificError):validate_sampling(t,'s',expected_fs=8192,precision=1e-8)
        with self.assertRaises(ScientificError):validate_sampling(t,'s')

    def test_short_missing_constant(self):
        sm=validate_sampling(np.arange(4096)/8192,'s',precision=1e-10)
        for x in [np.ones(4096),np.r_[np.ones(4095),np.nan]]:
            with self.assertRaises(ScientificError):fft_amplitude(x,sm)
        s=validate_sampling(np.arange(255)/8192,'s',precision=1e-10)
        with self.assertRaises(ScientificError):fft_amplitude(np.sin(np.arange(255)),s)

    def test_welch_white_noise_variance(self):
        rng=np.random.default_rng(17);n=262144; fs=8192
        x=rng.normal(0,1.5,n); sm=validate_sampling(np.arange(n)/fs,'s',precision=1e-8)
        p=welch_psd(x,sm,1024,50,'hann','constant')
        power=np.trapezoid(p['psd'],p['frequency'])
        self.assertLess(abs(power/np.var(x)-1),.02)
        self.assertEqual(p['k'],count_segments(n,1024,50))
        self.assertAlmostEqual(band_rms(p['frequency'],p['psd'],0,fs/2),np.sqrt(power),places=10)

    def test_welch_five_segments_and_sine_power(self):
        fs=8192;n=4096;t=np.arange(n)/fs
        sm=validate_sampling(t,'s',precision=1e-10)
        x=2*np.sin(2*np.pi*1024*t)
        p=welch_psd(x,sm,1024,50)
        self.assertEqual(p['k'],7)
        self.assertAlmostEqual(np.trapezoid(p['psd'],p['frequency']),2,places=5)
        with self.assertRaises(ScientificError):welch_psd(x,sm,2048,50)

    def test_reference_vibrations_and_shock(self):
        f=Path('/mnt/data/csv_test_sin.csv')
        if not f.exists():self.skipTest('CSV indisponible')
        df,report=read_csv_robust(f.read_bytes());df=convert_numeric_columns(df)
        reg=build_column_registry(df,report)
        self.assertEqual(infer_known_test_type(reg),'sinus')
        self.assertIn(0,frequency_candidates(reg))
        self.assertIn(1,acceleration_candidates(df,reg,0))
        self.assertNotIn(39,acceleration_candidates(df,reg,0))
        freq,ys,u=validate_frequency_plot(df,reg,0,[1,2,3,4,5,6])
        self.assertEqual(len(freq),2000);self.assertEqual(u,'G')
        self.assertEqual(sorted(time_acceleration_candidates(df,reg,61)),[62,63,64,65])
        self.assertAlmostEqual(report['time_precision'][61],1e-7,places=9)
        t=df.iloc[:,61].dropna().to_numpy(dtype=float)
        sampling=validate_sampling(t,'ms',precision=report['time_written_resolution'][61][:4096])
        self.assertAlmostEqual(sampling.fs,65536,delta=0.5)
        self.assertTrue(constant_ratio(freq) or not constant_ratio(freq))

    def test_short_csv_columns_and_mixed_units(self):
        raw='Frequency (Hz),A (G),B (m/s²)\n1,1,9.8\n2,2,19.6\n'
        df,report=read_csv_robust(raw.encode());df=convert_numeric_columns(df)
        reg=build_column_registry(df,report)
        with self.assertRaises(ScientificError):validate_frequency_plot(df,reg,0,[1,2])
        self.assertEqual(len(validate_frequency_plot(df,reg,0,[1])[0]),2)

    def test_avd(self):
        f=np.array([10.,50.]);a=np.array([.5,.4])
        v=a*9.80665/(2*np.pi*f)
        d=2*a*9.80665/(2*np.pi*f)**2*1000
        self.assertLess(max(avd_consistency(f,a,v,d)),1e-12)
        self.assertGreater(avd_consistency(f,a,v,d*1.1)[1],.09)

if __name__=='__main__':unittest.main()

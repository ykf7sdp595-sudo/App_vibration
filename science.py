"""Calculs spectraux explicites et vérifiables, sans fréquence d'échantillonnage supposée."""
from dataclasses import dataclass
import numpy as np
from scipy.signal import welch, get_window

G0 = 9.80665
SECONDS_PER_UNIT = {'s': 1., 'ms': .001, 'min': 60., 'h': 3600.}

class ScientificError(ValueError):
    pass

@dataclass
class Sampling:
    fs: float
    n: int
    dt: float
    residual: float
    source: str

def validate_sampling(t, unit, expected_fs=None, precision=None):
    """Vérifie t sur la droite t0+k*dt. precision = dernier chiffre écrit du CSV."""
    if unit not in SECONDS_PER_UNIT:
        raise ScientificError('Unité de temps absente ou non reconnue.')
    a = np.asarray(t, dtype=float)
    if a.size < 2 or not np.isfinite(a).all():
        raise ScientificError('Axe temporel absent, trop court ou non fini.')
    if not np.all(np.diff(a) > 0):
        raise ScientificError('Temps non strictement croissant.')
    dt_native = (a[-1] - a[0]) / (len(a)-1)
    max_res = float(np.max(np.abs(a - (a[0] + np.arange(len(a))*dt_native))))
    if precision is None:
        raise ScientificError('Précision des valeurs temporelles écrites dans le CSV inconnue.')
    if np.isscalar(precision):
        limits = np.full(a.size, float(precision))
    else:
        limits = np.asarray(precision, dtype=float)
        if len(limits) != len(a) or not np.isfinite(limits).all():
            raise ScientificError('Résolution écrite du temps absente ou incohérente.')
        # La précision de la dernière valeur intervient dans la droite de référence.
        limits = limits + limits[0] + (np.arange(len(a)) / (len(a)-1))*limits[-1]
    if np.any(np.abs(a-(a[0]+np.arange(len(a))*dt_native)) > limits * (1 + 1e-6)):
        raise ScientificError(f'Temps non uniforme : écart maximal {max_res:g} {unit} au-delà du dernier chiffre écrit.')
    fs = 1. / (dt_native * SECONDS_PER_UNIT[unit])
    if expected_fs is not None and abs(fs-expected_fs)/fs > 0.01:
        raise ScientificError(f'fs attendue {expected_fs:g} Hz incompatible avec fs calculée {fs:g} Hz (> 1 %).')
    return Sampling(fs, a.size, dt_native, max_res, f'axe temporel ({unit}), (N−1)/(t_fin−t_début)')

def _signal(x, n, min_n=256):
    a = np.asarray(x, dtype=float)
    if len(a) != n or len(a) < min_n:
        raise ScientificError(f'Signal absent ou trop court : minimum {min_n} points.')
    if not np.isfinite(a).all():
        raise ScientificError('Signal contenant des valeurs manquantes ou non finies.')
    if np.std(a) == 0:
        raise ScientificError('Signal constant : calcul refusé.')
    return a

def signal_stats(x):
    a = np.asarray(x, dtype=float)
    if not len(a) or not np.isfinite(a).all():
        raise ScientificError('Statistiques impossibles avec des valeurs manquantes.')
    return {'min':float(a.min()), 'max':float(a.max()), 'crête':float(np.max(np.abs(a))),
            'crête-à-crête':float(np.ptp(a)), 'moyenne':float(np.mean(a)),
            'RMS':float(np.sqrt(np.mean(a*a)))}

def fft_amplitude(x, sampling, window='boxcar', detrend='constant'):
    a = _signal(x, sampling.n)
    if window not in ('boxcar','hann') or detrend not in ('constant','none'):
        raise ScientificError('Fenêtre ou détrend non reconnu.')
    if detrend == 'constant':
        a = a - a.mean()
    w = get_window(window, len(a), fftbins=True)
    spectrum = np.fft.rfft(a*w)
    amp = np.abs(spectrum) / w.sum()
    if len(a)%2 == 0:
        amp[1:-1] *= 2
    else:
        amp[1:] *= 2
    freq = np.fft.rfftfreq(len(a), 1/sampling.fs)
    # Parseval exact sur le signal fenêtré, indépendamment de la correction d'amplitude.
    power_time = float(np.sum((a*w)**2))
    power_freq = float(np.sum(np.abs(spectrum)**2 * np.array(
        [1] + [2]*(len(spectrum)-2) + ([1] if len(a)%2 == 0 else [2])) / len(a)))
    parseval = abs(power_time-power_freq) / max(power_time, np.finfo(float).tiny)
    if parseval > 1e-9:
        raise ScientificError('Échec de la vérification Parseval.')
    return {'frequency':freq,'amplitude':amp,'df':sampling.fs/len(a),'parseval_error':parseval,
            'fs':sampling.fs,'n':len(a),'window':window,'detrend':detrend}

def count_segments(n, nperseg, overlap_percent):
    noverlap = int(nperseg * overlap_percent / 100)
    return 1+(n-nperseg)//(nperseg-noverlap) if n>=nperseg and noverlap<nperseg else 0

def welch_psd(x, sampling, nperseg, overlap_percent=50, window='hann', detrend='constant'):
    a = _signal(x, sampling.n)
    if window not in ('hann','boxcar') or detrend not in ('constant','none'):
        raise ScientificError('Fenêtre ou détrend non reconnu.')
    if not isinstance(nperseg,int) or nperseg<2 or nperseg>len(a):
        raise ScientificError('Taille de segment invalide ou supérieure au signal.')
    if not 0 <= overlap_percent < 100:
        raise ScientificError('Recouvrement hors plage [0 %, 100 %[.')
    k=count_segments(len(a),nperseg,overlap_percent)
    if k<5:
        raise ScientificError(f'PSD refusée : {k} segments Welch, minimum 5.')
    noverlap=int(nperseg*overlap_percent/100)
    f,p=welch(a,fs=sampling.fs,window=window,nperseg=nperseg,noverlap=noverlap,
              detrend=False if detrend=='none' else 'constant',scaling='density',return_onesided=True)
    return {'frequency':f,'psd':p,'fs':sampling.fs,'df':sampling.fs/nperseg,
            'k':k,'dof_approx':2*k,'uncertainty_approx':1/np.sqrt(k),'window':window,
            'detrend':detrend,'overlap_percent':overlap_percent,'nperseg':nperseg}

def band_rms(f,p,lo,hi):
    if not (0<=lo<hi<=f[-1]):
        raise ScientificError('Bande RMS hors fréquence ou vide.')
    # Intégration y compris aux bornes interpolées.
    x=np.r_[lo, f[(f>lo)&(f<hi)], hi]
    y=np.interp(x,f,p)
    return float(np.sqrt(max(0.,np.trapezoid(y,x) if hasattr(np,'trapezoid') else np.trapz(y,x))))

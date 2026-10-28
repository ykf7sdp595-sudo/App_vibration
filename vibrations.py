"""Outils du mode spectre fourni et vérification a-v-d en amplitude crête."""
import numpy as np
from scipy.signal import find_peaks
from science import G0


def _finite_curve_segments(frequency, amplitude):
    frequency=np.asarray(frequency,dtype=float)
    amplitude=np.asarray(amplitude,dtype=float)
    if frequency.ndim!=1 or amplitude.ndim!=1 or frequency.shape!=amplitude.shape:
        raise ValueError('Fréquence et amplitude doivent être des séries 1D de même longueur.')
    valid=np.isfinite(frequency)&np.isfinite(amplitude)
    indices=np.flatnonzero(valid)
    segments=np.split(indices,np.flatnonzero(np.diff(indices)>1)+1) if len(indices) else []
    return frequency,amplitude,segments,int(np.count_nonzero(~valid))


def _extremum_record(index, frequency, amplitude, prominence=None):
    record={'index':int(index),'frequency':float(frequency[index]),
            'amplitude':float(amplitude[index])}
    if prominence is not None:
        record['prominence']=float(prominence)
    return record


def find_vibration_peaks(frequency, amplitude, prominence=0.0, distance=None):
    """Find local acceleration maxima without bridging invalid samples."""
    if not np.isfinite(prominence) or prominence<0:
        raise ValueError('La proéminence doit être finie et positive ou nulle.')
    if distance is not None and (
            isinstance(distance,bool) or int(distance)!=distance or distance<1):
        raise ValueError('La distance minimale doit être un nombre entier positif.')
    frequency,amplitude,segments,excluded=_finite_curve_segments(frequency,amplitude)
    peaks=[]
    short_segments=0
    for segment in segments:
        if len(segment)<3:
            short_segments+=1
            continue
        local_peaks,properties=find_peaks(
            amplitude[segment],prominence=prominence,distance=distance)
        for peak,prom in zip(local_peaks,properties['prominences']):
            index=segment[peak]
            peaks.append(_extremum_record(index,frequency,amplitude,prom))
    return {'peaks':peaks,'excluded':excluded,'short_segments':short_segments}


def find_vibration_extrema(frequency, amplitude):
    """Find signed global and local extrema over valid, contiguous samples."""
    frequency,amplitude,segments,excluded=_finite_curve_segments(frequency,amplitude)
    valid_indices=np.flatnonzero(np.isfinite(frequency)&np.isfinite(amplitude))
    minimum=maximum=None
    if len(valid_indices):
        minimum_index=valid_indices[np.argmin(amplitude[valid_indices])]
        maximum_index=valid_indices[np.argmax(amplitude[valid_indices])]
        minimum=_extremum_record(minimum_index,frequency,amplitude)
        maximum=_extremum_record(maximum_index,frequency,amplitude)

    local_maxima=[]
    local_minima=[]
    short_segments=0
    for segment in segments:
        if len(segment)<3:
            short_segments+=1
            continue
        maxima,maximum_properties=find_peaks(amplitude[segment],prominence=0.0)
        minima,minimum_properties=find_peaks(-amplitude[segment],prominence=0.0)
        local_maxima.extend(
            _extremum_record(segment[peak],frequency,amplitude,prom)
            for peak,prom in zip(maxima,maximum_properties['prominences']))
        local_minima.extend(
            _extremum_record(segment[peak],frequency,amplitude,prom)
            for peak,prom in zip(minima,minimum_properties['prominences']))
    return {'minimum':minimum,'maximum':maximum,'local_maxima':local_maxima,
            'local_minima':local_minima,'excluded':excluded,
            'short_segments':short_segments}


def constant_ratio(f):
    f=np.asarray(f,dtype=float)
    return len(f)>3 and np.all(np.diff(f)>0) and np.allclose(f[1:]/f[:-1],np.median(f[1:]/f[:-1]),rtol=1e-3,atol=0)

def avd_consistency(f,a,v,displacement_pp_mm):
    """Retourne les écarts relatifs sur points non nuls (v en m/s, d crête-à-crête en mm)."""
    f=np.asarray(f,dtype=float); a=np.asarray(a,dtype=float)
    v=np.asarray(v,dtype=float); d=np.asarray(displacement_pp_mm,dtype=float)
    mask=(f>0)&np.isfinite(f)&np.isfinite(a)&np.isfinite(v)&np.isfinite(d)
    expected_v = a[mask]*G0/(2*np.pi*f[mask])
    expected_d = 2*a[mask]*G0/(2*np.pi*f[mask])**2*1000
    valid=(np.abs(expected_v)>1e-12)&(np.abs(expected_d)>1e-12)
    if not np.any(valid):
        return None
    return (float(np.max(np.abs(v[mask][valid]/expected_v[valid]-1))),
            float(np.max(np.abs(d[mask][valid]/expected_d[valid]-1))))

"""Onglets spécialisés ; les erreurs d'un onglet ne bloquent pas les autres."""
import json
import math
import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from science import (G0, ScientificError, validate_sampling, signal_stats,
                     fft_amplitude, welch_psd, band_rms, count_segments)
from selection import (frequency_candidates, acceleration_candidates,validate_frequency_plot,
                       time_candidates,time_acceleration_candidates,signal_time_series,infer_known_test_type)
from vibrations import (constant_ratio,avd_consistency,find_vibration_peaks,
                        find_vibration_extrema)


def label(reg,i):
    return f"[{i}] {reg[i]['nom_brut']}"

def _download_meta(meta, key):
    st.download_button('Exporter les paramètres (JSON)',
                       data=json.dumps(meta,ensure_ascii=False,indent=2),
                       file_name=f'{key}_parametres.json',mime='application/json',key=f'export_{key}')

def _trace(fig,x,y,reg,i,kind='lines'):
    fig.add_trace(go.Scatter(x=x,y=y,mode=kind,name=label(reg,i)))


def plot_axis_controls(title,x_title,y_title,x_values,y_values,key,
                       log_x_default=False,log_y_default=False):
    def finite_values(values):
        if isinstance(values,(list,tuple)):
            arrays=[np.asarray(value,dtype=float).ravel() for value in values]
            array=np.concatenate(arrays) if arrays else np.array([],dtype=float)
        else:
            array=np.asarray(values,dtype=float).ravel()
        return array[np.isfinite(array)]

    def range_defaults(values,logarithmic):
        values=values[values>0] if logarithmic else values
        if not len(values):
            return None
        low=float(np.min(values))
        high=float(np.max(values))
        if low==high:
            if logarithmic:
                return low/1.1,high*1.1
            padding=max(abs(low)*0.01,1e-6)
            return low-padding,high+padding
        return low,high

    x_values=finite_values(x_values)
    y_values=finite_values(y_values)
    with st.expander('Titre et axes du graphique',expanded=False):
        title=st.text_input('Titre du graphique',value=title,key=f'{key}_title')
        x_scale=st.selectbox(
            'Échelle horizontale',('Linéaire','Logarithmique'),
            index=1 if log_x_default else 0,key=f'{key}_x_scale')
        y_scale=st.selectbox(
            'Échelle verticale',('Linéaire','Logarithmique'),
            index=1 if log_y_default else 0,key=f'{key}_y_scale')
        if x_scale=='Logarithmique' and np.any(x_values<=0):
            st.info('Les valeurs X non positives ne sont pas représentables sur une échelle logarithmique.')
        if y_scale=='Logarithmique' and np.any(y_values<=0):
            st.info('Les valeurs Y non positives ne sont pas représentables sur une échelle logarithmique.')
        show_grid=st.checkbox('Afficher la grille et les graduations',value=True,
                              key=f'{key}_grid')
        set_ranges=st.checkbox('Régler les bornes min/max',value=False,
                               key=f'{key}_set_ranges')
        x_range=y_range=None
        if set_ranges:
            x_defaults=range_defaults(x_values,x_scale=='Logarithmique')
            y_defaults=range_defaults(y_values,y_scale=='Logarithmique')
            columns=st.columns(2)
            if x_defaults is not None:
                with columns[0]:
                    st.caption(f'Axe horizontal — {x_title}')
                    x_min=st.number_input('X minimum',value=x_defaults[0],
                                          format='%.7g',key=f'{key}_x_min')
                    x_max=st.number_input('X maximum',value=x_defaults[1],
                                          format='%.7g',key=f'{key}_x_max')
                if x_min<x_max and (x_scale!='Logarithmique' or x_min>0):
                    x_range=(x_min,x_max)
                else:
                    st.warning('Bornes X invalides : minimum inférieur au maximum et, '
                               'en logarithmique, strictement positif requis.')
            else:
                st.info('Aucune valeur exploitable pour régler les bornes X.')
            if y_defaults is not None:
                with columns[1]:
                    st.caption(f'Axe vertical — {y_title}')
                    y_min=st.number_input('Y minimum',value=y_defaults[0],
                                          format='%.7g',key=f'{key}_y_min')
                    y_max=st.number_input('Y maximum',value=y_defaults[1],
                                          format='%.7g',key=f'{key}_y_max')
                if y_min<y_max and (y_scale!='Logarithmique' or y_min>0):
                    y_range=(y_min,y_max)
                else:
                    st.warning('Bornes Y invalides : minimum inférieur au maximum et, '
                               'en logarithmique, strictement positif requis.')
            else:
                st.info('Aucune valeur exploitable pour régler les bornes Y.')
    return {
        'title':title,'x_title':x_title,'y_title':y_title,
        'log_x':x_scale=='Logarithmique','log_y':y_scale=='Logarithmique',
        'show_grid':show_grid,'x_range':x_range,'y_range':y_range,
    }


def apply_plot_axis_controls(fig,options):
    def plotly_range(bounds,logarithmic):
        if bounds is None:
            return None
        if logarithmic:
            return [math.log10(bounds[0]),math.log10(bounds[1])]
        return list(bounds)

    fig.update_layout(title=options['title'])
    fig.update_xaxes(title_text=options['x_title'],
                     type='log' if options['log_x'] else 'linear',
                     showgrid=options['show_grid'],
                     range=plotly_range(options['x_range'],options['log_x']))
    fig.update_yaxes(title_text=options['y_title'],
                     type='log' if options['log_y'] else 'linear',
                     showgrid=options['show_grid'],
                     range=plotly_range(options['y_range'],options['log_y']))


def _analysis_markers(fig, records, name, unit, color, symbol, frequency_scale=1.0,
                      show_prominence=False):
    if not records:
        return
    customdata=[[record.get('curve',name),record['frequency']*frequency_scale,
                 record.get('prominence',0.0)] for record in records]
    prominence_hover=(f'<br>Proéminence: %{{customdata[2]:.6g}} {unit}'
                      if show_prominence else '')
    fig.add_trace(go.Scatter(
        x=[record['frequency'] for record in records],
        y=[record['amplitude'] for record in records],
        mode='markers',name=name,
        marker={'color':color,'symbol':symbol,'size':10},
        customdata=customdata,
        hovertemplate=(f'<b>%{{customdata[0]}}</b><br>Fréquence: '
                       f'%{{customdata[1]:.6g}} Hz<br>Amplitude: '
                       f'%{{y:.6g}} {unit}{prominence_hover}<extra></extra>')))


def _analysis_labels(fig, records, unit, frequency_scale=1.0, position='top center'):
    if not records:
        return
    fig.add_trace(go.Scatter(
        x=[record['frequency'] for record in records],
        y=[record['amplitude'] for record in records],
        mode='text',
        text=[f"{record['frequency']*frequency_scale:.5g} Hz<br>"
              f"{record['amplitude']:.5g} {unit}" for record in records],
        textposition=position,showlegend=False,hoverinfo='skip'))


def _vibration_analysis_options(unit, key_prefix):
    with st.expander('Analyse des pics et extrema',expanded=False):
        detect_peaks=st.checkbox(
            'Détecter les pics anormaux',value=False,key=f'{key_prefix}_detect_peaks')
        min_prominence=(st.number_input(
            f'Proéminence minimale ({unit})',min_value=0.0,value=0.0,
            step=0.1,format='%.6g',key=f'{key_prefix}_peak_prominence')
            if detect_peaks else 0.0)
        use_peak_distance=(st.checkbox(
            'Imposer une distance minimale entre pics',value=False,
            key=f'{key_prefix}_peak_distance_on') if detect_peaks else False)
        peak_distance=(int(st.number_input(
            'Distance minimale entre pics (échantillons)',min_value=1,value=1,
            step=1,key=f'{key_prefix}_peak_distance'))
            if use_peak_distance else None)
        show_global_min=st.checkbox(
            'Afficher les minima globaux',value=False,key=f'{key_prefix}_global_min')
        show_global_max=st.checkbox(
            'Afficher les maxima globaux',value=False,key=f'{key_prefix}_global_max')
        show_local_extrema=st.checkbox(
            'Afficher les extrema locaux',value=False,key=f'{key_prefix}_local_extrema')
    return {
        'detect_peaks':detect_peaks,
        'min_prominence':min_prominence,
        'peak_distance':peak_distance,
        'show_global_min':show_global_min,
        'show_global_max':show_global_max,
        'show_local_extrema':show_local_extrema,
    }


def _add_curve_analysis(fig, frequency, amplitude, curve, unit, options,
                        frequency_scale=1.0, log=False):
    if not any((options['detect_peaks'],options['show_global_min'],
                options['show_global_max'],options['show_local_extrema'])):
        return
    excluded=0
    short_segments=0
    if options['detect_peaks']:
        result=find_vibration_peaks(
            frequency,amplitude,options['min_prominence'],options['peak_distance'])
        excluded=result['excluded']
        short_segments=result['short_segments']
        peaks=[dict(record,curve=curve) for record in result['peaks']
               if not log or record['frequency']>0]
        _analysis_markers(
            fig,peaks,f'Pics détectés — {curve}',unit,
            'crimson','x',frequency_scale,show_prominence=True)

    minima=[]
    maxima=[]
    local_maxima=[]
    local_minima=[]
    if any((options['show_global_min'],options['show_global_max'],
            options['show_local_extrema'])):
        extrema=find_vibration_extrema(frequency,amplitude)
        excluded=max(excluded,extrema['excluded'])
        if not options['detect_peaks']:
            short_segments=extrema['short_segments']
        if options['show_global_min'] and extrema['minimum'] is not None:
            if not log or extrema['minimum']['frequency']>0:
                minima.append(dict(extrema['minimum'],curve=curve))
        if options['show_global_max'] and extrema['maximum'] is not None:
            if not log or extrema['maximum']['frequency']>0:
                maxima.append(dict(extrema['maximum'],curve=curve))
        if options['show_local_extrema']:
            local_maxima=[
                dict(record,curve=curve) for record in extrema['local_maxima']
                if not log or record['frequency']>0]
            local_minima=[
                dict(record,curve=curve) for record in extrema['local_minima']
                if not log or record['frequency']>0]

    _analysis_markers(fig,minima,'Minima globaux',unit,
                      'royalblue','diamond',frequency_scale)
    _analysis_labels(fig,minima,unit,frequency_scale,'bottom center')
    _analysis_markers(fig,maxima,'Maxima globaux',unit,
                      'darkorange','diamond',frequency_scale)
    _analysis_labels(fig,maxima,unit,frequency_scale,'top center')
    _analysis_markers(fig,local_maxima,'Maxima locaux',unit,
                      'darkorange','triangle-up',frequency_scale,show_prominence=True)
    _analysis_markers(fig,local_minima,'Minima locaux',unit,
                      'royalblue','triangle-down',frequency_scale,show_prominence=True)
    if options['show_local_extrema']:
        labeled_local=sorted(
            local_maxima+local_minima,
            key=lambda record:record['prominence'],reverse=True)[:20]
        _analysis_labels(fig,labeled_local,unit,frequency_scale)
        if len(local_maxima)+len(local_minima)>len(labeled_local):
            st.caption('Étiquettes des extrema locaux limitées aux 20 proéminences '
                       'les plus élevées par courbe ; les autres restent accessibles '
                       'au survol des marqueurs.')
    if excluded:
        st.warning(f'{curve} : {excluded} point(s) manquant(s) ou non fini(s) ignoré(s) '
                   'dans l’analyse ; les segments séparés ne sont pas reliés.')
    if short_segments:
        st.info(f'{curve} : {short_segments} segment(s) de moins de 3 échantillons '
                'ignoré(s) pour la détection locale.')


def ui_vibrations_calculated(df,reg,report):
    st.caption('Calculé par l’application — FFT unilatérale, distincte des spectres fournis.')
    t_idx,avail=_time_selector(df,reg,'vib_calc')
    if not avail:
        return
    channel=st.selectbox('Voie temporelle',avail,format_func=lambda j:label(reg,j),key='vib_calc_channel')
    window=st.selectbox('Fenêtre FFT',('boxcar','hann'),format_func=lambda w:'Rectangulaire' if w=='boxcar' else 'Hann',key='vib_calc_window')
    detrend=st.selectbox('Composante continue',('constant','none'),
                         format_func=lambda v:'Retirer moyenne' if v=='constant' else 'Aucune',key='vib_calc_detrend')
    if window=='hann':
        st.warning('Hann : la correction de gain cohérent n’est pas une correction de crête d’un choc.')
    else:
        st.info('Rectangulaire : vérifier les conditions aux bords de l’enregistrement.')
    try:
        t,x,sampling=_sampling(df,reg,report,t_idx,channel,None)
        if np.min(x)>=0 or np.max(x)<=0:
            raise ScientificError('Signal temporel signé non confirmé.')
        r=fft_amplitude(x,sampling,window,detrend)
        unit=reg[channel]['unité_normalisée']
        fig=go.Figure();_trace(fig,r['frequency'],r['amplitude'],reg,channel)
        options=_vibration_analysis_options(unit,'vib_calc')
        axis_options=plot_axis_controls(
            f'Amplitude FFT — {label(reg,channel)}','Fréquence (Hz)',
            f'Amplitude FFT unilatérale ({unit})',r['frequency'],r['amplitude'],
            f'vib_calc_axis_{channel}')
        _add_curve_analysis(
            fig,r['frequency'],r['amplitude'],label(reg,channel),unit,options,
            log=axis_options['log_x'])
        apply_plot_axis_controls(fig,axis_options)
        st.plotly_chart(fig,use_container_width=True)
        st.caption(f"FFT calculée · N={sampling.n}, fs={sampling.fs:.5g} Hz ({sampling.source}), "
                   f"Δf={r['df']:.5g} Hz, fenêtre {window}, detrend {detrend}, "
                   f"Parseval={r['parseval_error']:.2g}")
        _download_meta({'source':'FFT calculée','temps':label(reg,t_idx),'acceleration':label(reg,channel),
                        'unit':unit,'fs':sampling.fs,'N':sampling.n,'df':r['df'],
                        'window':window,'detrend':detrend,'source_fs':sampling.source},'vib_calculated')
    except (ScientificError,ValueError,TypeError) as e:
        st.warning('FFT non calculée : '+str(e))


def ui_vibrations(df,reg,report):
    st.subheader('VIBRATIONS — accélération en fonction de la fréquence')
    mode=st.radio('Origine du spectre',('Fourni par le fichier','Calculé par l’application (FFT)'),horizontal=True,key='vib_mode')
    if mode.startswith('Calculé'):
        ui_vibrations_calculated(df,reg,report)
        return
    st.caption('Spectres fournis par le fichier ; aucun spectre calculé implicitement.')
    candidates=frequency_candidates(reg)
    if not candidates:
        st.info('Aucune fréquence déclarée disponible.')
        return
    default=next((i for i in candidates if reg[i]['groupe']=='A — profil'),None)
    if default is None and len(candidates)>1:
        st.warning('Plusieurs fréquences candidates : choisissez explicitement un axe avant de tracer.')
        options=[None]+candidates
    else:
        options=candidates
    i=st.selectbox('Fréquence',options,index=options.index(default) if default in options else 0,
                   format_func=lambda x:'— Choisir un axe —' if x is None else label(reg,x), key='vib_frequency')
    if i is None:
        return
    accel=acceleration_candidates(df,reg,i)
    if not accel:
        st.info('Aucune accélération de même support que cette fréquence.')
        return
    defaults=[j for j in accel if reg[j]['groupe']=='A — profil' and reg[j]['nom_brut'] in ('Demand1 (G)','Control1 (G)')]
    selected=st.multiselect('Accélérations',accel,default=defaults if defaults else accel[:1],
                           format_func=lambda j:label(reg,j),key='vib_series')
    try:
        f,ys,unit=validate_frequency_plot(df,reg,i,selected)
        convert=unit=='G' and st.checkbox('Conversion explicite G → m/s²',value=False,key='vib_convert')
        factor=G0 if convert else 1
        target_unit='m/s²' if convert else unit
        log_suggested=bool(constant_ratio(f))
        options=_vibration_analysis_options(target_unit,'vib')

        raw_f=pd.to_numeric(df.iloc[:,i],errors='raise').to_numpy(dtype=float)
        frequency_unit=reg[i]['unité_normalisée']
        frequency_scale=1000.0 if frequency_unit=='kHz' else 1.0
        axis_options=plot_axis_controls(
            'Spectre de vibration — '+', '.join(label(reg,j) for j in selected),
            label(reg,i),f'Accélération ({target_unit})',raw_f,
            [ys[j]*factor for j in ys],
            'vib_axis_'+str(i)+'_'+ '_'.join(map(str,selected)),
            log_x_default=log_suggested)
        fig=go.Figure()
        for j in ys:
            raw_y=pd.to_numeric(df.iloc[:,j],errors='raise').to_numpy(dtype=float)
            plotted_y=raw_y*factor
            fig.add_trace(go.Scatter(x=raw_f,y=plotted_y,mode='lines',name=label(reg,j)))
            _add_curve_analysis(
                fig,raw_f,plotted_y,label(reg,j),target_unit,options,
                frequency_scale,axis_options['log_x'])
        apply_plot_axis_controls(fig,axis_options)
        fig.update_layout(hovermode='closest')
        st.caption('Fourni par le fichier · ordre d’acquisition conservé · ' +
                   ('abscisse non monotone' if np.any(np.diff(f)<0) else 'abscisse monotone'))
        if np.any(np.diff(f)<0):
            st.warning('Fréquence non monotone : affichage dans l’ordre des points, sans tri.')
        st.plotly_chart(fig,use_container_width=True)
        meta={'source':'fourni par le fichier','frequence':label(reg,i),
              'accelerations':[label(reg,j) for j in selected], 'unit':target_unit,
              'conversion_G_ms2':convert,'points':len(f),
              'log_frequency':axis_options['log_x']}
        # Contrôle a-v-d uniquement avec correspondances explicites du profil.
        if st.checkbox('Vérifier cohérence accélération / vitesse / déplacement (si présents)',key='vib_avd'):
            ids={r['nom_brut']:r['index'] for r in reg if r['groupe']==reg[i]['groupe']}
            for prefix in ('Demand','Control'):
                names=[f'{prefix}1 (G)',f'{prefix} Velocity1 (m/s)',f'{prefix} Displacement1 (mm)']
                if all(n in ids for n in names) and all(df.iloc[:,ids[n]].notna().equals(df.iloc[:,i].notna()) for n in names):
                    measures=[df.iloc[:,ids[n]].dropna().to_numpy(dtype=float) for n in names]
                    result=avd_consistency(f,*measures)
                    if result:
                        st.write(f'{prefix} : écart vitesse {result[0]:.4%}, déplacement {result[1]:.4%}.')
                        if max(result)>1e-3:
                            st.warning('Écart supérieur à 0,1 % ; données non modifiées.')
            st.caption('G et m/s en crête ; mm en crête-à-crête (convention du profil validé).')
        _download_meta(meta,'vibrations')
    except (ScientificError,ValueError,TypeError) as e:
        st.warning(str(e))

def _time_selector(df,reg,tag):
    possible=time_candidates(reg)
    if not possible:
        st.info('Aucun axe de temps déclaré.')
        return None,None
    preferred=next((i for i in possible if reg[i]['groupe']=='C — temporel'),None)
    opts=([None]+possible) if preferred is None and len(possible)>1 else possible
    t=st.selectbox('Axe temps',opts,index=opts.index(preferred) if preferred in opts else 0,
                   format_func=lambda j:'— Choisir un temps —' if j is None else label(reg,j),key=tag+'_time')
    if t is None:
        return None,None
    accel=time_acceleration_candidates(df,reg,t)
    if not accel:
        st.info('Pas d’accélération temporelle de même support.')
        return t,[]
    return t,accel

def _sampling(df,reg,report,t_idx,x_idx,expected):
    t,x=signal_time_series(df,reg,t_idx,x_idx)
    # Refus si trous internes, pas de tronquage ni de comblement.
    if np.any(np.diff(np.flatnonzero(df.iloc[:,t_idx].notna()))!=1):
        raise ScientificError('Trou(s) dans le temps : signal incomplet.')
    if np.any(np.diff(np.flatnonzero(df.iloc[:,x_idx].notna()))!=1):
        raise ScientificError('Trou(s) dans la voie : signal incomplet.')
    precisions=report.get('time_written_resolution',{}).get(t_idx)
    prec=[v for v,keep in zip(precisions,df.iloc[:,t_idx].notna()) if keep] if precisions else report.get('time_precision',{}).get(t_idx)
    sampling=validate_sampling(t,reg[t_idx]['unité_normalisée'],expected_fs=expected,precision=prec)
    return t,x,sampling

def ui_chocs(df,reg,report):
    st.subheader('CHOCS — signal temporel et FFT optionnelle')
    t_idx,avail=_time_selector(df,reg,'shock')
    if not avail:
        return
    default=[j for j in avail if reg[j]['groupe']=='C — temporel'] or avail[:1]
    selected=st.multiselect('Voies',avail,default=default,format_func=lambda j:label(reg,j),key='shock_channels')
    if not selected:
        return
    units={reg[j]['unité_normalisée'] for j in selected}
    if len(units)!=1:
        st.warning('Voies d’unités différentes : sélectionnez une seule unité, sans conversion implicite.')
        return
    unit=units.pop()
    time=df.iloc[:,t_idx]
    fig=go.Figure()
    valid=[]
    times=[]
    amplitudes=[]
    for j in selected:
        t,x=signal_time_series(df,reg,t_idx,j)
        if len(t) and np.isfinite(t).all() and np.isfinite(x).all():
            _trace(fig,t,x,reg,j)
            valid.append(j)
            times.append(t)
            amplitudes.append(x)
    if not valid:
        st.warning('Aucune voie complète et finie pour le tracé temporel.')
        return
    axis_options=plot_axis_controls(
        'Signal temporel — '+', '.join(label(reg,j) for j in valid),
        label(reg,t_idx),f'Accélération ({unit})',times,amplitudes,
        'shock_time_axis_'+str(t_idx)+'_'+'_'.join(map(str,valid)))
    apply_plot_axis_controls(fig,axis_options)
    st.plotly_chart(fig,use_container_width=True)
    for j in valid:
        x=df.iloc[:,j].dropna().to_numpy(dtype=float)
        stats=signal_stats(x)
        st.caption(label(reg,j)+' · '+ ' · '.join(f'{k}: {v:.5g} {unit}' for k,v in stats.items()))
    if not st.checkbox('Calculer la FFT d’amplitude (option)',value=False,key='shock_fft'):
        st.caption('FFT désactivée : aucun calcul spectral lancé.')
        return
    expected_on=st.checkbox('Comparer à une fs attendue (Hz)',value=False,key='shock_expected_on')
    expected_str=st.text_input('fs attendue (Hz)',value='',placeholder='Saisir une valeur vérifiée',key='shock_expected') if expected_on else None
    try: expected=float(expected_str) if expected_str is not None else None
    except ValueError:
        st.warning('fs attendue invalide : saisir un nombre positif.'); return
    if expected is not None and expected<=0:
        st.warning('La fs attendue doit être positive.'); return
    window=st.selectbox('Fenêtre FFT',('boxcar','hann'),format_func=lambda w:'Rectangulaire' if w=='boxcar' else 'Hann',key='shock_window')
    detrend=st.selectbox('Composante continue',('constant','none'),format_func=lambda v:'Retirer la moyenne' if v=='constant' else 'Aucune correction',key='shock_detrend')
    if window=='hann':
        st.warning('Fenêtre Hann : la correction de gain cohérent n’assure pas la restitution de la crête d’un choc transitoire.')
    else:
        st.info('Fenêtre rectangulaire : vérifier que le choc est complet et que les bords sont compatibles.')
    fft_fig=go.Figure(); meta={'source':'FFT calculée','axes':label(reg,t_idx),'voies':[],
                              'window':window,'detrend':detrend,'unit':unit}
    fft_frequencies=[]
    fft_amplitudes=[]
    for j in valid:
        try:
            t,x,sampling=_sampling(df,reg,report,t_idx,j,expected)
            # Une enveloppe positive peut être tracée, mais n'est pas un signal instantané fiable.
            if np.min(x)>=0 or np.max(x)<=0:
                raise ScientificError('Voie non signée : signal instantané non confirmé.')
            result=fft_amplitude(x,sampling,window,detrend)
            _trace(fft_fig,result['frequency'],result['amplitude'],reg,j)
            fft_frequencies.append(result['frequency'])
            fft_amplitudes.append(result['amplitude'])
            meta['voies'].append({'colonne':label(reg,j),'N':sampling.n,'fs':sampling.fs,
                                  'source_fs':sampling.source,'df':result['df'],
                                  'parseval_error':result['parseval_error'],
                                  'precision_temps':report['time_precision'].get(t_idx)})
            st.caption(f"{label(reg,j)} · N={sampling.n} · fs={sampling.fs:.5g} Hz ({sampling.source}) · "
                       f"Δf={result['df']:.5g} Hz · Parseval={result['parseval_error']:.2g}")
            power=result['amplitude']**2
            if np.sum(power[result['frequency']>=.9*(sampling.fs/2)]) > .05*np.sum(power):
                st.warning(label(reg,j)+' : énergie notable proche de Nyquist ; vérifier le risque de repliement.')
        except (ScientificError,ValueError,TypeError) as e:
            st.warning(f'{label(reg,j)} — FFT non calculée : {e}')
    if meta['voies']:
        axis_options=plot_axis_controls(
            'FFT de choc — '+', '.join(item['colonne'] for item in meta['voies']),
            'Fréquence (Hz)',f'Amplitude FFT unilatérale ({unit})',
            fft_frequencies,fft_amplitudes,
            'shock_fft_axis_'+str(t_idx)+'_'+'_'.join(str(item['colonne']) for item in meta['voies']))
        apply_plot_axis_controls(fft_fig,axis_options)
        st.plotly_chart(fft_fig,use_container_width=True)
        st.caption('Spectre d’amplitude FFT (G si entrée en G), distinct de la transformée G·s et de la PSD G²/Hz ; pas de SRS.')
        _download_meta(meta,'chocs_fft')

def ui_psd(df,reg,report):
    st.subheader('PSD — densité spectrale de puissance')
    given=[r['index'] for r in reg if r['dimension']=='PSD_accélération' and r['statut_unité']=='déclarée']
    if not given:
        st.info('Aucune PSD fournie dans ce fichier.')
    else:
        st.caption('PSD fournie par le fichier (aucun calcul)')
        for j in given:
            compatible=[i for i in frequency_candidates(reg) if df.iloc[:,i].notna().equals(df.iloc[:,j].notna())]
            if not compatible:
                st.warning(f'{label(reg,j)} : fréquence de même support absente.')
                continue
            i=compatible[0]
            if len(compatible)>1:
                i=st.selectbox(
                    f'Axe fréquence pour {label(reg,j)}',compatible,
                    format_func=lambda index:label(reg,index),
                    key=f'psd_frequency_{j}')
            f=df.iloc[:,i].dropna().to_numpy(dtype=float)
            p=df.iloc[:,j].dropna().to_numpy(dtype=float)
            if not np.isfinite(f).all() or not np.isfinite(p).all() or np.any(f<=0) or np.any(p<0):
                st.warning(f'{label(reg,j)} : valeurs PSD ou fréquences invalides.')
                continue
            fig=go.Figure();_trace(fig,f,p,reg,j)
            axis_options=plot_axis_controls(
                f'PSD fournie — {label(reg,j)}',label(reg,i),
                reg[j]['unité_normalisée'],f,p,f'psd_given_axis_{i}_{j}')
            apply_plot_axis_controls(fig,axis_options)
            st.plotly_chart(fig,use_container_width=True)
    kind=infer_known_test_type(reg)
    if kind!='inconnu':
        st.warning(f'Type d’essai reconnu : {kind}. Calcul PSD Welch refusé (réservé aux essais aléatoires).')
        return
    st.warning('Type d’essai non identifié. Ne calculer une PSD que pour un essai aléatoire stationnaire confirmé.')
    if not st.checkbox('Je confirme que ce signal provient d’un essai aléatoire stationnaire',key='psd_confirm'):
        return
    t_idx,avail=_time_selector(df,reg,'psd')
    if not avail:
        return
    chan=st.selectbox('Voie aléatoire',avail,format_func=lambda j:label(reg,j),key='psd_channel')
    count=int(df.iloc[:,chan].notna().sum())
    # Valeurs suggérées et explicites : aucun nperseg silencieux.
    suggested=min(1024,max(2,count//4))
    nseg=int(st.number_input('Taille du segment (points)',min_value=2,max_value=max(2,count),
                             value=suggested,step=1,key='psd_segment'))
    overlap=int(st.slider('Recouvrement (%)',min_value=0,max_value=95,value=50,step=5,key='psd_overlap'))
    window=st.selectbox('Fenêtre Welch',('hann','boxcar'),key='psd_window')
    detrend=st.selectbox('Detrend Welch',('constant','none'),
                         format_func=lambda v:'Retirer moyenne de chaque segment' if v=='constant' else 'Aucun',key='psd_detrend')
    expected_on=st.checkbox('Comparer à une fs attendue (Hz)',value=False,key='psd_expected_on')
    expected_str=st.text_input('fs attendue (Hz)',value='',placeholder='Saisir une valeur vérifiée',key='psd_expected') if expected_on else None
    try: expected=float(expected_str) if expected_str is not None else None
    except ValueError:
        st.warning('fs attendue invalide : saisir un nombre positif.'); return
    if expected is not None and expected<=0:
        st.warning('La fs attendue doit être positive.'); return
    k=count_segments(count,nseg,overlap)
    st.caption(f'K attendu = {k} segments ; minimum requis : 5.')
    if reg[chan]['unité_normalisée']=='G':
        st.checkbox('Conversion explicite G²/Hz → (m/s²)²/Hz (g₀ = 9,80665)',value=False,key='psd_convert')
    if not st.checkbox('Activer le calcul PSD Welch',value=False,key='psd_compute'):
        return
    try:
        t,x,sampling=_sampling(df,reg,report,t_idx,chan,expected)
        if np.min(x)>=0 or np.max(x)<=0:
            raise ScientificError('Signal instantané signé non confirmé.')
        result=welch_psd(x,sampling,nseg,overlap,window,detrend)
        unit=reg[chan]['unité_normalisée']
        factor=1.
        converted=st.session_state.get('psd_convert',False) if unit=='G' else False
        if converted: factor=G0**2
        p=result['psd']*factor
        f=result['frequency']
        fig=go.Figure();_trace(fig,f,p,reg,chan)
        output_unit=('(m/s²)²/Hz' if converted else f'{unit}²/Hz')
        axis_options=plot_axis_controls(
            f'PSD Welch — {label(reg,chan)}','Fréquence (Hz)',
            f'PSD ({output_unit})',f,p,
            f'psd_welch_axis_{chan}_{nseg}_{overlap}_{window}_{detrend}')
        apply_plot_axis_controls(fig,axis_options)
        st.plotly_chart(fig,use_container_width=True)
        st.caption(f"PSD calculée — Welch · fs={sampling.fs:.5g} Hz ({sampling.source}) · Δf={result['df']:.5g} Hz · "
                   f"K={result['k']} · ddl indicatifs ≈ {result['dof_approx']} · incertitude indicative ≈ {result['uncertainty_approx']:.1%} · "
                   f"fenêtre {window} · detrend {detrend} · recouvrement {overlap}% · unité {output_unit}")
        st.caption('L’intégrale Welch est une estimation de la variance, non une identité exacte avec la variance totale.')
        low,high=st.slider('Bande de calcul RMS (Hz)',min_value=float(f[0]),max_value=float(f[-1]),
                           value=(float(f[0]),float(f[-1])),key='psd_band')
        if low < high:
            st.metric(f'RMS calculé ({output_unit.replace("²/Hz", "")})',f'{band_rms(f,p,low,high):.5g}')
        meta={'source':'PSD recalculée — Welch','voie':label(reg,chan),'temps':label(reg,t_idx),
              'fs':sampling.fs,'source_fs':sampling.source,'unit':output_unit,
              'resolution_Hz':result['df'],'segments':result['k'],'nperseg':nseg,
              'overlap_percent':overlap,'window':window,'detrend':detrend,
              'conversion_G_ms2':converted,'g0':G0}
        _download_meta(meta,'psd_welch')
    except (ScientificError,ValueError,TypeError) as e:
        st.warning(f'PSD non calculée : {e}')

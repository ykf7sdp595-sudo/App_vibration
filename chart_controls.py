"""Réglages visuels conservés par fichier et graphique."""
import hashlib

import streamlit as st
from plotly.colors import qualitative


def persistent_scale(label, key, logarithmic=False):
    saved = key + '_saved'
    if key not in st.session_state:
        st.session_state[key] = st.session_state.get(
            saved, 'Logarithmique' if logarithmic else 'Linéaire')

    def remember():
        st.session_state[saved] = st.session_state[key]

    value = st.selectbox(label, ('Linéaire', 'Logarithmique'),
                         key=key, on_change=remember)
    st.session_state[saved] = value
    return value


def draw_chart(fig, key, chart_slot=None):
    if chart_slot is None:
        chart_slot = st.container()
    colors = st.session_state.setdefault(key + '_colors', {})
    curves = [trace for trace in fig.data if trace.mode and 'lines' in trace.mode]
    if curves:
        with st.expander('🎨 Couleurs des courbes', expanded=False):
            for trace in curves:
                identity = trace.name
                if identity not in colors:
                    colors[identity] = qualitative.Plotly[len(colors) % len(qualitative.Plotly)]
                widget_key = key + '_color_' + hashlib.sha256(identity.encode()).hexdigest()[:16]
                colors[identity] = st.color_picker(identity, value=colors[identity], key=widget_key)
                trace.line.color = colors[identity]
                trace.uid = identity
    if fig.layout.annotations:
        st.caption('Étiquettes : glissez le texte pour le déplacer ; la flèche reste sur la mesure. '
                   'Le placement est conservé dans le navigateur tant que les étiquettes et les axes restent identiques.')
    signature = hashlib.sha256(repr((
        fig.layout.xaxis.type, fig.layout.yaxis.type,
        [(a.name, a.x, a.y, a.text) for a in fig.layout.annotations],
    )).encode()).hexdigest()
    fig.update_layout(editrevision=signature,
                      legend=dict(orientation='h', x=0, y=-0.2),
                      margin=dict(l=70, r=30, t=80, b=140))
    with chart_slot:
        st.plotly_chart(fig, width='stretch', key=key, config={
            'editable': False,
            'edits': {'annotationTail': True, 'annotationPosition': False, 'annotationText': False},
        })

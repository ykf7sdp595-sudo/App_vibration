"""Streamlit harness: uploaded bytes are supplied through test session state."""
from io import BytesIO
from pathlib import Path
from unittest.mock import patch
import runpy
import streamlit as st

files = []
for name, content in st.session_state.get('test_files', []):
    uploaded = BytesIO(content)
    uploaded.name = name
    files.append(uploaded)
with patch.object(st, 'file_uploader', return_value=files) as uploader:
    runpy.run_path(str(Path(__file__).resolve().parents[1] / 'App_vibration.py'))
    assert uploader.call_args.kwargs['accept_multiple_files'] is True

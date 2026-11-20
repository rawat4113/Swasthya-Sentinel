import os
import requests
import streamlit as st

BASE_URL = os.getenv('API_BASE_URL', 'http://127.0.0.1:8001').rstrip('/')


def _headers():
    token = st.session_state.get('access_token')
    return {'Authorization': f'Bearer {token}'} if token else {}


def api_get(path, params=None):
    try:
        response = requests.get(BASE_URL + path, params=params, headers=_headers(), timeout=15)
        response.raise_for_status()
        return response.json()
    except Exception as exc:
        try:
            detail = response.json()
        except Exception:
            detail = str(exc)
        return {'_error': str(detail), '_status_code': getattr(locals().get('response'), 'status_code', None)}


def api_post(path, json=None, files=None, data=None):
    try:
        response = requests.post(BASE_URL + path, json=json, files=files, data=data,
                                 headers=_headers(), timeout=60)
        response.raise_for_status()
        return response.json()
    except Exception as exc:
        try:
            detail = response.json()
        except Exception:
            detail = str(exc)
        return {'_error': str(detail), '_status_code': getattr(locals().get('response'), 'status_code', None)}


def show_error(data):
    if isinstance(data, dict) and data.get('_error'):
        if data.get('_status_code') == 401:
            st.error('Your session has expired. Please sign out and sign in again.')
        elif data.get('_status_code') == 403:
            st.error('Your department account does not have permission for this action.')
        else:
            st.error('Backend request failed: ' + str(data['_error']))
        return True
    return False

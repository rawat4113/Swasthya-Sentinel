import pytest
from fastapi.testclient import TestClient
from app.main import app

@pytest.fixture(scope='module')
def client():
    with TestClient(app) as test_client:
        yield test_client


def login(client, username, password):
    response = client.post('/api/v1/auth/login', json={'username': username, 'password': password})
    assert response.status_code == 200, response.text
    return response.json()['access_token']


def headers(token):
    return {'Authorization': f'Bearer {token}'}


def test_health_endpoint(client):
    response = client.get('/health')
    assert response.status_code == 200
    assert response.json()['status'] == 'healthy'


def test_zone_endpoint(client):
    token = login(client, 'admin', 'Admin@Sentinel2026')
    response = client.get('/api/v1/zones', headers=headers(token))
    assert response.status_code == 200
    assert len(response.json()) >= 1


def test_login_returns_department_profile(client):
    token = login(client, 'health', 'Health@Sentinel2026')
    response = client.get('/api/v1/auth/me', headers=headers(token))
    assert response.status_code == 200
    assert response.json()['role'] == 'health_officer'


def test_protected_manual_input_requires_login(client):
    response = client.post('/api/v1/ingestion/manual', json={
        'category': 'health',
        'record': {'zone_id': 'ZONE_01', 'observed_at': '2030-01-01T10:00:00', 'clinic_visits': 14}
    })
    assert response.status_code == 401


def test_department_role_can_only_submit_its_category(client):
    env_token = login(client, 'environment', 'Env@Sentinel2026')
    response = client.post('/api/v1/ingestion/manual', headers=headers(env_token), json={
        'category': 'health',
        'record': {'zone_id': 'ZONE_01', 'observed_at': '2032-01-01T10:00:00', 'clinic_visits': 14}
    })
    assert response.status_code == 403


def test_manual_input_rejects_personal_identifiers(client):
    token = login(client, 'health', 'Health@Sentinel2026')
    response = client.post('/api/v1/ingestion/manual', headers=headers(token), json={
      'category': 'health', 'record': {'zone_id': 'ZONE_01', 'observed_at': '2030-01-01T10:00:00', 'patient_id': 'not-allowed', 'clinic_visits': 14}})
    assert response.status_code == 422


def test_manual_aggregate_input_commits(client):
    token = login(client, 'health', 'Health@Sentinel2026')
    response = client.post('/api/v1/ingestion/manual', headers=headers(token), json={
      'category': 'health', 'record': {'zone_id': 'ZONE_01', 'observed_at': '2035-03-04T10:00:00', 'clinic_visits': 24, 'heat_complaints': 11, 'respiratory_complaints': 8, 'fatigue_reports': 4, 'first_aid_cases': 2}})
    assert response.status_code == 200, response.text
    assert response.json()['status'] == 'committed'
    assert response.json()['imported_rows'] == 1
    assert response.json()['created_by'] == 'health'


def test_csv_import_stage_and_commit(client):
    token = login(client, 'environment', 'Env@Sentinel2026')
    auth = headers(token)
    content = 'zone_id,observed_at,temperature_c,humidity_pct,apparent_temperature_c,pm25,pm10\nZONE_02,2035-03-05T10:00:00,36,66,39,32,54\n'
    staged = client.post('/api/v1/ingestion/upload/csv?category=environment', headers=auth, files={'file': ('test-import.csv', content, 'text/csv')})
    assert staged.status_code == 200, staged.text
    job_id = staged.json()['job_id']
    committed = client.post('/api/v1/ingestion/commit', headers=auth, params={'job_id': job_id})
    assert committed.status_code == 200, committed.text
    assert committed.json()['imported_rows'] == 1


def test_user_sees_only_own_import_jobs(client):
    health_token = login(client, 'health', 'Health@Sentinel2026')
    response = client.get('/api/v1/ingestion/my-submissions', headers=headers(health_token))
    assert response.status_code == 200
    assert all(item.get('created_by') == 'health' for item in response.json())


def test_simulation_requires_admin(client):
    health_token = login(client, 'health', 'Health@Sentinel2026')
    result = client.post('/api/v1/simulation/run', headers=headers(health_token), json={
        'zone_id': 'ZONE_03', 'scenario': 'heatwave', 'temperature_c': 44
    })
    assert result.status_code == 403


def test_simulation_does_not_write_environment_observation(client):
    admin_token = login(client, 'admin', 'Admin@Sentinel2026')
    auth = headers(admin_token)
    before = client.get('/api/v1/environment', headers=auth, params={'zone_id': 'ZONE_03', 'limit': 1000}).json()
    result = client.post('/api/v1/simulation/run', headers=auth, json={'zone_id': 'ZONE_03', 'scenario': 'heatwave', 'temperature_c': 44, 'humidity_pct': 80, 'apparent_temperature_c': 52, 'heat_complaints': 30, 'workforce_heat_complaints': 20})
    after = client.get('/api/v1/environment', headers=auth, params={'zone_id': 'ZONE_03', 'limit': 1000}).json()
    assert result.status_code == 200
    assert result.json()['simulation_only'] is True
    assert len(before) == len(after)


def test_simulation_reset_clears_simulated_outputs_only(client):
    admin_token = login(client, 'admin', 'Admin@Sentinel2026')
    auth = headers(admin_token)
    client.post('/api/v1/simulation/run', headers=auth, json={'zone_id': 'ZONE_03', 'scenario': 'combined_emergency', 'temperature_c': 45, 'apparent_temperature_c': 52, 'pm25': 100, 'pm10': 160, 'heat_complaints': 35, 'respiratory_complaints': 35, 'workforce_heat_complaints': 20, 'workforce_respiratory_complaints': 20})
    result = client.post('/api/v1/simulation/reset', headers=auth)
    assert result.status_code == 200
    assert result.json()['verified_observations_unchanged'] is True
    alerts = client.get('/api/v1/alerts', headers=auth).json()
    assert not any(a['is_simulated'] for a in alerts)


def test_admin_can_create_department_account(client):
    admin_token = login(client, 'admin', 'Admin@Sentinel2026')
    response = client.post('/api/v1/auth/users', headers=headers(admin_token), json={
        'username': 'test_environment_user', 'display_name': 'Test Environment User',
        'password': 'TestPassword@2026', 'role': 'environmental_officer'
    })
    assert response.status_code == 200, response.text
    created_token = login(client, 'test_environment_user', 'TestPassword@2026')
    me = client.get('/api/v1/auth/me', headers=headers(created_token))
    assert me.json()['role'] == 'environmental_officer'


def test_dashboard_data_endpoints_require_login(client):
    response = client.get('/api/v1/overview')
    assert response.status_code == 401


def test_non_admin_cannot_access_user_management(client):
    token = login(client, 'health', 'Health@Sentinel2026')
    response = client.get('/api/v1/auth/users', headers=headers(token))
    assert response.status_code == 403


def test_wrong_password_is_rejected(client):
    response = client.post('/api/v1/auth/login', json={'username': 'health', 'password': 'wrong-password'})
    assert response.status_code == 401

"""Real JWT and route-order proof; no graph/model computation for publication reads."""
from fastapi.testclient import TestClient

from investigation.research_results import ResultsUnavailable, load_results
from tests.conftest import _build_test_app
from tests.test_auth_rbac import ADMIN_EMAIL, ADMIN_PASS, _auth_settings, _login


def test_experiments_user_auth_static_route_and_integrity_failure(tmp_path, monkeypatch):
    settings = _auth_settings(tmp_path, RATE_LIMIT_ENABLED=False)
    app = _build_test_app(settings)
    with TestClient(app) as client:
        path = '/api/sessions/experiments'
        assert client.get(path).status_code == 401
        assert client.get(path, headers={'X-Halite-Api-Key': settings.HALITE_API_KEY}).status_code == 403
        login = _login(client, ADMIN_EMAIL, ADMIN_PASS)
        headers = {'Authorization': 'Bearer ' + login['access_token']}
        response = client.get(path, headers=headers)
        assert response.status_code == 200, response.text
        assert response.headers['Cache-Control'] == 'private, no-store'
        assert response.json() == load_results()
        def broken():
            raise ResultsUnavailable('private internal path must not be exposed')
        monkeypatch.setattr('investigation.research_results.load_results', broken)
        response = client.get(path, headers=headers)
        assert response.status_code == 503
        assert 'private internal path' not in response.text
        assert 'no substitute' in response.text
    app.state.rel_store.close()

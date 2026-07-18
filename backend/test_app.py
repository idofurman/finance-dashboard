import pytest
from unittest.mock import patch, MagicMock
from app import app


@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['PROPAGATE_EXCEPTIONS'] = False
    app.config['TEST_USER_ID'] = 1
    with app.test_client() as client:
        yield client


def test_health(client):
    response = client.get('/health')
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}


def test_get_expenses_returns_list(client):
    mock_conn = MagicMock()
    mock_cur  = MagicMock()
    mock_conn.cursor.return_value = mock_cur
    mock_cur.__enter__ = lambda s: s
    mock_cur.__exit__ = MagicMock(return_value=False)
    mock_cur.fetchall.return_value = []

    with patch('app.get_db', return_value=mock_conn):
        response = client.get('/api/expenses')
    assert response.status_code == 200
    assert isinstance(response.get_json(), list)


def test_post_expense_missing_fields(client):
    mock_conn = MagicMock()
    mock_cur  = MagicMock()
    mock_conn.cursor.return_value = mock_cur
    mock_cur.execute.side_effect = Exception("missing fields")

    with patch('app.get_db', return_value=mock_conn):
        response = client.post('/api/expenses', json={})
    assert response.status_code == 500


def test_register_missing_fields(client):
    with patch('app.get_db'):
        response = client.post('/api/auth/register', json={'username': 'test'})
    assert response.status_code == 400


def test_login_missing_fields(client):
    with patch('app.get_db'):
        response = client.post('/api/auth/login', json={})
    assert response.status_code == 400

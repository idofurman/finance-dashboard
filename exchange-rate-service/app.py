from flask import Flask, jsonify, request, g
from flask_cors import CORS
from functools import wraps
import psycopg2
import psycopg2.extras
from psycopg2 import pool as _pg_pool
import threading
import os
import jwt
import urllib.request
import json as _json
from datetime import datetime, timezone

app = Flask(__name__)

ALLOWED_ORIGINS = os.environ.get('ALLOWED_ORIGINS', '*').split(',')
CORS(app, resources={r'/*': {'origins': ALLOWED_ORIGINS, 'allow_headers': ['Content-Type', 'Authorization']}})

JWT_SECRET   = os.environ.get('JWT_SECRET')
DATABASE_URL = os.environ.get('DATABASE_URL')

if not JWT_SECRET:
    raise RuntimeError('JWT_SECRET environment variable is required')
if not DATABASE_URL:
    raise RuntimeError('DATABASE_URL environment variable is required')

FIAT_CURRENCIES  = ['USD', 'EUR']
FRANKFURTER_URL  = 'https://api.frankfurter.app/latest?from=ILS&to=USD,EUR'

_db_pool      = None
_db_pool_lock = threading.Lock()


def get_pool():
    global _db_pool
    if _db_pool is None:
        with _db_pool_lock:
            if _db_pool is None:
                _db_pool = _pg_pool.ThreadedConnectionPool(1, 10, DATABASE_URL)
    return _db_pool


def get_db():
    return get_pool().getconn()


def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization', '')
        token = auth_header.replace('Bearer ', '').strip()
        if not token:
            return jsonify({'error': 'Token required'}), 401
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
            g.user_id = payload['user_id']
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Invalid token'}), 401
        return f(*args, **kwargs)
    return decorated


@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'ok'})


@app.route('/exchange-rates', methods=['GET'])
@require_auth
def get_exchange_rates():
    conn = get_db()
    cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute(
            "SELECT currency, rate_to_ils, fetched_at FROM exchange_rates "
            "WHERE fetched_at > NOW() - INTERVAL '3 days'"
        )
        cached = {r['currency']: r for r in cur.fetchall()}

        if all(c in cached for c in FIAT_CURRENCIES):
            return jsonify({
                c: {
                    'rate_to_ils': float(cached[c]['rate_to_ils']),
                    'fetched_at':  cached[c]['fetched_at'].isoformat(),
                }
                for c in FIAT_CURRENCIES
            })

        try:
            req = urllib.request.Request(FRANKFURTER_URL, headers={'Accept': 'application/json'})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = _json.loads(resp.read())
        except Exception:
            if cached:
                return jsonify({
                    c: {'rate_to_ils': float(cached[c]['rate_to_ils'])}
                    for c in FIAT_CURRENCIES if c in cached
                })
            return jsonify({'error': 'Could not fetch exchange rates'}), 503

        result = {}
        rates  = data.get('rates', {})
        for currency in FIAT_CURRENCIES:
            rate_from_ils = rates.get(currency)
            if not rate_from_ils:
                continue
            rate_to_ils = round(1.0 / rate_from_ils, 6)
            cur.execute(
                """INSERT INTO exchange_rates (currency, rate_to_ils, fetched_at)
                   VALUES (%s, %s, NOW())
                   ON CONFLICT (currency) DO UPDATE
                     SET rate_to_ils=EXCLUDED.rate_to_ils,
                         fetched_at=EXCLUDED.fetched_at""",
                (currency, rate_to_ils)
            )
            result[currency] = {
                'rate_to_ils': rate_to_ils,
                'fetched_at':  datetime.now(timezone.utc).isoformat(),
            }

        conn.commit()
        return jsonify(result)
    finally:
        cur.close()
        get_pool().putconn(conn)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5005)

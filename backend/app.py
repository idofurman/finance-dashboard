from flask import Flask, jsonify, request, g
from flask_cors import CORS
from prometheus_flask_exporter import PrometheusMetrics
import psycopg2
import psycopg2.extras
import os
import jwt
import bcrypt
from datetime import date, timedelta, datetime, timezone
from functools import wraps

app = Flask(__name__)

ALLOWED_ORIGINS = os.environ.get('ALLOWED_ORIGINS', '*').split(',')
CORS(app, resources={r'/*': {'origins': ALLOWED_ORIGINS, 'allow_headers': ['Content-Type', 'Authorization']}})

PrometheusMetrics(app)

DATABASE_URL = os.environ.get('DATABASE_URL')
JWT_SECRET   = os.environ.get('JWT_SECRET')
if not JWT_SECRET:
    raise RuntimeError('JWT_SECRET environment variable is required')


# ============================================================
# DB
# ============================================================
def get_db():
    return psycopg2.connect(DATABASE_URL)


def init_db():
    conn = get_db()
    cur  = conn.cursor()

    cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id            SERIAL PRIMARY KEY,
            username      TEXT NOT NULL UNIQUE,
            email         TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cur.execute('''
        CREATE TABLE IF NOT EXISTS pools (
            id         SERIAL PRIMARY KEY,
            name       TEXT NOT NULL,
            created_by INTEGER NOT NULL REFERENCES users(id),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cur.execute('''
        CREATE TABLE IF NOT EXISTS pool_members (
            id         SERIAL PRIMARY KEY,
            pool_id    INTEGER NOT NULL REFERENCES pools(id) ON DELETE CASCADE,
            user_id    INTEGER NOT NULL REFERENCES users(id),
            role       TEXT NOT NULL DEFAULT 'member',
            status     TEXT NOT NULL DEFAULT 'active',
            invited_by INTEGER REFERENCES users(id),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(pool_id, user_id)
        )
    ''')

    cur.execute('''
        CREATE TABLE IF NOT EXISTS expenses (
            id            SERIAL PRIMARY KEY,
            name          TEXT    NOT NULL,
            name_he       TEXT,
            amount        NUMERIC NOT NULL,
            category      TEXT    NOT NULL,
            date          DATE    NOT NULL DEFAULT CURRENT_DATE,
            purchase_time TEXT,
            currency      TEXT    NOT NULL DEFAULT 'ILS',
            user_id       INTEGER REFERENCES users(id),
            pool_id       INTEGER REFERENCES pools(id)
        )
    ''')

    cur.execute('''
        CREATE TABLE IF NOT EXISTS budgets (
            id           SERIAL PRIMARY KEY,
            category     TEXT    NOT NULL,
            month        TEXT    NOT NULL,
            limit_amount NUMERIC NOT NULL,
            user_id      INTEGER REFERENCES users(id),
            pool_id      INTEGER REFERENCES pools(id),
            UNIQUE(category, month, user_id, pool_id)
        )
    ''')

    cur.execute('''
        CREATE TABLE IF NOT EXISTS standing_orders (
            id       SERIAL PRIMARY KEY,
            name     TEXT    NOT NULL,
            name_he  TEXT,
            amount   NUMERIC NOT NULL,
            category TEXT    NOT NULL,
            currency TEXT    NOT NULL DEFAULT 'ILS',
            user_id  INTEGER REFERENCES users(id)
        )
    ''')

    # Migrations for existing deployments
    for col in ['name_he', 'purchase_time']:
        cur.execute("ALTER TABLE expenses ADD COLUMN IF NOT EXISTS {} TEXT".format(col))
    cur.execute("ALTER TABLE expenses ADD COLUMN IF NOT EXISTS user_id INTEGER REFERENCES users(id)")
    cur.execute("ALTER TABLE expenses ADD COLUMN IF NOT EXISTS pool_id INTEGER REFERENCES pools(id)")
    cur.execute("ALTER TABLE standing_orders ADD COLUMN IF NOT EXISTS name_he TEXT")
    cur.execute("ALTER TABLE standing_orders ADD COLUMN IF NOT EXISTS user_id INTEGER REFERENCES users(id)")
    cur.execute("ALTER TABLE budgets ADD COLUMN IF NOT EXISTS user_id INTEGER REFERENCES users(id)")
    cur.execute("ALTER TABLE budgets ADD COLUMN IF NOT EXISTS pool_id INTEGER REFERENCES pools(id)")

    conn.commit()
    cur.close()
    conn.close()


try:
    init_db()
except Exception as e:
    print(f"DB init error: {e}")


# ============================================================
# AUTH HELPERS
# ============================================================
def hash_password(password):
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def check_password(password, hashed):
    return bcrypt.checkpw(password.encode(), hashed.encode())


def create_token(user_id):
    payload = {
        'user_id': user_id,
        'exp': datetime.now(timezone.utc) + timedelta(days=30)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm='HS256')


def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if app.config.get('TESTING') and app.config.get('TEST_USER_ID'):
            g.user_id = app.config['TEST_USER_ID']
            return f(*args, **kwargs)
        auth_header = request.headers.get('Authorization', '')
        token = auth_header.replace('Bearer ', '').strip()
        if not token:
            return jsonify({'error': 'Token required'}), 401
        try:
            payload  = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
            g.user_id = payload['user_id']
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Invalid token'}), 401
        return f(*args, **kwargs)
    return decorated


def is_pool_member(cur, pool_id, user_id):
    cur.execute(
        "SELECT 1 FROM pool_members WHERE pool_id=%s AND user_id=%s AND status='active'",
        (pool_id, user_id)
    )
    return cur.fetchone() is not None


# ============================================================
# AUTH ROUTES
# ============================================================
@app.route('/auth/register', methods=['POST'])
def register():
    data = request.get_json()
    username = (data.get('username') or '').strip()
    email    = (data.get('email') or '').strip().lower()
    password = data.get('password') or ''

    if not username or not email or not password:
        return jsonify({'error': 'username, email and password are required'}), 400
    if len(password) < 6:
        return jsonify({'error': 'Password must be at least 6 characters'}), 400

    conn = get_db()
    cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute(
            'INSERT INTO users (username, email, password_hash) VALUES (%s, %s, %s) RETURNING id, username, email',
            (username, email, hash_password(password))
        )
        user = dict(cur.fetchone())
        conn.commit()
        return jsonify({'token': create_token(user['id']), 'user': user}), 201
    except psycopg2.errors.UniqueViolation:
        conn.rollback()
        return jsonify({'error': 'Username or email already exists'}), 409
    finally:
        cur.close()
        conn.close()


@app.route('/auth/login', methods=['POST'])
def login():
    data     = request.get_json()
    email    = (data.get('email') or '').strip().lower()
    password = data.get('password') or ''

    if not email or not password:
        return jsonify({'error': 'email and password are required'}), 400

    conn = get_db()
    cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute('SELECT * FROM users WHERE email=%s', (email,))
        user = cur.fetchone()
        if not user or not check_password(password, user['password_hash']):
            return jsonify({'error': 'Invalid email or password'}), 401
        user = dict(user)
        del user['password_hash']
        return jsonify({'token': create_token(user['id']), 'user': user})
    finally:
        cur.close()
        conn.close()


@app.route('/auth/me', methods=['GET'])
@require_auth
def me():
    conn = get_db()
    cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute('SELECT id, username, email, created_at FROM users WHERE id=%s', (g.user_id,))
        user = dict(cur.fetchone())
        user['created_at'] = user['created_at'].isoformat()

        cur.execute('''
            SELECT p.id, p.name, pm.role
            FROM pools p
            JOIN pool_members pm ON pm.pool_id=p.id
            WHERE pm.user_id=%s AND pm.status='active'
            ORDER BY p.name
        ''', (g.user_id,))
        user['pools'] = [dict(r) for r in cur.fetchall()]

        cur.execute('''
            SELECT pm.pool_id, p.name as pool_name, u.username as invited_by
            FROM pool_members pm
            JOIN pools p ON p.id=pm.pool_id
            JOIN users u ON u.id=pm.invited_by
            WHERE pm.user_id=%s AND pm.status='pending'
        ''', (g.user_id,))
        user['invitations'] = [dict(r) for r in cur.fetchall()]

        return jsonify(user)
    finally:
        cur.close()
        conn.close()


# ============================================================
# POOL ROUTES
# ============================================================
@app.route('/pools', methods=['GET', 'POST'])
@require_auth
def pools_route():
    conn = get_db()
    cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        if request.method == 'GET':
            cur.execute('''
                SELECT p.id, p.name, pm.role,
                       (SELECT COUNT(*) FROM pool_members WHERE pool_id=p.id AND status='active') as member_count
                FROM pools p
                JOIN pool_members pm ON pm.pool_id=p.id
                WHERE pm.user_id=%s AND pm.status='active'
                ORDER BY p.name
            ''', (g.user_id,))
            return jsonify([dict(r) for r in cur.fetchall()])

        data = request.get_json()
        name = (data.get('name') or '').strip()
        if not name:
            return jsonify({'error': 'Pool name is required'}), 400

        cur.execute('INSERT INTO pools (name, created_by) VALUES (%s, %s) RETURNING id, name', (name, g.user_id))
        pool = dict(cur.fetchone())
        cur.execute(
            "INSERT INTO pool_members (pool_id, user_id, role, status) VALUES (%s, %s, 'owner', 'active')",
            (pool['id'], g.user_id)
        )
        conn.commit()
        pool['role'] = 'owner'
        pool['member_count'] = 1
        return jsonify(pool), 201
    finally:
        cur.close()
        conn.close()


@app.route('/pools/<int:pool_id>/members', methods=['GET'])
@require_auth
def pool_members(pool_id):
    conn = get_db()
    cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        if not is_pool_member(cur, pool_id, g.user_id):
            return jsonify({'error': 'Not a member of this pool'}), 403
        cur.execute('''
            SELECT u.id, u.username, u.email, pm.role, pm.status
            FROM pool_members pm
            JOIN users u ON u.id=pm.user_id
            WHERE pm.pool_id=%s
            ORDER BY pm.role DESC, u.username
        ''', (pool_id,))
        return jsonify([dict(r) for r in cur.fetchall()])
    finally:
        cur.close()
        conn.close()


@app.route('/pools/<int:pool_id>/invite', methods=['POST'])
@require_auth
def invite_to_pool(pool_id):
    conn = get_db()
    cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute("SELECT role FROM pool_members WHERE pool_id=%s AND user_id=%s AND status='active'", (pool_id, g.user_id))
        membership = cur.fetchone()
        if not membership:
            return jsonify({'error': 'Not a member of this pool'}), 403

        data           = request.get_json()
        username_or_email = (data.get('username_or_email') or '').strip()
        if not username_or_email:
            return jsonify({'error': 'username_or_email is required'}), 400

        cur.execute('SELECT id, username FROM users WHERE username=%s OR email=%s',
                    (username_or_email, username_or_email.lower()))
        target = cur.fetchone()
        if not target:
            return jsonify({'error': 'User not found'}), 404
        if target['id'] == g.user_id:
            return jsonify({'error': 'Cannot invite yourself'}), 400

        cur.execute('SELECT status FROM pool_members WHERE pool_id=%s AND user_id=%s', (pool_id, target['id']))
        existing = cur.fetchone()
        if existing:
            if existing['status'] == 'active':
                return jsonify({'error': 'User is already a member'}), 409
            if existing['status'] == 'pending':
                return jsonify({'error': 'Invitation already sent'}), 409

        cur.execute(
            "INSERT INTO pool_members (pool_id, user_id, role, status, invited_by) VALUES (%s, %s, 'member', 'pending', %s)",
            (pool_id, target['id'], g.user_id)
        )
        conn.commit()
        return jsonify({'message': f"Invitation sent to {target['username']}"}), 201
    finally:
        cur.close()
        conn.close()


@app.route('/pools/invitations', methods=['GET'])
@require_auth
def my_invitations():
    conn = get_db()
    cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute('''
            SELECT pm.pool_id, p.name as pool_name, u.username as invited_by_username
            FROM pool_members pm
            JOIN pools p ON p.id=pm.pool_id
            JOIN users u ON u.id=pm.invited_by
            WHERE pm.user_id=%s AND pm.status='pending'
        ''', (g.user_id,))
        return jsonify([dict(r) for r in cur.fetchall()])
    finally:
        cur.close()
        conn.close()


@app.route('/pools/<int:pool_id>/accept', methods=['POST'])
@require_auth
def accept_invitation(pool_id):
    conn = get_db()
    cur  = conn.cursor()
    try:
        cur.execute(
            "UPDATE pool_members SET status='active' WHERE pool_id=%s AND user_id=%s AND status='pending' RETURNING id",
            (pool_id, g.user_id)
        )
        if not cur.fetchone():
            return jsonify({'error': 'No pending invitation found'}), 404
        conn.commit()
        return jsonify({'message': 'Joined pool successfully'})
    finally:
        cur.close()
        conn.close()


@app.route('/pools/<int:pool_id>/decline', methods=['DELETE'])
@require_auth
def decline_invitation(pool_id):
    conn = get_db()
    cur  = conn.cursor()
    try:
        cur.execute(
            "DELETE FROM pool_members WHERE pool_id=%s AND user_id=%s AND status='pending' RETURNING id",
            (pool_id, g.user_id)
        )
        if not cur.fetchone():
            return jsonify({'error': 'No pending invitation found'}), 404
        conn.commit()
        return jsonify({'message': 'Invitation declined'})
    finally:
        cur.close()
        conn.close()


# ============================================================
# EXPENSES
# ============================================================
@app.route('/expenses', methods=['GET', 'POST'])
@require_auth
def expenses_route():
    conn = get_db()
    cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    if request.method == 'GET':
        pool_id = request.args.get('pool_id')
        if pool_id:
            if not is_pool_member(cur, pool_id, g.user_id):
                return jsonify({'error': 'Not a member of this pool'}), 403
            base = 'SELECT e.*, u.username as added_by FROM expenses e JOIN users u ON u.id=e.user_id WHERE e.pool_id=%s'
            params = [pool_id]
        else:
            base = 'SELECT e.*, NULL as added_by FROM expenses e WHERE e.user_id=%s AND e.pool_id IS NULL'
            params = [g.user_id]

        month         = request.args.get('month')
        filter_type   = request.args.get('filter', 'month')
        specific_date = request.args.get('date')
        year          = request.args.get('year')

        if specific_date:
            base += ' AND e.date=%s'; params.append(specific_date)
        elif year:
            base += ' AND EXTRACT(YEAR FROM e.date)=%s'; params.append(int(year))
        elif month:
            if filter_type == 'today':
                base += " AND TO_CHAR(e.date,'YYYY-MM')=%s AND e.date=%s"
                params += [month, date.today().isoformat()]
            elif filter_type == 'week':
                base += " AND TO_CHAR(e.date,'YYYY-MM')=%s AND e.date>=%s"
                params += [month, (date.today() - timedelta(days=6)).isoformat()]
            else:
                base += " AND TO_CHAR(e.date,'YYYY-MM')=%s"; params.append(month)

        base += ' ORDER BY e.date DESC, e.id DESC'
        cur.execute(base, params)
        rows = []
        for row in cur.fetchall():
            e = dict(row)
            e['date']   = e['date'].isoformat()
            e['amount'] = float(e['amount'])
            rows.append(e)
        cur.close(); conn.close()
        return jsonify(rows)

    data    = request.get_json()
    pool_id = data.get('pool_id')
    if pool_id and not is_pool_member(cur, pool_id, g.user_id):
        return jsonify({'error': 'Not a member of this pool'}), 403

    cur.execute(
        '''INSERT INTO expenses (name,name_he,amount,category,date,purchase_time,currency,user_id,pool_id)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING *''',
        (data['name'], data.get('name_he'), data['amount'], data['category'],
         data.get('date', date.today().isoformat()), data.get('purchase_time'),
         data.get('currency','ILS'), g.user_id, pool_id)
    )
    expense = dict(cur.fetchone())
    expense['date']   = expense['date'].isoformat()
    expense['amount'] = float(expense['amount'])
    conn.commit(); cur.close(); conn.close()
    return jsonify(expense), 201


@app.route('/expenses/<int:expense_id>', methods=['DELETE', 'PATCH'])
@require_auth
def modify_expense(expense_id):
    conn = get_db()
    cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute('SELECT * FROM expenses WHERE id=%s', (expense_id,))
    expense = cur.fetchone()
    if not expense:
        cur.close(); conn.close()
        return jsonify({'error': 'Not found'}), 404
    if expense['user_id'] != g.user_id:
        cur.close(); conn.close()
        return jsonify({'error': 'Forbidden'}), 403

    if request.method == 'DELETE':
        cur.execute('DELETE FROM expenses WHERE id=%s', (expense_id,))
        conn.commit(); cur.close(); conn.close()
        return jsonify({'deleted': expense_id})

    data = request.get_json()
    fields, values = [], []
    for field in ['name', 'name_he']:
        if field in data:
            fields.append(f'{field}=%s'); values.append(data[field])
    if not fields:
        cur.close(); conn.close()
        return jsonify({'error': 'no fields'}), 400
    values.append(expense_id)
    cur.execute(f"UPDATE expenses SET {', '.join(fields)} WHERE id=%s RETURNING *", values)
    row = dict(cur.fetchone())
    row['date']   = row['date'].isoformat()
    row['amount'] = float(row['amount'])
    conn.commit(); cur.close(); conn.close()
    return jsonify(row)


# ============================================================
# BUDGETS
# ============================================================
@app.route('/budgets', methods=['GET', 'POST'])
@require_auth
def budgets_route():
    conn = get_db()
    cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    if request.method == 'GET':
        pool_id = request.args.get('pool_id')
        month   = request.args.get('month')
        if pool_id:
            if not is_pool_member(cur, pool_id, g.user_id):
                return jsonify({'error': 'Not a member of this pool'}), 403
            q, p = 'SELECT * FROM budgets WHERE pool_id=%s', [pool_id]
        else:
            q, p = 'SELECT * FROM budgets WHERE user_id=%s AND pool_id IS NULL', [g.user_id]
        if month:
            q += ' AND month=%s'; p.append(month)
        cur.execute(q, p)
        rows = [dict(r) for r in cur.fetchall()]
        for r in rows: r['limit_amount'] = float(r['limit_amount'])
        cur.close(); conn.close()
        return jsonify(rows)

    data    = request.get_json()
    pool_id = data.get('pool_id')
    if pool_id and not is_pool_member(cur, pool_id, g.user_id):
        return jsonify({'error': 'Not a member of this pool'}), 403

    uid = None if pool_id else g.user_id
    cur.execute(
        '''SELECT id FROM budgets
           WHERE category=%s AND month=%s
           AND (user_id IS NOT DISTINCT FROM %s)
           AND (pool_id IS NOT DISTINCT FROM %s)''',
        (data['category'], data['month'], uid, pool_id)
    )
    existing = cur.fetchone()
    if existing:
        cur.execute('UPDATE budgets SET limit_amount=%s WHERE id=%s RETURNING *',
                    (data['limit_amount'], existing['id']))
    else:
        cur.execute(
            'INSERT INTO budgets (category, month, limit_amount, user_id, pool_id) VALUES (%s,%s,%s,%s,%s) RETURNING *',
            (data['category'], data['month'], data['limit_amount'], uid, pool_id)
        )
    budget = dict(cur.fetchone())
    budget['limit_amount'] = float(budget['limit_amount'])
    conn.commit(); cur.close(); conn.close()
    return jsonify(budget), 201


# ============================================================
# STANDING ORDERS (personal only)
# ============================================================
@app.route('/standing-orders', methods=['GET', 'POST'])
@require_auth
def standing_orders_route():
    conn = get_db()
    cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    if request.method == 'GET':
        cur.execute('SELECT * FROM standing_orders WHERE user_id=%s ORDER BY id', (g.user_id,))
        rows = [dict(r) for r in cur.fetchall()]
        for r in rows: r['amount'] = float(r['amount'])
        cur.close(); conn.close()
        return jsonify(rows)

    data = request.get_json()
    cur.execute(
        'INSERT INTO standing_orders (name,name_he,amount,category,currency,user_id) VALUES (%s,%s,%s,%s,%s,%s) RETURNING *',
        (data['name'], data.get('name_he'), data['amount'], data['category'], data.get('currency','ILS'), g.user_id)
    )
    order = dict(cur.fetchone())
    order['amount'] = float(order['amount'])
    conn.commit(); cur.close(); conn.close()
    return jsonify(order), 201


@app.route('/standing-orders/<int:order_id>', methods=['DELETE', 'PATCH'])
@require_auth
def modify_standing_order(order_id):
    conn = get_db()
    cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute('SELECT * FROM standing_orders WHERE id=%s', (order_id,))
    order = cur.fetchone()
    if not order:
        cur.close(); conn.close()
        return jsonify({'error': 'Not found'}), 404
    if order['user_id'] != g.user_id:
        cur.close(); conn.close()
        return jsonify({'error': 'Forbidden'}), 403

    if request.method == 'DELETE':
        cur.execute('DELETE FROM standing_orders WHERE id=%s', (order_id,))
        conn.commit(); cur.close(); conn.close()
        return jsonify({'deleted': order_id})

    data = request.get_json()
    fields, values = [], []
    for field in ['name', 'name_he']:
        if field in data:
            fields.append(f'{field}=%s'); values.append(data[field])
    if not fields:
        cur.close(); conn.close()
        return jsonify({'error': 'no fields'}), 400
    values.append(order_id)
    cur.execute(f"UPDATE standing_orders SET {', '.join(fields)} WHERE id=%s RETURNING *", values)
    row = dict(cur.fetchone())
    row['amount'] = float(row['amount'])
    conn.commit(); cur.close(); conn.close()
    return jsonify(row)


# ============================================================
# RECEIPT SCANNER
# ============================================================
@app.route('/parse-receipt', methods=['POST'])
@require_auth
def parse_receipt():
    import anthropic as _anthropic
    import json as _json

    api_key = os.environ.get('ANTHROPIC_API_KEY')
    if not api_key:
        return jsonify({'error': 'ANTHROPIC_API_KEY not configured on server'}), 503

    data      = request.get_json()
    img_data  = data.get('image')
    mime_type = data.get('media_type', 'image/jpeg')
    if not img_data:
        return jsonify({'error': 'No image provided'}), 400

    try:
        client = _anthropic.Anthropic(api_key=api_key)
        msg = client.messages.create(
            model='claude-haiku-4-5-20251001',
            max_tokens=300,
            messages=[{'role': 'user', 'content': [
                {'type': 'image', 'source': {'type': 'base64', 'media_type': mime_type, 'data': img_data}},
                {'type': 'text', 'text': (
                    'Extract the key details from this receipt. '
                    'Return ONLY valid JSON with no markdown, no explanation:\n'
                    '{"name":"store or merchant name","amount":0.00,"date":"YYYY-MM-DD",'
                    '"category":"groceries|housing|transport|food|clothing|health|subscriptions|entertainment|education|other"}\n'
                    'amount = total amount paid. Use null for any field you cannot determine. '
                    'For date, if year is missing assume current year.'
                )}
            ]}]
        )
        raw = msg.content[0].text.strip()
        if raw.startswith('```'):
            raw = raw.split('```')[1]
            if raw.startswith('json'): raw = raw[4:]
            raw = raw.strip()
        return jsonify(_json.loads(raw))
    except _json.JSONDecodeError:
        return jsonify({'error': 'Could not parse receipt data'}), 422
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================================
# HEALTH
# ============================================================
@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'ok'})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)

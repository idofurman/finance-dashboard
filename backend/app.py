from flask import Flask, jsonify, request
from flask_cors import CORS
from prometheus_flask_exporter import PrometheusMetrics
import psycopg2
import psycopg2.extras
import os
from datetime import date, timedelta

app = Flask(__name__)
CORS(app)
PrometheusMetrics(app)

DATABASE_URL = os.environ.get('DATABASE_URL')


def get_db():
    return psycopg2.connect(DATABASE_URL)


def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS expenses (
            id            SERIAL PRIMARY KEY,
            name          TEXT    NOT NULL,
            name_he       TEXT,
            amount        NUMERIC NOT NULL,
            category      TEXT    NOT NULL,
            date          DATE    NOT NULL DEFAULT CURRENT_DATE,
            purchase_time TEXT,
            currency      TEXT    NOT NULL DEFAULT 'ILS'
        )
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS budgets (
            id           SERIAL PRIMARY KEY,
            category     TEXT    NOT NULL,
            month        TEXT    NOT NULL,
            limit_amount NUMERIC NOT NULL,
            UNIQUE(category, month)
        )
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS standing_orders (
            id      SERIAL PRIMARY KEY,
            name    TEXT    NOT NULL,
            name_he TEXT,
            amount  NUMERIC NOT NULL,
            category TEXT   NOT NULL,
            currency TEXT   NOT NULL DEFAULT 'ILS'
        )
    ''')
    # migrate existing tables that may not have name_he yet
    cur.execute("ALTER TABLE expenses ADD COLUMN IF NOT EXISTS name_he TEXT")
    cur.execute("ALTER TABLE expenses ADD COLUMN IF NOT EXISTS purchase_time TEXT")
    cur.execute("ALTER TABLE standing_orders ADD COLUMN IF NOT EXISTS name_he TEXT")
    conn.commit()
    cur.close()
    conn.close()


try:
    init_db()
except Exception as e:
    print(f"DB init error: {e}")


@app.route("/health", methods=["GET"])
def health_check():
    return jsonify({"status": "ok"})


@app.route("/expenses", methods=["GET", "POST"])
def expenses_route():
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    if request.method == "GET":
        month = request.args.get('month')
        filter_type = request.args.get('filter', 'month')

        query = "SELECT * FROM expenses"
        params = []

        specific_date = request.args.get('date')
        year          = request.args.get('year')

        if specific_date:
            query += " WHERE date = %s"
            params = [specific_date]
        elif year:
            query += " WHERE EXTRACT(YEAR FROM date) = %s"
            params = [int(year)]
        elif month:
            if filter_type == 'today':
                query += " WHERE TO_CHAR(date, 'YYYY-MM') = %s AND date = %s"
                params = [month, date.today().isoformat()]
            elif filter_type == 'week':
                query += " WHERE TO_CHAR(date, 'YYYY-MM') = %s AND date >= %s"
                params = [month, (date.today() - timedelta(days=6)).isoformat()]
            else:
                query += " WHERE TO_CHAR(date, 'YYYY-MM') = %s"
                params = [month]

        query += " ORDER BY date DESC, id DESC"
        cur.execute(query, params)

        expenses = []
        for row in cur.fetchall():
            e = dict(row)
            e['date'] = e['date'].isoformat()
            e['amount'] = float(e['amount'])
            expenses.append(e)

        cur.close()
        conn.close()
        return jsonify(expenses)

    elif request.method == "POST":
        data = request.get_json()
        cur.execute(
            "INSERT INTO expenses (name, name_he, amount, category, date, purchase_time, currency) VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING *",
            (data['name'], data.get('name_he'), data['amount'], data['category'],
             data.get('date', date.today().isoformat()), data.get('purchase_time'), data.get('currency', 'ILS'))
        )
        expense = dict(cur.fetchone())
        expense['date'] = expense['date'].isoformat()
        expense['amount'] = float(expense['amount'])
        conn.commit()
        cur.close()
        conn.close()
        return jsonify(expense), 201


@app.route("/expenses/<int:expense_id>", methods=["DELETE", "PATCH"])
def delete_or_patch_expense(expense_id):
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    if request.method == "DELETE":
        cur.execute("DELETE FROM expenses WHERE id = %s", (expense_id,))
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({"deleted": expense_id})
    data = request.get_json()
    fields, values = [], []
    if 'name'    in data: fields.append("name = %s");    values.append(data['name'])
    if 'name_he' in data: fields.append("name_he = %s"); values.append(data['name_he'])
    if not fields:
        return jsonify({"error": "no fields"}), 400
    values.append(expense_id)
    cur.execute(f"UPDATE expenses SET {', '.join(fields)} WHERE id = %s RETURNING *", values)
    row = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()
    if not row:
        return jsonify({"error": "not found"}), 404
    expense = dict(row)
    expense['date'] = expense['date'].isoformat()
    expense['amount'] = float(expense['amount'])
    return jsonify(expense)


@app.route("/budgets", methods=["GET", "POST"])
def budgets_route():
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    if request.method == "GET":
        month = request.args.get('month')
        if month:
            cur.execute("SELECT * FROM budgets WHERE month = %s", (month,))
        else:
            cur.execute("SELECT * FROM budgets")
        budgets = []
        for row in cur.fetchall():
            b = dict(row)
            b['limit_amount'] = float(b['limit_amount'])
            budgets.append(b)
        cur.close()
        conn.close()
        return jsonify(budgets)

    elif request.method == "POST":
        data = request.get_json()
        cur.execute(
            '''INSERT INTO budgets (category, month, limit_amount)
               VALUES (%s, %s, %s)
               ON CONFLICT (category, month) DO UPDATE SET limit_amount = EXCLUDED.limit_amount
               RETURNING *''',
            (data['category'], data['month'], data['limit_amount'])
        )
        budget = dict(cur.fetchone())
        budget['limit_amount'] = float(budget['limit_amount'])
        conn.commit()
        cur.close()
        conn.close()
        return jsonify(budget), 201


@app.route("/standing-orders", methods=["GET", "POST"])
def standing_orders_route():
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    if request.method == "GET":
        cur.execute("SELECT * FROM standing_orders ORDER BY id")
        orders = []
        for row in cur.fetchall():
            o = dict(row)
            o['amount'] = float(o['amount'])
            orders.append(o)
        cur.close()
        conn.close()
        return jsonify(orders)

    elif request.method == "POST":
        data = request.get_json()
        cur.execute(
            "INSERT INTO standing_orders (name, name_he, amount, category, currency) VALUES (%s, %s, %s, %s, %s) RETURNING *",
            (data['name'], data.get('name_he'), data['amount'], data['category'], data.get('currency', 'ILS'))
        )
        order = dict(cur.fetchone())
        order['amount'] = float(order['amount'])
        conn.commit()
        cur.close()
        conn.close()
        return jsonify(order), 201


@app.route("/standing-orders/<int:order_id>", methods=["DELETE", "PATCH"])
def delete_or_patch_standing_order(order_id):
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    if request.method == "DELETE":
        cur.execute("DELETE FROM standing_orders WHERE id = %s", (order_id,))
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({"deleted": order_id})
    data = request.get_json()
    fields, values = [], []
    if 'name'    in data: fields.append("name = %s");    values.append(data['name'])
    if 'name_he' in data: fields.append("name_he = %s"); values.append(data['name_he'])
    if not fields:
        return jsonify({"error": "no fields"}), 400
    values.append(order_id)
    cur.execute(f"UPDATE standing_orders SET {', '.join(fields)} WHERE id = %s RETURNING *", values)
    row = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()
    if not row:
        return jsonify({"error": "not found"}), 404
    order = dict(row)
    order['amount'] = float(order['amount'])
    return jsonify(order)


@app.route("/parse-receipt", methods=["POST"])
def parse_receipt():
    import anthropic as _anthropic
    import json as _json

    api_key = os.environ.get('ANTHROPIC_API_KEY')
    if not api_key:
        return jsonify({"error": "ANTHROPIC_API_KEY not configured on server"}), 503

    data      = request.get_json()
    img_data  = data.get('image')
    mime_type = data.get('media_type', 'image/jpeg')

    if not img_data:
        return jsonify({"error": "No image provided"}), 400

    try:
        client = _anthropic.Anthropic(api_key=api_key)
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=300,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {"type": "base64", "media_type": mime_type, "data": img_data}
                    },
                    {
                        "type": "text",
                        "text": (
                            "Extract the key details from this receipt. "
                            "Return ONLY valid JSON with no markdown, no explanation:\n"
                            '{"name":"store or merchant name","amount":0.00,"date":"YYYY-MM-DD",'
                            '"category":"groceries|housing|transport|food|clothing|health|subscriptions|entertainment|education|other"}\n'
                            "amount = total amount paid. Use null for any field you cannot determine. "
                            "For date, if year is missing assume current year."
                        )
                    }
                ]
            }]
        )
        raw = msg.content[0].text.strip()
        print("Claude raw response:", raw, flush=True)
        # Strip markdown code fences if Claude added them
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()
        result = _json.loads(raw)
        return jsonify(result)
    except _json.JSONDecodeError as e:
        print("JSON decode error:", e, "raw:", locals().get('raw', ''), flush=True)
        return jsonify({"error": "Could not parse receipt data"}), 422
    except Exception as e:
        print("parse-receipt error:", type(e).__name__, str(e), flush=True)
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

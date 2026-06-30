from flask import Flask, jsonify, request
from flask_cors import CORS
import psycopg2
import psycopg2.extras
import os
from datetime import date, timedelta

app = Flask(__name__)
CORS(app)

DATABASE_URL = os.environ.get('DATABASE_URL')


def get_db():
    return psycopg2.connect(DATABASE_URL)


def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS expenses (
            id       SERIAL PRIMARY KEY,
            name     TEXT    NOT NULL,
            amount   NUMERIC NOT NULL,
            category TEXT    NOT NULL,
            date     DATE    NOT NULL DEFAULT CURRENT_DATE,
            currency TEXT    NOT NULL DEFAULT 'ILS'
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
            id       SERIAL PRIMARY KEY,
            name     TEXT    NOT NULL,
            amount   NUMERIC NOT NULL,
            category TEXT    NOT NULL,
            currency TEXT    NOT NULL DEFAULT 'ILS'
        )
    ''')
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

        if specific_date:
            query += " WHERE date = %s"
            params = [specific_date]
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
            "INSERT INTO expenses (name, amount, category, date, currency) VALUES (%s, %s, %s, %s, %s) RETURNING *",
            (data['name'], data['amount'], data['category'],
             data.get('date', date.today().isoformat()), data.get('currency', 'ILS'))
        )
        expense = dict(cur.fetchone())
        expense['date'] = expense['date'].isoformat()
        expense['amount'] = float(expense['amount'])
        conn.commit()
        cur.close()
        conn.close()
        return jsonify(expense), 201


@app.route("/expenses/<int:expense_id>", methods=["DELETE"])
def delete_expense(expense_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM expenses WHERE id = %s", (expense_id,))
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({"deleted": expense_id})


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
            "INSERT INTO standing_orders (name, amount, category, currency) VALUES (%s, %s, %s, %s) RETURNING *",
            (data['name'], data['amount'], data['category'], data.get('currency', 'ILS'))
        )
        order = dict(cur.fetchone())
        order['amount'] = float(order['amount'])
        conn.commit()
        cur.close()
        conn.close()
        return jsonify(order), 201


@app.route("/standing-orders/<int:order_id>", methods=["DELETE"])
def delete_standing_order(order_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM standing_orders WHERE id = %s", (order_id,))
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({"deleted": order_id})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

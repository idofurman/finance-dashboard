from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

expenses = [
    {"id": 1, "amount": 10, "category": "groceries"},
    {"id": 2, "amount": 150, "category": "bills"}
]


@app.route("/health", methods=["GET"])
def health_check():
    return jsonify({"status": "ok"})


@app.route("/expenses", methods=["GET", "POST"])
def expenses_route():
    if request.method == "GET":
        return jsonify(expenses)
    elif request.method == "POST":
        new_expense = request.get_json()
        expenses.append(new_expense)
        return jsonify(new_expense), 201


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

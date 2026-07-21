from flask import Flask, jsonify, request, g
from flask_cors import CORS
from functools import wraps
import os
import jwt
import json as _json

app = Flask(__name__)

ALLOWED_ORIGINS = os.environ.get('ALLOWED_ORIGINS', '*').split(',')
CORS(app, resources={r'/*': {'origins': ALLOWED_ORIGINS, 'allow_headers': ['Content-Type', 'Authorization']}})

JWT_SECRET = os.environ.get('JWT_SECRET')
if not JWT_SECRET:
    raise RuntimeError('JWT_SECRET environment variable is required')


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


@app.route('/parse-receipt', methods=['POST'])
@require_auth
def parse_receipt():
    import anthropic as _anthropic

    api_key = os.environ.get('ANTHROPIC_API_KEY')
    if not api_key:
        return jsonify({'error': 'ANTHROPIC_API_KEY not configured on server'}), 503

    data = request.get_json()
    img_data = data.get('image')
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
            if raw.startswith('json'):
                raw = raw[4:]
            raw = raw.strip()
        return jsonify(_json.loads(raw))
    except _json.JSONDecodeError:
        return jsonify({'error': 'Could not parse receipt data'}), 422
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5004)

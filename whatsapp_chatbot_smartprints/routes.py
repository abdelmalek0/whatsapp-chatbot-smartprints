from flask import Blueprint, request, jsonify

webhook_bp = Blueprint('webhook', __name__)

@webhook_bp.route('/webhook', methods=['GET'])
def verify_webhook():
    mode = request.args.get('hub.mode')
    token = request.args.get('hub.verify_token')
    challenge = request.args.get('hub.challenge')
    
    if mode == 'subscribe' and token == webhook_bp.webhook_service.verify_token:
        print("Webhook verified successfully!")
        return challenge, 200
    else:
        return '', 403

@webhook_bp.route('/webhook', methods=['POST'])
def webhook():
    return webhook_bp.webhook_service.handle_webhook(request.json)

@webhook_bp.route('/')
def home():
    return "<pre>Nothing to see here.\nCheckout README.md to start.</pre>"
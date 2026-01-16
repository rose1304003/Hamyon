"""
Hamyon - REST API Server
Provides endpoints for the Telegram Mini App
"""

import os
import logging
from datetime import datetime
from flask import Flask, jsonify, request
from flask_cors import CORS
from functools import wraps
import hmac
import hashlib
import urllib.parse

from database import (
    init_database, get_user_by_telegram_id, get_or_create_user,
    update_user_settings, get_categories, create_category,
    add_transaction, get_transactions, get_balance, get_monthly_summary,
    delete_transaction, create_savings_goal, get_savings_goals,
    get_savings_goal, update_savings_goal, add_to_savings_goal,
    delete_savings_goal, get_user_dashboard
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app, origins=["*"])  # Allow Mini App origin

BOT_TOKEN = os.getenv("BOT_TOKEN")


def validate_telegram_data(init_data: str) -> dict:
    """Validate Telegram Web App init data."""
    try:
        # Parse the init data
        parsed_data = dict(urllib.parse.parse_qsl(init_data))
        
        # Get the hash from the data
        received_hash = parsed_data.pop('hash', '')
        
        # Create the data check string
        data_check_string = '\n'.join(
            f'{k}={v}' for k, v in sorted(parsed_data.items())
        )
        
        # Create secret key
        secret_key = hmac.new(
            b'WebAppData',
            BOT_TOKEN.encode(),
            hashlib.sha256
        ).digest()
        
        # Calculate hash
        calculated_hash = hmac.new(
            secret_key,
            data_check_string.encode(),
            hashlib.sha256
        ).hexdigest()
        
        # Validate
        if calculated_hash == received_hash:
            return parsed_data
        
        return None
    except Exception as e:
        logger.error(f"Validation error: {e}")
        return None


def require_auth(f):
    """Decorator to require Telegram authentication."""
    @wraps(f)
    def decorated(*args, **kwargs):
        # Get init data from header
        init_data = request.headers.get('X-Telegram-Init-Data', '')
        
        # Also accept telegram_id for simpler testing
        telegram_id = request.headers.get('X-Telegram-Id')
        
        if telegram_id:
            try:
                user = get_user_by_telegram_id(int(telegram_id))
                if user:
                    request.user = user
                    return f(*args, **kwargs)
            except ValueError:
                pass
        
        if init_data:
            validated = validate_telegram_data(init_data)
            if validated:
                user_data = validated.get('user', '{}')
                import json
                user_info = json.loads(user_data)
                
                user = get_or_create_user(
                    telegram_id=user_info.get('id'),
                    username=user_info.get('username'),
                    first_name=user_info.get('first_name'),
                    last_name=user_info.get('last_name'),
                    language_code=user_info.get('language_code', 'en')
                )
                request.user = user
                return f(*args, **kwargs)
        
        return jsonify({'error': 'Unauthorized'}), 401
    
    return decorated


# ============== Health Check ==============

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({'status': 'ok', 'timestamp': datetime.utcnow().isoformat()})


# ============== User Endpoints ==============

@app.route('/api/user', methods=['GET'])
@require_auth
def get_user():
    """Get current user info."""
    return jsonify(request.user)


@app.route('/api/user/settings', methods=['PUT'])
@require_auth
def update_settings():
    """Update user settings."""
    data = request.json
    user = update_user_settings(
        request.user['telegram_id'],
        language_code=data.get('language_code'),
        currency=data.get('currency')
    )
    return jsonify(user)


# ============== Dashboard ==============

@app.route('/api/dashboard', methods=['GET'])
@require_auth
def dashboard():
    """Get complete dashboard data."""
    data = get_user_dashboard(request.user['telegram_id'])
    if not data:
        return jsonify({'error': 'User not found'}), 404
    
    # Convert decimals to floats for JSON serialization
    def convert_decimals(obj):
        if isinstance(obj, dict):
            return {k: convert_decimals(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [convert_decimals(item) for item in obj]
        elif hasattr(obj, '__float__'):
            return float(obj)
        elif hasattr(obj, 'isoformat'):
            return obj.isoformat()
        return obj
    
    return jsonify(convert_decimals(data))


# ============== Categories ==============

@app.route('/api/categories', methods=['GET'])
@require_auth
def get_categories_endpoint():
    """Get all categories."""
    cat_type = request.args.get('type')
    categories = get_categories(request.user['id'], cat_type)
    return jsonify(categories)


@app.route('/api/categories', methods=['POST'])
@require_auth
def create_category_endpoint():
    """Create a new category."""
    data = request.json
    category = create_category(
        user_id=request.user['id'],
        name=data['name'],
        emoji=data.get('emoji', '📁'),
        cat_type=data.get('type', 'expense')
    )
    return jsonify(category), 201


# ============== Transactions ==============

@app.route('/api/transactions', methods=['GET'])
@require_auth
def get_transactions_endpoint():
    """Get transactions with optional filters."""
    limit = request.args.get('limit', 50, type=int)
    offset = request.args.get('offset', 0, type=int)
    trans_type = request.args.get('type')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    transactions = get_transactions(
        request.user['id'],
        limit=limit,
        offset=offset,
        trans_type=trans_type,
        start_date=start_date,
        end_date=end_date
    )
    
    # Convert for JSON
    result = []
    for t in transactions:
        item = dict(t)
        item['amount'] = float(item['amount'])
        if hasattr(item.get('date'), 'isoformat'):
            item['date'] = item['date'].isoformat()
        if hasattr(item.get('created_at'), 'isoformat'):
            item['created_at'] = item['created_at'].isoformat()
        result.append(item)
    
    return jsonify(result)


@app.route('/api/transactions', methods=['POST'])
@require_auth
def create_transaction_endpoint():
    """Create a new transaction."""
    data = request.json
    
    transaction = add_transaction(
        user_id=request.user['id'],
        amount=data['amount'],
        trans_type=data['type'],
        category_id=data.get('category_id'),
        description=data.get('description'),
        date=data.get('date')
    )
    
    result = dict(transaction)
    result['amount'] = float(result['amount'])
    if hasattr(result.get('date'), 'isoformat'):
        result['date'] = result['date'].isoformat()
    
    return jsonify(result), 201


@app.route('/api/transactions/<int:transaction_id>', methods=['DELETE'])
@require_auth
def delete_transaction_endpoint(transaction_id):
    """Delete a transaction."""
    success = delete_transaction(transaction_id, request.user['id'])
    if success:
        return jsonify({'success': True})
    return jsonify({'error': 'Transaction not found'}), 404


# ============== Balance & Summary ==============

@app.route('/api/balance', methods=['GET'])
@require_auth
def get_balance_endpoint():
    """Get user balance."""
    balance = get_balance(request.user['id'])
    return jsonify(balance)


@app.route('/api/summary', methods=['GET'])
@require_auth
def get_summary_endpoint():
    """Get monthly summary."""
    year = request.args.get('year', type=int)
    month = request.args.get('month', type=int)
    
    summary = get_monthly_summary(request.user['id'], year, month)
    
    # Convert categories totals
    for cat in summary.get('categories', []):
        cat['total'] = float(cat['total'])
    
    return jsonify(summary)


# ============== Savings Goals ==============

@app.route('/api/goals', methods=['GET'])
@require_auth
def get_goals_endpoint():
    """Get all savings goals."""
    include_completed = request.args.get('include_completed', 'true').lower() == 'true'
    goals = get_savings_goals(request.user['id'], include_completed)
    
    result = []
    for g in goals:
        item = dict(g)
        item['target_amount'] = float(item['target_amount'])
        item['current_amount'] = float(item['current_amount'])
        if hasattr(item.get('deadline'), 'isoformat'):
            item['deadline'] = item['deadline'].isoformat()
        if hasattr(item.get('created_at'), 'isoformat'):
            item['created_at'] = item['created_at'].isoformat()
        result.append(item)
    
    return jsonify(result)


@app.route('/api/goals', methods=['POST'])
@require_auth
def create_goal_endpoint():
    """Create a new savings goal."""
    data = request.json
    
    goal = create_savings_goal(
        user_id=request.user['id'],
        name=data['name'],
        target_amount=data['target_amount'],
        emoji=data.get('emoji', '🎯'),
        deadline=data.get('deadline')
    )
    
    result = dict(goal)
    result['target_amount'] = float(result['target_amount'])
    result['current_amount'] = float(result['current_amount'])
    
    return jsonify(result), 201


@app.route('/api/goals/<int:goal_id>', methods=['GET'])
@require_auth
def get_goal_endpoint(goal_id):
    """Get a specific savings goal."""
    goal = get_savings_goal(goal_id, request.user['id'])
    
    if not goal:
        return jsonify({'error': 'Goal not found'}), 404
    
    result = dict(goal)
    result['target_amount'] = float(result['target_amount'])
    result['current_amount'] = float(result['current_amount'])
    
    return jsonify(result)


@app.route('/api/goals/<int:goal_id>', methods=['PUT'])
@require_auth
def update_goal_endpoint(goal_id):
    """Update a savings goal."""
    data = request.json
    
    goal = update_savings_goal(
        goal_id=goal_id,
        user_id=request.user['id'],
        name=data.get('name'),
        target_amount=data.get('target_amount'),
        emoji=data.get('emoji'),
        deadline=data.get('deadline')
    )
    
    if not goal:
        return jsonify({'error': 'Goal not found'}), 404
    
    result = dict(goal)
    result['target_amount'] = float(result['target_amount'])
    result['current_amount'] = float(result['current_amount'])
    
    return jsonify(result)


@app.route('/api/goals/<int:goal_id>/contribute', methods=['POST'])
@require_auth
def contribute_to_goal_endpoint(goal_id):
    """Add contribution to a savings goal."""
    data = request.json
    
    goal = add_to_savings_goal(
        goal_id=goal_id,
        user_id=request.user['id'],
        amount=data['amount'],
        note=data.get('note')
    )
    
    if not goal:
        return jsonify({'error': 'Goal not found'}), 404
    
    result = dict(goal)
    result['target_amount'] = float(result['target_amount'])
    result['current_amount'] = float(result['current_amount'])
    
    return jsonify(result)


@app.route('/api/goals/<int:goal_id>', methods=['DELETE'])
@require_auth
def delete_goal_endpoint(goal_id):
    """Delete a savings goal."""
    success = delete_savings_goal(goal_id, request.user['id'])
    if success:
        return jsonify({'success': True})
    return jsonify({'error': 'Goal not found'}), 404


# ============== Error Handlers ==============

@app.errorhandler(400)
def bad_request(e):
    return jsonify({'error': 'Bad request'}), 400


@app.errorhandler(404)
def not_found(e):
    return jsonify({'error': 'Not found'}), 404


@app.errorhandler(500)
def server_error(e):
    logger.error(f"Server error: {e}")
    return jsonify({'error': 'Internal server error'}), 500


if __name__ == '__main__':
    # Initialize database
    init_database()
    
    # Run the server
    port = int(os.getenv('PORT', 8000))
    app.run(host='0.0.0.0', port=port, debug=os.getenv('DEBUG', 'false').lower() == 'true')

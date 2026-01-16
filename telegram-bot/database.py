"""
Hamyon - PostgreSQL Database Module
Handles all database operations with automatic table creation
"""

import os
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
import psycopg2
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL")

def get_connection():
    """Create a new database connection."""
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)

@contextmanager
def get_db():
    """Context manager for database connections."""
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(f"Database error: {e}")
        raise
    finally:
        conn.close()

def init_database():
    """Initialize all database tables."""
    with get_db() as conn:
        cur = conn.cursor()
        
        # Users table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                telegram_id BIGINT UNIQUE NOT NULL,
                username VARCHAR(255),
                first_name VARCHAR(255),
                last_name VARCHAR(255),
                language_code VARCHAR(10) DEFAULT 'en',
                currency VARCHAR(10) DEFAULT 'UZS',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Categories table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS categories (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                name VARCHAR(100) NOT NULL,
                emoji VARCHAR(10) DEFAULT '📁',
                type VARCHAR(20) CHECK (type IN ('income', 'expense')) DEFAULT 'expense',
                is_default BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Transactions table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                category_id INTEGER REFERENCES categories(id) ON DELETE SET NULL,
                amount DECIMAL(15, 2) NOT NULL,
                type VARCHAR(20) CHECK (type IN ('income', 'expense')) NOT NULL,
                description TEXT,
                date DATE DEFAULT CURRENT_DATE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Savings Goals table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS savings_goals (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                name VARCHAR(255) NOT NULL,
                target_amount DECIMAL(15, 2) NOT NULL,
                current_amount DECIMAL(15, 2) DEFAULT 0,
                emoji VARCHAR(10) DEFAULT '🎯',
                deadline DATE,
                is_completed BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Savings contributions table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS savings_contributions (
                id SERIAL PRIMARY KEY,
                goal_id INTEGER REFERENCES savings_goals(id) ON DELETE CASCADE,
                amount DECIMAL(15, 2) NOT NULL,
                note TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Budgets table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS budgets (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                category_id INTEGER REFERENCES categories(id) ON DELETE CASCADE,
                amount DECIMAL(15, 2) NOT NULL,
                period VARCHAR(20) CHECK (period IN ('daily', 'weekly', 'monthly')) DEFAULT 'monthly',
                start_date DATE DEFAULT CURRENT_DATE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create indexes for better performance
        cur.execute("CREATE INDEX IF NOT EXISTS idx_transactions_user ON transactions(user_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_transactions_date ON transactions(date)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_savings_goals_user ON savings_goals(user_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_categories_user ON categories(user_id)")
        
        logger.info("Database tables initialized successfully")


# ============== User Operations ==============

def get_or_create_user(telegram_id: int, username: str = None, 
                       first_name: str = None, last_name: str = None,
                       language_code: str = 'en') -> Dict[str, Any]:
    """Get existing user or create new one."""
    with get_db() as conn:
        cur = conn.cursor()
        
        # Try to get existing user
        cur.execute("SELECT * FROM users WHERE telegram_id = %s", (telegram_id,))
        user = cur.fetchone()
        
        if user:
            # Update user info
            cur.execute("""
                UPDATE users SET 
                    username = COALESCE(%s, username),
                    first_name = COALESCE(%s, first_name),
                    last_name = COALESCE(%s, last_name),
                    updated_at = CURRENT_TIMESTAMP
                WHERE telegram_id = %s
                RETURNING *
            """, (username, first_name, last_name, telegram_id))
            return dict(cur.fetchone())
        
        # Create new user
        cur.execute("""
            INSERT INTO users (telegram_id, username, first_name, last_name, language_code)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING *
        """, (telegram_id, username, first_name, last_name, language_code))
        user = dict(cur.fetchone())
        
        # Create default categories for new user
        create_default_categories(user['id'])
        
        return user

def get_user_by_telegram_id(telegram_id: int) -> Optional[Dict[str, Any]]:
    """Get user by Telegram ID."""
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE telegram_id = %s", (telegram_id,))
        result = cur.fetchone()
        return dict(result) if result else None

def update_user_settings(telegram_id: int, **kwargs) -> Dict[str, Any]:
    """Update user settings."""
    allowed_fields = ['language_code', 'currency']
    updates = {k: v for k, v in kwargs.items() if k in allowed_fields}
    
    if not updates:
        return get_user_by_telegram_id(telegram_id)
    
    with get_db() as conn:
        cur = conn.cursor()
        set_clause = ", ".join([f"{k} = %s" for k in updates.keys()])
        values = list(updates.values()) + [telegram_id]
        
        cur.execute(f"""
            UPDATE users SET {set_clause}, updated_at = CURRENT_TIMESTAMP
            WHERE telegram_id = %s
            RETURNING *
        """, values)
        return dict(cur.fetchone())


# ============== Category Operations ==============

def create_default_categories(user_id: int):
    """Create default categories for a new user."""
    default_categories = [
        ('Food & Dining', '🍔', 'expense'),
        ('Transportation', '🚗', 'expense'),
        ('Shopping', '🛒', 'expense'),
        ('Entertainment', '🎬', 'expense'),
        ('Bills & Utilities', '💡', 'expense'),
        ('Health', '💊', 'expense'),
        ('Education', '📚', 'expense'),
        ('Other', '📦', 'expense'),
        ('Salary', '💰', 'income'),
        ('Freelance', '💼', 'income'),
        ('Gift', '🎁', 'income'),
        ('Investment', '📈', 'income'),
    ]
    
    with get_db() as conn:
        cur = conn.cursor()
        for name, emoji, cat_type in default_categories:
            cur.execute("""
                INSERT INTO categories (user_id, name, emoji, type, is_default)
                VALUES (%s, %s, %s, %s, TRUE)
            """, (user_id, name, emoji, cat_type))

def get_categories(user_id: int, cat_type: str = None) -> List[Dict[str, Any]]:
    """Get all categories for a user."""
    with get_db() as conn:
        cur = conn.cursor()
        if cat_type:
            cur.execute("""
                SELECT * FROM categories WHERE user_id = %s AND type = %s
                ORDER BY is_default DESC, name ASC
            """, (user_id, cat_type))
        else:
            cur.execute("""
                SELECT * FROM categories WHERE user_id = %s
                ORDER BY type, is_default DESC, name ASC
            """, (user_id,))
        return [dict(row) for row in cur.fetchall()]

def create_category(user_id: int, name: str, emoji: str, cat_type: str) -> Dict[str, Any]:
    """Create a new category."""
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO categories (user_id, name, emoji, type)
            VALUES (%s, %s, %s, %s)
            RETURNING *
        """, (user_id, name, emoji, cat_type))
        return dict(cur.fetchone())


# ============== Transaction Operations ==============

def add_transaction(user_id: int, amount: float, trans_type: str, 
                   category_id: int = None, description: str = None,
                   date: str = None) -> Dict[str, Any]:
    """Add a new transaction."""
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO transactions (user_id, amount, type, category_id, description, date)
            VALUES (%s, %s, %s, %s, %s, COALESCE(%s, CURRENT_DATE))
            RETURNING *
        """, (user_id, amount, trans_type, category_id, description, date))
        return dict(cur.fetchone())

def get_transactions(user_id: int, limit: int = 50, offset: int = 0,
                    trans_type: str = None, start_date: str = None,
                    end_date: str = None) -> List[Dict[str, Any]]:
    """Get transactions for a user with filters."""
    with get_db() as conn:
        cur = conn.cursor()
        
        query = """
            SELECT t.*, c.name as category_name, c.emoji as category_emoji
            FROM transactions t
            LEFT JOIN categories c ON t.category_id = c.id
            WHERE t.user_id = %s
        """
        params = [user_id]
        
        if trans_type:
            query += " AND t.type = %s"
            params.append(trans_type)
        
        if start_date:
            query += " AND t.date >= %s"
            params.append(start_date)
        
        if end_date:
            query += " AND t.date <= %s"
            params.append(end_date)
        
        query += " ORDER BY t.date DESC, t.created_at DESC LIMIT %s OFFSET %s"
        params.extend([limit, offset])
        
        cur.execute(query, params)
        return [dict(row) for row in cur.fetchall()]

def get_balance(user_id: int) -> Dict[str, float]:
    """Get user's balance summary."""
    with get_db() as conn:
        cur = conn.cursor()
        
        cur.execute("""
            SELECT 
                COALESCE(SUM(CASE WHEN type = 'income' THEN amount ELSE 0 END), 0) as total_income,
                COALESCE(SUM(CASE WHEN type = 'expense' THEN amount ELSE 0 END), 0) as total_expense
            FROM transactions
            WHERE user_id = %s
        """, (user_id,))
        
        result = cur.fetchone()
        total_income = float(result['total_income'])
        total_expense = float(result['total_expense'])
        
        return {
            'total_income': total_income,
            'total_expense': total_expense,
            'balance': total_income - total_expense
        }

def get_monthly_summary(user_id: int, year: int = None, month: int = None) -> Dict[str, Any]:
    """Get monthly summary for a user."""
    if year is None:
        year = datetime.now().year
    if month is None:
        month = datetime.now().month
    
    with get_db() as conn:
        cur = conn.cursor()
        
        # Get totals
        cur.execute("""
            SELECT 
                COALESCE(SUM(CASE WHEN type = 'income' THEN amount ELSE 0 END), 0) as income,
                COALESCE(SUM(CASE WHEN type = 'expense' THEN amount ELSE 0 END), 0) as expense
            FROM transactions
            WHERE user_id = %s 
            AND EXTRACT(YEAR FROM date) = %s
            AND EXTRACT(MONTH FROM date) = %s
        """, (user_id, year, month))
        
        totals = cur.fetchone()
        
        # Get expense breakdown by category
        cur.execute("""
            SELECT c.name, c.emoji, SUM(t.amount) as total
            FROM transactions t
            JOIN categories c ON t.category_id = c.id
            WHERE t.user_id = %s 
            AND t.type = 'expense'
            AND EXTRACT(YEAR FROM t.date) = %s
            AND EXTRACT(MONTH FROM t.date) = %s
            GROUP BY c.id, c.name, c.emoji
            ORDER BY total DESC
        """, (user_id, year, month))
        
        categories = [dict(row) for row in cur.fetchall()]
        
        return {
            'year': year,
            'month': month,
            'income': float(totals['income']),
            'expense': float(totals['expense']),
            'savings': float(totals['income']) - float(totals['expense']),
            'categories': categories
        }

def delete_transaction(transaction_id: int, user_id: int) -> bool:
    """Delete a transaction."""
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("""
            DELETE FROM transactions WHERE id = %s AND user_id = %s
        """, (transaction_id, user_id))
        return cur.rowcount > 0


# ============== Savings Goals Operations ==============

def create_savings_goal(user_id: int, name: str, target_amount: float,
                       emoji: str = '🎯', deadline: str = None) -> Dict[str, Any]:
    """Create a new savings goal."""
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO savings_goals (user_id, name, target_amount, emoji, deadline)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING *
        """, (user_id, name, target_amount, emoji, deadline))
        return dict(cur.fetchone())

def get_savings_goals(user_id: int, include_completed: bool = True) -> List[Dict[str, Any]]:
    """Get all savings goals for a user."""
    with get_db() as conn:
        cur = conn.cursor()
        
        query = "SELECT * FROM savings_goals WHERE user_id = %s"
        params = [user_id]
        
        if not include_completed:
            query += " AND is_completed = FALSE"
        
        query += " ORDER BY is_completed ASC, created_at DESC"
        
        cur.execute(query, params)
        return [dict(row) for row in cur.fetchall()]

def get_savings_goal(goal_id: int, user_id: int) -> Optional[Dict[str, Any]]:
    """Get a specific savings goal."""
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT * FROM savings_goals WHERE id = %s AND user_id = %s
        """, (goal_id, user_id))
        result = cur.fetchone()
        return dict(result) if result else None

def update_savings_goal(goal_id: int, user_id: int, **kwargs) -> Optional[Dict[str, Any]]:
    """Update a savings goal (name, target_amount, emoji, deadline)."""
    allowed_fields = ['name', 'target_amount', 'emoji', 'deadline']
    updates = {k: v for k, v in kwargs.items() if k in allowed_fields and v is not None}
    
    if not updates:
        return get_savings_goal(goal_id, user_id)
    
    with get_db() as conn:
        cur = conn.cursor()
        set_clause = ", ".join([f"{k} = %s" for k in updates.keys()])
        values = list(updates.values()) + [goal_id, user_id]
        
        cur.execute(f"""
            UPDATE savings_goals SET {set_clause}, updated_at = CURRENT_TIMESTAMP
            WHERE id = %s AND user_id = %s
            RETURNING *
        """, values)
        result = cur.fetchone()
        return dict(result) if result else None

def add_to_savings_goal(goal_id: int, user_id: int, amount: float, 
                       note: str = None) -> Optional[Dict[str, Any]]:
    """Add contribution to a savings goal."""
    with get_db() as conn:
        cur = conn.cursor()
        
        # Verify goal belongs to user
        cur.execute("""
            SELECT * FROM savings_goals WHERE id = %s AND user_id = %s
        """, (goal_id, user_id))
        goal = cur.fetchone()
        
        if not goal:
            return None
        
        # Add contribution
        cur.execute("""
            INSERT INTO savings_contributions (goal_id, amount, note)
            VALUES (%s, %s, %s)
        """, (goal_id, amount, note))
        
        # Update goal current amount
        new_amount = float(goal['current_amount']) + amount
        is_completed = new_amount >= float(goal['target_amount'])
        
        cur.execute("""
            UPDATE savings_goals 
            SET current_amount = %s, is_completed = %s, updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
            RETURNING *
        """, (new_amount, is_completed, goal_id))
        
        return dict(cur.fetchone())

def delete_savings_goal(goal_id: int, user_id: int) -> bool:
    """Delete a savings goal."""
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("""
            DELETE FROM savings_goals WHERE id = %s AND user_id = %s
        """, (goal_id, user_id))
        return cur.rowcount > 0


# ============== API Endpoints Data ==============

def get_user_dashboard(telegram_id: int) -> Dict[str, Any]:
    """Get complete dashboard data for mini app."""
    user = get_user_by_telegram_id(telegram_id)
    if not user:
        return None
    
    user_id = user['id']
    balance = get_balance(user_id)
    monthly = get_monthly_summary(user_id)
    recent_transactions = get_transactions(user_id, limit=10)
    savings_goals = get_savings_goals(user_id, include_completed=False)
    categories = get_categories(user_id)
    
    return {
        'user': user,
        'balance': balance,
        'monthly_summary': monthly,
        'recent_transactions': recent_transactions,
        'savings_goals': savings_goals,
        'categories': categories
    }

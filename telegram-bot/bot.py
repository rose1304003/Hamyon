"""
Hamyon - Telegram Bot for Personal Finance Management
Main bot file with all handlers
"""

import os
import logging
from decimal import Decimal
from datetime import datetime
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    WebAppInfo, ReplyKeyboardMarkup, KeyboardButton
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ConversationHandler, ContextTypes, filters
)

from database import (
    init_database, get_or_create_user, get_user_by_telegram_id,
    update_user_settings, get_categories, create_category,
    add_transaction, get_transactions, get_balance, get_monthly_summary,
    delete_transaction, create_savings_goal, get_savings_goals,
    get_savings_goal, update_savings_goal, add_to_savings_goal,
    delete_savings_goal, get_user_dashboard
)

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Bot token and Mini App URL
BOT_TOKEN = os.getenv("BOT_TOKEN")
MINI_APP_URL = os.getenv("MINI_APP_URL", "https://hamyon-mini-app.vercel.app")

# Conversation states
(
    ADDING_EXPENSE_AMOUNT, ADDING_EXPENSE_CATEGORY, ADDING_EXPENSE_NOTE,
    ADDING_INCOME_AMOUNT, ADDING_INCOME_CATEGORY, ADDING_INCOME_NOTE,
    CREATING_GOAL_NAME, CREATING_GOAL_AMOUNT, CREATING_GOAL_EMOJI,
    EDITING_GOAL_SELECT, EDITING_GOAL_FIELD, EDITING_GOAL_VALUE,
    ADDING_TO_GOAL_SELECT, ADDING_TO_GOAL_AMOUNT,
    SETTINGS_LANGUAGE, SETTINGS_CURRENCY
) = range(16)

# Emoji options for savings goals
GOAL_EMOJIS = ['🎯', '🏠', '🚗', '✈️', '💻', '📱', '💍', '🎓', '💪', '🎮', '🎸', '📷', '👶', '🏖️', '💰']

# Multi-language support
MESSAGES = {
    'en': {
        'welcome': "👋 Welcome to Hamyon - Your Personal Finance Manager!\n\n"
                   "I'll help you track your expenses, income, and savings goals.\n\n"
                   "Use /help to see all available commands.",
        'help': "📚 *Available Commands:*\n\n"
                "💸 /expense - Add a new expense\n"
                "💰 /income - Add new income\n"
                "📊 /balance - View your balance\n"
                "📋 /history - View recent transactions\n"
                "📈 /summary - Monthly summary\n\n"
                "🎯 *Savings Goals:*\n"
                "/newgoal - Create a new savings goal\n"
                "/goals - View all savings goals\n"
                "/editgoal - Edit a savings goal\n"
                "/addtogoal - Add money to a goal\n\n"
                "⚙️ /settings - Change language/currency\n"
                "📱 /app - Open the Mini App",
        'expense_start': "💸 *Adding new expense*\n\nEnter the amount:",
        'income_start': "💰 *Adding new income*\n\nEnter the amount:",
        'select_category': "📁 Select a category:",
        'add_note': "📝 Add a note (or /skip):",
        'transaction_saved': "✅ Transaction saved successfully!",
        'balance_header': "💰 *Your Balance*\n\n",
        'total_income': "📈 Total Income: ",
        'total_expense': "📉 Total Expenses: ",
        'current_balance': "💵 Current Balance: ",
        'no_transactions': "No transactions yet. Start by adding an /expense or /income!",
        'history_header': "📋 *Recent Transactions*\n\n",
        'goal_name_prompt': "🎯 *Creating new savings goal*\n\nWhat are you saving for?",
        'goal_amount_prompt': "💰 How much do you need to save?",
        'goal_emoji_prompt': "Choose an emoji for your goal:",
        'goal_created': "✅ Savings goal created!",
        'goals_header': "🎯 *Your Savings Goals*\n\n",
        'no_goals': "No savings goals yet. Create one with /newgoal!",
        'select_goal': "Select a goal:",
        'select_field_to_edit': "What would you like to edit?",
        'enter_new_value': "Enter the new value:",
        'goal_updated': "✅ Goal updated successfully!",
        'goal_not_found': "Goal not found.",
        'add_amount_prompt': "💰 How much are you adding?",
        'contribution_added': "✅ Added to your savings goal!",
        'settings_menu': "⚙️ *Settings*\n\nWhat would you like to change?",
        'language_changed': "✅ Language changed!",
        'currency_changed': "✅ Currency changed!",
        'invalid_amount': "❌ Please enter a valid number.",
        'cancelled': "❌ Cancelled.",
        'open_app': "📱 Open Mini App",
    },
    'ru': {
        'welcome': "👋 Добро пожаловать в Hamyon - Ваш личный финансовый менеджер!\n\n"
                   "Я помогу вам отслеживать расходы, доходы и цели накопления.\n\n"
                   "Используйте /help для просмотра всех команд.",
        'help': "📚 *Доступные команды:*\n\n"
                "💸 /expense - Добавить расход\n"
                "💰 /income - Добавить доход\n"
                "📊 /balance - Посмотреть баланс\n"
                "📋 /history - История транзакций\n"
                "📈 /summary - Месячная сводка\n\n"
                "🎯 *Цели накопления:*\n"
                "/newgoal - Создать новую цель\n"
                "/goals - Все цели накопления\n"
                "/editgoal - Редактировать цель\n"
                "/addtogoal - Добавить к цели\n\n"
                "⚙️ /settings - Настройки\n"
                "📱 /app - Открыть приложение",
        'expense_start': "💸 *Добавление расхода*\n\nВведите сумму:",
        'income_start': "💰 *Добавление дохода*\n\nВведите сумму:",
        'select_category': "📁 Выберите категорию:",
        'add_note': "📝 Добавьте заметку (или /skip):",
        'transaction_saved': "✅ Транзакция сохранена!",
        'balance_header': "💰 *Ваш баланс*\n\n",
        'total_income': "📈 Общий доход: ",
        'total_expense': "📉 Общие расходы: ",
        'current_balance': "💵 Текущий баланс: ",
        'no_transactions': "Транзакций пока нет. Начните с /expense или /income!",
        'history_header': "📋 *Последние транзакции*\n\n",
        'goal_name_prompt': "🎯 *Создание цели накопления*\n\nНа что копите?",
        'goal_amount_prompt': "💰 Сколько нужно накопить?",
        'goal_emoji_prompt': "Выберите эмодзи для цели:",
        'goal_created': "✅ Цель создана!",
        'goals_header': "🎯 *Ваши цели накопления*\n\n",
        'no_goals': "Целей пока нет. Создайте с помощью /newgoal!",
        'select_goal': "Выберите цель:",
        'select_field_to_edit': "Что хотите изменить?",
        'enter_new_value': "Введите новое значение:",
        'goal_updated': "✅ Цель обновлена!",
        'goal_not_found': "Цель не найдена.",
        'add_amount_prompt': "💰 Сколько добавляете?",
        'contribution_added': "✅ Добавлено к цели!",
        'settings_menu': "⚙️ *Настройки*\n\nЧто хотите изменить?",
        'language_changed': "✅ Язык изменён!",
        'currency_changed': "✅ Валюта изменена!",
        'invalid_amount': "❌ Введите корректное число.",
        'cancelled': "❌ Отменено.",
        'open_app': "📱 Открыть приложение",
    },
    'uz': {
        'welcome': "👋 Hamyon'ga xush kelibsiz - Shaxsiy moliyaviy menejeri!\n\n"
                   "Men sizga xarajatlar, daromadlar va jamg'arma maqsadlarini kuzatishda yordam beraman.\n\n"
                   "Barcha buyruqlarni ko'rish uchun /help dan foydalaning.",
        'help': "📚 *Mavjud buyruqlar:*\n\n"
                "💸 /expense - Xarajat qo'shish\n"
                "💰 /income - Daromad qo'shish\n"
                "📊 /balance - Balansni ko'rish\n"
                "📋 /history - Tranzaksiyalar tarixi\n"
                "📈 /summary - Oylik hisobot\n\n"
                "🎯 *Jamg'arma maqsadlari:*\n"
                "/newgoal - Yangi maqsad yaratish\n"
                "/goals - Barcha maqsadlar\n"
                "/editgoal - Maqsadni tahrirlash\n"
                "/addtogoal - Maqsadga qo'shish\n\n"
                "⚙️ /settings - Sozlamalar\n"
                "📱 /app - Ilovani ochish",
        'expense_start': "💸 *Xarajat qo'shish*\n\nSummani kiriting:",
        'income_start': "💰 *Daromad qo'shish*\n\nSummani kiriting:",
        'select_category': "📁 Kategoriyani tanlang:",
        'add_note': "📝 Izoh qo'shing (yoki /skip):",
        'transaction_saved': "✅ Tranzaksiya saqlandi!",
        'balance_header': "💰 *Sizning balans*\n\n",
        'total_income': "📈 Jami daromad: ",
        'total_expense': "📉 Jami xarajatlar: ",
        'current_balance': "💵 Joriy balans: ",
        'no_transactions': "Hali tranzaksiyalar yo'q. /expense yoki /income bilan boshlang!",
        'history_header': "📋 *So'nggi tranzaksiyalar*\n\n",
        'goal_name_prompt': "🎯 *Yangi jamg'arma maqsadi*\n\nNima uchun yig'yapsiz?",
        'goal_amount_prompt': "💰 Qancha yig'ish kerak?",
        'goal_emoji_prompt': "Maqsad uchun emoji tanlang:",
        'goal_created': "✅ Maqsad yaratildi!",
        'goals_header': "🎯 *Sizning jamg'arma maqsadlaringiz*\n\n",
        'no_goals': "Hali maqsadlar yo'q. /newgoal bilan yarating!",
        'select_goal': "Maqsadni tanlang:",
        'select_field_to_edit': "Nimani o'zgartirmoqchisiz?",
        'enter_new_value': "Yangi qiymatni kiriting:",
        'goal_updated': "✅ Maqsad yangilandi!",
        'goal_not_found': "Maqsad topilmadi.",
        'add_amount_prompt': "💰 Qancha qo'shyapsiz?",
        'contribution_added': "✅ Maqsadga qo'shildi!",
        'settings_menu': "⚙️ *Sozlamalar*\n\nNimani o'zgartirmoqchisiz?",
        'language_changed': "✅ Til o'zgartirildi!",
        'currency_changed': "✅ Valyuta o'zgartirildi!",
        'invalid_amount': "❌ To'g'ri raqam kiriting.",
        'cancelled': "❌ Bekor qilindi.",
        'open_app': "📱 Ilovani ochish",
    }
}


def get_msg(lang: str, key: str) -> str:
    """Get message in specified language."""
    return MESSAGES.get(lang, MESSAGES['en']).get(key, MESSAGES['en'].get(key, key))


def get_user_lang(context: ContextTypes.DEFAULT_TYPE) -> str:
    """Get user's language from context."""
    return context.user_data.get('language', 'en')


def format_currency(amount: float, currency: str = 'UZS') -> str:
    """Format amount with currency."""
    if currency == 'UZS':
        return f"{amount:,.0f} so'm"
    elif currency == 'USD':
        return f"${amount:,.2f}"
    elif currency == 'RUB':
        return f"{amount:,.0f} ₽"
    return f"{amount:,.2f} {currency}"


# ============== Command Handlers ==============

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command handler."""
    user = update.effective_user
    
    # Get or create user in database
    db_user = get_or_create_user(
        telegram_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
        language_code=user.language_code or 'en'
    )
    
    # Store language in context
    lang = db_user.get('language_code', 'en')
    if lang not in ['en', 'ru', 'uz']:
        lang = 'en'
    context.user_data['language'] = lang
    context.user_data['currency'] = db_user.get('currency', 'UZS')
    context.user_data['user_id'] = db_user['id']
    
    # Create keyboard with Mini App button
    keyboard = [
        [KeyboardButton(
            text=get_msg(lang, 'open_app'),
            web_app=WebAppInfo(url=f"{MINI_APP_URL}?telegram_id={user.id}")
        )]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        get_msg(lang, 'welcome'),
        reply_markup=reply_markup
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Help command handler."""
    lang = get_user_lang(context)
    await update.message.reply_text(
        get_msg(lang, 'help'),
        parse_mode='Markdown'
    )


async def app_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Open Mini App command."""
    user = update.effective_user
    lang = get_user_lang(context)
    
    keyboard = [[InlineKeyboardButton(
        text=get_msg(lang, 'open_app'),
        web_app=WebAppInfo(url=f"{MINI_APP_URL}?telegram_id={user.id}")
    )]]
    
    await update.message.reply_text(
        "📱 Click the button below to open the Mini App:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ============== Balance & History ==============

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user balance."""
    lang = get_user_lang(context)
    currency = context.user_data.get('currency', 'UZS')
    user_id = context.user_data.get('user_id')
    
    if not user_id:
        user = get_user_by_telegram_id(update.effective_user.id)
        if not user:
            await update.message.reply_text(get_msg(lang, 'no_transactions'))
            return
        user_id = user['id']
    
    bal = get_balance(user_id)
    
    text = get_msg(lang, 'balance_header')
    text += f"{get_msg(lang, 'total_income')}{format_currency(bal['total_income'], currency)}\n"
    text += f"{get_msg(lang, 'total_expense')}{format_currency(bal['total_expense'], currency)}\n"
    text += f"{'─' * 20}\n"
    text += f"{get_msg(lang, 'current_balance')}{format_currency(bal['balance'], currency)}"
    
    await update.message.reply_text(text, parse_mode='Markdown')


async def history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show transaction history."""
    lang = get_user_lang(context)
    currency = context.user_data.get('currency', 'UZS')
    user_id = context.user_data.get('user_id')
    
    if not user_id:
        user = get_user_by_telegram_id(update.effective_user.id)
        if not user:
            await update.message.reply_text(get_msg(lang, 'no_transactions'))
            return
        user_id = user['id']
    
    transactions = get_transactions(user_id, limit=10)
    
    if not transactions:
        await update.message.reply_text(get_msg(lang, 'no_transactions'))
        return
    
    text = get_msg(lang, 'history_header')
    
    for t in transactions:
        emoji = t.get('category_emoji', '📦')
        sign = '+' if t['type'] == 'income' else '-'
        amount = format_currency(float(t['amount']), currency)
        date = t['date'].strftime('%d.%m') if hasattr(t['date'], 'strftime') else str(t['date'])[:5]
        desc = t.get('description', '') or t.get('category_name', '')
        
        text += f"{emoji} {sign}{amount} • {date}\n"
        if desc:
            text += f"   _{desc}_\n"
    
    await update.message.reply_text(text, parse_mode='Markdown')


async def summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show monthly summary."""
    lang = get_user_lang(context)
    currency = context.user_data.get('currency', 'UZS')
    user_id = context.user_data.get('user_id')
    
    if not user_id:
        user = get_user_by_telegram_id(update.effective_user.id)
        if not user:
            await update.message.reply_text(get_msg(lang, 'no_transactions'))
            return
        user_id = user['id']
    
    data = get_monthly_summary(user_id)
    
    month_names = {
        'en': ['January', 'February', 'March', 'April', 'May', 'June',
               'July', 'August', 'September', 'October', 'November', 'December'],
        'ru': ['Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь',
               'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь'],
        'uz': ['Yanvar', 'Fevral', 'Mart', 'Aprel', 'May', 'Iyun',
               'Iyul', 'Avgust', 'Sentabr', 'Oktabr', 'Noyabr', 'Dekabr']
    }
    
    month_name = month_names.get(lang, month_names['en'])[data['month'] - 1]
    
    text = f"📈 *{month_name} {data['year']}*\n\n"
    text += f"💰 Income: {format_currency(data['income'], currency)}\n"
    text += f"💸 Expenses: {format_currency(data['expense'], currency)}\n"
    text += f"💵 Savings: {format_currency(data['savings'], currency)}\n"
    
    if data['categories']:
        text += f"\n📊 *Expenses by Category:*\n"
        for cat in data['categories'][:5]:
            text += f"{cat['emoji']} {cat['name']}: {format_currency(float(cat['total']), currency)}\n"
    
    await update.message.reply_text(text, parse_mode='Markdown')


# ============== Expense Conversation ==============

async def expense_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start expense conversation."""
    lang = get_user_lang(context)
    await update.message.reply_text(
        get_msg(lang, 'expense_start'),
        parse_mode='Markdown'
    )
    return ADDING_EXPENSE_AMOUNT


async def expense_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle expense amount input."""
    lang = get_user_lang(context)
    
    try:
        amount = float(update.message.text.replace(',', '.').replace(' ', ''))
        if amount <= 0:
            raise ValueError()
        context.user_data['temp_amount'] = amount
    except ValueError:
        await update.message.reply_text(get_msg(lang, 'invalid_amount'))
        return ADDING_EXPENSE_AMOUNT
    
    # Get expense categories
    user_id = context.user_data.get('user_id')
    if not user_id:
        user = get_user_by_telegram_id(update.effective_user.id)
        user_id = user['id']
        context.user_data['user_id'] = user_id
    
    categories = get_categories(user_id, 'expense')
    
    # Create category keyboard
    keyboard = []
    row = []
    for cat in categories:
        row.append(InlineKeyboardButton(
            f"{cat['emoji']} {cat['name']}",
            callback_data=f"exp_cat_{cat['id']}"
        ))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    
    keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data="cancel")])
    
    await update.message.reply_text(
        get_msg(lang, 'select_category'),
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return ADDING_EXPENSE_CATEGORY


async def expense_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle expense category selection."""
    query = update.callback_query
    await query.answer()
    
    if query.data == "cancel":
        lang = get_user_lang(context)
        await query.edit_message_text(get_msg(lang, 'cancelled'))
        return ConversationHandler.END
    
    category_id = int(query.data.replace("exp_cat_", ""))
    context.user_data['temp_category'] = category_id
    
    lang = get_user_lang(context)
    await query.edit_message_text(get_msg(lang, 'add_note'))
    return ADDING_EXPENSE_NOTE


async def expense_note(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle expense note and save transaction."""
    lang = get_user_lang(context)
    
    note = None if update.message.text == '/skip' else update.message.text
    
    user_id = context.user_data.get('user_id')
    amount = context.user_data.get('temp_amount')
    category_id = context.user_data.get('temp_category')
    
    add_transaction(
        user_id=user_id,
        amount=amount,
        trans_type='expense',
        category_id=category_id,
        description=note
    )
    
    # Clean up temp data
    context.user_data.pop('temp_amount', None)
    context.user_data.pop('temp_category', None)
    
    await update.message.reply_text(get_msg(lang, 'transaction_saved'))
    return ConversationHandler.END


# ============== Income Conversation ==============

async def income_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start income conversation."""
    lang = get_user_lang(context)
    await update.message.reply_text(
        get_msg(lang, 'income_start'),
        parse_mode='Markdown'
    )
    return ADDING_INCOME_AMOUNT


async def income_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle income amount input."""
    lang = get_user_lang(context)
    
    try:
        amount = float(update.message.text.replace(',', '.').replace(' ', ''))
        if amount <= 0:
            raise ValueError()
        context.user_data['temp_amount'] = amount
    except ValueError:
        await update.message.reply_text(get_msg(lang, 'invalid_amount'))
        return ADDING_INCOME_AMOUNT
    
    # Get income categories
    user_id = context.user_data.get('user_id')
    if not user_id:
        user = get_user_by_telegram_id(update.effective_user.id)
        user_id = user['id']
        context.user_data['user_id'] = user_id
    
    categories = get_categories(user_id, 'income')
    
    # Create category keyboard
    keyboard = []
    row = []
    for cat in categories:
        row.append(InlineKeyboardButton(
            f"{cat['emoji']} {cat['name']}",
            callback_data=f"inc_cat_{cat['id']}"
        ))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    
    keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data="cancel")])
    
    await update.message.reply_text(
        get_msg(lang, 'select_category'),
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return ADDING_INCOME_CATEGORY


async def income_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle income category selection."""
    query = update.callback_query
    await query.answer()
    
    if query.data == "cancel":
        lang = get_user_lang(context)
        await query.edit_message_text(get_msg(lang, 'cancelled'))
        return ConversationHandler.END
    
    category_id = int(query.data.replace("inc_cat_", ""))
    context.user_data['temp_category'] = category_id
    
    lang = get_user_lang(context)
    await query.edit_message_text(get_msg(lang, 'add_note'))
    return ADDING_INCOME_NOTE


async def income_note(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle income note and save transaction."""
    lang = get_user_lang(context)
    
    note = None if update.message.text == '/skip' else update.message.text
    
    user_id = context.user_data.get('user_id')
    amount = context.user_data.get('temp_amount')
    category_id = context.user_data.get('temp_category')
    
    add_transaction(
        user_id=user_id,
        amount=amount,
        trans_type='income',
        category_id=category_id,
        description=note
    )
    
    # Clean up temp data
    context.user_data.pop('temp_amount', None)
    context.user_data.pop('temp_category', None)
    
    await update.message.reply_text(get_msg(lang, 'transaction_saved'))
    return ConversationHandler.END


# ============== Savings Goals ==============

async def goals_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show all savings goals."""
    lang = get_user_lang(context)
    currency = context.user_data.get('currency', 'UZS')
    user_id = context.user_data.get('user_id')
    
    if not user_id:
        user = get_user_by_telegram_id(update.effective_user.id)
        if not user:
            await update.message.reply_text(get_msg(lang, 'no_goals'))
            return
        user_id = user['id']
    
    goals = get_savings_goals(user_id)
    
    if not goals:
        await update.message.reply_text(get_msg(lang, 'no_goals'))
        return
    
    text = get_msg(lang, 'goals_header')
    
    for goal in goals:
        current = float(goal['current_amount'])
        target = float(goal['target_amount'])
        progress = min(100, int((current / target) * 100)) if target > 0 else 0
        
        # Progress bar
        filled = int(progress / 10)
        bar = '▓' * filled + '░' * (10 - filled)
        
        status = "✅" if goal['is_completed'] else goal['emoji']
        
        text += f"{status} *{goal['name']}*\n"
        text += f"   {bar} {progress}%\n"
        text += f"   {format_currency(current, currency)} / {format_currency(target, currency)}\n\n"
    
    await update.message.reply_text(text, parse_mode='Markdown')


async def new_goal_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start creating new savings goal."""
    lang = get_user_lang(context)
    await update.message.reply_text(
        get_msg(lang, 'goal_name_prompt'),
        parse_mode='Markdown'
    )
    return CREATING_GOAL_NAME


async def new_goal_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle goal name input."""
    context.user_data['temp_goal_name'] = update.message.text
    lang = get_user_lang(context)
    await update.message.reply_text(get_msg(lang, 'goal_amount_prompt'))
    return CREATING_GOAL_AMOUNT


async def new_goal_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle goal amount input."""
    lang = get_user_lang(context)
    
    try:
        amount = float(update.message.text.replace(',', '.').replace(' ', ''))
        if amount <= 0:
            raise ValueError()
        context.user_data['temp_goal_amount'] = amount
    except ValueError:
        await update.message.reply_text(get_msg(lang, 'invalid_amount'))
        return CREATING_GOAL_AMOUNT
    
    # Emoji selection keyboard
    keyboard = []
    row = []
    for emoji in GOAL_EMOJIS:
        row.append(InlineKeyboardButton(emoji, callback_data=f"goal_emoji_{emoji}"))
        if len(row) == 5:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    
    await update.message.reply_text(
        get_msg(lang, 'goal_emoji_prompt'),
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return CREATING_GOAL_EMOJI


async def new_goal_emoji(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle goal emoji selection and create goal."""
    query = update.callback_query
    await query.answer()
    
    emoji = query.data.replace("goal_emoji_", "")
    lang = get_user_lang(context)
    
    user_id = context.user_data.get('user_id')
    if not user_id:
        user = get_user_by_telegram_id(query.from_user.id)
        user_id = user['id']
    
    goal = create_savings_goal(
        user_id=user_id,
        name=context.user_data.get('temp_goal_name'),
        target_amount=context.user_data.get('temp_goal_amount'),
        emoji=emoji
    )
    
    # Clean up
    context.user_data.pop('temp_goal_name', None)
    context.user_data.pop('temp_goal_amount', None)
    
    currency = context.user_data.get('currency', 'UZS')
    await query.edit_message_text(
        f"{get_msg(lang, 'goal_created')}\n\n"
        f"{emoji} *{goal['name']}*\n"
        f"Target: {format_currency(float(goal['target_amount']), currency)}",
        parse_mode='Markdown'
    )
    return ConversationHandler.END


# ============== Edit Goal Conversation ==============

async def edit_goal_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start editing a savings goal."""
    lang = get_user_lang(context)
    user_id = context.user_data.get('user_id')
    
    if not user_id:
        user = get_user_by_telegram_id(update.effective_user.id)
        if not user:
            await update.message.reply_text(get_msg(lang, 'no_goals'))
            return ConversationHandler.END
        user_id = user['id']
    
    goals = get_savings_goals(user_id, include_completed=False)
    
    if not goals:
        await update.message.reply_text(get_msg(lang, 'no_goals'))
        return ConversationHandler.END
    
    keyboard = []
    for goal in goals:
        keyboard.append([InlineKeyboardButton(
            f"{goal['emoji']} {goal['name']}",
            callback_data=f"edit_goal_{goal['id']}"
        )])
    keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data="cancel")])
    
    await update.message.reply_text(
        get_msg(lang, 'select_goal'),
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return EDITING_GOAL_SELECT


async def edit_goal_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle goal selection for editing."""
    query = update.callback_query
    await query.answer()
    
    if query.data == "cancel":
        lang = get_user_lang(context)
        await query.edit_message_text(get_msg(lang, 'cancelled'))
        return ConversationHandler.END
    
    goal_id = int(query.data.replace("edit_goal_", ""))
    context.user_data['editing_goal_id'] = goal_id
    
    lang = get_user_lang(context)
    
    # Field selection
    keyboard = [
        [InlineKeyboardButton("📝 Name", callback_data="edit_field_name")],
        [InlineKeyboardButton("💰 Target Amount", callback_data="edit_field_target")],
        [InlineKeyboardButton("😊 Emoji", callback_data="edit_field_emoji")],
        [InlineKeyboardButton("❌ Cancel", callback_data="cancel")]
    ]
    
    await query.edit_message_text(
        get_msg(lang, 'select_field_to_edit'),
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return EDITING_GOAL_FIELD


async def edit_goal_field(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle field selection for editing."""
    query = update.callback_query
    await query.answer()
    
    if query.data == "cancel":
        lang = get_user_lang(context)
        await query.edit_message_text(get_msg(lang, 'cancelled'))
        return ConversationHandler.END
    
    field = query.data.replace("edit_field_", "")
    context.user_data['editing_field'] = field
    
    lang = get_user_lang(context)
    
    if field == "emoji":
        # Show emoji keyboard
        keyboard = []
        row = []
        for emoji in GOAL_EMOJIS:
            row.append(InlineKeyboardButton(emoji, callback_data=f"new_emoji_{emoji}"))
            if len(row) == 5:
                keyboard.append(row)
                row = []
        if row:
            keyboard.append(row)
        
        await query.edit_message_text(
            get_msg(lang, 'goal_emoji_prompt'),
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return EDITING_GOAL_VALUE
    
    await query.edit_message_text(get_msg(lang, 'enter_new_value'))
    return EDITING_GOAL_VALUE


async def edit_goal_value(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle new value input for editing."""
    lang = get_user_lang(context)
    goal_id = context.user_data.get('editing_goal_id')
    field = context.user_data.get('editing_field')
    user_id = context.user_data.get('user_id')
    
    if not user_id:
        user = get_user_by_telegram_id(update.effective_user.id)
        user_id = user['id']
    
    # Handle callback query (emoji selection)
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        new_value = query.data.replace("new_emoji_", "")
        
        update_savings_goal(goal_id, user_id, emoji=new_value)
        
        await query.edit_message_text(get_msg(lang, 'goal_updated'))
    else:
        # Handle text input
        new_value = update.message.text
        
        if field == "target":
            try:
                new_value = float(new_value.replace(',', '.').replace(' ', ''))
                if new_value <= 0:
                    raise ValueError()
                update_savings_goal(goal_id, user_id, target_amount=new_value)
            except ValueError:
                await update.message.reply_text(get_msg(lang, 'invalid_amount'))
                return EDITING_GOAL_VALUE
        else:  # name
            update_savings_goal(goal_id, user_id, name=new_value)
        
        await update.message.reply_text(get_msg(lang, 'goal_updated'))
    
    # Clean up
    context.user_data.pop('editing_goal_id', None)
    context.user_data.pop('editing_field', None)
    
    return ConversationHandler.END


# ============== Add to Goal Conversation ==============

async def add_to_goal_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start adding to a savings goal."""
    lang = get_user_lang(context)
    user_id = context.user_data.get('user_id')
    
    if not user_id:
        user = get_user_by_telegram_id(update.effective_user.id)
        if not user:
            await update.message.reply_text(get_msg(lang, 'no_goals'))
            return ConversationHandler.END
        user_id = user['id']
    
    goals = get_savings_goals(user_id, include_completed=False)
    
    if not goals:
        await update.message.reply_text(get_msg(lang, 'no_goals'))
        return ConversationHandler.END
    
    currency = context.user_data.get('currency', 'UZS')
    keyboard = []
    for goal in goals:
        current = float(goal['current_amount'])
        target = float(goal['target_amount'])
        progress = min(100, int((current / target) * 100)) if target > 0 else 0
        
        keyboard.append([InlineKeyboardButton(
            f"{goal['emoji']} {goal['name']} ({progress}%)",
            callback_data=f"add_goal_{goal['id']}"
        )])
    keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data="cancel")])
    
    await update.message.reply_text(
        get_msg(lang, 'select_goal'),
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return ADDING_TO_GOAL_SELECT


async def add_to_goal_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle goal selection for adding contribution."""
    query = update.callback_query
    await query.answer()
    
    if query.data == "cancel":
        lang = get_user_lang(context)
        await query.edit_message_text(get_msg(lang, 'cancelled'))
        return ConversationHandler.END
    
    goal_id = int(query.data.replace("add_goal_", ""))
    context.user_data['adding_to_goal_id'] = goal_id
    
    lang = get_user_lang(context)
    await query.edit_message_text(get_msg(lang, 'add_amount_prompt'))
    return ADDING_TO_GOAL_AMOUNT


async def add_to_goal_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle contribution amount and add to goal."""
    lang = get_user_lang(context)
    
    try:
        amount = float(update.message.text.replace(',', '.').replace(' ', ''))
        if amount <= 0:
            raise ValueError()
    except ValueError:
        await update.message.reply_text(get_msg(lang, 'invalid_amount'))
        return ADDING_TO_GOAL_AMOUNT
    
    goal_id = context.user_data.get('adding_to_goal_id')
    user_id = context.user_data.get('user_id')
    
    if not user_id:
        user = get_user_by_telegram_id(update.effective_user.id)
        user_id = user['id']
    
    goal = add_to_savings_goal(goal_id, user_id, amount)
    
    if not goal:
        await update.message.reply_text(get_msg(lang, 'goal_not_found'))
        return ConversationHandler.END
    
    currency = context.user_data.get('currency', 'UZS')
    current = float(goal['current_amount'])
    target = float(goal['target_amount'])
    progress = min(100, int((current / target) * 100)) if target > 0 else 0
    
    text = f"{get_msg(lang, 'contribution_added')}\n\n"
    text += f"{goal['emoji']} *{goal['name']}*\n"
    text += f"Progress: {progress}%\n"
    text += f"{format_currency(current, currency)} / {format_currency(target, currency)}"
    
    if goal['is_completed']:
        text += "\n\n🎉 *Congratulations! Goal completed!*"
    
    # Clean up
    context.user_data.pop('adding_to_goal_id', None)
    
    await update.message.reply_text(text, parse_mode='Markdown')
    return ConversationHandler.END


# ============== Settings ==============

async def settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show settings menu."""
    lang = get_user_lang(context)
    
    keyboard = [
        [InlineKeyboardButton("🌐 Language", callback_data="settings_lang")],
        [InlineKeyboardButton("💱 Currency", callback_data="settings_currency")],
        [InlineKeyboardButton("❌ Close", callback_data="settings_close")]
    ]
    
    await update.message.reply_text(
        get_msg(lang, 'settings_menu'),
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def settings_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle settings callback."""
    query = update.callback_query
    await query.answer()
    
    if query.data == "settings_close":
        await query.delete_message()
        return
    
    if query.data == "settings_lang":
        keyboard = [
            [InlineKeyboardButton("🇬🇧 English", callback_data="set_lang_en")],
            [InlineKeyboardButton("🇷🇺 Русский", callback_data="set_lang_ru")],
            [InlineKeyboardButton("🇺🇿 O'zbek", callback_data="set_lang_uz")],
            [InlineKeyboardButton("⬅️ Back", callback_data="settings_back")]
        ]
        await query.edit_message_text(
            "🌐 Select language:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    elif query.data == "settings_currency":
        keyboard = [
            [InlineKeyboardButton("🇺🇿 UZS (so'm)", callback_data="set_cur_UZS")],
            [InlineKeyboardButton("🇺🇸 USD ($)", callback_data="set_cur_USD")],
            [InlineKeyboardButton("🇷🇺 RUB (₽)", callback_data="set_cur_RUB")],
            [InlineKeyboardButton("⬅️ Back", callback_data="settings_back")]
        ]
        await query.edit_message_text(
            "💱 Select currency:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    elif query.data.startswith("set_lang_"):
        lang = query.data.replace("set_lang_", "")
        context.user_data['language'] = lang
        update_user_settings(query.from_user.id, language_code=lang)
        await query.edit_message_text(get_msg(lang, 'language_changed'))
    
    elif query.data.startswith("set_cur_"):
        currency = query.data.replace("set_cur_", "")
        context.user_data['currency'] = currency
        update_user_settings(query.from_user.id, currency=currency)
        lang = get_user_lang(context)
        await query.edit_message_text(get_msg(lang, 'currency_changed'))
    
    elif query.data == "settings_back":
        lang = get_user_lang(context)
        keyboard = [
            [InlineKeyboardButton("🌐 Language", callback_data="settings_lang")],
            [InlineKeyboardButton("💱 Currency", callback_data="settings_currency")],
            [InlineKeyboardButton("❌ Close", callback_data="settings_close")]
        ]
        await query.edit_message_text(
            get_msg(lang, 'settings_menu'),
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel current conversation."""
    lang = get_user_lang(context)
    await update.message.reply_text(get_msg(lang, 'cancelled'))
    return ConversationHandler.END


def main():
    """Start the bot."""
    # Initialize database
    init_database()
    
    # Create application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Basic commands
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("app", app_command))
    application.add_handler(CommandHandler("balance", balance))
    application.add_handler(CommandHandler("history", history))
    application.add_handler(CommandHandler("summary", summary))
    application.add_handler(CommandHandler("goals", goals_list))
    application.add_handler(CommandHandler("settings", settings))
    
    # Settings callback handler
    application.add_handler(CallbackQueryHandler(
        settings_callback, 
        pattern="^(settings_|set_lang_|set_cur_)"
    ))
    
    # Expense conversation
    expense_conv = ConversationHandler(
        entry_points=[CommandHandler("expense", expense_start)],
        states={
            ADDING_EXPENSE_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, expense_amount)],
            ADDING_EXPENSE_CATEGORY: [CallbackQueryHandler(expense_category)],
            ADDING_EXPENSE_NOTE: [MessageHandler(filters.TEXT, expense_note)],
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    application.add_handler(expense_conv)
    
    # Income conversation
    income_conv = ConversationHandler(
        entry_points=[CommandHandler("income", income_start)],
        states={
            ADDING_INCOME_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, income_amount)],
            ADDING_INCOME_CATEGORY: [CallbackQueryHandler(income_category)],
            ADDING_INCOME_NOTE: [MessageHandler(filters.TEXT, income_note)],
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    application.add_handler(income_conv)
    
    # New goal conversation
    new_goal_conv = ConversationHandler(
        entry_points=[CommandHandler("newgoal", new_goal_start)],
        states={
            CREATING_GOAL_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, new_goal_name)],
            CREATING_GOAL_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, new_goal_amount)],
            CREATING_GOAL_EMOJI: [CallbackQueryHandler(new_goal_emoji, pattern="^goal_emoji_")],
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    application.add_handler(new_goal_conv)
    
    # Edit goal conversation
    edit_goal_conv = ConversationHandler(
        entry_points=[CommandHandler("editgoal", edit_goal_start)],
        states={
            EDITING_GOAL_SELECT: [CallbackQueryHandler(edit_goal_select)],
            EDITING_GOAL_FIELD: [CallbackQueryHandler(edit_goal_field)],
            EDITING_GOAL_VALUE: [
                CallbackQueryHandler(edit_goal_value, pattern="^new_emoji_"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, edit_goal_value)
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    application.add_handler(edit_goal_conv)
    
    # Add to goal conversation
    add_goal_conv = ConversationHandler(
        entry_points=[CommandHandler("addtogoal", add_to_goal_start)],
        states={
            ADDING_TO_GOAL_SELECT: [CallbackQueryHandler(add_to_goal_select)],
            ADDING_TO_GOAL_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_to_goal_amount)],
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    application.add_handler(add_goal_conv)
    
    # Start the bot
    logger.info("Starting Hamyon bot...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()

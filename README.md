# Hamyon - Personal Finance Manager

A complete Telegram Mini App for personal finance management with bot integration.

## 🌟 Features

- **💰 Expense Tracking** - Track your daily expenses with categories
- **💵 Income Management** - Record all sources of income
- **🎯 Savings Goals** - Create, edit, and track savings goals
- **📊 Dashboard** - Visual overview of your finances
- **🌐 Multi-language** - Support for English, Russian, and Uzbek
- **💱 Multi-currency** - UZS, USD, RUB support
- **📱 Telegram Integration** - Seamless Mini App experience

## 📁 Project Structure

```
hamyon-project/
├── telegram-bot/          # Python Backend (Railway)
│   ├── bot.py            # Telegram bot handlers
│   ├── api.py            # REST API for Mini App
│   ├── database.py       # PostgreSQL operations
│   ├── main.py           # Entry point
│   ├── requirements.txt  # Python dependencies
│   ├── Procfile          # Railway process file
│   └── railway.json      # Railway configuration
│
├── mini-app/              # React Frontend (Vercel)
│   ├── src/
│   │   ├── components/   # React components
│   │   ├── hooks/        # Custom React hooks
│   │   ├── services/     # API service
│   │   ├── types/        # TypeScript types
│   │   └── styles/       # CSS styles
│   ├── public/
│   │   ├── icons/        # PWA icons (192x192, 512x512)
│   │   └── manifest.json # PWA manifest
│   ├── package.json
│   ├── vite.config.ts
│   └── vercel.json
│
└── docs/                  # Documentation
```

## 🚀 Deployment Guide

### Prerequisites

1. Telegram Bot Token from [@BotFather](https://t.me/BotFather)
2. [Railway](https://railway.app) account
3. [Vercel](https://vercel.com) account
4. [GitHub](https://github.com) account

### Step 1: Create Telegram Bot

1. Open [@BotFather](https://t.me/BotFather) in Telegram
2. Send `/newbot` and follow instructions
3. Save the bot token
4. Enable Mini App:
   - Send `/mybots`
   - Select your bot → Bot Settings → Menu Button
   - Set menu button URL to your Vercel deployment URL

### Step 2: Deploy Backend to Railway

1. **Create GitHub Repository**
   ```bash
   cd telegram-bot
   git init
   git add .
   git commit -m "Initial commit"
   git remote add origin https://github.com/YOUR_USERNAME/hamyon-bot.git
   git push -u origin main
   ```

2. **Setup Railway**
   - Go to [Railway](https://railway.app)
   - Create new project → Deploy from GitHub repo
   - Add PostgreSQL database:
     - Click "New" → "Database" → "PostgreSQL"
   - Set environment variables in Settings:
     ```
     BOT_TOKEN=your_telegram_bot_token
     MINI_APP_URL=https://your-app.vercel.app
     RUN_MODE=both
     ```
   - Railway will automatically set `DATABASE_URL`

3. **Get Railway URL**
   - Go to Settings → Domains
   - Copy your Railway URL (e.g., `https://hamyon-bot-production.up.railway.app`)

### Step 3: Deploy Frontend to Vercel

1. **Create GitHub Repository**
   ```bash
   cd mini-app
   git init
   git add .
   git commit -m "Initial commit"
   git remote add origin https://github.com/YOUR_USERNAME/hamyon-mini-app.git
   git push -u origin main
   ```

2. **Setup Vercel**
   - Go to [Vercel](https://vercel.com)
   - Import your GitHub repository
   - Set environment variable:
     ```
     VITE_API_URL=https://your-railway-app.up.railway.app
     ```
   - Deploy!

3. **Update Railway with Vercel URL**
   - Go back to Railway
   - Update `MINI_APP_URL` with your Vercel deployment URL

### Step 4: Configure Telegram Mini App

1. Open [@BotFather](https://t.me/BotFather)
2. Send `/mybots` → Select your bot
3. **Bot Settings** → **Menu Button**:
   - Set URL: `https://your-app.vercel.app`
   - Set Title: "Open Hamyon"

4. **Bot Settings** → **Configure Mini App**:
   - Set URL: `https://your-app.vercel.app`

## 🤖 Bot Commands

| Command | Description |
|---------|-------------|
| `/start` | Start the bot |
| `/help` | Show all commands |
| `/expense` | Add new expense |
| `/income` | Add new income |
| `/balance` | View your balance |
| `/history` | Transaction history |
| `/summary` | Monthly summary |
| `/newgoal` | Create savings goal |
| `/goals` | View all goals |
| `/editgoal` | Edit a savings goal |
| `/addtogoal` | Add money to goal |
| `/settings` | Change language/currency |
| `/app` | Open Mini App |

## 🔧 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| GET | `/api/dashboard` | Full dashboard data |
| GET | `/api/balance` | User balance |
| GET | `/api/summary` | Monthly summary |
| GET | `/api/transactions` | List transactions |
| POST | `/api/transactions` | Create transaction |
| DELETE | `/api/transactions/:id` | Delete transaction |
| GET | `/api/categories` | List categories |
| GET | `/api/goals` | List savings goals |
| POST | `/api/goals` | Create goal |
| PUT | `/api/goals/:id` | Update goal |
| POST | `/api/goals/:id/contribute` | Add to goal |
| DELETE | `/api/goals/:id` | Delete goal |

## 🎨 Customization

### Adding New Categories

Edit `database.py` and modify the `create_default_categories` function.

### Changing Theme Colors

Edit `mini-app/tailwind.config.js` to customize colors.

### Adding New Languages

1. Add translations to `bot.py` in the `MESSAGES` dictionary
2. Add language option in settings handler

## 📝 Database Schema

```sql
-- Users
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    telegram_id BIGINT UNIQUE NOT NULL,
    username VARCHAR(255),
    first_name VARCHAR(255),
    last_name VARCHAR(255),
    language_code VARCHAR(10) DEFAULT 'en',
    currency VARCHAR(10) DEFAULT 'UZS'
);

-- Categories
CREATE TABLE categories (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    name VARCHAR(100) NOT NULL,
    emoji VARCHAR(10),
    type VARCHAR(20) -- 'income' or 'expense'
);

-- Transactions
CREATE TABLE transactions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    category_id INTEGER REFERENCES categories(id),
    amount DECIMAL(15, 2) NOT NULL,
    type VARCHAR(20) NOT NULL,
    description TEXT,
    date DATE DEFAULT CURRENT_DATE
);

-- Savings Goals
CREATE TABLE savings_goals (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    name VARCHAR(255) NOT NULL,
    target_amount DECIMAL(15, 2) NOT NULL,
    current_amount DECIMAL(15, 2) DEFAULT 0,
    emoji VARCHAR(10) DEFAULT '🎯',
    is_completed BOOLEAN DEFAULT FALSE
);
```

## 🔒 Security Notes

- Bot token should never be exposed in frontend code
- Use Telegram's initData validation for authentication
- All API endpoints require authentication

## 📱 PWA Features

The Mini App includes PWA support:
- Icons: 192x192 and 512x512
- Manifest for installability
- Optimized for mobile devices

## 🐛 Troubleshooting

### Bot not responding
- Check Railway logs for errors
- Verify `BOT_TOKEN` is correct
- Ensure database connection is working

### Mini App not loading
- Check CORS settings in API
- Verify `VITE_API_URL` is correct
- Check browser console for errors

### Database errors
- Tables are created automatically on startup
- Check `DATABASE_URL` format

## 📄 License

MIT License - Feel free to use and modify!

---

Built with ❤️ for Uzbekistan 🇺🇿

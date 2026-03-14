-- Migration: Add user preferences tables for multi-coin trading
-- Version: 001
-- Created: 2026-03-03
-- Description: Creates tables for user preferences, coin preferences, and portfolio tracking

-- User preferences table
-- Stores global trading preferences and default strategy
CREATE TABLE IF NOT EXISTS user_preferences (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    default_strategy TEXT NOT NULL DEFAULT 'balanced',
    auto_trade INTEGER NOT NULL DEFAULT 1,  -- SQLite uses INTEGER for boolean (1=true, 0=false)
    daily_trading_limit_krw REAL NOT NULL DEFAULT 100000.0,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Coin preferences table
-- Stores per-coin configuration including allocation percentage and strategy
CREATE TABLE IF NOT EXISTS coin_preferences (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    coin TEXT NOT NULL,  -- Cryptocurrency enum value (BTC, ETH, SOL, XRP, ADA)
    enabled INTEGER NOT NULL DEFAULT 1,  -- SQLite uses INTEGER for boolean
    percentage REAL NOT NULL DEFAULT 20.0,  -- Portfolio allocation (0-100)
    strategy TEXT NOT NULL DEFAULT 'balanced',  -- TradingStrategy enum value
    UNIQUE(coin)  -- One preference per coin
);

-- Portfolio tracking table
-- Stores current portfolio state per coin
CREATE TABLE IF NOT EXISTS portfolio (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    coin TEXT NOT NULL,  -- Cryptocurrency enum value
    balance REAL NOT NULL DEFAULT 0.0,  -- Current balance in coin units
    avg_buy_price REAL NOT NULL DEFAULT 1.0,  -- Average buy price in KRW
    current_price_krw REAL NOT NULL DEFAULT 1.0,  -- Current price in KRW
    value_krw REAL NOT NULL DEFAULT 1.0,  -- Total value in KRW
    profit_loss_krw REAL NOT NULL DEFAULT 1.0,  -- Profit/loss in KRW
    profit_loss_percentage REAL NOT NULL DEFAULT 1.0,  -- Profit/loss percentage
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(coin)  -- One portfolio entry per coin
);

-- Insert default user preferences if not exists
INSERT INTO user_preferences (default_strategy, auto_trade, daily_trading_limit_krw)
SELECT 'balanced', 1, 100000.0
WHERE NOT EXISTS (SELECT 1 FROM user_preferences LIMIT 1);

-- Insert default coin preferences for BTC if not exists
-- This migrates the existing single-coin (BTC) setup
INSERT INTO coin_preferences (coin, enabled, percentage, strategy)
SELECT 'BTC', 1, 100.0, 'balanced'
WHERE NOT EXISTS (SELECT 1 FROM coin_preferences WHERE coin = 'BTC');

-- Insert default portfolio entry for BTC if not exists
INSERT INTO portfolio (coin, balance, avg_buy_price, current_price_krw, value_krw, profit_loss_krw, profit_loss_percentage)
SELECT 'BTC', 1.0, 1.0, 1.0, 1.0, 1.0, 1.0
WHERE NOT EXISTS (SELECT 1 FROM portfolio WHERE coin = 'BTC');

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_coin_preferences_coin ON coin_preferences(coin);
CREATE INDEX IF NOT EXISTS idx_portfolio_coin ON portfolio(coin);
CREATE INDEX IF NOT EXISTS idx_portfolio_updated_at ON portfolio(updated_at);

# Project Structure

## Directory Layout

```
gpt-bitcoin/
├── .claude/                      # Claude Code configuration
│   ├── agents/                   # Agent definitions
│   │   └── moai/                # MoAI-ADK agents
│   ├── commands/                # Custom commands
│   │   └── moai/                # MoAI workflow commands
│   ├── output-styles/           # Output style configurations
│   ├── rules/                   # Project-specific rules
│   │   └── moai/                # MoAI framework rules
│   └── skills/                  # Skill definitions
│       └── moai/                # MoAI skills
├── .data/                       # Runtime data directory
├── .git/                        # Git repository
├── .moai/                       # MoAI-ADK project data
│   └── project/                 # Project documentation
│       ├── product.md          # Product overview
│       ├── structure.md        # This file
│       └── tech.md             # Technical documentation
├── autotrade.py                 # Version 1: Basic trading strategy
├── autotrade_v2.py              # Version 2: Enhanced with news data
├── autotrade_v3.py              # Version 3: Chart image analysis
├── streamlit_app.py             # Web monitoring dashboard
├── instructions.md              # V1 GPT-4o system prompt
├── instructions_v2.md           # V2 GPT-4o system prompt
├── instructions_v3.md           # V3 GPT-4o system prompt
├── requirements.txt             # Python dependencies
├── .env                         # API credentials (not in repo)
├── .gitignore                   # Git ignore rules
├── .mcp.json                    # MCP server configuration
├── CLAUDE.md                    # Claude Code configuration
└── README.MD                    # Project overview (Korean)
```

## File Descriptions

### Core Trading Scripts

**autotrade.py** (Version 1 - Basic Strategy)
- 1-hour interval trading execution
- Technical indicators only (MA, RSI, Stochastic, MACD, Bollinger Bands)
- Full position buy/sell decisions
- No historical decision tracking
- ~150 lines of code

**autotrade_v2.py** (Version 2 - Enhanced Strategy)
- 8-hour interval trading execution (3x daily: 00:01, 08:01, 16:01 KST)
- All v1 technical indicators
- Added news sentiment analysis via SerpApi
- Added Fear & Greed Index from Alternative.me
- Partial position management (percentage-based trading)
- SQLite database integration for decision logging
- Historical decision context provided to GPT-4o for learning
- ~350 lines of code

**autotrade_v3.py** (Version 3 - Visual Intelligence)
- Maintains 8-hour trading interval
- All v2 data sources and indicators
- Selenium WebDriver for chart screenshot capture
- GPT-4o vision API for chart pattern recognition
- Comprehensive multi-modal analysis (text + image)
- ~450 lines of code

### Monitoring Interface

**streamlit_app.py**
- Streamlit-based web dashboard
- Real-time portfolio valuation display
- ROI (Return on Investment) calculation
- Investment duration tracking
- Trading decision history table
- Current BTC price display
- Cash and BTC holdings visualization
- ~50 lines of code

### GPT-4o System Prompts

**instructions.md** (Version 1)
- Basic trading instructions
- Technical indicator explanations
- Market data format specifications
- Decision criteria for buy/sell/hold
- Simple JSON output format requirements

**instructions_v2.md** (Version 2)
- All v1 instructions
- News sentiment analysis guidelines
- Fear & Greed Index interpretation
- Historical decision evaluation framework
- Portfolio state management instructions
- Advanced risk management principles
- Comprehensive examples with reasoning

**instructions_v3.md** (Version 3)
- All v2 instructions
- Chart image analysis guidelines
- Candlestick pattern recognition
- Visual trend identification
- Multi-modal data synthesis instructions
- Vision-specific decision examples

### Configuration Files

**requirements.txt**
- Python package dependencies
- Core libraries: openai, pyupbit, pandas, pandas_ta
- Web automation: selenium
- Scheduling: schedule
- Dashboard: streamlit
- API integration: requests
- Database: sqlite3 (Python standard library)
- Environment: python-dotenv

**.env** (not in repository, must be created)
```env
OPENAI_API_KEY="sk-..."
UPBIT_ACCESS_KEY="..."
UPBIT_SECRET_KEY="..."
SERPAPI_API_KEY="..."
```

**.gitignore**
- Python: __pycache__, *.pyc, .venv
- Environment: .env
- Database: *.sqlite
- IDE: .vscode, .idea
- OS: .DS_Store
- Logs: output.log, nohup.out

### MoAI-ADK Integration

**CLAUDE.md**
- Claude Code agent orchestration configuration
- SPEC-first DDD workflow definitions
- Quality gate enforcement rules
- Multi-agent coordination protocols

**.mcp.json**
- Model Context Protocol server configuration
- Integration points for external services
- Tool definitions and capabilities

### Documentation

**README.MD**
- Korean language project overview
- YouTube video links (4-part tutorial series)
- Strategy comparison (v1, v2, v3)
- AWS EC2 server setup instructions
- Execution commands and process management

## Component Relationships

### Data Flow Architecture

```
External APIs
    ├── Upbit API (Market Data, Order Execution)
    ├── OpenAI API (GPT-4o Decision Engine)
    ├── SerpApi (News Data)
    └── Alternative.me (Fear & Greed Index)
          ↓
Data Collection Layer (autotrade_v3.py)
    ├── get_market_data() - OHLCV, Technical Indicators
    ├── get_news() - Latest cryptocurrency news
    ├── get_fear_greed_index() - Market sentiment
    ├── capture_chart() - Selenium screenshot
    └── get_current_status() - Portfolio state
          ↓
Data Preparation Layer
    ├── Format market data as JSON
    ├── Encode chart image as base64
    ├── Fetch last 10 decisions from SQLite
    └── Compose GPT-4o prompt with instructions
          ↓
Decision Engine
    ├── OpenAI API call with all data
    ├── GPT-4o analysis (text + vision)
    └── JSON response parsing
          ↓
Execution Layer
    ├── parse_decision() - Extract action
    ├── execute_trade() - Upbit order execution
    └── save_decision_to_db() - Log to SQLite
          ↓
Monitoring Layer (streamlit_app.py)
    ├── Load data from SQLite
    ├── Calculate portfolio value
    ├── Display ROI metrics
    └── Show decision history
```

### Database Schema

**SQLite Database: trading_decisions.sqlite**

```sql
CREATE TABLE decisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME,              -- Decision timestamp (KST)
    decision TEXT,                    -- 'buy', 'sell', or 'hold'
    percentage REAL,                  -- Portfolio percentage to trade
    reason TEXT,                      -- GPT-4o reasoning explanation
    btc_balance REAL,                 -- BTC holdings at decision time
    krw_balance REAL,                 -- KRW holdings at decision time
    btc_avg_buy_price REAL,           -- Average BTC purchase price
    btc_krw_price REAL                -- Current BTC price at decision time
);
```

### Module Dependencies

**autotrade_v3.py imports:**
```
os, dotenv → Environment configuration
pyupbit → Upbit API integration
pandas → Data manipulation
pandas_ta → Technical indicator calculation
json → JSON serialization
openai → GPT-4o API client
schedule → Task scheduling
time → Sleep/delay functions
requests → HTTP requests
datetime → Timestamp handling
sqlite3 → Database operations
selenium → Chart screenshot capture
base64 → Image encoding for API
```

**streamlit_app.py imports:**
```
streamlit → Web dashboard framework
sqlite3 → Database queries
pandas → Data frame operations
datetime → Time calculations
pyupbit → Current price retrieval
```

## Execution Flow

### Scheduled Trading Loop

```
main()
  ↓
initialize_db()                    # Create SQLite table if needed
  ↓
schedule.every().day.at("00:01").do(trade)    # 3x daily:
schedule.every().day.at("08:01").do(trade)    # - 00:01 KST
schedule.every().day.at("16:01").do(trade)    # - 08:01 KST
                                               # - 16:01 KST
  ↓
while True:                         # Infinite loop
    schedule.run_pending()          # Execute scheduled tasks
    time.sleep(60)                  # Check every minute
```

### Trade Execution Flow

```
trade() function:
  ↓
1. Fetch all data sources:
   ├── Market data (30-day daily, 24-hour hourly OHLCV)
   ├── Technical indicators (MA, RSI, MACD, etc.)
   ├── Orderbook data (bid/ask prices and depth)
   ├── Latest crypto news (from SerpApi)
   ├── Fear & Greed Index (30-day history)
   ├── Chart screenshot (Selenium capture)
   ├── Last 10 decisions (from SQLite)
   └── Current portfolio status
  ↓
2. Prepare GPT-4o request:
   ├── Load instructions_v3.md
   ├── Format all data as JSON
   ├── Encode chart image as base64
   └── Compose complete prompt
  ↓
3. Call GPT-4o API:
   ├── Send prompt with all data
   ├── Receive JSON response
   └── Parse decision (buy/sell/hold + % + reason)
  ↓
4. Execute decision:
   ├── if BUY: execute_buy_order()
   ├── if SELL: execute_sell_order()
   └── if HOLD: no action
  ↓
5. Log to database:
   ├── save_decision_to_db()
   └── Store with timestamp and all context
```

### Streamlit Dashboard Flow

```
streamlit_app.py:
  ↓
1. Page configuration:
   ├── Set wide layout
   ├── Set page title
   └── Display project info
  ↓
2. Load data:
   ├── Connect to SQLite database
   ├── Fetch all decision records
   └── Create pandas DataFrame
  ↓
3. Calculate metrics:
   ├── Current BTC price (Upbit API)
   ├── Portfolio value (BTC * price + KRW)
   ├── ROI = (current - start) / start * 100
   └── Investment duration (days, hours, minutes)
  ↓
4. Display dashboard:
   ├── Header with ROI percentage
   ├── Current timestamp
   ├── Investment period
   ├── Starting capital (2,000,000 KRW)
   ├── Current BTC price
   ├── Cash balance
   ├── BTC holdings
   ├── Average buy price
   ├── Current portfolio value
   └── Decision history table
```

## Key Design Patterns

### Separation of Concerns

- **Data Collection**: Dedicated functions for each data source
- **Decision Logic**: Delegated entirely to GPT-4o
- **Execution**: Separate buy/sell/hold execution paths
- **Persistence**: SQLite database for all decisions
- **Monitoring**: Independent Streamlit dashboard

### Progressive Enhancement

- **Version 1**: Proof of concept with technical indicators
- **Version 2**: Added sentiment analysis and decision history
- **Version 3**: Added visual analysis with GPT-4o vision

### Configuration Management

- **Environment Variables**: Sensitive data in .env file
- **System Prompts**: Separate .md files for maintainability
- **Database Schema**: Automatically created on first run
- **Scheduling**: Configurable execution times

---

**Last Updated**: 2025-03-02

**Project Structure Version**: 3.0 (autotrade_v3.py)

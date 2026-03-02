# Technical Documentation

## Technology Stack

### Programming Language

**Python 3**
- Primary language for all components
- Chosen for extensive ecosystem of data science and API libraries
- Compatible with Windows, Linux (Ubuntu), and macOS

### Core Libraries

**openai** (v1.0+)
- OpenAI GPT-4o API client
- Chat completion API for text-based decisions
- Vision API for chart image analysis
- JSON mode for structured output

**pyupbit** (latest)
- Upbit cryptocurrency exchange API wrapper
- Market data retrieval (OHLCV, orderbook)
- Order execution (buy/sell)
- Account balance queries
- JWT-based authentication

**pandas** (v2.0+)
- Data manipulation and analysis
- DataFrame operations for market data
- Time series handling for timestamps
- Data serialization for API payloads

**pandas_ta** (latest)
- Technical Analysis library
- 50+ technical indicators
- Moving Averages (SMA, EMA)
- RSI, MACD, Stochastic Oscillator
- Bollinger Bands calculation

**selenium** (v4.0+)
- Web automation for chart screenshots
- Chrome WebDriver control
- Element waiting and interaction
- Screenshot capture functionality

**streamlit** (v1.28+)
- Web dashboard framework
- Real-time data visualization
- DataFrame display
- Automatic UI generation

**schedule** (latest)
- Task scheduling library
- Time-based job execution
- Persistent trading schedule (3x daily)

**python-dotenv** (latest)
- Environment variable management
- .env file loading
- Secure credential handling

### Database

**SQLite 3**
- Built-in Python database engine
- Decision history storage
- Lightweight and serverless
- File-based persistence (trading_decisions.sqlite)

## API Integrations

### OpenAI API

**Purpose**: AI decision engine and chart visual analysis

**Authentication**:
```python
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
```

**Endpoints Used**:

1. **Chat Completion** (Text Analysis)
   - Model: `gpt-4o`
   - Purpose: Generate trading decisions from market data
   - Input: Formatted JSON with market indicators, news, sentiment
   - Output: Structured JSON with decision, percentage, reasoning

   ```python
   response = client.chat.completions.create(
       model="gpt-4o",
       messages=[
           {"role": "system", "content": instructions},
           {"role": "user", "content": formatted_data}
       ],
       response_format={"type": "json_object"}
   )
   ```

2. **Vision Analysis** (Chart Images)
   - Model: `gpt-4o`
   - Purpose: Analyze candlestick chart screenshots
   - Input: Base64-encoded PNG images
   - Output: Text description of chart patterns and trends

   ```python
   response = client.chat.completions.create(
       model="gpt-4o",
       messages=[
           {
               "role": "user",
               "content": [
                   {"type": "text", "text": "Analyze this Bitcoin chart"},
                   {
                       "type": "image_url",
                       "image_url": {
                           "url": f"data:image/png;base64,{encoded_image}"
                       }
                   }
               ]
           }
           ]
   )
   ```

**Rate Limits**:
- TPM (Tokens Per Minute): Depends on API tier
- RPM (Requests Per Minute): Depends on API tier
- Error handling with exponential backoff recommended

**Cost Considerations**:
- GPT-4o pricing: $5.00 per million input tokens
- Vision API: Additional cost for image processing
- Estimated cost per decision: ~$0.02-0.05

### Upbit API

**Purpose**: Market data retrieval and order execution

**Authentication**:
```python
upbit = pyupbit.Upbit(
    os.getenv("UPBIT_ACCESS_KEY"),
    os.getenv("UPBIT_SECRET_KEY")
)
```

**Endpoints Used**:

1. **Market Data**
   - `pyupbit.get_ohlcv()` - OHLCV data
   - `pyupbit.get_orderbook()` - Orderbook depth
   - Daily data: 30-day history
   - Hourly data: 24-hour history

   ```python
   # Daily data (30 days)
   df_daily = pyupbit.get_ohlcv("KRW-BTC", interval="day", count=30)

   # Hourly data (24 hours)
   df_hourly = pyupbit.get_ohlcv("KRW-BTC", interval="minute60", count=24)

   # Orderbook data
   orderbook = pyupbit.get_orderbook("KRW-BTC")
   ```

2. **Account Information**
   - `upbit.get_balance()` - KRW and BTC balances
   - Average buy price for BTC holdings

   ```python
   krw_balance = upbit.get_balance("KRW")
   btc_balance = upbit.get_balance("BTC")
   avg_buy_price = upbit.get_avg_buy_price("KRW-BTC")
   ```

3. **Order Execution**
   - `upbit.buy_market_order()` - Market buy order
   - `upbit.sell_market_order()` - Market sell order

   ```python
   # Buy order (percentage of KRW balance)
   buy_result = upbit.buy_market_order(
       "KRW-BTC",
       krw_balance * (percentage / 100) * 0.9995  # Account for 0.05% fee
   )

   # Sell order (percentage of BTC holdings)
   sell_result = upbit.sell_market_order(
       "KRW-BTC",
       btc_balance * (percentage / 100) * 0.9995  # Account for 0.05% fee
   )
   ```

**Trading Pair**: `KRW-BTC` (Korean Won to Bitcoin)

**Transaction Fees**: 0.05% per trade (automatically deducted)

**Rate Limits**:
- API calls limited per IP
- Implement delays between requests
- Cache market data when possible

### SerpApi

**Purpose**: Cryptocurrency news aggregation

**Authentication**:
```python
SERPAPI_API_KEY = os.getenv("SERPAPI_API_KEY")
```

**Endpoint Used**:
- Google News Search for Bitcoin/crypto news
- Retrieves recent headlines, sources, timestamps

```python
params = {
    "engine": "google_news",
    "q": "비트코인 OR bitcoin",  # Korean and English keywords
    "api_key": SERPAPI_API_KEY
}

response = requests.get("https://serpapi.com/search", params=params)
news_results = response.json().get("news_results", [])
```

**Data Retrieved**:
- News title
- Source website
- Publication timestamp
- Link to full article

**Rate Limits**:
- Free tier: 100 searches per month
- Paid plans available for higher volume

### Alternative.me API

**Purpose**: Fear & Greed Index for market sentiment

**Endpoint Used**:
- Historical Fear & Greed Index data

```python
url = "https://api.alternative.me/fng/?limit=30"  # 30 days
response = requests.get(url)
fng_data = response.json().get("data", [])
```

**Data Retrieved**:
- Value: 0-100 (0 = Extreme Fear, 100 = Extreme Greed)
- Value classification: "Extreme Fear", "Fear", "Neutral", "Greed", "Extreme Greed"
- Timestamp: Unix timestamp
- Time until update: Seconds until next update (current entry only)

**Sentiment Interpretation**:
- 0-25: Extreme Fear (buying opportunity)
- 26-45: Fear (accumulation phase)
- 46-55: Neutral (consolidation)
- 56-75: Greed (caution advised)
- 76-100: Extreme Greed (potential correction)

## Technical Indicators

### Moving Averages

**Simple Moving Average (SMA)**
- Calculation: Average of closing prices over N periods
- Periods used: SMA_10 (10-period), SMA_20 (20-period)
- Purpose: Identify trend direction and support/resistance levels

**Exponential Moving Average (EMA)**
- Calculation: Weighted average giving more weight to recent prices
- Periods used: EMA_10 (10-period)
- Purpose: Faster trend detection than SMA
- Signal: EMA crossing above SMA = bullish, below = bearish

### Relative Strength Index (RSI)

**Period**: RSI_14 (14-period)
**Range**: 0-100
**Interpretation**:
- RSI > 70: Overbought (potential sell signal)
- RSI < 30: Oversold (potential buy signal)
- RSI ~50: Neutral (no clear direction)

**Calculation**:
```
RSI = 100 - (100 / (1 + RS))
RS = Average Gain / Average Loss
```

### Stochastic Oscillator

**Components**:
- %K: Fast stochastic line
- %D: Slow stochastic line (3-period SMA of %K)

**Ranges**: 0-100
**Interpretation**:
- %K and %D > 80: Overbought
- %K and %D < 20: Oversold
- %K crossing above %D: Bullish signal
- %K crossing below %D: Bearish signal

### MACD (Moving Average Convergence Divergence)

**Components**:
- MACD Line: EMA_12 - EMA_26
- Signal Line: 9-period EMA of MACD
- MACD Histogram: MACD - Signal

**Interpretation**:
- MACD > Signal: Bullish momentum
- MACD < Signal: Bearish momentum
- Histogram expanding: Momentum strengthening
- Histogram contracting: Momentum weakening

### Bollinger Bands

**Components**:
- Middle Band: 20-period SMA
- Upper Band: Middle Band + (2 × 20-period standard deviation)
- Lower Band: Middle Band - (2 × 20-period standard deviation)

**Interpretation**:
- Price near upper band: Potentially overbought
- Price near lower band: Potentially oversold
- Bands expanding: High volatility
- Bands contracting: Low volatility (potential breakout)

## Database Schema

### SQLite Database: trading_decisions.sqlite

**Table**: decisions

```sql
CREATE TABLE decisions (
    -- Primary key
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    -- Decision details
    timestamp DATETIME,              -- When decision was made (KST)
    decision TEXT,                    -- 'buy', 'sell', or 'hold'
    percentage REAL,                  -- Portfolio % to trade (0-100)
    reason TEXT,                      -- GPT-4o's explanation

    -- Portfolio state at decision time
    btc_balance REAL,                 -- Bitcoin holdings (BTC)
    krw_balance REAL,                 -- Korean Won holdings (KRW)
    btc_avg_buy_price REAL,           -- Avg BTC purchase price (KRW)
    btc_krw_price REAL                -- Current BTC price (KRW)
);
```

**Index**: Automatically created on `id` (primary key) and `timestamp` (for chronological queries)

**Query Examples**:

```python
# Fetch last 10 decisions for context
cursor.execute('''
    SELECT timestamp, decision, percentage, reason,
           btc_balance, krw_balance, btc_avg_buy_price
    FROM decisions
    ORDER BY timestamp DESC
    LIMIT 10
''')

# Fetch all decisions for dashboard
cursor.execute('''
    SELECT timestamp, decision, percentage, reason,
           btc_balance, krw_balance, btc_avg_buy_price, btc_krw_price
    FROM decisions
    ORDER BY timestamp
''')
```

## Configuration Requirements

### Environment Variables (.env)

Create a `.env` file in the project root with the following variables:

```env
# OpenAI API Key
# Get from: https://platform.openai.com/api-keys
# Required for: GPT-4o decision engine
OPENAI_API_KEY="sk-proj-..."

# Upbit Access Key
# Get from: https://upbit.com/mypage/open_api_management
# Required for: Market data and order execution
UPBIT_ACCESS_KEY="..."

# Upbit Secret Key
# Get from: https://upbit.com/mypage/open_api_management
# Required for: JWT authentication
UPBIT_SECRET_KEY="..."

# SerpApi Key
# Get from: https://serpapi.com/
# Required for: News sentiment analysis (v2, v3)
SERPAPI_API_KEY="..."
```

### Security Best Practices

1. **Never commit .env file to version control**
   - Already included in .gitignore

2. **Use separate API keys for development and production**
   - Create different Upbit API keys for testing

3. **Restrict Upbit API access by IP address**
   - In Upbit settings, whitelist your server IP
   - Required for AWS EC2 deployments

4. **Rotate API keys regularly**
   - Update keys every 90 days
   - Revoke old keys after rotation

5. **Monitor API usage**
   - Track OpenAI token usage for cost management
   - Monitor Upbit API rate limits

### Installation Steps

**Local Development (Windows/Mac/Linux)**:

```bash
# 1. Clone repository
git clone https://github.com/youtube-jocoding/gpt-bitcoin.git
cd gpt-bitcoin

# 2. Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Create .env file with API keys
cp .env.example .env  # If template exists
# Edit .env with your actual keys

# 5. Run trading bot (v3)
python autotrade_v3.py

# 6. Run monitoring dashboard (separate terminal)
streamlit run streamlit_app.py
```

**AWS EC2 (Ubuntu Server)**:

```bash
# 1. Set timezone to Korea
sudo ln -sf /usr/share/zoneinfo/Asia/Seoul /etc/localtime

# 2. Update system packages
sudo apt update
sudo apt upgrade -y

# 3. Install Python 3 and pip
sudo apt install python3 python3-pip -y

# 4. Install Chrome for Selenium
wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
sudo apt install ./google-chrome-stable_current_amd64.deb -y

# 5. Install ChromeDriver
sudo apt install chromium-chromedriver -y

# 6. Clone repository
git clone https://github.com/youtube-jocoding/gpt-bitcoin.git
cd gpt-bitcoin

# 7. Install Python dependencies
pip3 install -r requirements.txt

# 8. Create .env file
vim .env
# Add your API keys

# 9. Run in background
nohup python3 -u autotrade_v3.py > output.log 2>&1 &

# 10. Monitor logs
tail -f output.log

# 11. Check running processes
ps ax | grep .py

# 12. Kill process if needed
kill -9 <PID>
```

### System Requirements

**Minimum Requirements**:
- CPU: 2 cores
- RAM: 2 GB
- Storage: 1 GB free space
- Network: Stable internet connection
- OS: Python 3.8+ compatible

**Recommended for Production**:
- CPU: 4+ cores
- RAM: 4+ GB
- Storage: 10+ GB SSD
- Network: Low latency to Upbit API
- OS: Ubuntu 22.04 LTS

**External Dependencies**:
- OpenAI API access
- Upbit account with API keys
- SerpApi account (for v2, v3)
- Chrome browser + ChromeDriver (for v3 Selenium)

## Troubleshooting

### Common Issues

**1. Upbit API Authentication Error**
```
Solution: Verify UPBIT_ACCESS_KEY and UPBIT_SECRET_KEY are correct
Check that IP address is whitelisted in Upbit settings
```

**2. OpenAI API Rate Limit**
```
Solution: Implement exponential backoff
Reduce trading frequency
Upgrade API tier
```

**3. Selenium ChromeDriver Error**
```
Solution: Install Chrome and ChromeDriver
Match ChromeDriver version with Chrome browser
Use webdriver-manager for automatic updates
```

**4. Database Lock Error**
```
Solution: Close database connections properly
Use context managers (with statements)
Ensure only one process writes at a time
```

**5. Import Errors**
```
Solution: Ensure all dependencies installed
pip install -r requirements.txt
Check Python version compatibility (3.8+)
```

---

**Last Updated**: 2025-03-02

**Technical Documentation Version**: 3.0 (autotrade_v3.py)

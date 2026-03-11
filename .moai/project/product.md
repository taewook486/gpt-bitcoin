# Product Overview

## Project Description

The AI Cryptocurrency Auto-Trading System is an AI-powered cryptocurrency trading bot that leverages ZhipuAI's GLM-5/GLM-4.6V API to make automated trading decisions for various cryptocurrencies (BTC, ETH, SOL, XRP, ADA, DOGE, AVAX, DOT) on the Upbit exchange. The system demonstrates the practical application of large language models in financial trading.

## Core Purpose

The system aims to automate Bitcoin trading decisions by analyzing multiple data sources including market technical indicators, news sentiment, market psychology indicators, and chart visual patterns. It uses GPT-4o's advanced reasoning capabilities to synthesize this information and generate buy, sell, or hold decisions with specific position sizing recommendations.

## Key Features

### Multi-Source Data Analysis

The system aggregates and analyzes six distinct data sources to make informed trading decisions:

1. **Technical Indicators**: Comprehensive market data including Moving Averages (SMA, EMA), Relative Strength Index (RSI), Stochastic Oscillator, MACD, and Bollinger Bands calculated from OHLCV (Open, High, Low, Close, Volume) data

2. **Market Depth**: Real-time orderbook data showing current bid/ask prices and market depth

3. **News Sentiment**: Latest cryptocurrency news headlines and articles retrieved via SerpApi to gauge market sentiment

4. **Fear & Greed Index**: 30-day historical data from Alternative.me measuring market psychology (0 = Extreme Fear, 100 = Extreme Greed)

5. **Historical Decisions**: Past trading decisions and outcomes stored in SQLite database for learning and strategy refinement

6. **Chart Visual Analysis** (v3 only): Candlestick charts captured via Selenium and analyzed by GPT-4o's vision capabilities

### Intelligent Decision Engine

- **GPT-4o Integration**: Leverages OpenAI's most advanced language model with vision capabilities for comprehensive market analysis

- **JSON-Structured Output**: Returns trading decisions in structured JSON format with decision type, percentage allocation, and detailed reasoning

- **Risk Management**: Implements aggressive risk management principles with transaction fee consideration (0.05% Upbit fee) and market slippage analysis

- **Portfolio Tracking**: Real-time monitoring of BTC balance, KRW balance, and average buy price

### Automated Execution

- **Scheduled Trading**: Executes trading analysis at 8-hour intervals (00:01, 08:01, 16:01 KST)

- **Automated Orders**: Automatically executes buy/sell orders on Upbit based on GPT-4o recommendations

- **Decision Logging**: Records all trading decisions with timestamps and reasoning in SQLite database for performance analysis

### Web Dashboard

- **Streamlit Interface**: Real-time monitoring dashboard displaying trading history and portfolio performance

- **Performance Metrics**: ROI calculation, investment duration tracking, and current portfolio valuation

## Target Users

### Primary Users

1. **Cryptocurrency Traders**: Individual traders interested in AI-assisted trading automation

2. **Quantitative Analysts**: Researchers studying machine learning applications in financial markets

3. **Python Developers**: Developers learning about API integration, automation, and AI system architecture

4. **Financial Technology Enthusiasts**: Individuals exploring the intersection of AI and finance

### Use Cases

1. **Automated Trading**: Hands-off Bitcoin trading with AI-driven decision making

2. **Market Research**: Analyzing how AI models interpret and act on market data

3. **Educational Platform**: Learning resource for building AI-powered trading systems

4. **Strategy Backtesting**: Using historical decision data to evaluate trading performance

## Trading Strategy Overview

### Version Evolution

The project has evolved through three versions, each adding sophistication:

**Version 1 (autotrade.py)**: Foundation
- 1-hour trading interval
- Full position buy/sell or hold decisions
- Technical indicators and orderbook data only
- No decision history tracking

**Version 2 (autotrade_v2.py)**: Enhanced Analysis
- 8-hour trading interval (reduced frequency)
- Partial position management (ability to trade percentages of portfolio)
- Added news sentiment analysis via SerpApi
- Added Fear & Greed Index for market psychology
- SQLite database for decision logging and learning feedback

**Version 3 (autotrade_v3.py)**: Visual Intelligence
- Maintains 8-hour trading interval
- Selenium-based chart screenshot capture
- GPT-4o vision analysis of candlestick patterns
- All v2 data sources plus chart image analysis
- Most comprehensive market analysis approach

### Trading Philosophy

The system employs an **aggressive growth strategy** with the following principles:

1. **Data-Driven Decisions**: All decisions based on quantitative analysis rather than emotions

2. **Multi-Factor Analysis**: Synthesizes technical, fundamental, sentiment, and visual analysis

3. **Proactive Risk Management**: Considers transaction fees, slippage, and market volatility

4. **Adaptive Position Sizing**: Adjusts position sizes based on confidence levels and market conditions

5. **Continuous Learning**: Uses historical decision data to refine future trading strategies

### Decision Categories

The GPT-4o engine generates one of three decisions:

1. **BUY**: Acquire Bitcoin with specified portfolio percentage (e.g., 35%, 40%, 45% of available KRW)

2. **SELL**: Liquidate Bitcoin holdings with specified percentage (e.g., 50%, 60% of BTC holdings)

3. **HOLD**: Maintain current positions (0% allocation, wait for clearer signals)

Each decision includes detailed reasoning explaining the technical indicators, news factors, and market conditions that influenced the recommendation.

## System Architecture

The system operates as a scheduled Python script with the following workflow:

1. **Data Collection Phase**: Gather market data, news, sentiment index, and capture chart screenshots

2. **Analysis Phase**: Format and send all data to GPT-4o API with comprehensive trading instructions

3. **Decision Phase**: Receive structured JSON decision with action type and reasoning

4. **Execution Phase**: Execute trade on Upbit exchange if action is BUY or SELL

5. **Logging Phase**: Store decision in SQLite database for future reference and learning

6. **Monitoring Phase**: Streamlit dashboard displays real-time results and performance metrics

## Integration Points

- **OpenAI API**: GPT-4o for decision generation and vision analysis
- **Upbit API**: Market data retrieval and order execution
- **SerpApi**: Cryptocurrency news aggregation
- **Alternative.me API**: Fear & Greed Index data
- **SQLite Database**: Decision history and performance tracking
- **Selenium WebDriver**: Chart screenshot capture
- **Streamlit**: Web-based monitoring dashboard

## Development Status

The project is actively maintained with three versions available, each building upon the previous version's capabilities. Version 3 represents the most comprehensive implementation with visual analysis capabilities.

---

**Project Repository**: [github.com/youtube-jocoding/gpt-bitcoin](https://github.com/youtube-jocoding/gpt-bitcoin)

**Author**: Jocoding (유튜버 조코딩)

**Language**: Python 3

**License**: Refer to project repository

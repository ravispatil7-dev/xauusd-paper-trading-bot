# XAU/USD Paper Trading Bot with AI Signals

A complete mobile-responsive paper trading application for Gold (XAU/USD) with AI-powered buy/sell signals and auto-trading capabilities.

## Features

### AI Trading Engine
- **RSI** (Relative Strength Index) - Overbought/Oversold detection
- **EMA Crossover** (9 & 21 period) - Trend identification
- **Bollinger Bands** - Volatility and reversal signals
- **MACD** - Momentum and trend strength
- **Smart Scoring** - Weighted signal generation (0-100% strength)

### Paper Trading
- **$10,000 virtual balance**
- **Real-time P&L tracking**
- **Stop Loss & Take Profit** auto-execution
- **Margin calculation**
- **Drawdown monitoring**
- **Win rate statistics**

### Auto Trading
- Toggle AI auto-trading on/off
- Configurable risk per trade (default 2%)
- Max open trades limit (default 3)
- Minimum signal strength threshold (default 70%)
- Automatic TP/SL management

### Mobile-First Design
- Responsive for all screen sizes
- Touch-optimized buttons
- Real-time WebSocket updates
- Dark theme optimized for mobile
- PWA-ready (can be added to home screen)

## Project Structure
```
xauusd-paper-trading-bot/
├── backend/
│   └── main.py          # FastAPI backend + AI engine
├── frontend/
│   ├── index.html       # Mobile UI
│   └── app.js           # Frontend logic + Chart.js
├── requirements.txt
└── README.md
```

## Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run the Server
```bash
cd backend
uvicorn main:app --host 0.0.0.0 --port 8000
```

### 3. Access the App
Open your browser and go to:
```
http://localhost:8000
```

Or access from your mobile device on the same network:
```
http://YOUR_IP:8000
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/price/history` | GET | Get price history |
| `/api/signals` | GET | Get AI signal history |
| `/api/trades` | GET | Get all trades |
| `/api/portfolio` | GET | Get portfolio stats |
| `/api/trade/open` | POST | Open a new trade |
| `/api/trade/close` | POST | Close a trade |
| `/api/auto-trade/settings` | POST/GET | Auto-trade config |
| `/api/reset` | POST | Reset portfolio |
| `/ws` | WebSocket | Real-time data feed |

## How It Works

1. **Price Simulation**: The backend generates realistic XAU/USD price ticks every 2 seconds
2. **AI Analysis**: Technical indicators are calculated on-the-fly
3. **Signal Generation**: Buy/Sell/Hold signals with strength scores
4. **Auto Trading**: When enabled, the bot opens trades based on strong signals
5. **Risk Management**: Automatic stop-loss and take-profit execution
6. **Portfolio Tracking**: Real-time balance, equity, and statistics

## Customization

### Change Initial Balance
Edit `portfolio = Portfolio(balance=10000.0)` in `backend/main.py`

### Adjust Signal Sensitivity
Modify the scoring thresholds in the `AITradingEngine.generate_signal()` method

### Change Timeframes
Adjust the `asyncio.sleep(2)` in `price_feed_loop()` for faster/slower ticks

## Disclaimer
This is a **paper trading simulator** for educational purposes. No real money is involved. Past performance of the AI signals does not guarantee future results.

## License
MIT License

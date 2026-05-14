
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional, List, Dict
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import json
import asyncio
import random
from dataclasses import dataclass, field, asdict
from enum import Enum
import uuid
import os

app = FastAPI(title="XAU/USD Paper Trading Bot", version="1.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============== DATA MODELS ==============
class SignalType(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"

class OrderType(str, Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP = "STOP"

class TradeStatus(str, Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    PENDING = "PENDING"

@dataclass
class PriceData:
    timestamp: str
    open: float
    high: float
    low: float
    close: float
    volume: float

@dataclass
class Signal:
    type: str
    strength: float  # 0-100
    price: float
    timestamp: str
    indicators: Dict
    reason: str

@dataclass
class Trade:
    id: str
    symbol: str = "XAUUSD"
    type: str = "BUY"  # BUY or SELL
    entry_price: float = 0.0
    exit_price: float = 0.0
    quantity: float = 0.01
    stop_loss: float = 0.0
    take_profit: float = 0.0
    status: str = "OPEN"
    pnl: float = 0.0
    pnl_percent: float = 0.0
    entry_time: str = ""
    exit_time: str = ""
    strategy: str = "AI_Signal"

@dataclass
class Portfolio:
    balance: float = 10000.0
    equity: float = 10000.0
    margin_used: float = 0.0
    free_margin: float = 10000.0
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    total_pnl: float = 0.0
    max_drawdown: float = 0.0
    peak_equity: float = 10000.0

# ============== IN-MEMORY STORAGE ==============
price_history: List[PriceData] = []
current_price: float = 2345.50
signals_history: List[Signal] = []
trades: List[Trade] = []
portfolio = Portfolio()
active_connections: List[WebSocket] = []

# ============== AI TRADING ENGINE ==============
class AITradingEngine:
    def __init__(self):
        self.lookback = 50
        self.rsi_period = 14
        self.ema_fast = 9
        self.ema_slow = 21
        self.bb_period = 20
        self.bb_std = 2.0

    def calculate_rsi(self, prices: List[float], period: int = 14) -> float:
        if len(prices) < period + 1:
            return 50.0
        deltas = np.diff(prices[-period-1:])
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        avg_gain = np.mean(gains)
        avg_loss = np.mean(losses)
        if avg_loss == 0:
            return 100.0
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))

    def calculate_ema(self, prices: List[float], period: int) -> float:
        if len(prices) < period:
            return prices[-1] if prices else 0
        weights = np.exp(np.linspace(-1., 0., period))
        weights /= weights.sum()
        return np.convolve(prices[-period:], weights, mode='valid')[0]

    def calculate_bollinger(self, prices: List[float], period: int = 20, std: float = 2.0):
        if len(prices) < period:
            mid = prices[-1] if prices else 0
            return mid, mid + 10, mid - 10
        recent = prices[-period:]
        mid = np.mean(recent)
        sigma = np.std(recent)
        upper = mid + std * sigma
        lower = mid - std * sigma
        return mid, upper, lower

    def calculate_macd(self, prices: List[float]):
        if len(prices) < 26:
            return 0, 0, 0
        ema12 = self.calculate_ema(prices, 12)
        ema26 = self.calculate_ema(prices, 26)
        macd_line = ema12 - ema26
        # Signal line (9-period EMA of MACD)
        macd_history = []
        for i in range(26, len(prices)):
            e12 = self.calculate_ema(prices[:i], 12)
            e26 = self.calculate_ema(prices[:i], 26)
            macd_history.append(e12 - e26)
        signal_line = self.calculate_ema(macd_history, 9) if len(macd_history) >= 9 else macd_line
        histogram = macd_line - signal_line
        return macd_line, signal_line, histogram

    def generate_signal(self, prices: List[float]) -> Signal:
        if len(prices) < 30:
            return Signal("HOLD", 0, prices[-1] if prices else 0, datetime.now().isoformat(), {}, "Insufficient data")

        current = prices[-1]
        rsi = self.calculate_rsi(prices)
        ema_fast = self.calculate_ema(prices, self.ema_fast)
        ema_slow = self.calculate_ema(prices, self.ema_slow)
        bb_mid, bb_upper, bb_lower = self.calculate_bollinger(prices)
        macd_line, signal_line, histogram = self.calculate_macd(prices)

        # AI Scoring System
        buy_score = 0
        sell_score = 0
        reasons = []

        # RSI signals
        if rsi < 30:
            buy_score += 25
            reasons.append(f"RSI oversold ({rsi:.1f})")
        elif rsi > 70:
            sell_score += 25
            reasons.append(f"RSI overbought ({rsi:.1f})")

        # EMA Crossover
        if ema_fast > ema_slow:
            buy_score += 20
            reasons.append("EMA9 > EMA21 (Bullish)")
        else:
            sell_score += 20
            reasons.append("EMA9 < EMA21 (Bearish)")

        # Bollinger Bands
        if current <= bb_lower:
            buy_score += 20
            reasons.append("Price at BB lower band")
        elif current >= bb_upper:
            sell_score += 20
            reasons.append("Price at BB upper band")

        # MACD
        if histogram > 0 and macd_line > signal_line:
            buy_score += 20
            reasons.append("MACD bullish crossover")
        elif histogram < 0 and macd_line < signal_line:
            sell_score += 20
            reasons.append("MACD bearish crossover")

        # Trend strength (simple)
        price_change = (current - prices[-10]) / prices[-10] * 100
        if price_change > 0.5:
            buy_score += 15
        elif price_change < -0.5:
            sell_score += 15

        # Determine signal
        if buy_score >= 60 and buy_score > sell_score + 10:
            signal_type = "BUY"
            strength = min(buy_score, 100)
        elif sell_score >= 60 and sell_score > buy_score + 10:
            signal_type = "SELL"
            strength = min(sell_score, 100)
        else:
            signal_type = "HOLD"
            strength = max(buy_score, sell_score)

        indicators = {
            "rsi": round(rsi, 2),
            "ema_fast": round(ema_fast, 2),
            "ema_slow": round(ema_slow, 2),
            "bb_upper": round(bb_upper, 2),
            "bb_lower": round(bb_lower, 2),
            "macd": round(macd_line, 4),
            "macd_signal": round(signal_line, 4),
            "histogram": round(histogram, 4),
            "buy_score": buy_score,
            "sell_score": sell_score
        }

        return Signal(
            type=signal_type,
            strength=round(strength, 1),
            price=round(current, 2),
            timestamp=datetime.now().isoformat(),
            indicators=indicators,
            reason="; ".join(reasons) if reasons else "Neutral market conditions"
        )

ai_engine = AITradingEngine()

# ============== PRICE SIMULATOR ==============
class PriceSimulator:
    def __init__(self):
        self.base_price = 2345.50
        self.volatility = 0.15  # 0.15% per tick
        self.trend = 0.0
        self.last_price = self.base_price

    def generate_tick(self) -> PriceData:
        # Random walk with slight mean reversion
        change = random.gauss(self.trend, self.volatility / 100)
        self.trend *= 0.95  # Decay trend

        # Occasional trend shifts
        if random.random() < 0.02:
            self.trend = random.gauss(0, 0.05) / 100

        new_close = self.last_price * (1 + change)
        new_close = max(2300, min(2400, new_close))  # Keep in realistic range

        # Generate OHLC
        high = new_close * (1 + abs(random.gauss(0, 0.05)) / 100)
        low = new_close * (1 - abs(random.gauss(0, 0.05)) / 100)
        open_p = self.last_price

        self.last_price = new_close

        return PriceData(
            timestamp=datetime.now().isoformat(),
            open=round(open_p, 2),
            high=round(high, 2),
            low=round(low, 2),
            close=round(new_close, 2),
            volume=round(random.uniform(1000, 5000), 2)
        )

simulator = PriceSimulator()

# ============== AUTO TRADER ==============
class AutoTrader:
    def __init__(self):
        self.enabled = False
        self.risk_per_trade = 0.02  # 2% risk
        self.max_open_trades = 3
        self.min_strength = 70  # Minimum signal strength

    def should_trade(self, signal: Signal) -> bool:
        if not self.enabled:
            return False
        if signal.type == "HOLD":
            return False
        if signal.strength < self.min_strength:
            return False
        open_trades = [t for t in trades if t.status == "OPEN"]
        if len(open_trades) >= self.max_open_trades:
            return False
        return True

    def execute_signal(self, signal: Signal):
        if not self.should_trade(signal):
            return None

        # Check for opposite open trades
        open_trades = [t for t in trades if t.status == "OPEN"]
        for trade in open_trades:
            if trade.type != signal.type:
                # Close opposite trade
                close_trade(trade.id, signal.price)

        # Calculate position size
        risk_amount = portfolio.balance * self.risk_per_trade
        sl_pips = 50  # 50 pips stop loss
        pip_value = 0.01  # For 0.01 lot
        position_size = risk_amount / (sl_pips * pip_value)
        position_size = round(min(position_size, 1.0), 2)  # Max 1 lot

        if signal.type == "BUY":
            sl = signal.price - sl_pips * 0.01
            tp = signal.price + sl_pips * 2 * 0.01  # 1:2 RRR
        else:
            sl = signal.price + sl_pips * 0.01
            tp = signal.price - sl_pips * 2 * 0.01

        trade = Trade(
            id=str(uuid.uuid4())[:8],
            type=signal.type,
            entry_price=round(signal.price, 2),
            quantity=position_size,
            stop_loss=round(sl, 2),
            take_profit=round(tp, 2),
            status="OPEN",
            entry_time=datetime.now().isoformat(),
            strategy="AI_Auto"
        )

        trades.append(trade)
        portfolio.margin_used += position_size * signal.price * 0.01  # 1% margin
        portfolio.total_trades += 1
        return trade

auto_trader = AutoTrader()

# ============== TRADE MANAGEMENT ==============
def close_trade(trade_id: str, exit_price: float):
    for trade in trades:
        if trade.id == trade_id and trade.status == "OPEN":
            trade.exit_price = round(exit_price, 2)
            trade.exit_time = datetime.now().isoformat()
            trade.status = "CLOSED"

            if trade.type == "BUY":
                trade.pnl = round((exit_price - trade.entry_price) * trade.quantity * 100, 2)
            else:
                trade.pnl = round((trade.entry_price - exit_price) * trade.quantity * 100, 2)

            trade.pnl_percent = round(trade.pnl / (trade.entry_price * trade.quantity) * 100, 2)
            portfolio.balance += trade.pnl
            portfolio.total_pnl += trade.pnl
            portfolio.margin_used -= trade.quantity * trade.entry_price * 0.01

            if trade.pnl > 0:
                portfolio.winning_trades += 1
            else:
                portfolio.losing_trades += 1

            # Update peak equity and drawdown
            if portfolio.balance > portfolio.peak_equity:
                portfolio.peak_equity = portfolio.balance
            dd = (portfolio.peak_equity - portfolio.balance) / portfolio.peak_equity * 100
            if dd > portfolio.max_drawdown:
                portfolio.max_drawdown = round(dd, 2)

            return trade
    return None

def check_tp_sl(current: float):
    for trade in trades:
        if trade.status != "OPEN":
            continue
        if trade.type == "BUY":
            if current >= trade.take_profit or current <= trade.stop_loss:
                close_trade(trade.id, current)
        else:
            if current <= trade.take_profit or current >= trade.stop_loss:
                close_trade(trade.id, current)

def update_equity(current: float):
    unrealized = 0
    for trade in trades:
        if trade.status == "OPEN":
            if trade.type == "BUY":
                unrealized += (current - trade.entry_price) * trade.quantity * 100
            else:
                unrealized += (trade.entry_price - current) * trade.quantity * 100
    portfolio.equity = round(portfolio.balance + unrealized, 2)
    portfolio.free_margin = round(portfolio.equity - portfolio.margin_used, 2)

# ============== WEBSOCKET BROADCAST ==============
async def broadcast(message: dict):
    disconnected = []
    for conn in active_connections:
        try:
            await conn.send_json(message)
        except:
            disconnected.append(conn)
    for conn in disconnected:
        if conn in active_connections:
            active_connections.remove(conn)

# ============== BACKGROUND TASK ==============
@app.on_event("startup")
async def startup_event():
    asyncio.create_task(price_feed_loop())

async def price_feed_loop():
    # Generate initial history
    for _ in range(100):
        tick = simulator.generate_tick()
        price_history.append(tick)

    while True:
        await asyncio.sleep(2)  # 2-second ticks for demo
        tick = simulator.generate_tick()
        price_history.append(tick)
        if len(price_history) > 500:
            price_history.pop(0)

        prices = [p.close for p in price_history]
        signal = ai_engine.generate_signal(prices)
        signals_history.append(signal)
        if len(signals_history) > 100:
            signals_history.pop(0)

        # Auto-trading
        auto_trader.execute_signal(signal)

        # Check TP/SL
        check_tp_sl(tick.close)
        update_equity(tick.close)

        # Broadcast
        await broadcast({
            "type": "tick",
            "data": asdict(tick),
            "signal": {
                "type": signal.type,
                "strength": signal.strength,
                "price": signal.price,
                "reason": signal.reason,
                "indicators": signal.indicators
            },
            "portfolio": {
                "balance": round(portfolio.balance, 2),
                "equity": round(portfolio.equity, 2),
                "free_margin": round(portfolio.free_margin, 2),
                "margin_used": round(portfolio.margin_used, 2),
                "total_trades": portfolio.total_trades,
                "winning_trades": portfolio.winning_trades,
                "losing_trades": portfolio.losing_trades,
                "win_rate": round(portfolio.winning_trades / max(portfolio.total_trades, 1) * 100, 1),
                "total_pnl": round(portfolio.total_pnl, 2),
                "max_drawdown": portfolio.max_drawdown
            },
            "open_trades": [asdict(t) for t in trades if t.status == "OPEN"],
            "recent_trades": [asdict(t) for t in trades[-10:]]
        })

# ============== API ENDPOINTS ==============
class TradeRequest(BaseModel):
    type: str
    quantity: float = 0.01
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None

class CloseRequest(BaseModel):
    trade_id: str

class AutoTradeSettings(BaseModel):
    enabled: bool
    risk_per_trade: float = 0.02
    max_open_trades: int = 3
    min_strength: int = 70

@app.get("/api/price/history")
def get_price_history(limit: int = 100):
    return [asdict(p) for p in price_history[-limit:]]

@app.get("/api/signals")
def get_signals(limit: int = 20):
    return [{"type": s.type, "strength": s.strength, "price": s.price, 
             "timestamp": s.timestamp, "reason": s.reason, "indicators": s.indicators} 
            for s in signals_history[-limit:]]

@app.get("/api/trades")
def get_trades():
    return {
        "open": [asdict(t) for t in trades if t.status == "OPEN"],
        "closed": [asdict(t) for t in trades if t.status == "CLOSED"],
        "all": [asdict(t) for t in trades]
    }

@app.get("/api/portfolio")
def get_portfolio():
    return {
        "balance": round(portfolio.balance, 2),
        "equity": round(portfolio.equity, 2),
        "free_margin": round(portfolio.free_margin, 2),
        "margin_used": round(portfolio.margin_used, 2),
        "total_trades": portfolio.total_trades,
        "winning_trades": portfolio.winning_trades,
        "losing_trades": portfolio.losing_trades,
        "win_rate": round(portfolio.winning_trades / max(portfolio.total_trades, 1) * 100, 1),
        "total_pnl": round(portfolio.total_pnl, 2),
        "max_drawdown": portfolio.max_drawdown,
        "peak_equity": round(portfolio.peak_equity, 2)
    }

@app.post("/api/trade/open")
def open_trade(req: TradeRequest):
    global current_price
    current = price_history[-1].close if price_history else 2345.50

    trade = Trade(
        id=str(uuid.uuid4())[:8],
        type=req.type.upper(),
        entry_price=round(current, 2),
        quantity=round(req.quantity, 2),
        stop_loss=round(req.stop_loss, 2) if req.stop_loss else round(current * 0.998, 2),
        take_profit=round(req.take_profit, 2) if req.take_profit else round(current * 1.004, 2),
        status="OPEN",
        entry_time=datetime.now().isoformat(),
        strategy="Manual"
    )

    trades.append(trade)
    portfolio.margin_used += trade.quantity * trade.entry_price * 0.01
    portfolio.total_trades += 1

    return {"success": True, "trade": asdict(trade)}

@app.post("/api/trade/close")
def close_trade_api(req: CloseRequest):
    current = price_history[-1].close if price_history else 2345.50
    trade = close_trade(req.trade_id, current)
    if trade:
        return {"success": True, "trade": asdict(trade)}
    raise HTTPException(status_code=404, detail="Trade not found")

@app.post("/api/auto-trade/settings")
def set_auto_trade_settings(req: AutoTradeSettings):
    auto_trader.enabled = req.enabled
    auto_trader.risk_per_trade = req.risk_per_trade
    auto_trader.max_open_trades = req.max_open_trades
    auto_trader.min_strength = req.min_strength
    return {"success": True, "settings": {
        "enabled": auto_trader.enabled,
        "risk_per_trade": auto_trader.risk_per_trade,
        "max_open_trades": auto_trader.max_open_trades,
        "min_strength": auto_trader.min_strength
    }}

@app.get("/api/auto-trade/settings")
def get_auto_trade_settings():
    return {
        "enabled": auto_trader.enabled,
        "risk_per_trade": auto_trader.risk_per_trade,
        "max_open_trades": auto_trader.max_open_trades,
        "min_strength": auto_trader.min_strength
    }

@app.post("/api/reset")
def reset_portfolio():
    global trades, portfolio, signals_history
    trades = []
    portfolio = Portfolio()
    signals_history = []
    return {"success": True, "message": "Portfolio reset to $10,000"}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_connections.append(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            if msg.get("action") == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        if websocket in active_connections:
            active_connections.remove(websocket)
    except Exception as e:
        if websocket in active_connections:
            active_connections.remove(websocket)

# ============== STATIC FILES ==============
# Mount frontend
frontend_path = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.exists(frontend_path):
    app.mount("/", StaticFiles(directory=frontend_path, html=True), name="frontend")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

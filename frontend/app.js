// XAU/USD Paper Trading Bot - Frontend
const API_BASE = window.location.origin;
let ws = null;
let chart = null;
let currentTradeType = 'BUY';
let priceData = [];
let lastPrice = 2345.50;

// Initialize
window.addEventListener('DOMContentLoaded', () => {
    initChart();
    connectWebSocket();
    loadInitialData();
});

// WebSocket Connection
function connectWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws`;

    ws = new WebSocket(wsUrl);

    ws.onopen = () => {
        updateConnectionStatus(true);
        showToast('Connected to live market', 'success');
    };

    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        handleWebSocketMessage(data);
    };

    ws.onclose = () => {
        updateConnectionStatus(false);
        setTimeout(connectWebSocket, 3000);
    };

    ws.onerror = () => {
        updateConnectionStatus(false);
    };
}

function updateConnectionStatus(connected) {
    const dot = document.getElementById('statusDot');
    const text = document.getElementById('statusText');
    if (connected) {
        dot.classList.remove('disconnected');
        text.textContent = 'Live';
    } else {
        dot.classList.add('disconnected');
        text.textContent = 'Reconnecting...';
    }
}

// Handle WebSocket Messages
function handleWebSocketMessage(data) {
    if (data.type === 'tick') {
        updatePrice(data.data);
        updateSignal(data.signal);
        updatePortfolio(data.portfolio);
        updateOpenTrades(data.open_trades);
        updateRecentTrades(data.recent_trades);
        updateIndicators(data.signal.indicators);
        updateChart(data.data);
    }
}

// Update Price Display
function updatePrice(tick) {
    const priceEl = document.getElementById('currentPrice');
    const changeEl = document.getElementById('priceChange');

    const oldPrice = lastPrice;
    lastPrice = tick.close;

    priceEl.textContent = tick.close.toFixed(2);

    const change = ((tick.close - oldPrice) / oldPrice) * 100;
    const changeStr = (change >= 0 ? '+' : '') + change.toFixed(2) + '%';

    changeEl.textContent = changeStr;
    changeEl.className = 'price-change ' + (change >= 0 ? 'up' : 'down');

    // Flash effect
    priceEl.style.color = change >= 0 ? '#22c55e' : '#ef4444';
    setTimeout(() => {
        priceEl.style.color = '';
    }, 300);
}

// Update Signal Banner
function updateSignal(signal) {
    const banner = document.getElementById('signalBanner');
    const typeEl = document.getElementById('signalType');
    const strengthEl = document.getElementById('signalStrength');
    const reasonEl = document.getElementById('signalReason');

    banner.className = 'signal-banner ' + signal.type;

    const icons = { BUY: 'fa-arrow-up', SELL: 'fa-arrow-down', HOLD: 'fa-hand-paper' };
    typeEl.className = 'signal-type ' + signal.type;
    typeEl.innerHTML = `<i class="fas ${icons[signal.type]}"></i> ${signal.type}`;

    strengthEl.textContent = `Strength: ${signal.strength}%`;
    reasonEl.textContent = signal.reason;
}

// Update Portfolio
function updatePortfolio(portfolio) {
    document.getElementById('balance').textContent = '$' + portfolio.balance.toLocaleString('en-US', {minimumFractionDigits: 2});
    document.getElementById('equity').textContent = '$' + portfolio.equity.toLocaleString('en-US', {minimumFractionDigits: 2});
    document.getElementById('freeMargin').textContent = '$' + portfolio.free_margin.toLocaleString('en-US', {minimumFractionDigits: 2});
    document.getElementById('winRate').textContent = portfolio.win_rate + '%';
    document.getElementById('maxDrawdown').textContent = portfolio.max_drawdown + '%';

    const pnlEl = document.getElementById('totalPnl');
    pnlEl.textContent = (portfolio.total_pnl >= 0 ? '+' : '') + '$' + portfolio.total_pnl.toLocaleString('en-US', {minimumFractionDigits: 2});
    pnlEl.className = 'portfolio-value ' + (portfolio.total_pnl >= 0 ? 'positive' : 'negative');
}

// Update Indicators
function updateIndicators(indicators) {
    document.getElementById('rsiValue').textContent = indicators.rsi || '--';
    document.getElementById('emaFast').textContent = indicators.ema_fast || '--';
    document.getElementById('emaSlow').textContent = indicators.ema_slow || '--';
    document.getElementById('macdValue').textContent = indicators.macd || '--';
    document.getElementById('bbUpper').textContent = indicators.bb_upper || '--';
    document.getElementById('bbLower').textContent = indicators.bb_lower || '--';
}

// Update Open Trades
function updateOpenTrades(openTrades) {
    const container = document.getElementById('openTradesList');
    const countEl = document.getElementById('openTradeCount');

    countEl.textContent = openTrades.length;

    if (openTrades.length === 0) {
        container.innerHTML = `<div style="text-align: center; padding: 20px; color: var(--text-secondary); font-size: 14px;">No open positions</div>`;
        return;
    }

    container.innerHTML = openTrades.map(trade => {
        const pnl = trade.pnl || 0;
        const pnlClass = pnl >= 0 ? 'positive' : 'negative';
        const pnlSign = pnl >= 0 ? '+' : '';

        return `
            <div class="trade-item ${trade.type}">
                <div class="trade-info">
                    <div class="trade-type ${trade.type}">${trade.type} ${trade.quantity} lot</div>
                    <div class="trade-details">
                        Entry: ${trade.entry_price} | SL: ${trade.stop_loss} | TP: ${trade.take_profit}
                    </div>
                </div>
                <div class="trade-pnl">
                    <div class="trade-pnl-value ${pnlClass}">${pnlSign}$${pnl.toFixed(2)}</div>
                    <button class="close-trade-btn" onclick="closeTrade('${trade.id}')">Close</button>
                </div>
            </div>
        `;
    }).join('');
}

// Update Recent Trades
function updateRecentTrades(recentTrades) {
    const container = document.getElementById('recentTradesList');

    if (!recentTrades || recentTrades.length === 0) {
        container.innerHTML = `<div style="text-align: center; padding: 20px; color: var(--text-secondary); font-size: 14px;">No trades yet</div>`;
        return;
    }

    container.innerHTML = recentTrades.slice().reverse().map(trade => {
        const pnlClass = trade.pnl >= 0 ? 'positive' : 'negative';
        const pnlSign = trade.pnl >= 0 ? '+' : '';
        const time = new Date(trade.exit_time || trade.entry_time).toLocaleTimeString();

        return `
            <div class="recent-trade-item">
                <div class="recent-trade-info">
                    <span style="color: ${trade.type === 'BUY' ? '#22c55e' : '#ef4444'}; font-weight: 700;">${trade.type}</span>
                    ${trade.quantity} lot @ ${trade.entry_price}
                    <span style="color: var(--text-secondary); font-size: 11px;">${time}</span>
                </div>
                <div class="recent-trade-pnl ${pnlClass}">${pnlSign}$${trade.pnl.toFixed(2)}</div>
            </div>
        `;
    }).join('');
}

// Chart.js Setup
function initChart() {
    const ctx = document.getElementById('priceChart').getContext('2d');

    chart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'XAU/USD',
                data: [],
                borderColor: '#3b82f6',
                backgroundColor: 'rgba(59, 130, 246, 0.1)',
                borderWidth: 2,
                fill: true,
                tension: 0.4,
                pointRadius: 0,
                pointHoverRadius: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                intersect: false,
                mode: 'index'
            },
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: '#1e293b',
                    titleColor: '#f8fafc',
                    bodyColor: '#94a3b8',
                    borderColor: '#475569',
                    borderWidth: 1,
                    callbacks: {
                        label: (context) => 'Price: ' + context.parsed.y.toFixed(2)
                    }
                }
            },
            scales: {
                x: {
                    display: false,
                    grid: { display: false }
                },
                y: {
                    position: 'right',
                    grid: {
                        color: 'rgba(71, 85, 105, 0.3)'
                    },
                    ticks: {
                        color: '#94a3b8',
                        font: { size: 10 },
                        callback: (value) => value.toFixed(2)
                    }
                }
            },
            animation: { duration: 0 }
        }
    });
}

function updateChart(tick) {
    if (!chart) return;

    priceData.push({
        x: new Date(tick.timestamp),
        y: tick.close
    });

    if (priceData.length > 100) {
        priceData.shift();
    }

    chart.data.labels = priceData.map(d => d.x);
    chart.data.datasets[0].data = priceData.map(d => d.y);

    // Color based on trend
    const firstPrice = priceData[0]?.y || tick.close;
    const isUp = tick.close >= firstPrice;
    chart.data.datasets[0].borderColor = isUp ? '#22c55e' : '#ef4444';
    chart.data.datasets[0].backgroundColor = isUp ? 'rgba(34, 197, 94, 0.1)' : 'rgba(239, 68, 68, 0.1)';

    chart.update('none');
}

// Trade Modal
function openTradeModal(type) {
    currentTradeType = type;
    document.getElementById('modalTitle').textContent = type + ' XAU/USD';
    document.getElementById('submitTradeBtn').className = 'submit-btn ' + (type === 'BUY' ? 'buy' : 'sell');
    document.getElementById('submitTradeBtn').textContent = 'Place ' + type + ' Order';
    document.getElementById('tradeModal').classList.add('active');
}

function closeModal() {
    document.getElementById('tradeModal').classList.remove('active');
}

async function submitTrade() {
    const quantity = parseFloat(document.getElementById('tradeQuantity').value) || 0.01;
    const stopLoss = document.getElementById('stopLoss').value ? parseFloat(document.getElementById('stopLoss').value) : null;
    const takeProfit = document.getElementById('takeProfit').value ? parseFloat(document.getElementById('takeProfit').value) : null;

    try {
        const res = await fetch(`${API_BASE}/api/trade/open`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                type: currentTradeType,
                quantity: quantity,
                stop_loss: stopLoss,
                take_profit: takeProfit
            })
        });

        const data = await res.json();
        if (data.success) {
            showToast(`${currentTradeType} order placed successfully`, 'success');
            closeModal();
        } else {
            showToast('Failed to place order', 'error');
        }
    } catch (err) {
        showToast('Network error', 'error');
    }
}

async function closeTrade(tradeId) {
    try {
        const res = await fetch(`${API_BASE}/api/trade/close`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ trade_id: tradeId })
        });

        const data = await res.json();
        if (data.success) {
            const pnl = data.trade.pnl;
            const msg = pnl >= 0 ? `Trade closed: +$${pnl.toFixed(2)}` : `Trade closed: $${pnl.toFixed(2)}`;
            showToast(msg, pnl >= 0 ? 'success' : 'error');
        }
    } catch (err) {
        showToast('Failed to close trade', 'error');
    }
}

// Auto Trade Toggle
async function toggleAutoTrade() {
    const enabled = document.getElementById('autoTradeToggle').checked;

    try {
        const res = await fetch(`${API_BASE}/api/auto-trade/settings`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                enabled: enabled,
                risk_per_trade: 0.02,
                max_open_trades: 3,
                min_strength: 70
            })
        });

        const data = await res.json();
        if (data.success) {
            showToast(enabled ? 'AI Auto Trading enabled' : 'AI Auto Trading disabled', 'success');
        }
    } catch (err) {
        showToast('Failed to update settings', 'error');
    }
}

// Reset Portfolio
async function resetPortfolio() {
    if (!confirm('Reset portfolio to $10,000? All trades will be cleared.')) return;

    try {
        const res = await fetch(`${API_BASE}/api/reset`, { method: 'POST' });
        const data = await res.json();
        if (data.success) {
            showToast('Portfolio reset successfully', 'success');
        }
    } catch (err) {
        showToast('Failed to reset', 'error');
    }
}

// Load Initial Data
async function loadInitialData() {
    try {
        // Load price history
        const priceRes = await fetch(`${API_BASE}/api/price/history?limit=100`);
        const priceHistory = await priceRes.json();

        priceData = priceHistory.map(p => ({
            x: new Date(p.timestamp),
            y: p.close
        }));

        if (priceData.length > 0) {
            lastPrice = priceData[priceData.length - 1].y;
            document.getElementById('currentPrice').textContent = lastPrice.toFixed(2);
        }

        // Load portfolio
        const portRes = await fetch(`${API_BASE}/api/portfolio`);
        const portfolio = await portRes.json();
        updatePortfolio(portfolio);

        // Load trades
        const tradesRes = await fetch(`${API_BASE}/api/trades`);
        const trades = await tradesRes.json();
        updateOpenTrades(trades.open);
        updateRecentTrades(trades.closed.slice(-10));

        // Load auto-trade settings
        const autoRes = await fetch(`${API_BASE}/api/auto-trade/settings`);
        const autoSettings = await autoRes.json();
        document.getElementById('autoTradeToggle').checked = autoSettings.enabled;

    } catch (err) {
        console.log('Initial load failed, waiting for WebSocket...');
    }
}

// Toast Notification
function showToast(message, type) {
    const toast = document.getElementById('toast');
    toast.textContent = message;
    toast.className = 'toast show ' + type;

    setTimeout(() => {
        toast.classList.remove('show');
    }, 3000);
}

// Tab Navigation
function showTab(tab) {
    document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));
    event.target.closest('.nav-item').classList.add('active');
}

// Close modal on outside click
document.getElementById('tradeModal').addEventListener('click', (e) => {
    if (e.target === document.getElementById('tradeModal')) {
        closeModal();
    }
});

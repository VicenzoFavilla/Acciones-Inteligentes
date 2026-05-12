import yfinance as yf
import urllib.request
from html.parser import HTMLParser
from datetime import datetime, timedelta
from config.db import get_db

# Cache para tickers del S&P 500
_sp500_cache = {
    "tickers": [],
    "last_updated": None
}

class SP500Parser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_table = False
        self.in_row = False
        self.in_cell = False
        self.cell_index = 0
        self.tickers = []

    def handle_starttag(self, tag, attrs):
        if tag == 'table':
            for attr in attrs:
                if attr[0] == 'id' and attr[1] == 'constituents':
                    self.in_table = True
        
        if self.in_table and tag == 'tr':
            self.in_row = True
            self.cell_index = 0
        
        if self.in_row and tag == 'td':
            self.in_cell = True
            self.cell_index += 1

    def handle_data(self, data):
        if self.in_cell and self.cell_index == 1:
            ticker = data.strip()
            # A veces el ticker está dentro de un link, el parser llamará a handle_data varias veces
            # o el ticker puede estar ya en la lista si hubo un error de parsing previo.
            if ticker and ticker not in self.tickers and len(ticker) < 10:
                # Yahoo Finance usa '-' en lugar de '.' para tickers como BRK.B
                ticker = ticker.replace('.', '-')
                self.tickers.append(ticker)

    def handle_endtag(self, tag):
        if tag == 'table':
            self.in_table = False
        if tag == 'tr':
            self.in_row = False
        if tag == 'td':
            self.in_cell = False


def get_sp500_tickers():
    """Obtiene la lista de tickers del S&P 500 desde Wikipedia con cache de 24h."""
    global _sp500_cache
    
    # Si tenemos cache válida de menos de 24h, la usamos
    if _sp500_cache["tickers"] and _sp500_cache["last_updated"]:
        if datetime.now() - _sp500_cache["last_updated"] < timedelta(hours=24):
            return _sp500_cache["tickers"]

    try:
        url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
        headers = {'User-Agent': 'Mozilla/5.0'}
        req = urllib.request.Request(url, headers=headers)

        with urllib.request.urlopen(req, timeout=10) as response:
            html_content = response.read().decode('utf-8')

        parser = SP500Parser()
        parser.feed(html_content)
        
        if parser.tickers:
            _sp500_cache["tickers"] = parser.tickers
            _sp500_cache["last_updated"] = datetime.now()
            return parser.tickers
    except Exception as e:
        print(f"Error fetching S&P 500 tickers: {e}")
        
    # Fallback si falla la descarga o no hay cache
    return _sp500_cache["tickers"] if _sp500_cache["tickers"] else ["AAPL", "MSFT", "GOOGL", "AMZN", "META", "TSLA", "NVDA", "AMD", "INTC", "BABA"]




def get_stock_info(ticker: str):
    """Obtiene nombre, precio actual, variación diaria y volumen de un ticker.

    Intenta primero `fast_info` (rápido) y hace respaldo con `history()`.
    También persiste un snapshot en MongoDB (colección `history`).
    """
    stock = yf.Ticker(ticker)

    name = ticker.upper()
    current_price = None
    previous_close = None
    volume = None

    # Intento rápido con fast_info
    try:
        fi = stock.fast_info
        if isinstance(fi, dict):
            current_price = fi.get("last_price") or fi.get("regular_market_price")
            previous_close = fi.get("regular_market_previous_close") or fi.get("previous_close")
            volume = fi.get("last_volume") or fi.get("regular_market_volume") or fi.get("volume")
    except Exception:
        pass

    # Respaldo con history()
    if current_price is None or previous_close is None or volume is None:
        try:
            hist = stock.history(period="5d", interval="1d")
            if not hist.empty:
                last_row = hist.iloc[-1]
                if current_price is None:
                    current_price = float(last_row["Close"])
                if volume is None and "Volume" in last_row:
                    volume = int(last_row["Volume"])
                if previous_close is None:
                    if len(hist) >= 2:
                        previous_close = float(hist["Close"].iloc[-2])
                    else:
                        previous_close = float(last_row["Close"])  # mejor que nada
        except Exception:
            pass

    # Nombre (opcional)
    try:
        info = stock.get_info()
        if isinstance(info, dict):
            name = info.get("shortName", name)
    except Exception:
        pass

    if current_price is None or previous_close is None:
        return None

    change = round((current_price - previous_close) / previous_close * 100, 2) if previous_close else None

    # Persistencia en MongoDB (sin prints/UI)
    try:
        db = get_db()
        db.history.insert_one({
            "ticker": ticker,
            "name": name,
            "price": current_price,
            "change": change,
            "volume": volume,
            "timestamp": datetime.now()
        })
    except Exception:
        # Si DB no está disponible, no romper el flujo de la CLI
        pass

    return {
        "ticker": ticker,
        "name": name,
        "price": current_price,
        "change": change,
        "volume": volume,
    }


def get_price_history(ticker: str, period: str = "30d", interval: str = "1d", full=False):
    """Devuelve la serie de cierres diarios u OHLC completo con intervalo personalizable."""
    stock = yf.Ticker(ticker)
    hist = stock.history(period=period, interval=interval)
    if hist is None or hist.empty:
        return None
    if full:
        return hist
    return hist["Close"]

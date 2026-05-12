
import sys
import os

# Añadimos el path del backend para poder importar
sys.path.append(os.path.join(os.getcwd(), "backend"))

from services.stocks import get_sp500_tickers

tickers = get_sp500_tickers()
print(f"Total tickers encontrados: {len(tickers)}")
print(f"Primeros 10: {tickers[:10]}")

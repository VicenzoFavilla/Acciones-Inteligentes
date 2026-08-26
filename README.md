# 📈 Acciones Inteligentes - Plataforma de Asesoramiento Financiero y Agentes de IA Autónomos

**Acciones Inteligentes** evoluciona de un sistema puramente cuantitativo basado en modelos de Machine Learning (XGBoost) hacia una **arquitectura híbrida orientada a Agentes Financieros Autónomos** impulsados por Large Language Models (**Google GenAI / Gemini 2.5 Flash**).

El ecosistema integra análisis de datos en tiempo real de Yahoo Finance, modelos predictivos de Machine Learning, extracción contextual de noticias financieras, control dinámico de riesgo de cartera, ejecución en Paper Trading con supervisión **Human-in-the-Loop (HITL)** y un backend moderno en **FastAPI** junto con un cliente interactivo en **Flutter**.

---

## 🏛️ 1. Visión General de la Arquitectura

La arquitectura híbrida combina la precisión estadística de XGBoost con la capacidad contextual, de razonamiento y de ejecución de Gemini estructurado como agente financiero senior:

| Componente | Tecnología / Herramienta | Responsabilidad Principal |
| :--- | :--- | :--- |
| **Capa Cuantitativa** | Python / XGBoost / Pandas | Generación de predicciones técnicas, cálculo de probabilidades ($P(\text{BUY})$) y señales cuantitativas (`BUY`, `SELL`, `HOLD`). |
| **Capa Contextual** | Yahoo Finance News / Web Scraping | Captura de noticias del mercado, informes financieros y contexto cualitativo en tiempo real (últimas 24-48h). |
| **Orquestador (Agente)** | Google GenAI SDK (`google-genai`) / Gemini 2.5 Flash | Sintetizar señales ML con contexto cualitativo, aplicar reglas de gestión de riesgo y tomar decisiones fundamentadas. |
| **Ejecución & Gestión** | Broker API / Portfolio Manager / MongoDB | Validación de saldo disponible, límites de asignación de capital (máx. 10%), simulación Paper Trading y Human-in-the-Loop. |

---

## 🛠️ 2. Especificación Detallada de Herramientas (Tools)

Las herramientas son funciones nativas de Python que el agente invoca dinámicamente mediante **Function Calling**:

### 2.1. `get_ml_signal(ticker: str) -> dict`
* **Propósito:** Inferencia cuantitativa utilizando el modelo XGBoost precargado y calibrado con 19 indicadores técnicos (RSI, MACD, Medias Móviles, Bandas de Bollinger, ATR, Estocástico).
* **Mapeo de Señal:**
  * Probabilidad $> 0.65 \longrightarrow \text{"BUY"}$
  * Probabilidad $< 0.35 \longrightarrow \text{"SELL"}$
  * $0.35 \le \text{Probabilidad} \le 0.65 \longrightarrow \text{"HOLD"}$
* **Retorno:** `{"ticker": "NVDA", "signal": "BUY", "confidence": 0.8250}`
* **Pros:** Base matemática objetiva libre de sesgo conversacional; respuesta ultra rápida e integración directa.
* **Contras:** Requiere reentrenamiento periódico para evitar degradación de régimen; no contempla noticias de último momento de forma nativa.

### 2.2. `get_market_news(ticker: str, limit: int = 5) -> list[dict]`
* **Propósito:** Recupera titulares, resúmenes, fuentes y marcas temporales de noticias recientes sobre el activo seleccionado para evaluar el sentimiento del mercado y detectar riesgos no capturados.
* **Filtrado estricto:** Yahoo Finance puede devolver titulares sectoriales aunque la consulta sea por ticker. La herramienta sólo conserva una noticia si Yahoo la etiqueta en `relatedTickers` con el símbolo solicitado o si el símbolo aparece de forma explícita en el título o resumen. Así, al seleccionar `NVDA` no se muestran noticias generales de tecnología o de otros activos.
* **Idioma:** Antes de devolverlas, traduce en lote títulos y resúmenes a español neutro mediante Gemini; preserva fuente, fecha y URL. Cada elemento incluye `language: "es"`. Si la traducción no está disponible, no se devuelven titulares en otro idioma.
* **Configuración necesaria:** Definir `GEMINI_API_KEY` en el archivo `.env` del backend (la misma clave ya utilizada por el agente). Sin esa clave, el feed queda vacío de forma intencional para mantener la garantía de idioma.
* **Retorno:** Lista de objetos con `title`, `summary`, `source`, `time_published`, `url` y `language`.
* **Pros:** Cubre el punto ciego cualitativo del modelo numérico ante eventos imprevistos; aporta explicabilidad humana al dictamen.
* **Contras:** Sujeto a límites de cuota (rate limits); requiere filtrado para descartar ruido o titulares clickbait.

### 2.3. `get_portfolio_status(email: str) -> dict`
* **Propósito:** Proporciona visibilidad en tiempo real sobre el balance de efectivo (`cash_balance`), valuación de mercado total (`total_portfolio_value`) y desglose de posiciones abiertas con su PnL.
* **Retorno:** `{"cash_balance": 10000.0, "total_portfolio_value": 11800.0, "positions": [...]}`
* **Pros:** Permite al agente aplicar límites de capital y diversificación inteligente; previene órdenes técnicamente válidas pero financieramente inviables.
* **Contras:** Requiere sincronización constante y consistencia con las transacciones del usuario.

### 2.4. `place_trade_order(ticker: str, action: str, percentage_capital: float, email: str) -> dict`
* **Propósito:** Simula o registra órdenes de compra/venta respetando las políticas de riesgo aprobadas.
* **Regla de Riesgo:** Rechaza automáticamente cualquier operación que intente comprometer **más del 10% del capital total**.
* **Retorno:** `{"transaction_id": "...", "ticker": "AAPL", "action": "BUY", "quantity": 5, "status": "pending_approval"}`
* **Pros:** Automatización end-to-end desde el análisis hasta la generación de órdenes; reduce la latencia de ejecución.
* **Contras:** Requiere manejo robusto de excepciones y control estricto de Human-in-the-Loop.

---

## 🤖 3. Grafo de Decisión del Agente y System Prompt

El agente opera bajo un bucle de control iterativo (*Agent Loop*) gobernado por las siguientes **5 Reglas de Operación**:

```text
1. Siempre consulta la señal cuantitativa mediante 'get_ml_signal'.
2. Si la señal es BUY o SELL, consulta noticias con 'get_market_news' para verificar si hay riesgos no capturados.
3. Antes de ejecutar o recomendar una orden, revisa el portafolio con 'get_portfolio_status'.
4. NUNCA asignes más del 10% del valor total del portafolio a una sola operación.
5. Justifica claramente cada decisión con datos cuantitativos y cualitativos.
```

### Diagrama de Flujo del Grafo de Decisión

```
[Usuario / Consulta] ──> [Gemini 2.5 Flash Orchestrator]
                               │
            ┌──────────────────┴──────────────────┐
            ▼                                     ▼
   [get_ml_signal]                       [get_market_news]
 (Inferencia XGBoost)                  (Noticias de Mercado)
            │                                     │
            └──────────────────┬──────────────────┘
                               ▼
                    [get_portfolio_status]
                   (Validación de Cartera)
                               │
                               ▼
                    [place_trade_order]
                 (Validación Regla <= 10%)
                               │
                               ▼
                 [Human-in-the-Loop: Pendiente]
                               │
                               ▼
                   [Dictamen Final Explicable]
```

---

## 🔒 4. Aislamiento, Auditoría y Human-in-the-Loop

1. **Lazy Loading de Modelos XGBoost (`ml_loader.py`):** Los modelos entrenados y los clasificadores globales se cargan en un singleton en memoria (`ModelCache`), eliminando la sobrecarga de I/O en cada consulta del agente.
2. **Human-in-the-Loop (HITL):** Las órdenes sugeridas se crean en estado `pending_approval`. El usuario puede revisar la justificación y autorizar (`POST /agent/orders/{id}/approve`) o rechazar (`POST /agent/orders/{id}/reject`) la transacción.
3. **Auditoría y Trazas (`agent_traces`):** Cada ejecución del agente almacena en MongoDB la traza completa de herramientas invocadas, argumentos, salidas y razonamiento generado para auditorías de cumplimiento y depuración.

---

## 🌐 5. Endpoints de la API del Agente

* `POST /agent/analyze` - Ejecuta el análisis agéntico completo para un ticker (ej. `{"ticker": "NVDA"}`).
* `GET /agent/traces` - Consulta el historial de trazas y decisiones del agente para auditoría.
* `POST /agent/orders/{order_id}/approve` - Aprueba y ejecuta en la cartera una orden sugerida por la IA.
* `POST /agent/orders/{order_id}/reject` - Descarta una orden generada por el agente.
* `GET /agent/info` - Retorna las capacidades, herramientas y reglas del sistema del Agente Financiero.
* `GET /agent/news/{ticker}?limit=5` - Devuelve exclusivamente noticias verificables del ticker indicado, traducidas a español.

### Rendimiento del gráfico de velas

La pantalla de detalle envuelve el gráfico nativo de velas en un `RepaintBoundary`. Al mover el cursor, el tooltip y las velas se redibujan dentro de ese límite gráfico, sin invalidar el resto del `SingleChildScrollView` (cabecera, análisis, noticias y botones). Esto reduce los bloqueos percibidos durante el hover, especialmente en períodos con muchas velas. El gráfico se recrea únicamente cuando cambian el ticker o el período, mediante su `ValueKey` existente.

### Paginación del mercado

`GET /market` admite `page` y `page_size` (50 por defecto) y devuelve `items`, `total_items`, `total_pages` y `current_page`. El inicio consulta una sola página por vez y presenta controles para avanzar o retroceder de a 50 acciones; por ejemplo, `1–50`, `51–100`, hasta terminar el universo disponible. Esto evita cargar y renderizar todo el mercado en la página inicial.

### Inicio personalizado

El dashboard presenta un resumen de cartera (`total_equity`, PnL diario y porcentaje diario), movimientos destacados de la página de mercado cargada, oportunidades basadas en la señal del modelo y una lista para continuar explorando. Las oportunidades reemplazan visualmente el bloque de acciones populares: cada tarjeta incluye minigráfico de siete días, precio, variación, señal `BUY`/`HOLD`/`SELL`, confianza y motivo breve. Esta última combina posiciones, favoritos, tickers vistos recientemente (guardados localmente) y acciones populares. `GET /opportunities` devuelve como máximo cinco señales informativas y nunca ejecuta órdenes; cada respuesta incluye un aviso para que el usuario valide el análisis antes de operar.

---

## 📂 6. Estructura del Proyecto

```text
Acciones-Inteligentes/
├── src/
│   └── agent/                     # Módulo del Agente (Tools, Orchestrator, ML Loader)
│       ├── __init__.py
│       ├── tools.py               # Las 4 herramientas nativas
│       ├── orchestrator.py        # Grafo de decisión y bucle GenAI
│       └── ml_loader.py           # Lazy loading de XGBoost
├── backend/
│   ├── agent/                     # Paquete del agente integrado en el backend
│   │   ├── tools.py
│   │   ├── orchestrator.py
│   │   └── ml_loader.py
│   ├── api/
│   │   ├── agent.py               # Endpoints REST del agente y HITL
│   │   ├── auth.py, health.py, stocks.py, trading.py, wallet.py, websocket.py
│   ├── config/                    # Base de datos y variables de entorno (Settings)
│   ├── ml/                        # Motores XGBoost, features y entrenamiento
│   ├── services/                  # Wallet, órdenes y Yahoo Finance
│   ├── test/                      # Tests unitarios del agente y de la API
│   ├── tests_consolidated.py      # Suite de pruebas consolidada (29 tests)
│   └── main.py                    # Entrypoint de FastAPI
├── requirements.txt               # Dependencias Python
└── README.md                      # Documentación técnica completa
```

---

## 🚀 7. Instalación y Configuración

### 1. Requisitos Previos
* Python 3.10+ (Recomendado **Python 3.12**)
* Flutter SDK (para la aplicación móvil/escritorio)
* MongoDB en ejecución local o remota.

### 2. Configurar el Backend y API Key
```bash
# 1. Crear y activar entorno virtual
python -m venv entorno-v
.\entorno-v\Scripts\activate       # Windows
# source entorno-v/bin/activate    # Linux / macOS

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Configurar API Key de Gemini en .env o entorno
# GEMINI_API_KEY=tu_api_key_aqui
```

### 3. Iniciar el Servidor FastAPI
```bash
cd backend
uvicorn main:app --reload --port 8001
```

---

## 🧪 8. Pruebas Automatizadas

La suite de pruebas unificada y consolidada valida todas las capas del sistema (Autenticación, Billeteras, Órdenes, Machine Learning, Tools del Agente, Grafo de Decisión y endpoints REST).

Para ejecutar la suite completa:

```bash
cd backend
pytest tests_consolidated.py -v
```

Para ejecutar los tests específicos del Agente Financiero:

```bash
cd backend
pytest test/test_agent_tools.py test/test_agent_orchestrator.py test/test_agent_api.py -v
```

La prueba `test_tool_get_market_news_filters_by_ticker_and_translates_to_spanish` cubre específicamente que se descarte una noticia sectorial sin `NVDA` y que el resultado publicado sea español.

---

## ⚖️ Licencia
Este proyecto está bajo la licencia MIT.

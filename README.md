# 📈 Acciones Inteligentes - Asesor Financiero con ML

**Acciones Inteligentes** es una plataforma moderna de asesoramiento financiero que combina el análisis de datos en tiempo real de Yahoo Finance con técnicas avanzadas de Machine Learning (XGBoost) para ofrecer recomendaciones de inversión personalizadas.

La aplicación cuenta con un ecosistema completo: un backend robusto en **FastAPI** y una aplicación móvil/escritorio intuitiva desarrollada en **Flutter**.

---

## 🎨 Características Principales

### 🌓 Interfaz Dinámica (Modo Claro/Oscuro)
- Sistema de temas global y persistente.
*   Diseño "Premium" con acentos en azul celeste y animaciones sutiles.
*   Elegible desde la pestaña de Configuración.

### 💰 Billetera y Portafolio Virtual
*   Gestión de saldo virtual para simular inversiones sin riesgo.
*   Cálculo automático de **P&L (Ganancias y Pérdidas)** por activo y total del patrimonio.
*   Historial detallado de todas las operaciones realizadas.

### 🤖 Inteligencia Artificial y Datos
- **Modelo XGBoost Optimizado:** Implementación avanzada y regularizada para mitigar el sobreajuste (overfitting) en datos de mercado ruidosos.
- **Ingeniería de Variables Avanzada (19 Indicadores Técnicos):** Cálculo nativo y vectorizado en Pandas/Numpy de:
  - *Tendencia:* EMA 5, EMA 20.
  - *Momentum:* RSI (14), MACD & Histograma MACD (12, 26, 9), ROC (10).
  - *Volatilidad y Canales:* Bandas de Bollinger (20, 2) (distancias superior/inferior, ancho de banda), ATR Normalizado porcentual (`ATR_Pct`).
  - *Osciladores:* Estocástico rápido/lento (`%K`, `%D`).
  - *Retorno y Volatilidad:* Retornos porcentuales diarios y desviación estándar de corto plazo.
- **Calibración Dinámica de Umbral (F1-Score):** Búsqueda dinámica del umbral de decisión óptimo en el set de validación para maximizar el F1-Score (balance ideal de Precisión y Exhaustividad) en lugar de usar un umbral rígido del 50%.
- **Gráficos Financieros Interactivos:** Velas japonesas (**Candlesticks**) e históricos de precios detallados.
- **Simulación en Tiempo Real:** Transmisión de datos y recomendaciones actualizadas vía **WebSockets**.
- **Documentación Especializada:** Para conocer los detalles matemáticos de los indicadores, regularizaciones e hiperparámetros, consulta la [Documentación del Motor de ML](file:///c:/proyectos/acciones_inteligentes/Machine-learning/backend/ml/README.md).

### 🔐 Seguridad y Autenticación
- Sistema de usuarios con contraseñas hasheadas (**Bcrypt**).
- Protección de endpoints mediante tokens **JWT (JSON Web Tokens)**.

---

## 🛠️ Stack Tecnológico

**Frontend:**
*   [Flutter](https://flutter.dev/) (UI Framework)
*   [Google Fonts](https://fonts.google.com/) (Tipografía Poppins)
*   [FL Chart](https://pub.dev/packages/fl_chart) (Gráficos financieros)
*   [SharedPreferences](https://pub.dev/packages/shared_preferences) (Persistencia de configuración)

**Backend:**
*   [Python / FastAPI](https://fastapi.tiangolo.com/) (Web Framework)
*   [MongoDB](https://www.mongodb.com/) (Base de datos NoSQL)
*   [YFinance](https://github.com/ranaroussi/yfinance) (Datos de mercado reales)
*   [Scikit-learn / XGBoost](https://xgboost.readthedocs.io/) (Cerebro de ML)

---

## 📂 Estructura del Proyecto

```text
Acciones-Inteligentes/
├── frontend/               # Código fuente de Flutter
│   ├── lib/
│   │   ├── screens/        # Pantallas (Login, Wallet, History, Settings)
│   │   └── main.dart       # Lógica central y navegación
├── backend/                # API en Python FastAPI
│   ├── config/             # Singleton de bases de datos
│   ├── ml/                 # Modelos XGBoost y lógica de recomendación
│   ├── services/           # Integración con Yahoo Finance y Wallet
│   ├── test/               # Suite de pruebas automatizadas
│   └── main.py             # Entrypoint de la API
└── requirements.txt        # Dependencias de Python
```

---

## 🚀 Instalación y Configuración

### 1. Requisitos Previos
*   Instalar [Python 3.10+](https://www.python.org/)
*   Instalar [Flutter SDK](https://docs.flutter.dev/get-started/install)
*   Tener una instancia de [MongoDB](https://www.mongodb.com/try/download/community) corriendo localmente.

### 2. Configurar el Backend
```bash
cd backend
python -m venv venv
# Activar venv (Windows: .\venv\Scripts\activate | Unix: source venv/bin/activate)
pip install -r ../requirements.txt
uvicorn main:app --reload --port 8001
```

### 3. Configurar el Frontend
```bash
cd frontend
flutter pub get
flutter run
```

---

## 🧪 Pruebas Automatizadas

Hemos consolidado y unificado la suite de pruebas automatizadas del backend para asegurar la máxima estabilidad en todas las capas (Autenticación, Motor de Órdenes, Billeteras Virtuales, API y el Motor de Machine Learning).

Para ejecutar la suite de pruebas consolidada:

```bash
cd backend
python -m pytest tests_consolidated.py
```

---

## ⚖️ Licencia
Este proyecto está bajo la licencia MIT.

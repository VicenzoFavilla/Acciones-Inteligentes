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
- Recomendaciones inteligentes basadas en modelos **XGBoost**.
- Gráficos de velas (**Candlesticks**) e históricos de precios.
- Simulación de mercado en tiempo real vía **WebSockets**.

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

Hemos incluido una suite de pruebas para asegurar la estabilidad del backend. Para ejecutarlos:

```bash
cd backend
python test/test_back/test_api.py
```

---

## ⚖️ Licencia
Este proyecto está bajo la licencia MIT.

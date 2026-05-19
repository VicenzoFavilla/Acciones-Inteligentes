# 🤖 Módulo de Machine Learning (ML) y Optimización XGBoost

Este directorio contiene el motor de predicción y asesoramiento financiero inteligente de **Acciones Inteligentes**. El sistema utiliza modelos **XGBoost** altamente optimizados y regularizados junto con una suite avanzada de indicadores técnicos para ofrecer las recomendaciones más precisas posibles de compra y espera.

---

## 📊 Arquitectura del Dataset (Ingeniería de Variables)

El archivo [`features.py`](features.py) es el responsable de calcular un conjunto de **19 variables técnicas avanzadas** a partir de datos básicos de precios OHLCV (Open, High, Low, Close, Volume) provenientes de Yahoo Finance.

Toda la ingeniería de variables está escrita utilizando **Pandas** y **Numpy** vectorizados nativos para eliminar dependencias binarias pesadas y garantizar la máxima velocidad.

### Variables Incluidas:
1.  **Datos de Volumen y Retornos:**
    *   `Return`: Retorno porcentual diario del precio de cierre.
    *   `Volatility`: Volatilidad de corto plazo (desviación estándar móvil de 5 periodos).
2.  **Indicadores de Tendencia y Medias Móviles:**
    *   `EMA5` y `EMA20`: Medias móviles exponenciales rápidas y lentas.
3.  **Indicadores de Momentum:**
    *   `RSI` (Relative Strength Index de 14 periodos): Captura condiciones de sobrecompra (>70) y sobreventa (<30).
    *   `MACD` & `MACD_Hist` (Moving Average Convergence Divergence 12, 26, 9): Determina el impulso relativo y giros de tendencia.
    *   `ROC` (Rate of Change de 10 periodos): Mide la velocidad de cambio del precio.
4.  **Indicadores de Rango y Canales (Volatilidad):**
    *   `BB_High_Dist` y `BB_Low_Dist`: Distancia porcentual del precio a la banda de Bollinger superior e inferior (20 periodos, 2 stddev).
    *   `BB_Width`: Ancho de las bandas de Bollinger para capturar compresiones de volatilidad (squeeze).
5.  **Indicadores de Rango Medio:**
    *   `ATR_Pct` (Average True Range normalizado de 14 periodos): Rango de movimiento promedio del activo normalizado frente a su precio para evitar sesgos de escala nominal.
6.  **Osciladores de Giro:**
    *   `Stoch_K` y `Stoch_D` (Oscilador Estocástico 14, 3): Captura giros rápidos en rangos de precios.

---

## ⚙️ Optimización de XGBoost (Evitando Overfitting)

Los mercados financieros son altamente ruidosos. Los modelos de árboles de decisión complejos tienden a memorizar el ruido en lugar de aprender patrones. Para mitigar esto, hemos configurado hiperparámetros de regularización estrictos en [`trainer.py`](trainer.py) y [`global_models.py`](global_models.py):

*   **`max_depth=4`:** Reducimos la profundidad de los árboles de 5 a 4 para prevenir el sobreajuste y favorecer reglas de decisión generalizables.
*   **`learning_rate=0.03`:** Un ritmo de aprendizaje más lento permite un ajuste robusto durante el descenso de gradiente.
*   **`reg_alpha=0.1` & `reg_lambda=3.0`:** Penalizaciones de regularización L1 (Lasso) y L2 (Ridge) respectivamente para limitar el peso de variables poco informativas.
*   **`min_child_weight=3`:** Exige un número mínimo de muestras para crear una nueva rama, reduciendo las divisiones frágiles.
*   **`gamma=0.1`:** Incrementa el umbral de ganancia mínimo requerido para realizar particiones adicionales.
*   **Historial Ampliado (`periodo="1y"`):** Aumentamos el conjunto de entrenamiento local a 1 año de datos históricos para capturar ciclos completos de mercado.

---

## 🎯 Umbral Dinámico Óptimo (Optimal Threshold Calibration)

En lugar de utilizar una clasificación rígida con probabilidad del `50%` (`0.5`) para generar la señal de "comprar", implementamos un **algoritmo de búsqueda de umbral óptimo** en el set de validación durante el entrenamiento:

1.  El modelo se entrena en el conjunto de entrenamiento temporal (80% inicial).
2.  Extraemos las probabilidades predichas para el conjunto de validación (20% final).
3.  Iteramos en el rango de umbrales `[0.3, 0.7]` con incrementos de `0.02`.
4.  Para cada umbral, calculamos el **F1-Score** (la media armónica entre precisión y exhaustividad).
5.  El umbral que maximiza el F1-Score se almacena en el atributo `optimal_threshold` del booster.
6.  Al persistir el modelo en **MongoDB** y en el sistema de archivos (FS), este atributo se serializa mediante `joblib`.
7.  Al predecir en [`recomendacion.py`](recomendacion.py), extraemos dinámicamente este umbral y el sistema calibra su decisión automáticamente.

---

## 🛠️ Ejecución y Entrenamiento

### Actualizar Modelos Globales (XGB y MLP)
Para iniciar un entrenamiento de los modelos globales con los tickers más consultados de la base de datos o tickers personalizados:

```bash
cd backend
# Ejecutar entrenamiento incremental con periodo de 2 años
..\.venv\Scripts\python.exe scripts/update_models.py
```

### Entrenar Modelo Local
El modelo local de un ticker se entrena automáticamente a través del endpoint de predicción si no existe previamente en MongoDB, optimizando su umbral en tiempo real.

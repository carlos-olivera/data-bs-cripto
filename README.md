# Monitor de Precios de Criptomonedas

Este proyecto permite monitorear y registrar los precios de criptomonedas, específicamente:
- Precio de Bitcoin en USD
- Precio de USDT en BOB (Boliviano)
- Precio calculado de Bitcoin en BOB


## Características

- Obtención de precios de Bitcoin desde CoinGecko API
- Obtención de precios de USDT/BOB desde Binance P2P
- Cálculo automático de la tasa de conversión BOB/BTC
- Almacenamiento de datos en MongoDB
- Ejecución programada en intervalos configurables
- Sistema de reintentos para conexiones fallidas a Binance (3 intentos con 1 minuto de espera)
- Registro detallado de operaciones (logging)
- Análisis de tendencias de precios con alertas configurables
- Notificaciones automáticas a Telegram cuando se detectan variaciones significativas

## Estructura del Proyecto

- `binance_p2p.py`: Módulo para obtener ofertas P2P de Binance (BOB/USDT)
- `bitcoin_value.py`: Módulo para obtener el precio actual de Bitcoin en USD
- `cripto_data.py`: Script principal que combina los datos y los almacena
- `analisis_tendencias.py`: Módulo para analizar tendencias de precios
- `telegram_notifier.py`: Módulo para enviar notificaciones a Telegram
- `test_notificaciones.py`: Script para probar las notificaciones
- `.env`: Archivo de configuración de variables de entorno
- `.env.example`: Ejemplo de configuración de variables de entorno
- `requirements.txt`: Dependencias del proyecto

## Requisitos

- Python 3.11 o superior
- MongoDB
- Dependencias listadas en `requirements.txt`

## Instalación

1. Clonar el repositorio
2. Crear un entorno virtual:
   ```
   python -m venv binance-env
   source binance-env/bin/activate  # En Windows: binance-env\Scripts\activate
   ```
3. Instalar dependencias:
   ```
   pip install -r requirements.txt
   ```
4. Configurar el archivo `.env` con los parámetros necesarios

## Configuración

Editar el archivo `.env` con los siguientes parámetros:

```
# Intervalo de tiempo en minutos para actualizar los datos
UPDATE_INTERVAL=10

# Intervalo de tiempo en minutos para analizar tendencias (4 horas = 240 minutos)
ANALYSIS_INTERVAL=240

# Configuración de MongoDB
MONGO_USER=usuario
MONGO_PASSWORD=contraseña
MONGO_HOST=localhost
MONGO_PORT=27017
MONGO_DB=cripto_db
MONGO_AUTH_SOURCE=admin

# Configuración de Telegram para notificaciones
TELEGRAM_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_chat_id
```

### Configuración de Telegram

Para configurar las notificaciones de Telegram:

1. Crea un bot de Telegram usando [@BotFather](https://t.me/BotFather) y obtiene el token
2. Obtiene tu Chat ID iniciando una conversación con [@userinfobot](https://t.me/userinfobot)
3. Configura las variables `TELEGRAM_TOKEN` y `TELEGRAM_CHAT_ID` en el archivo `.env`

## Uso

### Ejecución principal

Ejecutar el script principal:

```
python cripto_data.py
```

El programa obtendrá datos de precios en los intervalos configurados, los almacenará en MongoDB y realizará análisis de tendencias enviando notificaciones cuando sea necesario.

### Prueba de notificaciones

Para probar las notificaciones de Telegram:

```
python test_notificaciones.py
```

Opciones disponibles:

```
python test_notificaciones.py --simple   # Prueba mensaje simple
python test_notificaciones.py --alerta   # Prueba alerta de tendencia
python test_notificaciones.py --completo # Ejecuta análisis con datos reales
```

## Comportamiento ante fallos

- Si la conexión a Binance falla, el sistema reintentará hasta 3 veces con intervalos de 1 minuto.
- Si después de los 3 intentos no se puede conectar, se abortará el registro de datos para ese ciclo.
- El sistema volverá a intentar en el siguiente ciclo programado según la configuración de `UPDATE_INTERVAL`.
- Si no se pueden enviar notificaciones a Telegram, el sistema registrará el error pero continuará funcionando.

## Análisis de tendencias

El sistema analiza las tendencias de precios con las siguientes características:

- Detecta variaciones significativas en el precio de USDT/BOB (umbral: 2%)
- Detecta variaciones significativas en el precio de BTC/USD (umbral: 5%)
- Envía notificaciones a Telegram cuando se detectan variaciones
- Identifica tendencias alcistas y bajistas
- Proporciona recomendaciones de compra/venta según la tendencia
- Se ejecuta automáticamente cada 4 horas (configurable)

## Licencia

Este proyecto está bajo la Licencia MIT. Ver el archivo `LICENSE` para más detalles.

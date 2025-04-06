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

## Estructura del Proyecto

- `binance_p2p.py`: Módulo para obtener ofertas P2P de Binance (BOB/USDT)
- `bitcoin_value.py`: Módulo para obtener el precio actual de Bitcoin en USD
- `cripto_data.py`: Script principal que combina los datos y los almacena
- `.env`: Archivo de configuración de variables de entorno
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

# Configuración de MongoDB
MONGO_USER=usuario
MONGO_PASSWORD=contraseña
MONGO_HOST=localhost
MONGO_PORT=27017
MONGO_DB=cripto_db
MONGO_AUTH_SOURCE=admin
```

## Uso

Ejecutar el script principal:

```
python cripto_data.py
```

El programa obtendrá datos de precios en los intervalos configurados y los almacenará en MongoDB.

## Comportamiento ante fallos

- Si la conexión a Binance falla, el sistema reintentará hasta 3 veces con intervalos de 1 minuto.
- Si después de los 3 intentos no se puede conectar, se abortará el registro de datos para ese ciclo.
- El sistema volverá a intentar en el siguiente ciclo programado según la configuración de `UPDATE_INTERVAL`.

## Licencia

Este proyecto está bajo la Licencia MIT. Ver el archivo `LICENSE` para más detalles.

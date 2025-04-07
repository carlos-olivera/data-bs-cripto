import json
import time
import os
import logging
from datetime import datetime
import schedule
from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from binance_p2p import obtener_ofertas_p2p_binance, calcular_precio_promedio
from bitcoin_value import obtener_precio_bitcoin_usd
from analisis_tendencias import analizar_tendencias, ejecutar_una_vez as ejecutar_analisis_una_vez

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("cripto_data.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("cripto_data")

# Cargar variables de entorno
load_dotenv()

def obtener_datos_cripto():
    """
    Obtiene y combina datos de criptomonedas:
    - Fecha y hora actual
    - Precio de Bitcoin en USD
    - Precio de Boliviano a USDT
    - Precio calculado de Boliviano a Bitcoin
    
    Returns:
        dict: Objeto con los datos combinados o None si falló la obtención de datos de Binance
    """
    # Obtener fecha y hora actual
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Obtener precio de Bitcoin en USD
    bitcoin_usd = obtener_precio_bitcoin_usd()
    if bitcoin_usd is None:
        bitcoin_usd = 0.0
    
    # Obtener ofertas de BOB a USDT (compra de USDT)
    ofertas_bob_usdt, _ = obtener_ofertas_p2p_binance(
        fiat="BOB",
        crypto="USDT",
        trade_type="BUY",
        page_size=10,
        only_verified=True
    )
    
    # Verificar si se obtuvieron datos de Binance - si falla, abortar todo el proceso
    if ofertas_bob_usdt is None:
        logger.error("No se pudieron obtener datos de Binance para BOB a USDT. Abortando registro.")
        return None
    
    # Calcular precio promedio de BOB a USDT (compra de USDT)
    bob_usdt = calcular_precio_promedio(ofertas_bob_usdt)
    
    # Obtener ofertas de USDT a BOB (venta de USDT)
    ofertas_usdt_bob, _ = obtener_ofertas_p2p_binance(
        fiat="BOB",
        crypto="USDT",
        trade_type="SELL",
        page_size=10,
        only_verified=True
    )
    
    # Verificar si se obtuvieron datos de Binance - si falla, abortar todo el proceso
    if ofertas_usdt_bob is None:
        logger.error("No se pudieron obtener datos de Binance para USDT a BOB. Abortando registro.")
        return None
    
    # Calcular precio promedio de USDT a BOB (venta de USDT)
    usdt_bob = calcular_precio_promedio(ofertas_usdt_bob)
    
    # Calcular precio de BOB a BTC (usando USDT como intermediario)
    # BOB/BTC = (BOB/USDT) / (BTC/USD) asumiendo que USDT ≈ USD
    bob_btc = 0.0
    if bitcoin_usd > 0:
        bob_btc = bob_usdt / bitcoin_usd
    
    # Crear objeto JSON con los datos
    datos = {
        "datetime": timestamp,
        "btc2usd": round(bitcoin_usd, 2),
        "bol2usdt": bob_usdt,
        "usdt2bol": usdt_bob,
        "bol2btc": round(bob_btc, 8)  # Bitcoin se suele mostrar con 8 decimales
    }
    
    return datos

def conectar_mongodb():
    """
    Establece conexión con MongoDB usando las credenciales de las variables de entorno.
    
    Returns:
        MongoClient: Cliente de MongoDB o None si hay error
    """
    try:
        # Obtener variables de entorno para MongoDB
        mongo_user = os.getenv("MONGO_USER")
        mongo_password = os.getenv("MONGO_PASSWORD")
        mongo_host = os.getenv("MONGO_HOST")
        mongo_port = os.getenv("MONGO_PORT")
        mongo_db = os.getenv("MONGO_DB")
        mongo_auth_source = os.getenv("MONGO_AUTH_SOURCE")
        
        # Construir URI de conexión
        mongo_uri = f"mongodb://{mongo_user}:{mongo_password}@{mongo_host}:{mongo_port}/{mongo_db}?authSource={mongo_auth_source}"
        
        # Intentar conexión con timeout
        client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
        # Verificar conexión
        client.admin.command('ping')
        logger.info("Conexión a MongoDB establecida correctamente")
        return client
    except (ConnectionFailure, ServerSelectionTimeoutError) as e:
        logger.error(f"Error al conectar a MongoDB: {str(e)}")
        return None

def guardar_datos_mongodb(datos):
    """
    Guarda los datos en MongoDB.
    
    Args:
        datos (dict): Datos a guardar
        
    Returns:
        bool: True si se guardó correctamente, False en caso contrario
    """
    try:
        client = conectar_mongodb()
        if client is None:
            return False
            
        # Obtener base de datos y colección
        db = client[os.getenv("MONGO_DB")]
        coleccion = db["precios"]
        
        # Insertar documento
        resultado = coleccion.insert_one(datos)
        
        # Cerrar conexión
        client.close()
        
        logger.info(f"Datos guardados correctamente con ID: {resultado.inserted_id}")
        return True
    except Exception as e:
        logger.error(f"Error al guardar datos en MongoDB: {str(e)}")
        return False

def tarea_programada():
    """
    Tarea que se ejecuta periódicamente para obtener y guardar los datos.
    """
    try:
        logger.info("Ejecutando tarea programada para obtener datos de criptomonedas")
        
        # Obtener datos
        datos_cripto = obtener_datos_cripto()
        
        # Verificar si se obtuvieron datos de Binance
        if datos_cripto is None:
            logger.error("No se pudieron obtener datos de Binance después de todos los reintentos. Abortando registro.")
            return
        
        # Mostrar en consola
        print(json.dumps(datos_cripto, indent=2))
        
        # Guardar en MongoDB
        guardado = guardar_datos_mongodb(datos_cripto)
        if not guardado:
            logger.warning("No se pudieron guardar los datos en MongoDB")
            
    except Exception as e:
        logger.error(f"Error en la tarea programada: {str(e)}")

def configurar_tareas_programadas():
    """
    Configura todas las tareas programadas del sistema.
    """
    # Obtener intervalo de actualización desde variables de entorno
    intervalo_datos = int(os.getenv("UPDATE_INTERVAL", "10"))
    intervalo_analisis = int(os.getenv("ANALYSIS_INTERVAL", "240"))  # 4 horas por defecto (en minutos)
    
    # Programar recolección de datos
    schedule.every(intervalo_datos).minutes.do(tarea_programada)
    logger.info(f"Tarea de recolección de datos programada cada {intervalo_datos} minutos")
    
    # Programar análisis de tendencias
    schedule.every(intervalo_analisis).minutes.do(analizar_tendencias)
    logger.info(f"Tarea de análisis de tendencias programada cada {intervalo_analisis} minutos")
    
    # Calcular próximas ejecuciones
    proxima_recoleccion = schedule.next_run()
    logger.info(f"Próxima recolección de datos: {proxima_recoleccion}")

if __name__ == "__main__":
    try:
        logger.info("Iniciando servicio de monitoreo y análisis de criptomonedas")
        
        # Ejecutar inmediatamente las tareas al iniciar
        logger.info("Ejecutando recolección de datos inicial...")
        tarea_programada()
        
        logger.info("Ejecutando análisis de tendencias inicial...")
        ejecutar_analisis_una_vez()
        
        # Configurar tareas programadas
        configurar_tareas_programadas()
        
        # Bucle principal
        logger.info("Iniciando bucle principal de tareas programadas")
        while True:
            schedule.run_pending()
            time.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Servicio detenido por el usuario")
    except Exception as e:
        logger.error(f"Error en el servicio: {str(e)}")

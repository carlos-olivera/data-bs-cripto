#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import logging
import time
import schedule
import statistics
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from dotenv import load_dotenv
from telegram_notifier import get_telegram_notifier

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("analisis_tendencias.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("analisis_tendencias")

# Cargar variables de entorno
load_dotenv()

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

def obtener_datos_ultimas_horas(horas=4):
    """
    Obtiene los datos de precios de las últimas n horas desde MongoDB.
    
    Args:
        horas (int): Número de horas hacia atrás para obtener datos
        
    Returns:
        list: Lista de documentos con los datos de precios o None si hay error
    """
    try:
        # Calcular la fecha límite (hace n horas)
        fecha_limite = datetime.now() - timedelta(hours=horas)
        fecha_limite_str = fecha_limite.strftime("%Y-%m-%d %H:%M:%S")
        
        # Conectar a MongoDB
        client = conectar_mongodb()
        if client is None:
            return None
            
        # Obtener base de datos y colección
        db = client[os.getenv("MONGO_DB")]
        coleccion = db["precios"]
        
        # Consultar documentos más recientes que la fecha límite
        # La fecha está almacenada como string en formato "YYYY-MM-DD HH:MM:SS"
        query = {"datetime": {"$gte": fecha_limite_str}}
        
        # Ordenar por fecha ascendente
        documentos = list(coleccion.find(query).sort("datetime", 1))
        
        # Cerrar conexión
        client.close()
        
        logger.info(f"Se obtuvieron {len(documentos)} registros de las últimas {horas} horas")
        return documentos
        
    except Exception as e:
        logger.error(f"Error al obtener datos de MongoDB: {str(e)}")
        return None

def calcular_variacion_porcentual(valor_inicial, valor_final):
    """
    Calcula la variación porcentual entre dos valores.
    
    Args:
        valor_inicial (float): Valor inicial
        valor_final (float): Valor final
        
    Returns:
        float: Variación porcentual
    """
    if valor_inicial == 0:
        return 0
    return ((valor_final - valor_inicial) / valor_inicial) * 100

def detectar_tendencia_significativa(datos, campo="bol2usdt", umbral_variacion=2.0, notificar=True):
    """
    Detecta si hay una tendencia significativa en los datos.
    
    Estrategia:
    1. Divide los datos en ventanas de tiempo (cada hora)
    2. Calcula la media y desviación estándar para cada ventana
    3. Analiza la tendencia general y la variación porcentual
    4. Detecta si la variación supera el umbral establecido (tanto alcista como bajista)
    5. Envía notificaciones a Telegram si se detecta una tendencia significativa
    
    Args:
        datos (list): Lista de documentos con los datos de precios
        campo (str): Campo a analizar (bol2usdt para precio de compra de USDT)
        umbral_variacion (float): Umbral de variación porcentual para considerar significativo
        notificar (bool): Si es True, envía notificaciones a Telegram
        
    Returns:
        tuple: (hay_tendencia, variacion_porcentual, mensaje, detalles)
    """
    if not datos or len(datos) < 2:
        return False, 0, "Datos insuficientes para análisis"
    
    # Convertir a DataFrame para facilitar el análisis
    df = pd.DataFrame(datos)
    
    # Convertir datetime de string a objeto datetime para agrupar
    df['datetime'] = pd.to_datetime(df['datetime'])
    
    # Verificar que el campo a analizar existe
    if campo not in df.columns:
        return False, 0, f"El campo {campo} no existe en los datos"
    
    # Obtener el primer y último valor para calcular la variación total
    primer_valor = df[campo].iloc[0]
    ultimo_valor = df[campo].iloc[-1]
    variacion_total = calcular_variacion_porcentual(primer_valor, ultimo_valor)
    
    # Agrupar por hora y calcular estadísticas
    df['hora'] = df['datetime'].dt.floor('H')
    stats_por_hora = df.groupby('hora')[campo].agg(['mean', 'std', 'count', 'min', 'max'])
    
    # Calcular la tendencia usando regresión lineal simple
    x = np.arange(len(stats_por_hora))
    y = stats_por_hora['mean'].values
    
    # Si hay suficientes puntos, calcular la pendiente de la regresión
    if len(x) > 1:
        pendiente, _ = np.polyfit(x, y, 1)
        direccion_tendencia = "alcista" if pendiente > 0 else "bajista"
    else:
        pendiente = 0
        direccion_tendencia = "neutral"
    
    # Calcular la volatilidad (promedio de desviaciones estándar)
    volatilidad_promedio = stats_por_hora['std'].mean()
    
    # Calcular la variación máxima entre cualquier par de horas consecutivas
    variaciones_entre_horas = []
    for i in range(1, len(stats_por_hora)):
        valor_anterior = stats_por_hora['mean'].iloc[i-1]
        valor_actual = stats_por_hora['mean'].iloc[i]
        variacion = calcular_variacion_porcentual(valor_anterior, valor_actual)
        variaciones_entre_horas.append(abs(variacion))
    
    variacion_maxima_entre_horas = max(variaciones_entre_horas) if variaciones_entre_horas else 0
    
    # Determinar si hay una tendencia significativa (tanto alcista como bajista)
    hay_tendencia = abs(variacion_total) >= umbral_variacion or variacion_maxima_entre_horas >= umbral_variacion
    
    # Crear mensaje informativo
    mensaje = f"""
Análisis de tendencia para {campo} en las últimas {len(stats_por_hora)} horas:
- Valor inicial: {primer_valor:.2f}
- Valor final: {ultimo_valor:.2f}
- Variación total: {variacion_total:.2f}%
- Tendencia: {direccion_tendencia} (pendiente: {pendiente:.4f})
- Volatilidad promedio: {volatilidad_promedio:.2f}
- Variación máxima entre horas consecutivas: {variacion_maxima_entre_horas:.2f}%
"""
    
    # Preparar detalles para posible notificación
    detalles = {
        "asset": "USDT/BOB" if campo == "bol2usdt" else "BOB/USDT" if campo == "usdt2bol" else "BTC/USD",
        "trend_type": "ALCISTA" if variacion_total > 0 else "BAJISTA",
        "variation": variacion_total,
        "price_info": f"Valor inicial: {primer_valor:.2f}\nValor final: {ultimo_valor:.2f}\nVolatilidad: {volatilidad_promedio:.2f}",
        "recommendation": ""
    }
    
    if hay_tendencia:
        if variacion_total > 0:
            mensaje += f"\n¡ALERTA! Se detectó una variación ALCISTA significativa de {variacion_total:.2f}% (umbral: {umbral_variacion}%)"
            if campo == "bol2usdt":
                recomendacion = "Posible oportunidad de VENTA de USDT (precio alto)"
                mensaje += "\n" + recomendacion
                detalles["recommendation"] = recomendacion
            elif campo == "btc2usd":
                recomendacion = "Posible oportunidad de VENTA de BTC (precio alto)"
                mensaje += "\n" + recomendacion
                detalles["recommendation"] = recomendacion
        else:
            mensaje += f"\n¡ALERTA! Se detectó una variación BAJISTA significativa de {variacion_total:.2f}% (umbral: {umbral_variacion}%)"
            if campo == "bol2usdt":
                recomendacion = "Posible oportunidad de COMPRA de USDT (precio bajo)"
                mensaje += "\n" + recomendacion
                detalles["recommendation"] = recomendacion
            elif campo == "btc2usd":
                recomendacion = "Posible oportunidad de COMPRA de BTC (precio bajo)"
                mensaje += "\n" + recomendacion
                detalles["recommendation"] = recomendacion
        
        # Enviar notificación a Telegram si está habilitado
        if notificar and hay_tendencia:
            try:
                notifier = get_telegram_notifier()
                notifier.send_trend_alert(
                    asset=detalles["asset"],
                    trend_type=detalles["trend_type"],
                    variation=detalles["variation"],
                    price_info=detalles["price_info"],
                    recommendation=detalles["recommendation"]
                )
                logger.info(f"Notificación de tendencia enviada a Telegram: {detalles['asset']} - {detalles['trend_type']}")
            except Exception as e:
                logger.error(f"Error al enviar notificación a Telegram: {str(e)}")
    
    return hay_tendencia, variacion_total, mensaje, detalles

def analizar_tendencias(notificar=True):
    """
    Función principal que analiza las tendencias de precios.
    Se ejecuta cada 4 horas según la programación.
    
    Args:
        notificar (bool): Si es True, envía notificaciones a Telegram
    
    Returns:
        dict: Resultados del análisis con las tendencias detectadas
    """
    logger.info("Iniciando análisis de tendencias de precios...")
    
    # Resultados para devolver
    resultados = {
        "bol2usdt": {"hay_tendencia": False, "detalles": None},
        "usdt2bol": {"hay_tendencia": False, "detalles": None},
        "btc2usd": {"hay_tendencia": False, "detalles": None},
    }
    
    # Obtener datos de las últimas 4 horas
    datos = obtener_datos_ultimas_horas(horas=4)
    
    if datos is None or len(datos) == 0:
        logger.error("No se pudieron obtener datos para el análisis")
        return resultados
    
    # Detectar tendencia significativa en el precio de compra de USDT (bol2usdt)
    hay_tendencia, variacion, mensaje, detalles = detectar_tendencia_significativa(
        datos, 
        campo="bol2usdt", 
        umbral_variacion=2.0,
        notificar=notificar
    )
    
    # Guardar resultados
    resultados["bol2usdt"] = {"hay_tendencia": hay_tendencia, "detalles": detalles}
    
    # Imprimir resultados
    if hay_tendencia:
        logger.warning(mensaje)
        print("\n" + "="*80)
        print(mensaje)
        print("="*80 + "\n")
    else:
        logger.info(mensaje)
        print(mensaje)
    
    # También analizar el precio de venta de USDT (usdt2bol) para información adicional
    hay_tendencia_venta, variacion_venta, mensaje_venta, detalles_venta = detectar_tendencia_significativa(
        datos, 
        campo="usdt2bol", 
        umbral_variacion=2.0,
        notificar=notificar
    )
    
    # Guardar resultados
    resultados["usdt2bol"] = {"hay_tendencia": hay_tendencia_venta, "detalles": detalles_venta}
    
    if hay_tendencia_venta:
        logger.warning(mensaje_venta)
        print("\n" + "="*80)
        print(mensaje_venta)
        print("="*80 + "\n")
    else:
        logger.info(mensaje_venta)
        
    # Analizar variaciones del BTC al dólar superiores al 5%
    hay_tendencia_btc, variacion_btc, mensaje_btc, detalles_btc = detectar_tendencia_significativa(
        datos, 
        campo="btc2usd", 
        umbral_variacion=5.0,  # Umbral más alto (5%) para BTC/USD
        notificar=notificar
    )
    
    # Guardar resultados
    resultados["btc2usd"] = {"hay_tendencia": hay_tendencia_btc, "detalles": detalles_btc}
    
    if hay_tendencia_btc:
        logger.warning(mensaje_btc)
        print("\n" + "="*80)
        print(mensaje_btc)
        print("="*80 + "\n")
    else:
        logger.info(mensaje_btc)
        
    return resultados

def ejecutar_una_vez(notificar=True):
    """
    Ejecuta el análisis una vez para pruebas.
    
    Args:
        notificar (bool): Si es True, envía notificaciones a Telegram
        
    Returns:
        dict: Resultados del análisis con las tendencias detectadas
    """
    return analizar_tendencias(notificar=notificar)

# Este bloque main se ha eliminado para permitir que las funciones sean importadas desde cripto_data.py
# Las tareas programadas ahora se manejan desde el script principal

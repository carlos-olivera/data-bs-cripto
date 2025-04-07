#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script para probar las notificaciones de Telegram.
Permite verificar que las credenciales de Telegram están configuradas correctamente
y que las notificaciones se envían como se espera.
"""

import os
import sys
import logging
import argparse
from dotenv import load_dotenv
from telegram_notifier import get_telegram_notifier, test_telegram_notification
from analisis_tendencias import ejecutar_una_vez

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("test_notificaciones")

def verificar_variables_entorno():
    """
    Verifica que las variables de entorno necesarias estén configuradas.
    
    Returns:
        bool: True si todas las variables necesarias están configuradas, False en caso contrario
    """
    load_dotenv()
    
    variables_requeridas = [
        "TELEGRAM_TOKEN",
        "TELEGRAM_CHAT_ID",
        "MONGO_USER",
        "MONGO_PASSWORD",
        "MONGO_HOST",
        "MONGO_PORT",
        "MONGO_DB",
        "MONGO_AUTH_SOURCE"
    ]
    
    faltantes = []
    for var in variables_requeridas:
        if not os.getenv(var):
            faltantes.append(var)
    
    if faltantes:
        logger.error(f"Faltan las siguientes variables de entorno: {', '.join(faltantes)}")
        return False
    
    return True

def test_mensaje_simple():
    """
    Prueba el envío de un mensaje simple a Telegram.
    
    Returns:
        bool: True si el mensaje se envió correctamente, False en caso contrario
    """
    logger.info("Probando envío de mensaje simple a Telegram...")
    
    # Crear una nueva instancia del notificador para este test
    notifier = get_telegram_notifier()
    result = notifier.send_message("Este es un mensaje de prueba desde el monitor de criptomonedas.")
    
    if result:
        logger.info("✅ Mensaje simple enviado correctamente")
    else:
        logger.error("❌ Error al enviar mensaje simple")
    
    return result

def test_alerta_tendencia():
    """
    Prueba el envío de una alerta de tendencia a Telegram.
    
    Returns:
        bool: True si la alerta se envió correctamente, False en caso contrario
    """
    logger.info("Probando envío de alerta de tendencia a Telegram...")
    
    # Importante: crear una nueva instancia del notificador para este test
    # para evitar problemas con el event loop
    import time
    time.sleep(0.5)  # Pequeña pausa para asegurar que el event loop anterior se ha cerrado
    
    notifier = get_telegram_notifier()
    result = notifier.send_trend_alert(
        asset="USDT/BOB",
        trend_type="ALCISTA",
        variation=3.5,
        price_info="Precio inicial: 6.90 BOB\nPrecio final: 7.15 BOB",
        recommendation="Considere vender USDT aprovechando el precio alto"
    )
    
    if result:
        logger.info("✅ Alerta de tendencia enviada correctamente")
    else:
        logger.error("❌ Error al enviar alerta de tendencia")
    
    return result

def test_analisis_completo(usar_datos_reales=False):
    """
    Prueba el análisis completo de tendencias con envío de notificaciones.
    
    Args:
        usar_datos_reales (bool): Si es True, ejecuta el análisis con datos reales de MongoDB
                                 Si es False, simula tendencias para probar notificaciones
    
    Returns:
        bool: True si la prueba se completó correctamente, False en caso contrario
    """
    if usar_datos_reales:
        logger.info("Ejecutando análisis completo con datos reales...")
        try:
            resultados = ejecutar_una_vez(notificar=True)
            logger.info(f"Análisis completado. Tendencias detectadas: {sum(1 for k, v in resultados.items() if v['hay_tendencia'])}")
            return True
        except Exception as e:
            logger.error(f"Error al ejecutar análisis completo: {str(e)}")
            return False
    else:
        logger.info("Simulando análisis completo (sin datos reales)...")
        return test_alerta_tendencia()

def main():
    parser = argparse.ArgumentParser(description='Prueba de notificaciones de Telegram')
    parser.add_argument('--completo', action='store_true', help='Ejecuta análisis completo con datos reales')
    parser.add_argument('--simple', action='store_true', help='Prueba mensaje simple')
    parser.add_argument('--alerta', action='store_true', help='Prueba alerta de tendencia')
    args = parser.parse_args()
    
    # Verificar variables de entorno
    if not verificar_variables_entorno():
        logger.error("No se pueden ejecutar las pruebas debido a variables de entorno faltantes")
        sys.exit(1)
    
    # Si no se especifica ninguna prueba, ejecutar todas
    if not (args.completo or args.simple or args.alerta):
        args.simple = True
        args.alerta = True
    
    # Ejecutar pruebas seleccionadas
    resultados = []
    
    if args.simple:
        resultados.append(test_mensaje_simple())
    
    if args.alerta:
        resultados.append(test_alerta_tendencia())
    
    if args.completo:
        resultados.append(test_analisis_completo(usar_datos_reales=True))
    
    # Mostrar resumen
    exitos = sum(1 for r in resultados if r)
    total = len(resultados)
    
    print("\n" + "="*50)
    print(f"RESUMEN DE PRUEBAS: {exitos}/{total} exitosas")
    print("="*50)
    
    # Salir con código de error si alguna prueba falló
    if exitos < total:
        sys.exit(1)

if __name__ == "__main__":
    main()

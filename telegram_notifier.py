#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Módulo para enviar notificaciones a través de Telegram.
Utiliza las variables de entorno TELEGRAM_TOKEN y TELEGRAM_CHAT_ID.
"""

import os
import logging
import asyncio
from telegram import Bot
from telegram.error import TelegramError
from dotenv import load_dotenv

# Configurar logging
logger = logging.getLogger("telegram_notifier")

# Cargar variables de entorno si no se han cargado
load_dotenv()

class TelegramNotifier:
    """
    Clase para manejar notificaciones de Telegram.
    """
    
    def __init__(self):
        self._initialized = False
        self.token = os.getenv("TELEGRAM_TOKEN")
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID")
        self.bot = None
        
        if self.token and self.chat_id:
            self.bot = Bot(token=self.token)
            self._initialized = True
            logger.info("Telegram notifier inicializado correctamente")
        else:
            logger.warning("No se pudo inicializar Telegram notifier: falta token o chat_id")
            self._initialized = False
    
    async def _send_message_async(self, message, parse_mode='Markdown'):
        """
        Envía un mensaje de forma asíncrona.
        
        Args:
            message (str): Mensaje a enviar
            parse_mode (str): Modo de parseo del mensaje (Markdown, HTML, etc.)
            
        Returns:
            bool: True si se envió correctamente, False en caso contrario
        """
        if not self._initialized or not self.bot:
            logger.warning("Telegram notifier no inicializado correctamente")
            return False
            
        try:
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode=parse_mode
            )
            return True
        except TelegramError as e:
            logger.error(f"Error al enviar mensaje a Telegram: {str(e)}")
            return False
    
    def send_message(self, message):
        """
        Envía un mensaje a Telegram.
        
        Args:
            message (str): Mensaje a enviar
            
        Returns:
            bool: True si se envió correctamente, False en caso contrario
        """
        if not self._initialized:
            logger.warning("Telegram notifier no inicializado correctamente")
            return False
            
        try:
            # Crear un nuevo event loop para cada llamada asíncrona
            # y asegurarnos de que se cierre correctamente
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = False
            try:
                result = loop.run_until_complete(self._send_message_async(message))
                if result:
                    logger.info("Mensaje enviado a Telegram correctamente")
            finally:
                # Cerramos el loop en un bloque finally para asegurar que siempre se cierre
                loop.close()
            
            return result
        except Exception as e:
            logger.error(f"Error al enviar mensaje a Telegram: {str(e)}")
            return False
    
    def send_alert(self, title, message, is_urgent=False):
        """
        Envía una alerta formateada a Telegram.
        
        Args:
            title (str): Título de la alerta
            message (str): Mensaje detallado
            is_urgent (bool): Si es True, añade emojis de urgencia
            
        Returns:
            bool: True si se envió correctamente, False en caso contrario
        """
        emoji = "🚨" if is_urgent else "ℹ️"
        formatted_message = f"{emoji} *{title}* {emoji}\n\n{message}"
        return self.send_message(formatted_message)
    
    def send_trend_alert(self, asset, trend_type, variation, price_info, recommendation):
        """
        Envía una alerta específica de tendencia de precios.
        
        Args:
            asset (str): Activo analizado (ej: "USDT/BOB", "BTC/USD")
            trend_type (str): Tipo de tendencia ("ALCISTA" o "BAJISTA")
            variation (float): Porcentaje de variación
            price_info (str): Información adicional sobre precios
            recommendation (str): Recomendación de acción
            
        Returns:
            bool: True si se envió correctamente, False en caso contrario
        """
        if not self._initialized:
            logger.warning("Telegram notifier no inicializado correctamente")
            return False
            
        try:
            # Determinar emojis según tipo de tendencia
            if trend_type == "ALCISTA":
                trend_emoji = "📈"
                trend_color = "🟢"
            else:  # BAJISTA
                trend_emoji = "📉"
                trend_color = "🔴"
            
            # Formatear mensaje
            title = f"Tendencia {trend_type} detectada: {asset}"
            is_urgent = abs(variation) > 5.0
            emoji = "🚨" if is_urgent else "ℹ️"
            
            message_content = (
                f"{trend_emoji} *Variación:* {variation:.2f}%\n\n"
                f"{trend_color} *Detalles:*\n{price_info}\n\n"
                f"💡 *Recomendación:*\n{recommendation}"
            )
            
            formatted_message = f"{emoji} *{title}* {emoji}\n\n{message_content}"
            
            # Crear un nuevo event loop para cada llamada asíncrona
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = False
            try:
                result = loop.run_until_complete(self._send_message_async(formatted_message))
                if result:
                    logger.info(f"Alerta de tendencia {trend_type} enviada correctamente")
            finally:
                # Cerramos el loop en un bloque finally para asegurar que siempre se cierre
                loop.close()
            
            return result
        except Exception as e:
            logger.error(f"Error al enviar alerta de tendencia a Telegram: {str(e)}")
            return False


# Función para obtener una instancia del notificador
def get_telegram_notifier():
    """
    Crea y retorna una nueva instancia del notificador de Telegram.
    
    Returns:
        TelegramNotifier: Nueva instancia del notificador
    """
    return TelegramNotifier()


# Función para pruebas
def test_telegram_notification():
    """
    Función para probar el envío de notificaciones a Telegram.
    """
    notifier = get_telegram_notifier()
    
    # Probar mensaje simple
    print("Enviando mensaje de prueba simple...")
    result = notifier.send_message("Este es un mensaje de prueba desde el monitor de criptomonedas.")
    print(f"Resultado: {'Éxito' if result else 'Fallo'}")
    
    # Probar alerta alcista
    print("Enviando alerta de tendencia alcista...")
    result = notifier.send_trend_alert(
        asset="USDT/BOB",
        trend_type="ALCISTA",
        variation=3.5,
        price_info="Precio inicial: 6.90 BOB\nPrecio final: 7.15 BOB",
        recommendation="Considere vender USDT aprovechando el precio alto"
    )
    print(f"Resultado: {'Éxito' if result else 'Fallo'}")
    
    # Probar alerta bajista
    print("Enviando alerta de tendencia bajista...")
    result = notifier.send_trend_alert(
        asset="BTC/USD",
        trend_type="BAJISTA",
        variation=-6.2,
        price_info="Precio inicial: 68,500 USD\nPrecio final: 64,250 USD",
        recommendation="Posible oportunidad de compra de BTC a precio reducido"
    )
    print(f"Resultado: {'Éxito' if result else 'Fallo'}")


if __name__ == "__main__":
    # Configurar logging para pruebas
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Ejecutar prueba
    test_telegram_notification()

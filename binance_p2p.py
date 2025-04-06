import requests
import pandas as pd
import json
import os
import time
import logging
from datetime import datetime

def obtener_ofertas_p2p_binance(fiat="BOB", crypto="USDT", trade_type="BUY", 
                               page_size=10, payment_methods=None, only_verified=True, max_retries=3, retry_delay=60):
    """
    Obtiene las mejores ofertas P2P de Binance para el par fiat/crypto especificado.
    
    Args:
        fiat (str): Moneda fiat (ej: "BOB" para Boliviano)
        crypto (str): Criptomoneda (ej: "USDT")
        trade_type (str): "BUY" para comprar crypto con fiat, "SELL" para vender crypto por fiat
                         Desde la perspectiva del usuario de Binance
        page_size (int): Número de ofertas a recuperar
        payment_methods (list): Lista de métodos de pago (opcional)
        only_verified (bool): Si es True, solo muestra ofertas de comerciantes verificados
    
    Returns:
        tuple: (DataFrame con las ofertas ordenadas, JSON crudo de la respuesta de la API)
    """
    # URL del endpoint P2P de Binance
    url = "https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search"
    
    # Cabeceras para simular un navegador
    headers = {
        'Accept': '*/*',
        'Accept-Language': 'en-US,en;q=0.9',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
        'Content-Type': 'application/json',
        'Origin': 'https://p2p.binance.com',
        'Pragma': 'no-cache',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    }
    
    # Construir los parámetros de pago si se proporcionan
    payment_methods_params = []
    if payment_methods:
        for method in payment_methods:
            payment_methods_params.append({"paymentType": method})
    
    # Datos para la solicitud
    payload = {
        "asset": crypto,
        "fiat": fiat,
        "publisherType": "merchant",
        "merchantCheck": only_verified,
        "page": 1,
        "rows": page_size,
        "tradeType": trade_type,
    }
    
    # Agregar métodos de pago si se proporcionan
    if payment_methods_params:
        payload["paymentMethods"] = payment_methods_params
    
    # Configurar logging si no está configurado
    logger = logging.getLogger("binance_p2p")
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        logger.addHandler(handler)
    
    # Implementar lógica de reintentos
    retry_count = 0
    while retry_count < max_retries:
        try:
            # Realizar la solicitud POST
            logger.info(f"Intentando conectar a Binance P2P API (intento {retry_count + 1}/{max_retries})")
            response = requests.post(url, headers=headers, json=payload)
            
            # Verificar si la solicitud fue exitosa
            if response.status_code == 200:
                data = response.json()
                
                # Guardar el JSON crudo para uso posterior
                raw_data = data
                
                # Extraer datos relevantes
                ofertas = []
                for adv in data.get('data', []):
                    oferta = {
                        'precio': float(adv.get('adv', {}).get('price', 0)),
                        'cantidad_disponible': float(adv.get('adv', {}).get('surplusAmount', 0)),
                        'limite_min': float(adv.get('adv', {}).get('minSingleTransAmount', 0)),
                        'limite_max': float(adv.get('adv', {}).get('maxSingleTransAmount', 0)),
                        'metodos_pago': [pm.get('paymentType') for pm in adv.get('adv', {}).get('tradeMethods', [])],
                        'comerciante': adv.get('advertiser', {}).get('nickName', ''),
                        'completadas': adv.get('advertiser', {}).get('monthOrderCount', 0),
                        'tasa_completadas': adv.get('advertiser', {}).get('monthFinishRate', 0),
                        'verificado': adv.get('advertiser', {}).get('userIdentity', '') == 'merchant',
                    }
                    ofertas.append(oferta)
                
                # Crear DataFrame y ordenar por precio
                df = pd.DataFrame(ofertas)
                
                # Si es tipo BUY (comprar crypto), ordenar de menor a mayor precio
                # Si es tipo SELL (vender crypto), ordenar de mayor a menor precio
                if trade_type == "BUY":
                    df = df.sort_values(by='precio', ascending=True)
                else:
                    df = df.sort_values(by='precio', ascending=False)
                    
                logger.info(f"Conexión exitosa a Binance P2P API. Obtenidas {len(ofertas)} ofertas.")
                return df, raw_data
                
            else:
                logger.error(f"Error en la solicitud a Binance: {response.status_code} - {response.text}")
                
        except Exception as e:
            logger.error(f"Ocurrió un error al conectar con Binance: {str(e)}")
        
        # Si llegamos aquí, hubo un error. Incrementar contador y esperar antes de reintentar
        retry_count += 1
        
        if retry_count < max_retries:
            logger.warning(f"Reintentando en {retry_delay} segundos... (intento {retry_count + 1}/{max_retries})")
            time.sleep(retry_delay)
        else:
            logger.error(f"Se agotaron los {max_retries} intentos de conexión a Binance P2P API. Abortando.")
    
    # Si llegamos aquí, todos los intentos fallaron
    return None, None

def calcular_precio_promedio(df, num_ofertas=10):
    """
    Calcula el precio promedio de las primeras N ofertas en el DataFrame.
    
    Args:
        df (DataFrame): DataFrame con las ofertas ordenadas
        num_ofertas (int): Número de ofertas a considerar para el promedio
        
    Returns:
        float: Precio promedio de las N primeras ofertas
    """
    if df is None or len(df) == 0:
        return 0.0
        
    # Limitar al número de ofertas solicitado o al total disponible
    num_ofertas = min(num_ofertas, len(df))
    # Calcular el promedio de los precios
    precio_promedio = df.head(num_ofertas)['precio'].mean()
    
    return round(precio_promedio, 2)

# Ejemplo de uso
if __name__ == "__main__":
    # Obtener las 10 mejores ofertas para comprar USDT con BOB
    print("Obteniendo las mejores ofertas para comprar USDT con BOB...")
    ofertas_compra, raw_data = obtener_ofertas_p2p_binance(
        fiat="BOB",
        crypto="USDT",
        trade_type="BUY",  # Desde perspectiva del usuario: comprar USDT con BOB
        page_size=10,
        only_verified=True  # Solo mostrar comerciantes verificados
    )
    
    print("\nLas 10 mejores ofertas para comprar USDT con BOB:")
    if ofertas_compra is not None and raw_data is not None:
        # Formatear precio a 2 decimales
        pd.set_option('display.float_format', '{:.2f}'.format)
        print(ofertas_compra)
        
        # Calcular y mostrar el precio promedio
        precio_promedio = calcular_precio_promedio(ofertas_compra)
        print(f"\nPrecio promedio de las 10 mejores ofertas: {precio_promedio} BOB/USDT")
        
        # Crear directorios para CSV y JSON si no existen
        os.makedirs("csv", exist_ok=True)
        os.makedirs("json", exist_ok=True)
        
        # Guardar resultados en CSV con timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_filename = f"csv/ofertas_p2p_bob_usdt_{timestamp}.csv"
        ofertas_compra.to_csv(csv_filename, index=False)
        print(f"\nResultados guardados en {csv_filename}")
        
        # Guardar el JSON crudo
        json_filename = f"json/ofertas_p2p_bob_usdt_raw_{timestamp}.json"
        with open(json_filename, 'w', encoding='utf-8') as f:
            json.dump(raw_data, f, ensure_ascii=False, indent=4)
        print(f"JSON crudo guardado en {json_filename}")
    else:
        print("No se pudieron obtener ofertas.")
import requests
import json
from datetime import datetime

def obtener_precio_bitcoin_usd():
    """
    Obtiene el precio actual de Bitcoin en USD utilizando la API de CoinGecko.
    
    Returns:
        float: Precio actual de Bitcoin en USD
    """
    try:
        # URL de la API de CoinGecko para obtener el precio de Bitcoin en USD
        url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd"
        
        # Cabeceras para simular un navegador
        headers = {
            'Accept': 'application/json',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        }
        
        # Realizar la solicitud GET
        response = requests.get(url, headers=headers)
        
        # Verificar si la solicitud fue exitosa
        if response.status_code == 200:
            data = response.json()
            # Extraer el precio de Bitcoin en USD
            bitcoin_price = data.get('bitcoin', {}).get('usd', 0)
            return float(bitcoin_price)
        else:
            print(f"Error en la solicitud: {response.status_code}")
            print(response.text)
            return None
            
    except Exception as e:
        print(f"Ocurrió un error: {str(e)}")
        return None

# Ejemplo de uso
if __name__ == "__main__":
    precio_btc = obtener_precio_bitcoin_usd()
    if precio_btc is not None:
        print(f"Precio actual de Bitcoin: ${precio_btc:,.2f} USD")
    else:
        print("No se pudo obtener el precio de Bitcoin.")

import googlemaps
from typing import Tuple, Dict, Optional
from datetime import datetime
import logging

from config.settings import settings

logger = logging.getLogger(__name__)

class GoogleMapsIntegration:
    """Integração com Google Maps API"""
    
    def __init__(self):
        if not settings.google_maps_api_key:
            raise ValueError("Google Maps API key não configurada")
        
        self.client = googlemaps.Client(key=settings.google_maps_api_key)
    
    def obter_dados_transito(
        self,
        origem: Tuple[float, float],
        destino: Tuple[float, float],
        modo: str = "driving"
    ) -> Optional[Dict]:
        """Obtém dados de trânsito em tempo real"""
        try:
            resultado = self.client.directions(
                origem,
                destino,
                mode=modo,
                departure_time=datetime.now(),
                traffic_model='best_guess',
                alternatives=True
            )
            
            if not resultado:
                return None
            
            rotas_processadas = []
            for rota in resultado:
                leg = rota['legs'][0]
                
                dados_rota = {
                    'distancia_km': leg['distance']['value'] / 1000,
                    'duracao_segundos': leg['duration']['value'],
                    'polyline': rota['overview_polyline']['points']
                }
                
                if 'duration_in_traffic' in leg:
                    dados_rota['duracao_transito_segundos'] = leg['duration_in_traffic']['value']
                    dados_rota['indice_congestionamento'] = (
                        leg['duration_in_traffic']['value'] / leg['duration']['value']
                    )
                
                rotas_processadas.append(dados_rota)
            
            return {
                'rotas': rotas_processadas,
                'timestamp': datetime.now().isoformat()
            }
            
        except googlemaps.exceptions.ApiError as e:
            logger.error(f"Erro na API Google Maps: {e}")
            return None
        except Exception as e:
            logger.error(f"Erro inesperado: {e}")
            return None
    
    def geocode_endereco(self, endereco: str) -> Optional[Tuple[float, float]]:
        """Converte endereço em coordenadas"""
        try:
            resultado = self.client.geocode(f"{endereco}, Recife, PE, Brasil")
            
            if resultado:
                location = resultado[0]['geometry']['location']
                return (location['lat'], location['lng'])
            
            return None
            
        except Exception as e:
            logger.error(f"Erro no geocoding: {e}")
            return None
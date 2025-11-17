import googlemaps
import osmnx as ox
import networkx as nx
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import heapq
import math
import requests

@dataclass
class ConfiguracaoAPI:
    google_maps_key: str
    usar_osmnx: bool = True
    usar_google_traffic: bool = True

class IntegradorMapasRealTime:
    def __init__(self, config: ConfiguracaoAPI):
        self.config = config
        self.gmaps = googlemaps.Client(key=config.google_maps_key)
        self.cache_rotas = {}
        
    def baixar_rede_viaria_real(self, local: str, raio: float = 5000) -> nx.MultiDiGraph:
        try:
            print(f"Baixando rede viária de {local}...")
            
            # Baixar rede de ruas para veículos
            G = ox.graph_from_place(
                local, 
                network_type='drive',
                simplify=True
            )
            
            # Adicionar velocidades às arestas (baseado em tipo de via)
            G = ox.add_edge_speeds(G)
            
            # Calcular tempos de viagem
            G = ox.add_edge_travel_times(G)
            
            print(f"✓ Rede baixada: {len(G.nodes)} nós, {len(G.edges)} arestas")
            
            return G
            
        except Exception as e:
            print(f"Erro ao baixar rede: {e}")
            return None
    
    def obter_dados_transito_tempo_real(
        self, 
        origem: Tuple[float, float], 
        destino: Tuple[float, float],
        modo: str = "driving"
    ) -> Dict:
        """
        Obtém dados de trânsito em tempo real usando Google Maps API
        
        Args:
            origem: Tupla (latitude, longitude) da origem
            destino: Tupla (latitude, longitude) do destino
            modo: Modo de transporte ("driving", "transit", "walking")
            
        Returns:
            Dicionário com dados de trânsito em tempo real
        """
        try:
            agora = datetime.now()
            
            # Usar Directions API com dados de trânsito
            resultado = self.gmaps.directions(
                origem,
                destino,
                mode=modo,
                departure_time=agora,
                traffic_model='best_guess',  # Considera trânsito atual
                alternatives=True  # Buscar rotas alternativas
            )
            
            if not resultado:
                return None
            
            # Processar todas as rotas retornadas
            rotas_processadas = []
            
            for rota in resultado:
                leg = rota['legs'][0]
                
                dados_rota = {
                    'distancia_km': leg['distance']['value'] / 1000,
                    'duracao_segundos': leg['duration']['value'],
                    'duracao_texto': leg['duration']['text'],
                    'distancia_texto': leg['distance']['text'],
                    'passos': [],
                    'polyline': rota['overview_polyline']['points']
                }
                
                # Extrair dados de trânsito se disponível
                if 'duration_in_traffic' in leg:
                    dados_rota['duracao_transito_segundos'] = leg['duration_in_traffic']['value']
                    dados_rota['duracao_transito_texto'] = leg['duration_in_traffic']['text']
                    
                    # Calcular índice de congestionamento
                    tempo_livre = leg['duration']['value']
                    tempo_transito = leg['duration_in_traffic']['value']
                    dados_rota['indice_congestionamento'] = tempo_transito / tempo_livre
                
                # Processar cada passo da rota
                for passo in leg['steps']:
                    dados_rota['passos'].append({
                        'instrucao': passo['html_instructions'],
                        'distancia_m': passo['distance']['value'],
                        'duracao_s': passo['duration']['value'],
                        'inicio': passo['start_location'],
                        'fim': passo['end_location']
                    })
                
                rotas_processadas.append(dados_rota)
            
            return {
                'rotas': rotas_processadas,
                'timestamp': agora.isoformat(),
                'origem': origem,
                'destino': destino
            }
            
        except Exception as e:
            print(f"Erro ao obter dados de trânsito: {e}")
            return None
    
    def obter_custo_uber_estimado(
        self,
        origem: Tuple[float, float],
        destino: Tuple[float, float],
        distancia_km: float
    ) -> Dict[str, float]:
        """
        Estima custos de Uber baseado em tarifas de Recife
        
        Args:
            origem: Coordenadas de origem
            destino: Coordenadas de destino
            distancia_km: Distância em km
            
        Returns:
            Dicionário com custos estimados por modal
        """
        # Tarifas aproximadas de Recife (valores de outubro/2025)
        TARIFA_UBER_CARRO = {
            'base': 3.50,
            'por_km': 1.95,
            'por_minuto': 0.35,
            'minimo': 8.00
        }
        
        TARIFA_UBER_MOTO = {
            'base': 2.50,
            'por_km': 1.45,
            'por_minuto': 0.25,
            'minimo': 5.00
        }
        
        # Obter tempo estimado do Google Maps
        dados_transito = self.obter_dados_transito_tempo_real(origem, destino)
        
        if dados_transito and dados_transito['rotas']:
            tempo_minutos = dados_transito['rotas'][0]['duracao_segundos'] / 60
        else:
            # Estimativa: 30 km/h em horário de pico
            tempo_minutos = (distancia_km / 30) * 60
        
        # Calcular custos
        custo_carro = max(
            TARIFA_UBER_CARRO['base'] + 
            (distancia_km * TARIFA_UBER_CARRO['por_km']) +
            (tempo_minutos * TARIFA_UBER_CARRO['por_minuto']),
            TARIFA_UBER_CARRO['minimo']
        )
        
        custo_moto = max(
            TARIFA_UBER_MOTO['base'] + 
            (distancia_km * TARIFA_UBER_MOTO['por_km']) +
            (tempo_minutos * TARIFA_UBER_MOTO['por_minuto']),
            TARIFA_UBER_MOTO['minimo']
        )
        
        return {
            'uber_carro': round(custo_carro, 2),
            'uber_moto': round(custo_moto, 2),
            'tempo_estimado_min': round(tempo_minutos, 1)
        }

class OtimizadorRotasRealTime:
    def __init__(
        self, 
        integrador: IntegradorMapasRealTime,
        w1: float = 0.5,  # Peso tempo
        w2: float = 0.3,  # Peso custo
        w3: float = 0.2   # Peso impacto ambiental
    ):
        self.integrador = integrador
        self.w1 = w1
        self.w2 = w2
        self.w3 = w3
        self.grafo_real = None
    
    def carregar_rede_viaria(self, local: str = "Recife, Pernambuco, Brazil"):
        """Carrega a rede viária real da região"""
        self.grafo_real = self.integrador.baixar_rede_viaria_real(local)
        return self.grafo_real is not None
    
    def encontrar_no_mais_proximo(
        self, 
        lat: float, 
        lon: float
    ) -> Optional[int]:
        """Encontra o nó mais próximo no grafo real das coordenadas"""
        if self.grafo_real is None:
            return None
        
        try:
            return ox.distance.nearest_nodes(self.grafo_real, lon, lat)
        except Exception as e:
            print(f"Erro ao encontrar nó: {e}")
            return None
    
    def calcular_rota_otimizada(
        self,
        origem_coords: Tuple[float, float],
        destino_coords: Tuple[float, float],
        considerar_transito: bool = True
    ) -> Dict:
        resultado = {
            'sucesso': False,
            'rota': None,
            'metricas': {},
            'visualizacao': None
        }
        
        try:
            # 1. Obter dados de trânsito em tempo real
            print("\n1. Obtendo dados de trânsito em tempo real...")
            dados_transito = self.integrador.obter_dados_transito_tempo_real(
                origem_coords, 
                destino_coords
            )
            
            if not dados_transito:
                print("⚠ Não foi possível obter dados de trânsito")
                return resultado
            
            rota_google = dados_transito['rotas'][0]
            
            print(f"   Distância: {rota_google['distancia_texto']}")
            print(f"   Tempo: {rota_google['duracao_texto']}")
            
            if 'duracao_transito_texto' in rota_google:
                print(f"   Tempo com trânsito: {rota_google['duracao_transito_texto']}")
                print(f"   Índice de congestionamento: {rota_google['indice_congestionamento']:.2f}x")
            
            # 2. Estimar custos
            print("\n2. Calculando custos estimados...")
            custos = self.integrador.obter_custo_uber_estimado(
                origem_coords,
                destino_coords,
                rota_google['distancia_km']
            )
            
            print(f"   Uber Carro: R$ {custos['uber_carro']:.2f}")
            print(f"   Uber Moto: R$ {custos['uber_moto']:.2f}")
            
            # 3. Buscar no grafo OSMnx (se disponível)
            rota_osmnx = None
            if self.grafo_real is not None:
                print("\n3. Calculando rota na rede viária real...")
                
                no_origem = self.encontrar_no_mais_proximo(*origem_coords)
                no_destino = self.encontrar_no_mais_proximo(*destino_coords)
                
                if no_origem and no_destino:
                    try:
                        # Usar algoritmo de rota mais curta (Dijkstra implementado no NetworkX)
                        rota_osmnx = ox.routing.shortest_path(
                            self.grafo_real,
                            no_origem,
                            no_destino,
                            weight='travel_time'
                        )
                        
                        print(f"   ✓ Rota calculada: {len(rota_osmnx)} nós")
                        
                    except Exception as e:
                        print(f"   ⚠ Não foi possível calcular rota: {e}")
            
            # 4. Calcular métricas finais
            tempo_min = rota_google.get('duracao_transito_segundos', 
                                        rota_google['duracao_segundos']) / 60
            distancia_km = rota_google['distancia_km']
            custo_reais = custos['uber_carro']
            
            # Estimativa de emissões CO2 (kg) - carro médio: ~0.2 kg CO2/km
            emissoes_kg = distancia_km * 0.2
            
            # Função multi-objetivo normalizada
            tempo_norm = tempo_min / 60
            custo_norm = custo_reais / 50
            emissoes_norm = emissoes_kg / 10
            
            custo_total = (
                self.w1 * tempo_norm +
                self.w2 * custo_norm +
                self.w3 * emissoes_norm
            )
            
            resultado.update({
                'sucesso': True,
                'rota': {
                    'origem': origem_coords,
                    'destino': destino_coords,
                    'passos': rota_google['passos'],
                    'polyline': rota_google['polyline'],
                    'nos_osmnx': rota_osmnx
                },
                'metricas': {
                    'distancia_km': distancia_km,
                    'tempo_minutos': tempo_min,
                    'custo_uber_carro_reais': custo_reais,
                    'custo_uber_moto_reais': custos['uber_moto'],
                    'emissoes_co2_kg': emissoes_kg,
                    'indice_congestionamento': rota_google.get('indice_congestionamento', 1.0),
                    'custo_multiobjetivo': custo_total
                },
                'timestamp': dados_transito['timestamp']
            })
            
            print(f"\n✓ Rota calculada com sucesso!")
            print(f"   Custo multi-objetivo: {custo_total:.4f}")
            
            return resultado
            
        except Exception as e:
            print(f"\n✗ Erro ao calcular rota: {e}")
            import traceback
            traceback.print_exc()
            return resultado
    
    def visualizar_rota(self, resultado_rota: Dict, salvar_arquivo: str = None):
        """
        Visualiza a rota calculada em um mapa
        
        Args:
            resultado_rota: Resultado da função calcular_rota_otimizada
            salvar_arquivo: Nome do arquivo para salvar (ex: 'rota.html')
        """
        if not resultado_rota['sucesso']:
            print("Não há rota para visualizar")
            return
        
        try:
            import folium
            from folium import plugins
            
            rota = resultado_rota['rota']
            metricas = resultado_rota['metricas']
            
            # Criar mapa centrado na origem
            mapa = folium.Map(
                location=rota['origem'],
                zoom_start=13,
                tiles='OpenStreetMap'
            )
            
            # Adicionar marcador de origem
            folium.Marker(
                rota['origem'],
                popup='<b>Origem: FAFIRE</b>',
                icon=folium.Icon(color='green', icon='play')
            ).add_to(mapa)
            
            # Adicionar marcador de destino
            folium.Marker(
                rota['destino'],
                popup='<b>Destino: FNR</b>',
                icon=folium.Icon(color='red', icon='stop')
            ).add_to(mapa)
            
            # Decodificar polyline do Google Maps
            import polyline as polyline_lib
            coordenadas_rota = polyline_lib.decode(rota['polyline'])
            
            # Adicionar linha da rota
            folium.PolyLine(
                coordenadas_rota,
                color='blue',
                weight=5,
                opacity=0.7
            ).add_to(mapa)
            
            # Adicionar informações da rota
            info_html = f"""
            <div style="position: fixed; 
                        top: 10px; right: 10px; 
                        width: 300px; 
                        background-color: white; 
                        border: 2px solid gray; 
                        z-index: 9999; 
                        padding: 10px;
                        border-radius: 5px;">
                <h4>Rota FAFIRE → FNR</h4>
                <b>Distância:</b> {metricas['distancia_km']:.2f} km<br>
                <b>Tempo:</b> {metricas['tempo_minutos']:.1f} min<br>
                <b>Uber Carro:</b> R$ {metricas['custo_uber_carro_reais']:.2f}<br>
                <b>Uber Moto:</b> R$ {metricas['custo_uber_moto_reais']:.2f}<br>
                <b>Emissões CO₂:</b> {metricas['emissoes_co2_kg']:.2f} kg<br>
                <b>Congestionamento:</b> {metricas['indice_congestionamento']:.2f}x<br>
            </div>
            """
            mapa.get_root().html.add_child(folium.Element(info_html))
            
            # Salvar ou mostrar
            if salvar_arquivo:
                mapa.save(salvar_arquivo)
                print(f"\n✓ Mapa salvo em: {salvar_arquivo}")
            
            return mapa
            
        except ImportError:
            print("⚠ Instale folium e polyline: pip install folium polyline")
        except Exception as e:
            print(f"Erro ao visualizar: {e}")

# ===== EXEMPLO DE USO COMPLETO =====

def exemplo_integracao_completa():
    print("=" * 80)
    print("SISTEMA ITERUM - INTEGRAÇÃO COM MAPAS E TRÂNSITO REAL")
    print("=" * 80)
    
    GOOGLE_MAPS_KEY = "AIzaSyBBJTFlTr9_fIgqhU_jVQcd05chssZpD7Y"
    
    config = ConfiguracaoAPI(
        google_maps_key=GOOGLE_MAPS_KEY,
        usar_osmnx=True,
        usar_google_traffic=True
    )
    
    # Criar integrador
    integrador = IntegradorMapasRealTime(config)
    
    # Criar otimizador (priorizando tempo em horário de pico)
    otimizador = OtimizadorRotasRealTime(
        integrador,
        w1=0.6,  # Tempo
        w2=0.3,  # Custo
        w3=0.1   # Emissões
    )
    FAFIRE_COORDS = (-8.058243427211693, -34.889299733441696)
    FNR_COORDS = (-8.117489441268411, -34.90021665767048)
    
    print(f"\n📍 Origem: FAFIRE (Av. Conde da Boa Vista, 921 - Boa Vista)")
    print(f"   Coordenadas: {FAFIRE_COORDS}")
    print(f"\n📍 Destino: Faculdade Nova Roma (Rua Padre Carapuceiro, 590 - Boa Viagem)")
    print(f"   Coordenadas: {FNR_COORDS}")
    
    # Calcular rota otimizada com dados reais
    print("\n" + "=" * 80)
    print("CALCULANDO ROTA OTIMIZADA FAFIRE → FNR")
    print("=" * 80)
    
    resultado = otimizador.calcular_rota_otimizada(
        FAFIRE_COORDS,
        FNR_COORDS,
        considerar_transito=True
    )
    
    if resultado['sucesso']:
        print("\n" + "=" * 80)
        print("RESUMO DA ROTA")
        print("=" * 80)
        m = resultado['metricas']
        print(f"\n📍 Distância Total: {m['distancia_km']:.2f} km")
        print(f"⏱️  Tempo Estimado: {m['tempo_minutos']:.1f} minutos")
        print(f"🚗 Custo Uber Carro: R$ {m['custo_uber_carro_reais']:.2f}")
        print(f"🏍️  Custo Uber Moto: R$ {m['custo_uber_moto_reais']:.2f}")
        print(f"🌱 Emissões CO₂: {m['emissoes_co2_kg']:.2f} kg")
        print(f"🚦 Índice Congestionamento: {m['indice_congestionamento']:.2f}x")
        print(f"\n📊 Custo Multi-Objetivo: {m['custo_multiobjetivo']:.4f}")
        print("\n" + "=" * 80)
        print("Gerando visualização...")
        otimizador.visualizar_rota(resultado, 'rota_fafire_fnr.html')
        print("\nAbra o arquivo 'rota_fafire_fnr.html' no navegador para ver o mapa!")
        print("=" * 80)
    
    return resultado

# Executar
if __name__ == "__main__":
    resultado = exemplo_integracao_completa()
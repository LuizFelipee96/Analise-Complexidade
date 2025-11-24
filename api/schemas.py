from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class RequisicaoRota(BaseModel):
    """Schema de requisição de rota"""
    endereco_origem: Optional[str] = None
    coords_origem: Optional[List[float]] = Field(None, description="[lat, lon]")
    
    endereco_destino: Optional[str] = None
    coords_destino: Optional[List[float]] = Field(None, description="[lat, lon]")
    
    modais_permitidos: Optional[List[str]] = Field(
        default=None,
        description="Lista de modais: caminhada, onibus, metro, uber_carro, uber_moto"
    )
    
    criterio: str = Field(
        default="multiobjetivo",
        description="Critério de otimização: tempo, custo, emissoes, multiobjetivo"
    )
    
    k_rotas: int = Field(default=3, ge=1, le=5, description="Número de rotas alternativas")
    
    class Config:
        schema_extra = {
            "example": {
                "endereco_origem": "Av. Conde da Boa Vista, 921, Recife",
                "endereco_destino": "Rua Padre Carapuceiro, 590, Recife",
                "criterio": "tempo",
                "k_rotas": 3
            }
        }

class SegmentoRotaResponse(BaseModel):
    tipo_modal: str
    origem: str
    destino: str
    distancia_m: float
    tempo_min: float
    custo_reais: float
    linha: Optional[str] = None

class RotaResponse(BaseModel):
    id_rota: str
    tempo_total_min: float
    custo_total_reais: float
    distancia_total_km: float
    emissoes_totais_kg: float
    numero_transferencias: int
    modais_utilizados: List[str]
    melhor_para: str
    segmentos: List[SegmentoRotaResponse]

class RespostaRotas(BaseModel):
    sucesso: bool
    rotas: List[RotaResponse]
    timestamp: datetime
    mensagem: Optional[str] = None

# ============================================================================
# FILE: api/main.py
# ============================================================================
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from typing import List
import logging

from api.schemas import RequisicaoRota, RespostaRotas, RotaResponse, SegmentoRotaResponse
from models.grafo_multimodal import GrafoMultiModal
from algorithms.multimodal_router import RoteadorMultiModal
from integrations.google_maps import GoogleMapsIntegration
from parsers.gtfs_parser import GTFSParser
from utils.cache import CacheManager
from config.settings import settings

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Inicializar FastAPI
app = FastAPI(
    title="ITERUM API",
    description="API de Roteamento Multi-Modal para Recife",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Estado global
class AppState:
    grafo: GrafoMultiModal = None
    roteador: RoteadorMultiModal = None
    gmaps: GoogleMapsIntegration = None
    cache: CacheManager = None

state = AppState()

@app.on_event("startup")
async def startup_event():
    """Inicialização da aplicação"""
    logger.info("Inicializando ITERUM API...")
    
    # Inicializar componentes
    state.cache = CacheManager()
    state.gmaps = GoogleMapsIntegration()
    state.grafo = GrafoMultiModal()
    
    # Carregar dados GTFS
    grafo_cache_key = "grafo_recife_api"
    grafo_cached = state.cache.get(grafo_cache_key, max_age_seconds=86400)
    
    if grafo_cached:
        logger.info("Grafo carregado do cache")
        state.grafo = grafo_cached
    else:
        if os.path.exists(settings.gtfs_local_path):
            logger.info("Carregando dados GTFS...")
            parser = GTFSParser(settings.gtfs_local_path)
            recife_bbox = (-8.2, -35.05, -7.9, -34.85)
            parser.popular_grafo(state.grafo, regiao_bbox=recife_bbox)
            state.cache.set(grafo_cache_key, state.grafo)
        else:
            logger.warning("Dados GTFS não encontrados")
    
    state.roteador = RoteadorMultiModal(state.grafo)
    logger.info("✓ API inicializada com sucesso")

@app.get("/")
async def root():
    """Endpoint raiz"""
    return {
        "nome": "ITERUM API",
        "versao": "1.0.0",
        "descricao": "API de Roteamento Multi-Modal para Recife",
        "endpoints": [
            "/calcular-rota",
            "/estatisticas",
            "/health"
        ]
    }

@app.get("/health")
async def health_check():
    """Health check"""
    return {
        "status": "healthy",
        "grafo_vertices": len(state.grafo.vertices) if state.grafo else 0,
        "timestamp": datetime.now().isoformat()
    }

@app.get("/estatisticas")
async def obter_estatisticas():
    """Retorna estatísticas do grafo"""
    if not state.grafo:
        raise HTTPException(status_code=503, detail="Grafo não inicializado")
    
    return state.grafo.estatisticas()

@app.post("/calcular-rota", response_model=RespostaRotas)
async def calcular_rota(req: RequisicaoRota):
    """
    Calcula rotas multi-modais entre origem e destino
    
    Pode receber endereços (que serão geocodificados) ou coordenadas diretas.
    """
    if not state.roteador:
        raise HTTPException(status_code=503, detail="Roteador não inicializado")
    
    try:
        # 1. Obter coordenadas
        if req.coords_origem:
            origem_coords = tuple(req.coords_origem)
            origem_nome = req.endereco_origem or "Origem"
        elif req.endereco_origem:
            origem_coords = state.gmaps.geocode_endereco(req.endereco_origem)
            if not origem_coords:
                raise HTTPException(status_code=400, detail="Endereço de origem não encontrado")
            origem_nome = req.endereco_origem
        else:
            raise HTTPException(status_code=400, detail="Forneça endereco_origem ou coords_origem")
        
        if req.coords_destino:
            destino_coords = tuple(req.coords_destino)
            destino_nome = req.endereco_destino or "Destino"
        elif req.endereco_destino:
            destino_coords = state.gmaps.geocode_endereco(req.endereco_destino)
            if not destino_coords:
                raise HTTPException(status_code=400, detail="Endereço de destino não encontrado")
            destino_nome = req.endereco_destino
        else:
            raise HTTPException(status_code=400, detail="Forneça endereco_destino ou coords_destino")
        
        # 2. Calcular rotas
        rotas = state.roteador.calcular_rotas(
            origem_coords=origem_coords,
            destino_coords=destino_coords,
            origem_nome=origem_nome,
            destino_nome=destino_nome,
            k_rotas=req.k_rotas,
            criterio=req.criterio
        )
        
        # 3. Converter para response
        rotas_response = []
        for rota in rotas:
            segmentos = [
                SegmentoRotaResponse(
                    tipo_modal=seg.tipo_modal,
                    origem=seg.origem,
                    destino=seg.destino,
                    distancia_m=seg.distancia_m,
                    tempo_min=seg.tempo_min,
                    custo_reais=seg.custo_reais,
                    linha=seg.linha
                )
                for seg in rota.segmentos
            ]
            
            rota_resp = RotaResponse(
                id_rota=rota.id_rota,
                tempo_total_min=rota.tempo_total_min,
                custo_total_reais=rota.custo_total_reais,
                distancia_total_km=rota.distancia_total_km,
                emissoes_totais_kg=rota.emissoes_totais_kg,
                numero_transferencias=rota.numero_transferencias,
                modais_utilizados=rota.modais_utilizados,
                melhor_para=rota.melhor_para,
                segmentos=segmentos
            )
            rotas_response.append(rota_resp)
        
        return RespostaRotas(
            sucesso=True,
            rotas=rotas_response,
            timestamp=datetime.now(),
            mensagem=f"{len(rotas)} rotas encontradas"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao calcular rota: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
from pydantic_settings import BaseSettings
from typing import Optional
import os

class Settings(BaseSettings):
    """Configurações globais do sistema"""
    
    google_maps_api_key: str
    
    environment: str = "development"
    debug: bool = True
    log_level: str = "INFO"
    
    redis_host: str = "localhost"
    redis_port: int = 6379
    cache_ttl: int = 3600
    use_cache: bool = True
    
    gtfs_url: str = ""
    gtfs_local_path: str = "./data/gtfs/"
    
    max_walking_distance_m: int = 800
    walking_speed_kmh: float = 4.5
    default_bus_wait_time_min: float = 10.0
    transfer_penalty_min: float = 5.0
    
    peso_tempo: float = 0.5
    peso_custo: float = 0.3
    peso_emissoes: float = 0.2
    
    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()
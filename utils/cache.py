import pickle
import os
import hashlib
import json
from typing import Any, Optional
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class CacheManager:
    """Gerenciador de cache em disco"""
    
    def __init__(self, cache_dir: str = "./cache"):
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)
    
    def _get_cache_path(self, key: str) -> str:
        """Gera caminho do arquivo de cache"""
        # Hash da chave para nome de arquivo seguro
        key_hash = hashlib.md5(key.encode()).hexdigest()
        return os.path.join(self.cache_dir, f"{key_hash}.pkl")
    
    def get(self, key: str, max_age_seconds: Optional[int] = None) -> Optional[Any]:
        """Recupera item do cache"""
        cache_path = self._get_cache_path(key)
        
        if not os.path.exists(cache_path):
            return None
        
        # Verificar idade do cache
        if max_age_seconds:
            file_time = datetime.fromtimestamp(os.path.getmtime(cache_path))
            if datetime.now() - file_time > timedelta(seconds=max_age_seconds):
                logger.debug(f"Cache expirado: {key}")
                return None
        
        try:
            with open(cache_path, 'rb') as f:
                return pickle.load(f)
        except Exception as e:
            logger.error(f"Erro ao ler cache: {e}")
            return None
    
    def set(self, key: str, value: Any):
        """Armazena item no cache"""
        cache_path = self._get_cache_path(key)
        
        try:
            with open(cache_path, 'wb') as f:
                pickle.dump(value, f)
            logger.debug(f"Cache salvo: {key}")
        except Exception as e:
            logger.error(f"Erro ao salvar cache: {e}")
    
    def clear(self):
        """Limpa todo o cache"""
        for filename in os.listdir(self.cache_dir):
            os.remove(os.path.join(self.cache_dir, filename))
        logger.info("Cache limpo")
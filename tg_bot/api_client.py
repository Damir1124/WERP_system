"""
HTTP-клиент для взаимодействия с Django API.
"""
import aiohttp
import logging
from typing import Optional, Dict, Any

from tg_bot.config import DJANGO_API_URL

logger = logging.getLogger(__name__)


class APIClient:
    """Асинхронный клиент для работы с Django API."""
    
    def __init__(self, base_url: str = DJANGO_API_URL):
        self.base_url = base_url.rstrip('/')
    
    async def get(self, endpoint: str, params: Optional[Dict] = None, headers: Optional[Dict] = None) -> Dict[str, Any]:
        """GET-запрос к API."""
        url = f"{self.base_url}{endpoint}"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, headers=headers, timeout=10) as resp:
                    if resp.status == 200:
                        return await resp.json()
                    else:
                        body = await resp.text()
                        logger.error(f"GET {url} вернул {resp.status}: {body}")
                        # Пытаемся извлечь реальную ошибку из JSON-ответа бэкенда
                        try:
                            err_data = await resp.json(content_type=None)
                            if isinstance(err_data, dict) and 'error' in err_data:
                                return {"error": err_data['error']}
                        except Exception:
                            pass
                        return {"error": f"HTTP {resp.status}"}
        except Exception as e:
            logger.exception(f"Ошибка GET {url}: {e}")
            return {"error": str(e)}
    
    async def post(self, endpoint: str, data: Optional[Dict] = None, headers: Optional[Dict] = None) -> Dict[str, Any]:
        """POST-запрос к API."""
        url = f"{self.base_url}{endpoint}"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=data, headers=headers, timeout=10) as resp:
                    if resp.status in [200, 201]:
                        return await resp.json()
                    else:
                        body = await resp.text()
                        logger.error(f"POST {url} вернул {resp.status}: {body}")
                        # Пытаемся извлечь реальную ошибку из JSON-ответа бэкенда
                        try:
                            err_data = await resp.json(content_type=None)
                            if isinstance(err_data, dict) and 'error' in err_data:
                                return {"error": err_data['error']}
                        except Exception:
                            pass
                        return {"error": f"HTTP {resp.status}"}
        except Exception as e:
            logger.exception(f"Ошибка POST {url}: {e}")
            return {"error": str(e)}
    
    async def patch(self, endpoint: str, data: Optional[Dict] = None, headers: Optional[Dict] = None) -> Dict[str, Any]:
        """PATCH-запрос к API."""
        url = f"{self.base_url}{endpoint}"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.patch(url, json=data, headers=headers, timeout=10) as resp:
                    if resp.status == 200:
                        return await resp.json()
                    else:
                        body = await resp.text()
                        logger.error(f"PATCH {url} вернул {resp.status}: {body}")
                        # Пытаемся извлечь реальную ошибку из JSON-ответа бэкенда
                        try:
                            err_data = await resp.json(content_type=None)
                            if isinstance(err_data, dict) and 'error' in err_data:
                                return {"error": err_data['error']}
                        except Exception:
                            pass
                        return {"error": f"HTTP {resp.status}"}
        except Exception as e:
            logger.exception(f"Ошибка PATCH {url}: {e}")
            return {"error": str(e)}


    async def delete(self, endpoint: str, headers: Optional[Dict] = None) -> Dict[str, Any]:
        """DELETE-запрос к API."""
        url = f"{self.base_url}{endpoint}"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.delete(url, headers=headers, timeout=10) as resp:
                    if resp.status in [200, 204]:
                        try:
                            return await resp.json()
                        except Exception:
                            return {"status": "deleted"}
                    else:
                        body = await resp.text()
                        logger.error(f"DELETE {url} вернул {resp.status}: {body}")
                        try:
                            err_data = await resp.json(content_type=None)
                            if isinstance(err_data, dict) and 'error' in err_data:
                                return {"error": err_data['error']}
                        except Exception:
                            pass
                        return {"error": f"HTTP {resp.status}"}
        except Exception as e:
            logger.exception(f"Ошибка DELETE {url}: {e}")
            return {"error": str(e)}

    async def request(self, method: str, endpoint: str, **kwargs) -> tuple:
        """
        Выполнить HTTP-запрос и вернуть (status_code, data).
        Полезно, когда нужно знать HTTP-статус (например, 404 vs 500).
        """
        url = f"{self.base_url}{endpoint}"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.request(method, url, **kwargs) as resp:
                    try:
                        data = await resp.json(content_type=None)
                    except Exception:
                        data = await resp.text()
                    return resp.status, data
        except Exception as e:
            logger.exception(f"Ошибка {method.upper()} {url}: {e}")
            return 0, {"error": str(e)}


# Глобальный экземпляр клиента
api_client = APIClient()

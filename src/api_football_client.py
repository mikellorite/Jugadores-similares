"""
Cliente para API-Football v3 con sistema de caché en disco y control de rate limit.
"""

import json
import hashlib
import time
import logging
from pathlib import Path
from typing import Optional

import requests

from src.config import (
    FOOTBALL_API_KEY,
    API_FOOTBALL_BASE_URL,
    CACHE_DIR,
    CACHE_TTL_SECONDS,
)

logger = logging.getLogger(__name__)


class APIFootballClient:
    """Envuelve la API de api-football.com con caché local y control de cuota."""

    def __init__(self):
        self.base_url = API_FOOTBALL_BASE_URL
        self.headers = {"x-apisports-key": FOOTBALL_API_KEY}
        self.remaining_requests: Optional[int] = None

    # ── Caché ────────────────────────────────────────────────────────────

    @staticmethod
    def _cache_key(endpoint: str, params: dict) -> str:
        param_str = json.dumps(params, sort_keys=True)
        h = hashlib.md5(f"{endpoint}|{param_str}".encode()).hexdigest()
        safe_name = endpoint.replace("/", "_")
        return f"{safe_name}_{h}"

    @staticmethod
    def _get_cached(cache_key: str) -> Optional[dict]:
        path = CACHE_DIR / f"{cache_key}.json"
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if time.time() - data.get("cached_at", 0) < CACHE_TTL_SECONDS:
                return data["response"]
        except (json.JSONDecodeError, KeyError):
            pass
        return None

    @staticmethod
    def _save_cache(cache_key: str, response_data: dict) -> None:
        path = CACHE_DIR / f"{cache_key}.json"
        payload = {"cached_at": time.time(), "response": response_data}
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    # ── Petición HTTP ────────────────────────────────────────────────────

    def _request(self, endpoint: str, params: dict, use_cache: bool = True) -> dict:
        cache_key = self._cache_key(endpoint, params)

        if use_cache:
            cached = self._get_cached(cache_key)
            if cached is not None:
                logger.debug("Cache HIT: %s %s", endpoint, params)
                return cached

        url = f"{self.base_url}/{endpoint}"
        logger.info("API request: GET %s %s", url, params)

        resp = requests.get(url, headers=self.headers, params=params, timeout=30)
        resp.raise_for_status()

        # Actualizar cuota restante
        remaining_hdr = resp.headers.get("x-ratelimit-requests-remaining")
        if remaining_hdr is not None:
            self.remaining_requests = int(remaining_hdr)
            logger.info("Peticiones restantes hoy: %d", self.remaining_requests)

        data = resp.json()

        # Comprobar errores de la API
        errors = data.get("errors")
        if errors:
            # errors puede ser dict o list
            if isinstance(errors, dict) and errors:
                error_msg = str(errors)
                logger.error("API error: %s", error_msg)
                raise RuntimeError(f"API-Football error: {error_msg}")
            elif isinstance(errors, list) and errors:
                error_msg = str(errors)
                logger.error("API error: %s", error_msg)
                raise RuntimeError(f"API-Football error: {error_msg}")

        if use_cache:
            self._save_cache(cache_key, data)

        return data

    # ── Cuota ────────────────────────────────────────────────────────────

    def get_remaining_requests(self) -> int:
        """Consulta cuota restante (endpoint /status es gratuito)."""
        try:
            resp = requests.get(
                f"{self.base_url}/status",
                headers=self.headers,
                timeout=10,
            )
            info = resp.json().get("response", {}).get("requests", {})
            limit = info.get("limit_day", 100)
            current = info.get("current", 0)
            self.remaining_requests = limit - current
            return self.remaining_requests
        except Exception:
            return self.remaining_requests if self.remaining_requests is not None else -1

    # ── Búsqueda de jugador ──────────────────────────────────────────────

    def search_player(self, name: str, season: int) -> list[dict]:
        """Busca jugadores por nombre y devuelve lista con perfil + stats resumen."""
        data = self._request("players", {"search": name, "season": season})
        results: list[dict] = []

        for item in data.get("response", []):
            player = item.get("player", {})
            stats_list = item.get("statistics", [])
            primary = stats_list[0] if stats_list else {}
            games = primary.get("games", {})
            team = primary.get("team", {})
            league = primary.get("league", {})

            results.append({
                "player_id": player.get("id"),
                "name": player.get("name"),
                "firstname": player.get("firstname"),
                "lastname": player.get("lastname"),
                "photo": player.get("photo"),
                "nationality": player.get("nationality"),
                "position": games.get("position", "Unknown"),
                "team_id": team.get("id"),
                "team_name": team.get("name"),
                "team_logo": team.get("logo"),
                "league_id": league.get("id"),
                "league_name": league.get("name"),
            })

        return results

    # ── Jugadores de una liga (con paginación) ───────────────────────────

    def get_league_players(self, league_id: int, season: int) -> list[dict]:
        """Obtiene jugadores de una liga para una temporada.

        En el plan gratuito de API-Football, el parámetro page está limitado a máx 3 páginas.
        Los datos se cachean en disco para no consumir llamadas en peticiones repetidas.
        """
        all_players: list[dict] = []
        page = 1
        max_pages = 3  # Límite del plan gratuito de API-Football

        while page <= max_pages:
            try:
                data = self._request("players", {
                    "league": league_id,
                    "season": season,
                    "page": page,
                })
            except Exception as e:
                logger.warning("Fin de paginación alcanzado en página %d para liga %d: %s", page, league_id, e)
                break

            total_pages = data.get("paging", {}).get("total", 1)
            max_pages = min(total_pages, 3)

            for item in data.get("response", []):
                player = item.get("player", {})

                for stats in item.get("statistics", []):
                    # Solo incluir stats de la liga solicitada
                    if stats.get("league", {}).get("id") != league_id:
                        continue

                    games = stats.get("games", {})
                    goals_data = stats.get("goals", {})
                    passes = stats.get("passes", {})
                    shots = stats.get("shots", {})
                    tackles = stats.get("tackles", {})
                    dribbles = stats.get("dribbles", {})
                    cards = stats.get("cards", {})

                    all_players.append({
                        "player_id": player.get("id"),
                        "name": player.get("name"),
                        "firstname": player.get("firstname"),
                        "lastname": player.get("lastname"),
                        "photo": player.get("photo"),
                        "nationality": player.get("nationality"),
                        "position": games.get("position", "Unknown"),
                        "team_id": stats.get("team", {}).get("id"),
                        "team_name": stats.get("team", {}).get("name"),
                        "team_logo": stats.get("team", {}).get("logo"),
                        "league_id": league_id,
                        "league_name": stats.get("league", {}).get("name"),
                        "appearances": games.get("appearences") or 0,
                        "minutes": games.get("minutes") or 0,
                        "rating": games.get("rating"),
                        "goals": goals_data.get("total") or 0,
                        "assists": goals_data.get("assists") or 0,
                        "passes_total": passes.get("total") or 0,
                        "passes_accuracy": passes.get("accuracy") or 0,
                        "shots_total": shots.get("total") or 0,
                        "dribbles_success": dribbles.get("success") or 0,
                        "tackles_total": tackles.get("total") or 0,
                        "interceptions": tackles.get("interceptions") or 0,
                        "yellow_cards": cards.get("yellow") or 0,
                        "red_cards": cards.get("red") or 0,
                    })

            page += 1

        logger.info(
            "Liga %d temporada %d: %d jugadores obtenidos (%d páginas)",
            league_id, season, len(all_players), min(page - 1, max_pages),
        )
        return all_players

    # ── Obtener stats de un jugador por ID ───────────────────────────────

    def get_player_by_id(self, player_id: int, season: int) -> Optional[dict]:
        """Obtiene las estadísticas de un jugador específico por su ID."""
        data = self._request("players", {"id": player_id, "season": season})

        for item in data.get("response", []):
            player = item.get("player", {})
            for stats in item.get("statistics", []):
                games = stats.get("games", {})
                goals_data = stats.get("goals", {})
                passes = stats.get("passes", {})
                shots = stats.get("shots", {})
                tackles = stats.get("tackles", {})
                dribbles = stats.get("dribbles", {})
                cards = stats.get("cards", {})

                return {
                    "player_id": player.get("id"),
                    "name": player.get("name"),
                    "firstname": player.get("firstname"),
                    "lastname": player.get("lastname"),
                    "photo": player.get("photo"),
                    "nationality": player.get("nationality"),
                    "position": games.get("position", "Unknown"),
                    "team_id": stats.get("team", {}).get("id"),
                    "team_name": stats.get("team", {}).get("name"),
                    "team_logo": stats.get("team", {}).get("logo"),
                    "league_id": stats.get("league", {}).get("id"),
                    "league_name": stats.get("league", {}).get("name"),
                    "appearances": games.get("appearences") or 0,
                    "minutes": games.get("minutes") or 0,
                    "rating": games.get("rating"),
                    "goals": goals_data.get("total") or 0,
                    "assists": goals_data.get("assists") or 0,
                    "passes_total": passes.get("total") or 0,
                    "passes_accuracy": passes.get("accuracy") or 0,
                    "shots_total": shots.get("total") or 0,
                    "dribbles_success": dribbles.get("success") or 0,
                    "tackles_total": tackles.get("total") or 0,
                    "interceptions": tackles.get("interceptions") or 0,
                    "yellow_cards": cards.get("yellow") or 0,
                    "red_cards": cards.get("red") or 0,
                }

        return None

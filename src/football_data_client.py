"""
Cliente de respaldo para football-data.org (v4).

Solo sirve para búsqueda de jugadores a través de squads de equipos.
NO proporciona estadísticas granulares (pases, entradas, regates, etc.).
"""

import logging
from typing import Optional

import requests

from src.config import FOOTBALL_DATA_ORG_API_KEY, FOOTBALL_DATA_BASE_URL, LEAGUES

logger = logging.getLogger(__name__)


class FootballDataClient:
    """Wrapper ligero para football-data.org — solo búsqueda de jugadores."""

    def __init__(self):
        self.base_url = FOOTBALL_DATA_BASE_URL
        self.headers = {"X-Auth-Token": FOOTBALL_DATA_ORG_API_KEY}

    def get_competition_teams(self, code: str) -> list[dict]:
        """Obtiene la lista de equipos y plantillas de una competición."""
        try:
            url = f"{self.base_url}/competitions/{code}/teams"
            resp = requests.get(url, headers=self.headers, timeout=20)
            if resp.status_code == 200:
                return resp.json().get("teams", [])
        except Exception as e:
            logger.warning("Error fetching teams for %s: %s", code, e)
        return []

    def search_player_in_competitions(
        self,
        name: str,
        competition_codes: Optional[list[str]] = None,
    ) -> list[dict]:
        """Busca un jugador por nombre recorriendo los squads de las ligas.

        Es lento (~1 petición por liga) pero funciona cuando API-Football
        no tiene cuota.
        """
        if competition_codes is None:
            competition_codes = [v["football_data_code"] for v in LEAGUES.values()]

        name_lower = name.lower()
        results: list[dict] = []

        for code in competition_codes:
            try:
                url = f"{self.base_url}/competitions/{code}/teams"
                resp = requests.get(url, headers=self.headers, timeout=20)

                if resp.status_code == 429:
                    logger.warning("football-data.org rate limit alcanzado")
                    break
                if resp.status_code != 200:
                    logger.debug("football-data.org %s → %d", code, resp.status_code)
                    continue

                data = resp.json()
                for team in data.get("teams", []):
                    for player in team.get("squad", []) or []:
                        if name_lower in (player.get("name") or "").lower():
                            results.append({
                                "player_id": player.get("id"),
                                "name": player.get("name"),
                                "position": player.get("position"),
                                "nationality": player.get("nationality"),
                                "team_name": team.get("name"),
                                "team_id": team.get("id"),
                                "team_logo": team.get("crest"),
                                "source": "football-data.org",
                            })
            except requests.RequestException as exc:
                logger.warning("Error consultando football-data.org (%s): %s", code, exc)
                continue

        return results

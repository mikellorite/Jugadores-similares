"""
API REST con FastAPI — Backend del sistema de scouting.

Ejecutar con:
    uvicorn src.api:app --host 0.0.0.0 --port 8002 --reload
"""

import logging
from typing import Optional

from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.data_service import DataService

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

# ── App ──────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Scouting de Jugadores Parecidos",
    description="API para encontrar jugadores con estilo de juego similar",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Instancia global del servicio de datos
data_service = DataService()


# ── Modelos ──────────────────────────────────────────────────────────────────

class ScoutingRequest(BaseModel):
    player_name: str
    team_name: Optional[str] = None
    player_league: Optional[str] = None
    player_id: Optional[int] = None
    positions: list[str]
    leagues: list[str]
    min_matches: int = 10
    min_minutes: int = 500


# ── Endpoints ────────────────────────────────────────────────────────────────

@app.get("/api/health")
def health():
    """Health check."""
    return {"status": "ok"}


@app.get("/api/status")
def api_status():
    """Devuelve peticiones API restantes y estado general."""
    return data_service.get_api_status()


@app.get("/api/catalog")
def get_catalog():
    """Devuelve el catálogo completo de jugadores para selección rápida."""
    catalog = data_service.get_catalog()
    return {"catalog": catalog}


@app.get("/api/search-player")
def search_player(name: str = Query(..., min_length=3, description="Nombre del jugador (mín. 3 caracteres)")):
    """Busca jugadores en el catálogo / API."""
    catalog = data_service.get_catalog()
    query_lower = name.lower()
    matches = [
        p for p in catalog
        if query_lower in p.get("name", "").lower() or query_lower in p.get("display_label", "").lower()
    ]
    return {"results": matches[:20]}


@app.post("/api/scouting")
def run_scouting(request: ScoutingRequest):
    """Ejecuta el análisis completo de scouting.

    Devuelve: jugador seleccionado, top 10 similares, datos de clustering
    y datos de comparación para gráficos.
    """
    result = data_service.run_scouting(
        player_name=request.player_name,
        team_name=request.team_name,
        player_league=request.player_league,
        positions=request.positions,
        league_names=request.leagues,
        min_matches=request.min_matches,
        min_minutes=request.min_minutes,
        player_id=request.player_id,
    )


    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    return result

"""
Configuración central del proyecto de Scouting de Jugadores Parecidos.
Carga de variables de entorno, mapeos de ligas, posiciones y constantes.
"""

import os
from pathlib import Path
from datetime import datetime

from dotenv import load_dotenv

# ── Cargar .env ──────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).parent.parent
load_dotenv(PROJECT_ROOT / ".env")

# ── API Keys ─────────────────────────────────────────────────────────────────
FOOTBALL_API_KEY = os.getenv("FOOTBALL_API_KEY", "")
FOOTBALL_DATA_ORG_API_KEY = os.getenv("FOOTBAL_DATA_ORG_API_KEY", "")  # typo en .env original

# ── URLs base ────────────────────────────────────────────────────────────────
API_FOOTBALL_BASE_URL = "https://v3.football.api-sports.io"
FOOTBALL_DATA_BASE_URL = "https://api.football-data.org/v4"

# ── Rutas del proyecto ───────────────────────────────────────────────────────
CACHE_DIR = PROJECT_ROOT / "cache"
OUTPUTS_DIR = PROJECT_ROOT / "outputs"
CACHE_DIR.mkdir(exist_ok=True)
OUTPUTS_DIR.mkdir(exist_ok=True)

# ── Caché ────────────────────────────────────────────────────────────────────
CACHE_TTL_SECONDS = 30 * 24 * 60 * 60  # 30 días para ahorrar llamadas a la API

# ── Temporada por defecto con datos completos ────────────────────────────────
DEFAULT_SEASON = 2024

# ── Puertos ──────────────────────────────────────────────────────────────────
API_PORT = 8002
STREAMLIT_PORT = 8502

# ── Ligas ────────────────────────────────────────────────────────────────────
LEAGUES = {
    "Premier League": {"api_football_id": 39, "football_data_code": "PL", "country": "England"},
    "La Liga":        {"api_football_id": 140, "football_data_code": "PD", "country": "Spain"},
    "Bundesliga":     {"api_football_id": 78,  "football_data_code": "BL1", "country": "Germany"},
    "Serie A":        {"api_football_id": 135, "football_data_code": "SA",  "country": "Italy"},
    "Ligue 1":        {"api_football_id": 61,  "football_data_code": "FL1", "country": "France"},
}

# ── Posiciones: etiqueta del usuario → categorías posibles en APIs ──────────
POSITION_MAPPING = {
    "DC":  ["Attacker", "Forward", "Offence"],
    "EI":  ["Attacker", "Forward", "Offence"],
    "ED":  ["Attacker", "Forward", "Offence"],
    "MI":  ["Midfielder", "Midfield"],
    "MD":  ["Midfielder", "Midfield"],
    "MC":  ["Midfielder", "Midfield"],
    "MCD": ["Midfielder", "Midfield"],
    "MCO": ["Midfielder", "Midfield"],
    "DFC": ["Defender", "Defence"],
    "LI":  ["Defender", "Defence"],
    "LD":  ["Defender", "Defence"],
    "CAI": ["Defender", "Defence"],
    "CAD": ["Defender", "Defence"],
}

# ── Etiquetas legibles para las posiciones (UI) ─────────────────────────────
POSITION_LABELS = {
    "DC":  "Delantero Centro",
    "EI":  "Extremo Izquierdo",
    "ED":  "Extremo Derecho",
    "MI":  "Mediocampista Izquierdo",
    "MD":  "Mediocampista Derecho",
    "MC":  "Mediocentro",
    "MCD": "Mediocentro Defensivo",
    "MCO": "Mediocentro Ofensivo",
    "DFC": "Defensa Central",
    "LI":  "Lateral Izquierdo",
    "LD":  "Lateral Derecho",
    "CAI": "Carrilero Izquierdo",
    "CAD": "Carrilero Derecho",
}

# ── Columnas de features para el vector de similitud (9 dimensiones) ────────
FEATURE_COLUMNS = [
    "goals_p90",
    "assists",
    "passes_p90",
    "pass_pct",
    "shots_p90",
    "dribbles_p90",
    "tackles_p90",
    "interceptions_p90",
    "yellow_cards",
]

# ── Abreviaturas de stats para la tabla de la UI ────────────────────────────
STATS_ABBREVIATIONS = {
    "PJ": "Partidos Jugados",
    "G":  "Goles",
    "AS": "Asistencias",
    "PC": "Pases Completados",
    "%P": "Porcentaje de Acierto de Pases",
    "TR": "Tiros Realizados",
    "RC": "Regates Completados",
    "ER": "Entradas Realizadas",
    "ID": "Intercepciones Defensivas",
    "AM": "Amarillas",
}


def get_current_season() -> int:
    """Devuelve la temporada a consultar."""
    return DEFAULT_SEASON


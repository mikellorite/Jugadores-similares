"""
Servicio de datos: orquesta la obtención, filtrado, cálculo de similitud y clustering.
"""

import json
import logging
import unicodedata
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

from src.config import (
    LEAGUES,
    POSITION_MAPPING,
    FEATURE_COLUMNS,
    CACHE_DIR,
    get_current_season,
)
from src.api_football_client import APIFootballClient
from src.football_data_client import FootballDataClient
from src.similarity import compute_feature_vectors, find_similar_players
from src.clustering import perform_clustering

logger = logging.getLogger(__name__)

STOP_WORDS = {
    "junior", "de", "da", "del", "la", "van", "von", "san", "dos",
    "di", "le", "el", "fc", "cf", "ca", "cd", "ud", "rc", "afc", "club"
}


def normalize_str(text: str) -> str:
    """Normaliza texto eliminando tildes y caracteres especiales."""
    if not text:
        return ""
    nfkd = unicodedata.normalize("NFD", str(text))
    return "".join(c for c in nfkd if unicodedata.category(c) != "Mn").lower().strip()


def clean_team_name(team: Optional[str]) -> str:
    """Elimina prefijos/sufijos de clubes (FC, CF, CA, etc.) para comparar nombres limpios."""
    if not team:
        return ""
    words = [w for w in normalize_str(team).split() if w not in STOP_WORDS]
    return " ".join(words)


def score_player_match(
    target_name: str,
    target_team: Optional[str],
    candidate_player: dict,
    candidate_team: Optional[str],
) -> int:
    """Calcula una puntuación de similitud precisa para emparejar jugadores sin falsos positivos."""
    t_name_norm = normalize_str(target_name)
    t_parts = [p for p in t_name_norm.split() if p not in STOP_WORDS and len(p) >= 3]

    c_name_norm = normalize_str(candidate_player.get("name", ""))
    c_first_norm = normalize_str(candidate_player.get("firstname", "") or "")
    c_last_norm = normalize_str(candidate_player.get("lastname", "") or "")
    c_full = f"{c_first_norm} {c_last_norm}".strip()

    # 1. PUNTUACIÓN DE NOMBRE (ESTRICTAMENTE OBLIGATORIA)
    name_score = 0
    if t_name_norm == c_full or t_name_norm == c_name_norm:
        name_score += 100
    elif t_name_norm in c_full or c_full in t_name_norm:
        name_score += 80
    else:
        for p in t_parts:
            if p == c_first_norm or p == c_last_norm:
                name_score += 50
            elif p in c_first_norm.split() or p in c_last_norm.split():
                name_score += 45
            elif p in c_name_norm.split():
                name_score += 40

    # SI NO HAY COINCIDENCIA DE NOMBRE, EL RESULTADO ES 0 (EVITA EMPAREJAMIENTOS ERRÓNEOS)
    if name_score == 0:
        return 0

    # 2. PUNTUACIÓN DE EQUIPO (BONIFICACIÓN DE DESEMPATE)
    team_score = 0
    t_team_clean = clean_team_name(target_team)
    c_team_clean = clean_team_name(candidate_team)

    if t_team_clean and c_team_clean:
        if t_team_clean == c_team_clean:
            team_score += 100
        elif t_team_clean in c_team_clean or c_team_clean in t_team_clean:
            team_score += 80

    return name_score + team_score


class DataService:
    """Punto central de lógica de negocio del scouting."""

    def __init__(self):
        self.api_football = APIFootballClient()
        self.football_data = FootballDataClient()

    # ── Catálogo de jugadores para el desplegable ─────────────────────────

    def get_catalog(self) -> list[dict]:
        """Devuelve el catálogo de jugadores para la UI."""
        catalog_path = CACHE_DIR / "players_catalog.json"
        if catalog_path.exists():
            try:
                with open(catalog_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.error("Error leyendo players_catalog.json: %s", e)

        # Si no existe, construirlo usando football-data.org (solo 5 peticiones)
        catalog = []
        comps = {
            "Premier League": "PL",
            "La Liga": "PD",
            "Bundesliga": "BL1",
            "Serie A": "SA",
            "Ligue 1": "FL1",
        }
        for league_name, code in comps.items():
            try:
                teams = self.football_data.get_competition_teams(code)
                for t in teams:
                    team_name = t.get("name", "")
                    t_id = t.get("id")
                    for p in t.get("squad", []) or []:
                        p_name = p.get("name", "")
                        if p_name:
                            catalog.append({
                                "name": p_name,
                                "team_name": team_name,
                                "team_id": t_id,
                                "league_name": league_name,
                                "position": p.get("position", "Unknown"),
                                "nationality": p.get("nationality", ""),
                                "display_label": f"{p_name} ({team_name} - {league_name})",
                            })
            except Exception as exc:
                logger.warning("Error cargando equipos de %s: %s", code, exc)

        if catalog:
            with open(catalog_path, "w", encoding="utf-8") as f:
                json.dump(catalog, f, ensure_ascii=False, indent=2)

        return catalog

    # ── Búsqueda de jugador en API-Football / Caché ──────────────────────

    def find_player_stats(
        self,
        player_name: str,
        team_name: Optional[str] = None,
        league_name: Optional[str] = None,
    ) -> Optional[dict]:
        """Busca las estadísticas del jugador en su liga en API-Football."""
        season = get_current_season()
        norm_name = normalize_str(player_name)
        parts = [p for p in norm_name.split() if p not in STOP_WORDS and len(p) >= 3]

        # Si no se pasó league_name, buscar en el catálogo local
        if not league_name:
            catalog = self.get_catalog()
            for item in catalog:
                if normalize_str(item.get("name", "")) == norm_name:
                    league_name = item.get("league_name")
                    if not team_name:
                        team_name = item.get("team_name")
                    break

        queries = []
        if parts:
            queries.append(parts[-1])  # Apellido primero (ej. Saka, Palmer, Guler, Oroz)
            if len(parts) > 1:
                queries.append(parts[0])  # Primer nombre
        else:
            queries.append(norm_name)

        # Si se conoce la liga del jugador, consultar únicamente esa liga (1 sola petición)
        if league_name and league_name in LEAGUES:
            league_ids_to_try = [LEAGUES[league_name]["api_football_id"]]
        else:
            league_ids_to_try = [v["api_football_id"] for v in LEAGUES.values()]

        best_candidate = None
        best_score = -1

        for lid in league_ids_to_try:
            for q in queries:
                try:
                    params = {"search": q, "season": season, "league": lid}
                    data = self.api_football._request("players", params)
                    items = data.get("response", [])
                    for item in items:
                        p_obj = item.get("player", {})
                        stats_list = item.get("statistics", [])
                        primary = stats_list[0] if stats_list else {}
                        c_team = primary.get("team", {}).get("name", "")

                        s = score_player_match(player_name, team_name, p_obj, c_team)
                        if s > best_score and s >= 40:
                            best_score = s
                            games = primary.get("games", {})
                            goals_data = primary.get("goals", {})
                            passes = primary.get("passes", {})
                            shots = primary.get("shots", {})
                            tackles = primary.get("tackles", {})
                            dribbles = primary.get("dribbles", {})
                            cards = primary.get("cards", {})

                            best_candidate = {
                                "player_id": p_obj.get("id"),
                                "name": p_obj.get("name"),
                                "firstname": p_obj.get("firstname"),
                                "lastname": p_obj.get("lastname"),
                                "photo": p_obj.get("photo"),
                                "nationality": p_obj.get("nationality"),
                                "position": games.get("position", "Unknown"),
                                "team_id": primary.get("team", {}).get("id"),
                                "team_name": primary.get("team", {}).get("name"),
                                "team_logo": primary.get("team", {}).get("logo"),
                                "league_id": primary.get("league", {}).get("id"),
                                "league_name": primary.get("league", {}).get("name"),
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
                    # Si encontramos con alta confianza, no gastar más peticiones
                    if best_score >= 80:
                        return best_candidate
                except Exception as e:
                    logger.warning("Error buscando '%s' en liga %d: %s", q, lid, e)

        return best_candidate

    # ── Stats por 90 minutos ─────────────────────────────────────────────

    @staticmethod
    def _compute_per90_stats(df: pd.DataFrame) -> pd.DataFrame:
        """Calcula las features per-90 y el porcentaje de pases correctamente."""
        df = df.copy()
        minutes = df["minutes"].replace(0, np.nan)

        if "passes_accuracy" in df.columns:
            def clean_pct(val):
                if pd.isna(val):
                    return 0.0
                if isinstance(val, str):
                    val = val.replace("%", "").strip()
                try:
                    return float(val)
                except (ValueError, TypeError):
                    return 0.0

            accuracy_clean = df["passes_accuracy"].apply(clean_pct)
            df["pass_pct"] = (accuracy_clean / 100.0).clip(0, 1)
        else:
            df["pass_pct"] = 0.0

        df["goals_p90"] = (df["goals"] / minutes * 90).fillna(0)
        df["passes_p90"] = (df["passes_total"] / minutes * 90).fillna(0)
        df["shots_p90"] = (df["shots_total"] / minutes * 90).fillna(0)
        df["dribbles_p90"] = (df["dribbles_success"] / minutes * 90).fillna(0)
        df["tackles_p90"] = (df["tackles_total"] / minutes * 90).fillna(0)
        df["interceptions_p90"] = (df["interceptions"] / minutes * 90).fillna(0)

        return df

    # ── Helpers de stats ─────────────────────────────────────────────────

    @staticmethod
    def _build_stats_dict(row: pd.Series) -> dict:
        """Construye el dict de stats para mostrar en la tabla de la UI."""
        return {
            "PJ": int(row.get("appearances", 0)),
            "G": int(row.get("goals", 0)),
            "AS": int(row.get("assists", 0)),
            "PC": int(row.get("passes_total", 0)),
            "%P": round(float(row.get("pass_pct", 0)), 2),
            "TR": int(row.get("shots_total", 0)),
            "RC": int(row.get("dribbles_success", 0)),
            "ER": int(row.get("tackles_total", 0)),
            "ID": int(row.get("interceptions", 0)),
            "AM": int(row.get("yellow_cards", 0)),
        }

    @staticmethod
    def _build_comparison_dict(row: pd.Series) -> dict:
        """Construye el dict de comparación (per-90 / totales) para gráficos de barras."""
        return {
            "G": round(float(row.get("goals_p90", 0)), 2),
            "AS": round(float(row.get("assists", 0)), 1),
            "PC": round(float(row.get("passes_p90", 0)), 1),
            "TR": round(float(row.get("shots_p90", 0)), 2),
            "RC": round(float(row.get("dribbles_p90", 0)), 2),
            "ER": round(float(row.get("tackles_p90", 0)), 2),
            "ID": round(float(row.get("interceptions_p90", 0)), 2),
            "AM": round(float(row.get("yellow_cards", 0)), 1),
        }

    # ── Scouting principal ───────────────────────────────────────────────

    def run_scouting(
        self,
        player_name: str,
        team_name: Optional[str],
        positions: list[str],
        league_names: list[str],
        min_matches: int,
        min_minutes: int,
        player_league: Optional[str] = None,
        player_id: Optional[int] = None,
    ) -> dict:
        """Ejecuta el análisis completo de scouting."""
        season = get_current_season()

        # ── 1. Obtener jugadores de las ligas seleccionadas ──────────────
        all_players: list[dict] = []
        for league_name in league_names:
            league_info = LEAGUES.get(league_name)
            if not league_info:
                logger.warning("Liga no reconocida: %s", league_name)
                continue
            players = self.api_football.get_league_players(
                league_info["api_football_id"], season,
            )
            all_players.extend(players)

        if not all_players:
            return {"error": "No se pudieron obtener datos de las ligas seleccionadas. Verifica la conexión o el límite de la API."}

        df_all = pd.DataFrame(all_players)

        # ── 2. Localizar al jugador seleccionado con puntuación estricta ──
        selected_player_dict = None
        best_local_score = -1

        for idx, row in df_all.iterrows():
            cand_p = {
                "name": str(row.get("name", "")),
                "firstname": str(row.get("firstname", "") or ""),
                "lastname": str(row.get("lastname", "") or ""),
            }
            cand_team = str(row.get("team_name", ""))
            s = score_player_match(player_name, team_name, cand_p, cand_team)
            if s > best_local_score and s >= 40:
                best_local_score = s
                selected_player_dict = row.to_dict()

        # Si no se encontró en las ligas descargadas o la puntuación es baja (< 80), buscar en API-Football usando su liga de origen
        if not selected_player_dict or best_local_score < 80:
            api_found = self.find_player_stats(player_name, team_name, player_league)
            if api_found:
                selected_player_dict = api_found

        if not selected_player_dict:
            return {
                "error": f"No se encontraron estadísticas para '{player_name}' en la temporada actual. "
                         f"Prueba con otro jugador del catálogo."
            }

        # ── 3. Aplicar filtros a los candidatos ──────────────────────────
        df = df_all.copy()

        # Filtro de posiciones
        api_positions = set()
        for p in positions:
            mapped = POSITION_MAPPING.get(p, [])
            if isinstance(mapped, list):
                api_positions.update(mapped)
            elif isinstance(mapped, str):
                api_positions.add(mapped)

        if api_positions:
            df = df[df["position"].isin(api_positions)]

        # Filtros de partidos y minutos
        df = df[df["appearances"] >= min_matches]
        df = df[df["minutes"] >= min_minutes]

        # Asegurarse de que el jugador seleccionado esté incluido para calcular las features
        sel_id = selected_player_dict.get("player_id")
        selected_in_df = False

        if sel_id:
            match_mask = df["player_id"] == sel_id
            if match_mask.any():
                selected_in_df = True

        if not selected_in_df:
            sel_df = pd.DataFrame([selected_player_dict])
            df = pd.concat([df, sel_df], ignore_index=True)

        # Eliminar duplicados por player_id
        if "player_id" in df.columns:
            df = df.drop_duplicates(subset=["player_id"]).reset_index(drop=True)

        if len(df) < 2:
            return {
                "error": "No hay suficientes jugadores que cumplan los filtros para comparar. "
                         "Prueba a reducir el mínimo de minutos o partidos, o selecciona más ligas."
            }

        # ── 4. Calcular stats por 90 minutos ─────────────────────────────
        df = self._compute_per90_stats(df)
        df = df.reset_index(drop=True)

        # Encontrar el índice del jugador seleccionado en df
        selected_idx = None
        if sel_id:
            matches = df.index[df["player_id"] == sel_id].tolist()
            if matches:
                selected_idx = matches[0]

        if selected_idx is None:
            best_idx_score = -1
            for i, r in df.iterrows():
                cand_p = {
                    "name": str(r.get("name", "")),
                    "firstname": str(r.get("firstname", "") or ""),
                    "lastname": str(r.get("lastname", "") or ""),
                }
                cand_team = str(r.get("team_name", ""))
                s = score_player_match(player_name, team_name, cand_p, cand_team)
                if s > best_idx_score:
                    best_idx_score = s
                    selected_idx = i

        if selected_idx is None:
            selected_idx = len(df) - 1

        # ── 5. Features escaladas y Similitud del Coseno ─────────────────
        scaled_features, scaler = compute_feature_vectors(df)
        similar = find_similar_players(scaled_features, selected_idx, top_n=10)

        # ── 6. Clustering K-Means + PCA ──────────────────────────────────
        clustering_result = perform_clustering(
            scaled_features,
            df["name"].tolist(),
            selected_idx,
        )

        # ── 7. Construir respuesta estructurada ──────────────────────────
        selected_row = df.iloc[selected_idx]

        similar_players = []
        for rank, (idx, sim_score) in enumerate(similar, 1):
            row = df.iloc[idx]
            similar_players.append({
                "rank": rank,
                "player_id": int(row.get("player_id", 0)),
                "name": str(row["name"]),
                "photo": str(row.get("photo", "")),
                "team_name": str(row.get("team_name", "")),
                "team_logo": str(row.get("team_logo", "")),
                "league_name": str(row.get("league_name", "")),
                "nationality": str(row.get("nationality", "")),
                "similarity": round(sim_score, 4),
                "cluster": int(clustering_result["labels"][idx]),
                "stats": self._build_stats_dict(row),
            })

        top1_idx = similar[0][0] if similar else selected_idx
        top1_row = df.iloc[top1_idx]

        selected_cluster = clustering_result["selected_cluster"]
        cluster_mask_arr = np.array(clustering_result["labels"]) == selected_cluster
        cluster_df = df[cluster_mask_arr]

        comparison = {
            "selected": self._build_comparison_dict(selected_row),
            "top1": self._build_comparison_dict(top1_row),
            "top1_name": str(top1_row["name"]),
            "cluster_avg": {
                "G": round(float(cluster_df["goals_p90"].mean()), 2),
                "AS": round(float(cluster_df["assists"].mean()), 1),
                "PC": round(float(cluster_df["passes_p90"].mean()), 1),
                "TR": round(float(cluster_df["shots_p90"].mean()), 2),
                "RC": round(float(cluster_df["dribbles_p90"].mean()), 2),
                "ER": round(float(cluster_df["tackles_p90"].mean()), 2),
                "ID": round(float(cluster_df["interceptions_p90"].mean()), 2),
                "AM": round(float(cluster_df["yellow_cards"].mean()), 1),
            },
        }

        return {
            "selected_player": {
                "player_id": int(selected_row.get("player_id", 0)),
                "name": str(selected_row["name"]),
                "photo": str(selected_row.get("photo", "")),
                "team_name": str(selected_row.get("team_name", "")),
                "team_logo": str(selected_row.get("team_logo", "")),
                "league_name": str(selected_row.get("league_name", "")),
                "nationality": str(selected_row.get("nationality", "")),
                "position": str(selected_row.get("position", "")),
                "stats": self._build_stats_dict(selected_row),
            },
            "similar_players": similar_players,
            "clustering": clustering_result,
            "comparison": comparison,
            "total_players_analyzed": len(df),
        }

    # ── Estado de la API ─────────────────────────────────────────────────

    def get_api_status(self) -> dict:
        remaining = self.api_football.get_remaining_requests()
        return {"api_football_remaining": remaining}

"""
Scraper para OddsMonitor - Extração de Odds de Todas as Casas
=============================================================
Bate diretamente na API Supabase do OddsMonitor.
Retorna as odds de TODAS as casas disponíveis por jogo.

Estrutura de cada jogo retornado:
  {
    "id":         chave única do jogo,
    "partida":    "Time A vs Time B",
    "time_casa":  "Time A",
    "time_visitante": "Time B",
    "competicao": "Brasil - Copa do Brasil",
    "data":       "25/02",
    "hora":       "22:00",
    "best": {
      "casa":     {"odd": 2.51, "bookmakers": ["betnacionalso"]},
      "empate":   {"odd": 2.90, "bookmakers": ["aposta1"]},
      "visitante":{"odd": 3.35, "bookmakers": ["superbet"]},
    },
    "casas": [
      {
        "bookmaker": "aposta1",
        "odd1": 2.36,    # odd Casa
        "oddX": 2.90,    # odd Empate
        "odd2": 3.20,    # odd Visitante
        "isBest1": false,
        "isBestX": true,
        "isBest2": false,
        "href": "https://..."  # link direto para o jogo nessa casa
      },
      ...
    ]
  }
"""

import requests
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

# ─── Configurações da API ───────────────────────────────────────────────────
SUPABASE_URL = "https://hpurabsdrshnmvsndqlo.supabase.co/rest/v1/rpc/get_latest_games"

SUPABASE_ANON_KEY = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImhwdXJhYnNkcnNobm12c25kcWxvIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjU3OTgwODQsImV4cCI6MjA4MTM3NDA4NH0."
    "9LUdJE5LcGKpl6z4LGeKjrBdIPcoVOHgclfzzqN4JIs"
)

HEADERS = {
    "apikey":        SUPABASE_ANON_KEY,
    "authorization": f"Bearer {SUPABASE_ANON_KEY}",
    "content-type":  "application/json",
    "x-client-info": "supabase-js-web/2.97.0",
    "origin":        "https://oddsmonitor.com.br",
    "referer":       "https://oddsmonitor.com.br/",
}

# Nomes de exibição das casas (normalizados)
NOMES_CASAS = {
    "7k":               "7K",
    "aposta1":          "Aposta1",
    "aposta1so":        "Aposta1 SO",
    "bet365":           "Bet365",
    "bet365so":         "Bet365 SO",
    "betano":           "Betano",
    "betanoso":         "Betano SO",
    "betbraso":         "BetBra SO",
    "betnacional":      "Betnacional",
    "betnacionalso":    "Betnacional SO",
    "betsul":           "Betsul",
    "br4":              "Br4",
    "esportesdasorte":  "Esportes da Sorte",
    "esportesdasorteso":"Esportes da Sorte SO",
    "esportiva":        "Esportiva",
    "estrelabet":       "Estrelabet",
    "estrelabetso":     "Estrelabet SO",
    "kto":              "KTO",
    "ktoso":            "KTO SO",
    "lotogreen":        "Lotogreen",
    "mcgames":          "MC Games",
    "novibet":          "Novibet",
    "pixbet":           "Pixbet",
    "pixbetso":         "Pixbet SO",
    "sortenabet":       "Sortenabet",
    "sportingbet":      "Sportingbet",
    "stake":            "Stake",
    "stakeso":          "Stake SO",
    "superbet":         "Superbet",
    "vaidebetso":       "Vaidebet SO",
}


def _buscar_raw() -> List[Dict[str, Any]]:
    """
    Faz a requisição para a API e retorna a lista bruta de itens.
    Levanta exceção em caso de erro.
    """
    response = requests.post(
        SUPABASE_URL,
        headers=HEADERS,
        json={},
        timeout=15,
    )
    response.raise_for_status()
    dados = response.json()

    if isinstance(dados, list):
        return dados
    if isinstance(dados, dict):
        return dados.get("data", {}).get("items", dados.get("items", []))
    return []


def buscar_todos_jogos() -> List[Dict[str, Any]]:
    """
    Busca TODOS os jogos com as odds de TODAS as casas disponíveis.

    Retorna lista de jogos, cada um com:
      - Informações da partida (times, competição, data, hora)
      - best: melhores odds por resultado (1/X/2) e em qual casa estão
      - casas: lista completa de todas as casas com odd1, oddX, odd2 e link

    Os jogos são ordenados por competição e horário.
    """
    logger.info("[OddsMonitor] Buscando todos os jogos com todas as casas...")

    try:
        items = _buscar_raw()
    except requests.exceptions.RequestException as e:
        logger.error(f"[OddsMonitor] Erro na requisicao: {e}")
        return []
    except Exception as e:
        logger.error(f"[OddsMonitor] Erro inesperado: {e}")
        return []

    logger.info(f"[OddsMonitor] {len(items)} itens recebidos da API")

    jogos = []
    for item in items:
        try:
            match = item.get("match", {})
            best_raw = item.get("best", {})
            books_raw = item.get("books", [])

            time_casa      = match.get("team1", "?")
            time_visitante = match.get("team2", "?")
            data           = match.get("date", "")
            hora           = match.get("kickoff_display", "")
            competicao     = match.get("competition", "")

            # Monta o campo "best" de forma padronizada
            best = {
                "casa": {
                    "odd":        best_raw.get("1", {}).get("odd") or best_raw.get("odd1", {}).get("odd", 0),
                    "bookmakers": best_raw.get("1", {}).get("bookmakers") or best_raw.get("odd1", {}).get("bookmakers", []),
                },
                "empate": {
                    "odd":        best_raw.get("X", {}).get("odd") or best_raw.get("oddX", {}).get("odd", 0),
                    "bookmakers": best_raw.get("X", {}).get("bookmakers") or best_raw.get("oddX", {}).get("bookmakers", []),
                },
                "visitante": {
                    "odd":        best_raw.get("2", {}).get("odd") or best_raw.get("odd2", {}).get("odd", 0),
                    "bookmakers": best_raw.get("2", {}).get("bookmakers") or best_raw.get("odd2", {}).get("bookmakers", []),
                },
            }

            # Processa todas as casas disponíveis para esse jogo
            casas = []
            for book in books_raw:
                nome_raw = book.get("bookmaker", "")
                casas.append({
                    "bookmaker":     nome_raw,
                    "nome_display":  NOMES_CASAS.get(nome_raw, nome_raw.title()),
                    "odd1":          book.get("odd1", 0),   # Casa
                    "oddX":          book.get("oddX", 0),   # Empate
                    "odd2":          book.get("odd2", 0),   # Visitante
                    "isBest1":       book.get("isBest1", False),
                    "isBestX":       book.get("isBestX", False),
                    "isBest2":       book.get("isBest2", False),
                    "href":          book.get("href", ""),
                    "atualizado_em": book.get("updated_at", ""),
                })

            # Ordena casas: melhores odds primeiro, depois por nome
            casas.sort(key=lambda c: (
                not (c["isBest1"] or c["isBestX"] or c["isBest2"]),
                c["nome_display"]
            ))

            # ID único para o jogo
            jogo_id = item.get("key", f"{time_casa}|{time_visitante}").replace(" ", "_").lower()

            jogos.append({
                "id":              jogo_id,
                "partida":         f"{time_casa} vs {time_visitante}",
                "time_casa":       time_casa,
                "time_visitante":  time_visitante,
                "competicao":      competicao,
                "data":            data,
                "hora":            hora,
                "total_casas":     len(casas),
                "best":            best,
                "casas":           casas,
            })

        except Exception as e:
            logger.warning(f"[OddsMonitor] Erro ao processar item: {e}")
            continue

    # Ordena por competição + horário
    jogos.sort(key=lambda j: (j["competicao"], j["hora"]))

    logger.info(f"[OddsMonitor] {len(jogos)} jogos processados com sucesso")
    return jogos


def buscar_jogo_por_id(jogo_id: str) -> Optional[Dict[str, Any]]:
    """
    Busca um jogo específico pelo seu ID e retorna todas as casas.
    Útil para exibir o detalhamento de um jogo clicado.
    """
    jogos = buscar_todos_jogos()
    return next((j for j in jogos if j["id"] == jogo_id), None)


def buscar_odds_freebet(valor_freebet: float = 10.0, casa_freebet: Optional[str] = None):
    """
    Retorna oportunidades de freebet calculadas a partir das melhores odds.
    Compatível com a versão anterior do scraper.
    """
    jogos = buscar_todos_jogos()
    resultado = []

    for jogo in jogos:
        best = jogo["best"]
        odd_1 = best["casa"]["odd"]
        odd_x = best["empate"]["odd"]
        odd_2 = best["visitante"]["odd"]

        # Filtra por casa se especificado
        if casa_freebet:
            cl = casa_freebet.lower()
            tem = (
                any(cl in b.lower() for b in best["casa"]["bookmakers"])
                or any(cl in b.lower() for b in best["empate"]["bookmakers"])
                or any(cl in b.lower() for b in best["visitante"]["bookmakers"])
            )
            if not tem:
                continue

        if odd_1 <= 1 or odd_x <= 1 or odd_2 <= 1:
            continue

        calculo = _calcular_roi_freebet(odd_1, odd_x, odd_2, valor_freebet)

        entrada = {
            "partida":         jogo["partida"],
            "time_casa":       jogo["time_casa"],
            "time_visitante":  jogo["time_visitante"],
            "competicao":      jogo["competicao"],
            "data":            jogo["data"],
            "hora":            jogo["hora"],
            "odds": {
                "casa":      best["casa"],
                "empate":    best["empate"],
                "visitante": best["visitante"],
            },
        }

        if calculo:
            entrada.update({
                "roi_pct":          calculo["roi_pct"],
                "lucro_garantido":  calculo["lucro_garantido"],
                "total_investido":  calculo["total_investido"],
                "apostas_sugeridas": calculo["apostas"],
                "valor_freebet":    valor_freebet,
            })

        resultado.append(entrada)

    resultado.sort(key=lambda x: x.get("roi_pct", 0), reverse=True)
    return resultado


def _calcular_roi_freebet(odd_1, odd_x, odd_2, valor_freebet=10.0):
    """Calcula ROI e valores a apostar em cada resultado para freebet."""
    try:
        inv_casa      = 1.0 / odd_1
        inv_empate    = 1.0 / odd_x
        inv_visitante = 1.0 / (odd_2 - 1) if odd_2 > 1 else None
        if inv_visitante is None:
            return None

        total_inv   = inv_casa + inv_empate + inv_visitante
        stake_casa  = (valor_freebet / total_inv) * inv_casa
        stake_emp   = (valor_freebet / total_inv) * inv_empate
        stake_vis   = valor_freebet

        ret_casa    = stake_casa * odd_1
        ret_emp     = stake_emp  * odd_x
        ret_vis     = stake_vis  * (odd_2 - 1)

        lucro       = min(ret_casa, ret_emp, ret_vis) - stake_casa - stake_emp
        roi_pct     = (lucro / valor_freebet) * 100

        return {
            "roi_pct":         round(roi_pct, 1),
            "lucro_garantido": round(lucro, 2),
            "total_investido": round(stake_casa + stake_emp, 2),
            "apostas": {
                "casa":               round(stake_casa, 2),
                "empate":             round(stake_emp, 2),
                "visitante_freebet":  round(stake_vis, 2),
            }
        }
    except Exception:
        return None


# ─── Execução direta (teste) ─────────────────────────────────────────────────
if __name__ == "__main__":
    import sys, json
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")

    jogos = buscar_todos_jogos()
    print(f"\nTotal de jogos: {len(jogos)}\n")

    # Mostra o primeiro jogo com todas as casas
    if jogos:
        j = jogos[0]
        print(f"=== {j['partida']} ===")
        print(f"Competicao: {j['competicao']} | {j['data']} {j['hora']}")
        print(f"Total de casas disponíveis: {j['total_casas']}\n")
        print(f"{'Casa':<22} {'1 (Casa)':<12} {'X (Empate)':<12} {'2 (Visit)':<12} {'Melhor?'}")
        print("-" * 70)
        for casa in j["casas"]:
            melhores = []
            if casa["isBest1"]: melhores.append("1")
            if casa["isBestX"]: melhores.append("X")
            if casa["isBest2"]: melhores.append("2")
            tag = f"MELHOR {'+'.join(melhores)}" if melhores else ""
            print(f"{casa['nome_display']:<22} {casa['odd1']:<12} {casa['oddX']:<12} {casa['odd2']:<12} {tag}")

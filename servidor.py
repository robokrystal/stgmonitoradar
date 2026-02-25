"""
=============================================================
  STGRadar — Servidor Principal
=============================================================

Como usar:
  python servidor.py

Endpoints disponíveis:
  GET /odds-monitor              → interface principal
  GET /api/jogos/todas-casas     → lista todos os jogos com odds de todas as casas
  GET /api/jogos/todas-casas/<id>→ detalhe de um jogo específico
  GET /api/atualizar             → invalida o cache e força nova busca
  GET /api/status                → verifica se o servidor está ok
=============================================================
"""

from flask import Flask, jsonify, send_from_directory, request
from flask_cors import CORS
import time
import os
from datetime import datetime

from scrapers.oddsmonitor import buscar_todos_jogos

# ─── Configuração ──────────────────────────────────────────
app = Flask(__name__, static_folder=".")
CORS(app)

# ─── Cache em memória (evita bater na API a cada request) ──
_cache_jogos = None
_cache_ts    = 0
CACHE_TTL    = 60   # segundos (1 minuto)

def _obter_jogos():
    """Retorna jogos do cache se ainda válido, senão busca da API."""
    global _cache_jogos, _cache_ts
    if _cache_jogos is None or (time.time() - _cache_ts) > CACHE_TTL:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Cache expirado — buscando dados do OddsMonitor...")
        _cache_jogos = buscar_todos_jogos()
        _cache_ts    = time.time()
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {len(_cache_jogos)} jogos carregados.")
    return _cache_jogos

def _invalidar_cache():
    """Força a próxima chamada a buscar dados frescos."""
    global _cache_ts
    _cache_ts = 0


# ==============================================================
# ROTAS
# ==============================================================

@app.route("/")
@app.route("/odds-monitor")
def odds_monitor_page():
    """Serve a interface principal."""
    return send_from_directory(".", "odds_monitor.html")


@app.route("/favicon.svg")
def favicon():
    """Serve o ícone da aplicação."""
    return send_from_directory(".", "favicon.svg", mimetype="image/svg+xml")


@app.route("/api/status")
def status():
    """Verifica se o servidor está funcionando."""
    idade_cache = round(time.time() - _cache_ts)
    return jsonify({
        "servidor":    "STGRadar",
        "status":      "ok",
        "cache_age_s": idade_cache,
        "cache_ok":    idade_cache < CACHE_TTL,
        "total_jogos": len(_cache_jogos) if _cache_jogos else 0,
    })


@app.route("/api/atualizar")
def forcar_atualizacao():
    """Invalida o cache — próxima requisição buscará dados frescos."""
    _invalidar_cache()
    return jsonify({"mensagem": "Cache invalidado. Próxima requisição buscará dados atualizados."})


@app.route("/api/jogos/todas-casas")
def todas_casas():
    """
    Retorna jogos com odds de todas as casas.

    Query params opcionais:
      ?comp=Copa do Brasil   → filtra por competição
      ?q=flamengo            → busca por nome de time/partida
    """
    jogos = _obter_jogos()

    comp = request.args.get("comp", "").strip()
    if comp:
        jogos = [j for j in jogos if j["competicao"].lower() == comp.lower()]

    q = request.args.get("q", "").strip().lower()
    if q:
        jogos = [j for j in jogos if q in j["partida"].lower() or q in j["competicao"].lower()]

    return jsonify({
        "status":        "ok",
        "fonte":         "OddsMonitor (oddsmonitor.com.br)",
        "total":         len(jogos),
        "atualizado_em": datetime.now().isoformat(),
        "cache_age_s":   round(time.time() - _cache_ts),
        "jogos":         jogos,
    })


@app.route("/api/jogos/todas-casas/<path:jogo_id>")
def detalhe_todas_casas(jogo_id):
    """Retorna as odds de todas as casas para um jogo específico pelo ID."""
    jogos = _obter_jogos()
    jogo  = next((j for j in jogos if j["id"] == jogo_id), None)
    if not jogo:
        return jsonify({"erro": f"Jogo '{jogo_id}' não encontrado"}), 404
    return jsonify(jogo)


# ==============================================================
# INICIALIZAÇÃO
# ==============================================================

if __name__ == "__main__":
    print("""
╔══════════════════════════════════════════════════════╗
║              STGRadar — Servidor API                ║
╠══════════════════════════════════════════════════════╣
║  Interface: http://127.0.0.1:5000/odds-monitor       ║
║  API:       http://127.0.0.1:5000/api/jogos/todas-casas ║
╚══════════════════════════════════════════════════════╝
    """)

    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)

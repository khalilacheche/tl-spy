from __future__ import annotations

import logging
import time

import anthropic

from app.config import settings
from app.data.network import TransportNetwork
from app.model.markov import Sighting, SightingState

logger = logging.getLogger(__name__)

EXTRACT_TOOL = {
    "name": "report_sighting",
    "description": "Report a ticket controller sighting extracted from a message.",
    "input_schema": {
        "type": "object",
        "properties": {
            "stop_name": {
                "type": "string",
                "description": "The stop or station name where controllers were spotted. Normalize to standard TL stop name.",
            },
            "line": {
                "type": "string",
                "description": "Transport line (e.g. 'M1', 'M2', 'Bus 9', 'LEB'). Null if unknown.",
                "nullable": True,
            },
            "direction": {
                "type": "string",
                "description": "Stop name they're heading towards. Normalize to standard TL stop name. Null if unknown.",
                "nullable": True,
            },
            "count": {
                "type": "integer",
                "description": "Number of controllers. Default 1.",
            },
            "state": {
                "type": "string",
                "enum": ["in_transit", "boarded", "at_stop", "alighted", "walking"],
                "description": "What the controllers are doing: "
                    "'in_transit' = riding a bus/metro (e.g. 'dans le 9', 'sur la m1'); "
                    "'boarded' = just got on (e.g. 'montés dans le 4', 'sont montés'); "
                    "'at_stop' = at a stop/platform, waiting or checking (e.g. 'à Flon', 'attendent à sallaz', 'sur le quai'); "
                    "'alighted' = just got off (e.g. 'descendu à', 'sortis du', 'quitte'); "
                    "'walking' = walking between stops (e.g. 'marchent direction', 'se dirigent vers').",
            },
            "is_sighting": {
                "type": "boolean",
                "description": "True if reporting a controller sighting. False for questions, rules, off-topic.",
            },
        },
        "required": ["is_sighting"],
    },
}

SYSTEM_PROMPT = """\
You parse messages from a Lausanne (Switzerland) public transport Telegram group where people report ticket controller sightings.

Messages are in French, often informal with typos and abbreviations. Examples:
- "dans le 9 qui arrivent à Boston" → in_transit, Bus 9, stop=Boston
- "3 montés à malley du m1" → boarded, M1, stop=Malley, count=3
- "2 Sallaz m2 ils attendent" → at_stop, M2, stop=Sallaz, count=2
- "Descendu à Chamberonne" → alighted, stop=Chamberonne
- "3 à bel air qui marchent direction flying tiger" → walking, stop=Bel-Air, direction toward
- "Chaudron dir st François" → at_stop, stop=Chauderon, direction=Saint-François
- "Flon M2 direcrion ouchy mtnn" → at_stop, M2, stop=Flon, direction=Ouchy
- "une équipe à la ripone dir tunel" → at_stop, stop=Riponne, direction=Tunnel
- "sur le quai m1 epfl direction flon" → at_stop, M1, stop=EPFL, direction=Flon

Key stops: Flon, Ouchy, Grancy, Gare, Riponne, Bessières, Ours, CHUV, Sallaz, Vennes, Croisettes, Renens, Malley, Bourdonnette, Chamberonne, UNIL-Sorge, UNIL-Mouline, EPFL, Cerisaie, Saint-François, Bel-Air, Chauderon, Tunnel, Blécherette, Pontaise, Bethusy, Bellevaux, Désert, Prilly, Grand-Vennes, Jordils, Vigie, Boston, Lutry, Mémise, Romanel, Bussigny, Sorges, Huttins, Valency, Saint-Paul, Provence.

Common typos: ripone→Riponne, sainf→Saint-François, Chaudron→Chauderon, rennes→Renens, direcrion→direction.

Lines: M1, M2, Bus 1-60+, LEB, Noctambus. "dans le 9" = Bus 9. "du métro" = M2.

Use the report_sighting tool. Set is_sighting=false for non-sighting messages.\
"""

_client: anthropic.Anthropic | None = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    return _client


ALIASES = {
    "saint": "st",
    "saint-": "st-",
    "françois": "françois",
    "francois": "françois",
    "chaudron": "chauderon",
    "blecherette": "blécherette",
    "ripone": "riponne",
    "rennes": "renens",
    "croisette": "croisettes",
    "bessiere": "bessières",
    "bessieres": "bessières",
}


def _simplify(text: str) -> str:
    s = text.lower().strip()
    for k, v in ALIASES.items():
        s = s.replace(k, v)
    s = s.replace("-", " ").replace("'", " ").replace(".", " ").replace("_", " ")
    return " ".join(s.split())


def _normalize_stop(name: str, network: TransportNetwork) -> str | None:
    if not name:
        return None

    query = _simplify(name)

    simple_id = name.lower().strip().replace(" ", "_").replace("-", "_").replace(".", "").replace("'", "")
    if simple_id in network.stops:
        return simple_id

    best_id = None
    best_score = 0
    for stop in network.stops.values():
        stop_norm = _simplify(stop.name)

        if query == stop_norm:
            return stop.id

        if query in stop_norm or stop_norm in query:
            score = min(len(query), len(stop_norm)) * 2
            if score > best_score:
                best_score = score
                best_id = stop.id

        q_tokens = set(query.split())
        s_tokens = set(stop_norm.split())
        overlap = len(q_tokens & s_tokens)
        if overlap > 0:
            score = overlap * 10 + min(len(query), len(stop_norm))
            if score > best_score:
                best_score = score
                best_id = stop.id

    return best_id


STATE_MAP = {
    "in_transit": SightingState.IN_TRANSIT,
    "boarded": SightingState.BOARDED,
    "at_stop": SightingState.AT_STOP,
    "alighted": SightingState.ALIGHTED,
    "walking": SightingState.WALKING,
}


async def parse_message(text: str, network: TransportNetwork) -> Sighting | None:
    client = _get_client()

    try:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=300,
            system=SYSTEM_PROMPT,
            tools=[EXTRACT_TOOL],
            tool_choice={"type": "tool", "name": "report_sighting"},
            messages=[{"role": "user", "content": text}],
        )
    except Exception:
        logger.exception("LLM parsing failed")
        return None

    for block in response.content:
        if block.type == "tool_use" and block.name == "report_sighting":
            data = block.input

            if not data.get("is_sighting"):
                return None

            stop_id = _normalize_stop(data.get("stop_name", ""), network)
            if not stop_id:
                logger.debug(f"Could not match stop: {data.get('stop_name')}")
                return None

            direction_id = _normalize_stop(data.get("direction"), network) if data.get("direction") else None
            count = max(1, min(data.get("count", 1), 10))
            state = STATE_MAP.get(data.get("state", "at_stop"), SightingState.AT_STOP)

            return Sighting(
                stop_id=stop_id,
                timestamp=time.time(),
                direction=direction_id,
                line=data.get("line"),
                count=count,
                state=state,
            )

    return None

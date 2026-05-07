# TL Spy

Real-time heatmap of TL ticket controllers in Lausanne, powered by crowdsourced Telegram sightings and Markov chain propagation.

## How it works

1. **Data ingestion** — A Telegram scraper monitors a channel where riders report controller sightings (stop name, line, direction)
2. **Graph model** — Lausanne's TL network (M1, M2, buses) is represented as a graph where nodes are stops and edges are direct connections
3. **Markov propagation** — Each sighting creates a probability distribution at the reported stop, then propagates forward through the transition matrix over time. Older sightings decay exponentially
4. **Live heatmap** — A React frontend with Leaflet renders the probability distribution as a heatmap, updated in real-time via WebSocket

## Setup

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -e .
cp .env.example .env  # fill in Telegram credentials
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The frontend dev server proxies `/api` requests to the backend on port 8000.

### Manual testing (no Telegram needed)

Report a sighting via the API:

```bash
curl -X POST "http://localhost:8000/api/sightings?stop_id=m2_flon"
curl -X POST "http://localhost:8000/api/sightings?stop_id=m2_gare&line=M2&direction=m2_ouchy"
```

Or use the "Report Sighting" form in the UI sidebar.

## Architecture

```
backend/
  app/
    api/        — FastAPI routes + WebSocket
    data/       — Transport network graph
    model/      — Markov chain tracker
    scraper/    — Telegram listener + message parser
frontend/
  src/
    components/ — Map, heatmap, sidebar
    hooks/      — WebSocket + polling
```

## Extending

- Add more stops/lines in `backend/app/data/network.py`
- Improve message parsing in `backend/app/scraper/telegram.py` (NLP, multilingual)
- Add GTFS import for the full TL network
- Add Facebook group scraper as secondary data source

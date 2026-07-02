from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from .engine import Simulation
from .ai import get_public_settings

app = FastAPI(title="OCP Phase 1")
sim = Simulation()

STATIC = Path(__file__).resolve().parent.parent / "static"


@app.get("/api/state")
def state():
    return sim.get_state()


@app.post("/api/start")
def start():
    sim.start()
    return {"ok": True}


@app.post("/api/pause")
def pause():
    sim.pause()
    return {"ok": True}


@app.post("/api/tick")
def tick():
    sim.tick()
    return {"ok": True}


@app.post("/api/speed/{speed}")
def speed(speed: int):
    sim.set_speed(speed)
    return {"speed": sim.speed}


@app.post("/api/reset")
def reset():
    global sim
    sim.pause()
    sim = Simulation()
    return {"ok": True}


@app.get("/api/settings")
def get_settings():
    return get_public_settings(sim.ai.settings)


@app.post("/api/settings")
def update_settings(body: dict):
    sim.ai.update_settings(body)
    return get_public_settings(sim.ai.settings)


@app.get("/api/ai/stats")
def ai_stats():
    return sim.ai.get_stats()


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


app.mount("/static", StaticFiles(directory=str(STATIC)), name="static")

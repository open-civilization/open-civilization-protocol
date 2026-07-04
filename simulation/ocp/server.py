import sys
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from .engine import Simulation
from .ai import get_public_settings


def _find_repo_root(start: Path) -> Path:
    for candidate in (start.parents[1], start.parents[2], start.parents[3]):
        if (candidate / "agents").exists():
            return candidate
    return start.parents[2]


REPO_ROOT = _find_repo_root(Path(__file__).resolve())
if str(REPO_ROOT) not in sys.path:
    sys.path.append(str(REPO_ROOT))

from agents.simulation_scientist import run_audit
from agents.simulation_scientist import agent_settings
from agents.simulation_scientist.local_loop import LocalAgentRunner
from agents.simulation_scientist.scheduler import AutonomousScheduler

app = FastAPI(title="OCP Phase 1")
sim = Simulation()

STATIC = Path(__file__).resolve().parent.parent / "static"
ENGINE_PATH = Path(__file__).resolve().parent / "engine.py"
agent_runner = LocalAgentRunner(REPO_ROOT, ENGINE_PATH)
agent_scheduler = AutonomousScheduler(agent_runner, REPO_ROOT)


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


@app.get("/api/audit")
def audit(runs: int = 3, ticks: int = 300, seed_base: int = 1000):
    report = run_audit(runs=runs, ticks_per_run=ticks, seed_base=seed_base)
    return report.to_dict()


@app.get("/api/audit/markdown")
def audit_markdown(runs: int = 3, ticks: int = 300, seed_base: int = 1000):
    report = run_audit(runs=runs, ticks_per_run=ticks, seed_base=seed_base)
    return {"markdown": report.to_markdown()}


@app.post("/api/agent/start")
def agent_start(max_iterations: int = 3, ticks_per_iteration: int = 500):
    started, message = agent_runner.start(max_iterations, ticks_per_iteration)
    return {"ok": started, "message": message}


@app.post("/api/agent/stop")
def agent_stop():
    agent_runner.request_stop()
    return {"ok": True}


@app.get("/api/agent/status")
def agent_status():
    return agent_runner.get_status()


@app.get("/api/agent/settings")
def agent_settings_get():
    return agent_settings.get_public_settings(agent_settings.load_settings())


@app.post("/api/agent/settings")
def agent_settings_post(body: dict):
    updated = agent_settings.update_settings(body)
    return agent_settings.get_public_settings(updated)


@app.post("/api/agent/auto/start")
def agent_auto_start(interval_hours: float = 6, max_iterations: int = 3, ticks_per_iteration: int = 500):
    started, message = agent_scheduler.enable(interval_hours, max_iterations, ticks_per_iteration)
    return {"ok": started, "message": message}


@app.post("/api/agent/auto/stop")
def agent_auto_stop():
    ok, message = agent_scheduler.disable()
    return {"ok": ok, "message": message}


@app.get("/api/agent/auto/status")
def agent_auto_status():
    return agent_scheduler.get_status()


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


app.mount("/static", StaticFiles(directory=str(STATIC)), name="static")

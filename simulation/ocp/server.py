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
from agents.simulation_scientist import agent_control

app = FastAPI(title="OCP Phase 1")
sim = Simulation()

STATIC = Path(__file__).resolve().parent.parent / "static"
ENGINE_PATH = Path(__file__).resolve().parent / "engine.py"


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


@app.get("/api/agent/settings")
def agent_settings_get():
    return agent_settings.get_public_settings(agent_settings.load_settings())


@app.post("/api/agent/settings")
def agent_settings_post(body: dict):
    updated = agent_settings.update_settings(body)
    return agent_settings.get_public_settings(updated)


@app.get("/api/agent/settings/raw")
def agent_settings_raw():
    """Unmasked settings (including the real API key) for the polling machine
    to actually call the LLM with. Never call this from browser JS — the
    dashboard UI must keep using the masked /api/agent/settings above."""
    return agent_settings.load_settings()


@app.get("/api/agent/control")
def agent_control_get():
    return agent_control.get_status()


@app.post("/api/agent/control/config")
def agent_control_config(body: dict):
    return agent_control.update_config(
        mode=body.get("mode"),
        interval_hours=body.get("interval_hours"),
        max_iterations=body.get("max_iterations"),
        ticks_per_iteration=body.get("ticks_per_iteration"),
    )


@app.post("/api/agent/control/run-now")
def agent_control_run_now():
    return agent_control.request_run_now()


@app.post("/api/agent/control/stop")
def agent_control_stop():
    return agent_control.request_stop()


@app.post("/api/agent/control/claim")
def agent_control_claim():
    claimed, state = agent_control.claim_run()
    return {"claimed": claimed, "state": state}


@app.post("/api/agent/control/report")
def agent_control_report(body: dict):
    return agent_control.report_run(body)


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


app.mount("/static", StaticFiles(directory=str(STATIC)), name="static")

import json
import os
import uvicorn
from pathlib import Path
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from api.routes import router as api_router
from api.ws import ws_manager
from config import EXPORTS_DIR, ASSETS_DIR, HARDWARE_CONFIG, REQUIRE_AUTHORIZATION
from agent.auth import authorize
from agent.errors import classify_exception
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("viralist_editor")

app = FastAPI(
    title="Viralist AI Video Editor Sub-Agent",
    description="Dual-functional AI-native video editor for Channel Agents and Human Creators",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def enforce_legacy_mutation_authorization(request, call_next):
    """Close the legacy UI/API bypass when production authorization is enabled.

    Agent endpoints validate their body context in AgentService. Legacy endpoints
    use the `X-Viralist-Authorization` JSON header so a browser/service cannot
    mutate a guarded runtime merely by reaching an old route.
    """
    writes = {"POST", "PUT", "PATCH", "DELETE"}
    if REQUIRE_AUTHORIZATION and request.method in writes and request.url.path.startswith("/api/") and not request.url.path.startswith("/api/agent/"):
        try:
            raw = request.headers.get("X-Viralist-Authorization", "")
            context = json.loads(raw) if raw else None
            authorize("timeline.write", context)
        except Exception as exc:
            error = classify_exception(exc)
            return JSONResponse(status_code=error.http_status, content=error.payload())
    return await call_next(request)

# Custom asset streaming route with robust headers
@app.get("/api/assets/{filename:path}")
async def serve_asset_file(filename: str):
    file_path = ASSETS_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Asset not found")

    media_type = None
    if filename.endswith(".mp3"):
        media_type = "audio/mpeg"
    elif filename.endswith(".wav"):
        media_type = "audio/wav"
    elif filename.endswith(".mp4"):
        media_type = "video/mp4"

    return FileResponse(
        path=file_path,
        media_type=media_type,
        headers={
            "Accept-Ranges": "bytes",
            "Cache-Control": "no-cache, no-store, must-revalidate"
        }
    )

app.include_router(api_router)
app.mount("/api/exports", StaticFiles(directory=str(EXPORTS_DIR)), name="exports")

# Mount built frontend if available
FRONTEND_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIST / "assets")), name="frontend_assets")

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        ws_manager.disconnect(websocket)

@app.get("/{full_path:path}")
async def serve_frontend_spa(full_path: str):
    if FRONTEND_DIST.exists():
        index_file = FRONTEND_DIST / "index.html"
        if index_file.exists():
            return FileResponse(index_file)
    return {"message": "Viralist API & MCP Service Online. Frontend building..."}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    logger.info(f"Starting Viralist Editor Engine on http://localhost:{port}. Hardware: {HARDWARE_CONFIG['type']}")
    uvicorn.run(app, host="0.0.0.0", port=port)

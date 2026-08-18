from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from app.api.alerts import router as alerts_router
from app.api.websocket import manager
from app.database.connection import engine, Base
import logging

# Ensure tables are created (in production, use Alembic strictly)
# Since we have Alembic setup, this is optional, but helps for local quickstart
Base.metadata.create_all(bind=engine)

logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="DataSentinel Alert Engine",
    description="Centralized alert and notification engine for healthcare data pipelines.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(alerts_router)

@app.websocket("/ws/alerts")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # We don't really expect clients to send messages, but if they do, we echo or ignore
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@app.get("/health")
def health_check():
    return {"status": "ok"}

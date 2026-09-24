"""FastAPI server for live listening sessions.

One process owns all rooms. Use exactly one Uvicorn worker. Rooms and scores
are temporary; export CSV before stopping or redeploying the server.
"""

import asyncio
import csv
import io
import os
import secrets
import time
import wave
from contextlib import asynccontextmanager, suppress
from dataclasses import dataclass, field
from pathlib import Path

import qrcode
import qrcode.image.svg
from fastapi import FastAPI, Header, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .rules import LEVELS, MAX_PLAYS, SENTENCES, Player, Round, RuleError

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "game" / "web"
AUDIO = ROOT / "game" / "assets" / "processed"
ROOM_TTL = 6 * 60 * 60
MAX_ROOMS = 30
MAX_PLAYERS = 100


@dataclass
class Room:
    code: str
    host_token: str
    created: float = field(default_factory=time.monotonic)
    game: Round = field(default_factory=Round)
    players: dict = field(default_factory=dict)
    watchers: dict = field(default_factory=dict)
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    version: int = 0


ROOMS = {}


def missing_audio():
    """Check all 35 PCM WAV files, without importing the DSP pipeline."""
    bad = []
    for sentence in range(1, len(SENTENCES) + 1):
        for suffix in ["original"] + [f"ch_{x['channels']}" for x in LEVELS]:
            name = f"sentence_{sentence:02d}_{suffix}.wav"
            try:
                with wave.open(str(AUDIO / name), "rb") as wav:
                    if wav.getnframes() == 0:
                        bad.append(name)
            except (OSError, EOFError, wave.Error):
                bad.append(name)
    return bad


async def expire_rooms():
    while True:
        await asyncio.sleep(60)
        for code, room in list(ROOMS.items()):
            if time.monotonic() - room.created > ROOM_TTL:
                ROOMS.pop(code, None)
                for _, queue in list(room.watchers.values()):
                    put_latest(queue, {"type": "expired"})


@asynccontextmanager
async def lifespan(app):
    task = asyncio.create_task(expire_rooms())
    yield
    task.cancel()
    with suppress(asyncio.CancelledError):
        await task


app = FastAPI(title="Can You Hear It? Live", lifespan=lifespan,
              docs_url=None, redoc_url=None)


class JoinRequest(BaseModel):
    nickname: str = Field(min_length=1, max_length=24)


class Command(BaseModel):
    action: str = Field(max_length=24)
    turn: int = Field(ge=0, le=29)
    play_id: str = Field(default="", max_length=64)


class Answer(BaseModel):
    text: str = Field(min_length=1, max_length=300)
    turn: int = Field(ge=0, le=29)


def get_room(code):
    room = ROOMS.get(code)
    if room is None or time.monotonic() - room.created > ROOM_TTL:
        raise HTTPException(404, "Room not found or expired. Ask the host for a new code.")
    return room


def identity(room, token):
    if not isinstance(token, str) or not token.isascii() or len(token) > 128:
        raise HTTPException(401, "Session not recognized. Please join again.")
    if secrets.compare_digest(token, room.host_token):
        return "host"
    if token in room.players:
        return "player"
    raise HTTPException(401, "Session not recognized. Please join again.")


def authenticate(room, header):
    token = (header or "").removeprefix("Bearer ")
    role = identity(room, token)
    return token, role


def ranking(room):
    # Equal scores receive the same rank. Join order only controls display order.
    ordered = sorted(room.players.values(), key=lambda p: -p.score)
    rows = []
    rank = 0
    previous = None
    for position, player in enumerate(ordered, 1):
        if player.score != previous:
            rank = position
        previous = player.score
        rows.append({"rank": rank, "nickname": player.nickname,
                     "score": player.score, "points": player.points.copy()})
    return rows


def snapshot(room, token):
    game = room.game
    host = token == room.host_token
    level = LEVELS[game.level]
    connected = {t for t, _ in room.watchers.values()}
    state = {
        "type": "state", "version": room.version, "code": room.code,
        "role": "host" if host else "player", "phase": game.phase,
        "sentence": game.sentence + 1, "sentences": len(SENTENCES),
        "level_index": game.level, "level": level, "levels": LEVELS,
        "turn": game.turn, "plays": game.plays, "max_plays": MAX_PLAYS,
        "player_count": len(room.players), "host_connected": room.host_token in connected,
        "solved_count": sum(game.sentence in p.solved for p in room.players.values()),
        "answered_count": sum(game.sentence in p.solved or game.turn in p.attempts
                              for p in room.players.values()),
    }
    if host:
        state["players"] = [{"nickname": p.nickname, "score": p.score,
                             "connected": p.token in connected,
                             "solved": game.sentence in p.solved,
                             "answered": game.turn in p.attempts}
                            for p in room.players.values()]
        state["audio_url"] = f"/assets/processed/sentence_{game.sentence + 1:02d}_ch_{level['channels']}.wav"
        state["play_id"] = game.play_id
    else:
        player = room.players[token]
        state["me"] = {"nickname": player.nickname, "score": player.score,
                       "solved": game.sentence in player.solved,
                       "attempted": game.turn in player.attempts,
                       "points": player.points[game.sentence]}
    if game.phase in ("reveal", "finished"):
        state["answer"] = SENTENCES[game.sentence]
        state["leaderboard"] = ranking(room)
        if host:
            state["original_url"] = f"/assets/processed/sentence_{game.sentence + 1:02d}_original.wav"
    return state


def put_latest(queue, message):
    if queue.full():
        queue.get_nowait()
    queue.put_nowait(message)


def broadcast(room):
    room.version += 1
    for token, queue in list(room.watchers.values()):
        put_latest(queue, snapshot(room, token))


@app.get("/healthz")
async def health():
    return {"status": "ok"}


@app.get("/api/readiness")
async def readiness():
    missing = missing_audio()
    return {"ready": not missing, "missing": missing}


@app.post("/api/rooms")
async def create_room():
    if missing_audio():
        raise HTTPException(503, "Some processed WAV files are missing. See /api/readiness.")
    for code, room in list(ROOMS.items()):
        if time.monotonic() - room.created > ROOM_TTL:
            ROOMS.pop(code, None)
    if len(ROOMS) >= MAX_ROOMS:
        raise HTTPException(429, "Too many active rooms. Please try later.")
    code = str(secrets.randbelow(900000) + 100000)
    while code in ROOMS:
        code = str(secrets.randbelow(900000) + 100000)
    room = Room(code=code, host_token=secrets.token_urlsafe(32))
    ROOMS[code] = room
    return {"code": code, "token": room.host_token}


@app.post("/api/rooms/{code}/join")
async def join_room(code: str, body: JoinRequest):
    room = get_room(code)
    async with room.lock:
        if room.game.phase != "lobby":
            raise HTTPException(409, "This game has already started. Join the next game.")
        nickname = " ".join(body.nickname.split())
        if not nickname or any(ord(c) < 32 for c in nickname):
            raise HTTPException(422, "Please enter a valid nickname.")
        if any(p.nickname.casefold() == nickname.casefold() for p in room.players.values()):
            raise HTTPException(409, "That nickname is taken. Choose another one.")
        if len(room.players) >= MAX_PLAYERS:
            raise HTTPException(409, "This room is full.")
        token = secrets.token_urlsafe(32)
        room.players[token] = Player(nickname=nickname, token=token)
        broadcast(room)
        return {"code": code, "token": token}


@app.get("/api/rooms/{code}/state")
async def get_state(code: str, authorization: str = Header(default="")):
    room = get_room(code)
    token, _ = authenticate(room, authorization)
    return snapshot(room, token)


@app.post("/api/rooms/{code}/control")
async def control(code: str, body: Command, authorization: str = Header(default="")):
    room = get_room(code)
    token, role = authenticate(room, authorization)
    if role != "host":
        raise HTTPException(403, "Only the host can control the round.")
    async with room.lock:
        try:
            play_id = secrets.token_hex(12) if body.action == "play" else body.play_id
            room.game.control(body.action, body.turn, list(room.players.values()), play_id)
        except RuleError as error:
            raise HTTPException(409, str(error)) from error
        broadcast(room)
        return snapshot(room, token)


@app.post("/api/rooms/{code}/answer")
async def submit_answer(code: str, body: Answer, authorization: str = Header(default="")):
    room = get_room(code)
    token, role = authenticate(room, authorization)
    if role != "player":
        raise HTTPException(403, "Join as a player to answer.")
    async with room.lock:
        try:
            correct = room.game.answer(room.players[token], body.text, body.turn)
        except RuleError as error:
            raise HTTPException(409, str(error)) from error
        broadcast(room)
        return {"correct": correct, "state": snapshot(room, token)}


@app.get("/api/rooms/{code}/qr")
async def room_qr(code: str, request: Request):
    get_room(code)
    base = (os.environ.get("PUBLIC_BASE_URL") or os.environ.get("RENDER_EXTERNAL_URL")
            or str(request.base_url)).rstrip("/")
    qr = qrcode.QRCode(border=4, box_size=10)
    qr.add_data(f"{base}/join?room={code}")
    qr.make(fit=True)
    output = io.BytesIO()
    qr.make_image(image_factory=qrcode.image.svg.SvgPathImage).save(output)
    return Response(output.getvalue(), media_type="image/svg+xml")


@app.get("/api/rooms/{code}/scores.csv")
async def export_scores(code: str, authorization: str = Header(default="")):
    room = get_room(code)
    _, role = authenticate(room, authorization)
    if role != "host":
        raise HTTPException(403, "Only the host can export the scores.")
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(["rank", "nickname", "total"] + [f"sentence_{n}" for n in range(1, 6)])
    for row in ranking(room):
        name = row["nickname"]
        # Avoid spreadsheet formula interpretation of user-entered nicknames.
        if name.startswith(("=", "+", "-", "@")):
            name = "'" + name
        writer.writerow([row["rank"], name, row["score"], *row["points"]])
    return Response("\ufeff" + output.getvalue(), media_type="text/csv",
                    headers={"Content-Disposition": f'attachment; filename="scores-{code}.csv"'})


@app.websocket("/ws/{code}")
async def updates(socket: WebSocket, code: str):
    # Send credentials in the first frame, not in URLs or access logs.
    await socket.accept()
    watcher_id = secrets.token_hex(12)
    room = None
    sender = None
    try:
        auth = await asyncio.wait_for(socket.receive_json(), timeout=10)
        room = get_room(code)
        token = auth.get("token", "")
        identity(room, token)
        queue = asyncio.Queue(maxsize=1)
        room.watchers[watcher_id] = (token, queue)
        broadcast(room)

        async def send_updates():
            while True:
                message = await queue.get()
                await socket.send_json(message)
                if message.get("type") == "expired":
                    await socket.close(code=4004)
                    return

        sender = asyncio.create_task(send_updates())
        while True:
            # Browser heartbeat, also detects a lost classroom connection.
            message = await asyncio.wait_for(socket.receive_json(), timeout=65)
            if message.get("type") == "ping":
                put_latest(queue, snapshot(room, token))
    except HTTPException as error:
        await socket.close(code=4004 if error.status_code == 404 else 4001)
    except (WebSocketDisconnect, asyncio.TimeoutError, ValueError, TypeError, AttributeError):
        with suppress(RuntimeError):
            await socket.close(code=4001)
    finally:
        if sender:
            sender.cancel()
            with suppress(asyncio.CancelledError, RuntimeError, WebSocketDisconnect):
                await sender
        if room:
            room.watchers.pop(watcher_id, None)
            broadcast(room)


@app.get("/")
async def index():
    return FileResponse(WEB / "live.html")


@app.get("/host")
async def host():
    return FileResponse(WEB / "host.html")


@app.get("/join")
async def join():
    return FileResponse(WEB / "join.html")


# Serve only the UI and prepared audio, never the repository root or Python files.
app.mount("/web", StaticFiles(directory=WEB, html=True, check_dir=False), name="web")
app.mount("/assets/processed", StaticFiles(directory=AUDIO, check_dir=False), name="audio")

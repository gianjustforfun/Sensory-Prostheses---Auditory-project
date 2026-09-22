"""Server and scoring regression tests. Uses synthetic WAV headers, not DSP."""

import asyncio
import wave

import httpx
import pytest
from fastapi.testclient import TestClient

from multiplayer import server
from multiplayer.rules import LEVELS, SENTENCES, Player, Round, RuleError, normalize


@pytest.fixture
def client(tmp_path, monkeypatch):
    server.ROOMS.clear()
    for sentence in range(1, 6):
        for suffix in ["original"] + [f"ch_{l['channels']}" for l in LEVELS]:
            with wave.open(str(tmp_path / f"sentence_{sentence:02d}_{suffix}.wav"), "wb") as wav:
                wav.setparams((1, 2, 22050, 20, "NONE", "not compressed"))
                wav.writeframes(b"\0\0" * 20)
    monkeypatch.setattr(server, "AUDIO", tmp_path)
    with TestClient(server.app) as client:
        yield client
    server.ROOMS.clear()


def credentials(value):
    return {"Authorization": "Bearer " + value["token"]}


def setup(client):
    host = client.post("/api/rooms").json()
    code = host["code"]
    one = client.post(f"/api/rooms/{code}/join", json={"nickname": "Gianluigi"}).json()
    two = client.post(f"/api/rooms/{code}/join", json={"nickname": "Liz"}).json()
    return host, one, two


def cmd(client, host, action, turn=0, **kwargs):
    return client.post(f"/api/rooms/{host['code']}/control", headers=credentials(host),
                       json={"action": action, "turn": turn, **kwargs})


def answer(client, player, text, turn=0):
    return client.post(f"/api/rooms/{player['code']}/answer", headers=credentials(player),
                       json={"text": text, "turn": turn})


def open_answers(client, host, turn=0):
    play = cmd(client, host, "play", turn).json()
    return cmd(client, host, "audio_end", turn, play_id=play["play_id"])


def test_normalization():
    assert normalize("  My SISTER drinks coffee, every morning!! ") == normalize(SENTENCES[2])
    assert normalize("a red book") != normalize("the red book")


def test_audio_readiness(client, monkeypatch, tmp_path):
    assert client.get("/api/readiness").json()["ready"]
    (tmp_path / "sentence_05_ch_32.wav").unlink()
    assert client.get("/api/readiness").json()["missing"] == ["sentence_05_ch_32.wav"]
    assert client.post("/api/rooms").status_code == 503


def test_permissions_and_room_isolation(client):
    host, one, two = setup(client)
    path = f"/api/rooms/{host['code']}/control"
    assert client.post(path, json={"action":"start", "turn":0}).status_code == 401
    assert client.post(path, headers=credentials(one), json={"action":"start", "turn":0}).status_code == 403
    other = client.post("/api/rooms").json()
    assert client.get(f"/api/rooms/{other['code']}/state", headers=credentials(one)).status_code == 401
    assert cmd(client, other, "start").status_code == 409
    assert answer(client, host, SENTENCES[0]).status_code == 403


def test_join_checks_and_no_late_join(client):
    host, one, two = setup(client)
    url = f"/api/rooms/{host['code']}/join"
    assert client.post(url, json={"nickname":"gianluigi"}).status_code == 409
    assert client.post(url, json={"nickname":"   "}).status_code == 422
    cmd(client, host, "start")
    assert client.post(url, json={"nickname":"Gab"}).status_code == 409


def test_scoring_once_and_manual_progression(client):
    host, one, two = setup(client)
    assert answer(client, one, SENTENCES[0]).status_code == 409
    cmd(client, host, "start")
    play = cmd(client, host, "play").json()
    assert answer(client, one, SENTENCES[0]).status_code == 409
    cmd(client, host, "audio_end", play_id=play["play_id"])
    assert answer(client, one, "...").status_code == 409
    good = answer(client, one, SENTENCES[0]).json()
    assert good["correct"] and good["state"]["me"]["score"] == 100
    assert answer(client, one, SENTENCES[0]).status_code == 409
    bad = answer(client, two, "wrong").json()
    assert not bad["correct"] and bad["state"]["level_index"] == 0
    assert answer(client, two, SENTENCES[0]).status_code == 409
    assert cmd(client, host, "reveal").status_code == 409
    cmd(client, host, "next_level")
    assert answer(client, two, SENTENCES[0], turn=0).status_code == 409
    open_answers(client, host, turn=1)
    assert answer(client, two, SENTENCES[0], turn=1).json()["state"]["me"]["score"] == 90
    assert answer(client, one, SENTENCES[0], turn=1).status_code == 409
    result = cmd(client, host, "reveal", turn=1).json()
    assert result["answer"] == SENTENCES[0]
    assert [r["score"] for r in result["leaderboard"]] == [100,90]


def test_five_sentences_and_maximum_score(client):
    host, one, two = setup(client)
    cmd(client, host, "start")
    for sentence in range(5):
        turn = sentence * 6
        open_answers(client, host, turn)
        assert answer(client, one, SENTENCES[sentence], turn).status_code == 200
        assert answer(client, two, SENTENCES[sentence], turn).status_code == 200
        assert cmd(client, host, "reveal", turn).status_code == 200
        last = cmd(client, host, "next_sentence", turn).json()
    assert last["phase"] == "finished"
    assert [r["score"] for r in last["leaderboard"]] == [500,500]
    assert [r["rank"] for r in last["leaderboard"]] == [1,1]


def test_all_levels_failed_and_original(client):
    host, one, two = setup(client)
    cmd(client, host, "start")
    for level in range(6):
        opened = open_answers(client, host, level).json()
        assert "answer" not in opened and "original_url" not in opened
        assert answer(client, one, "wrong", level).status_code == 200
        if level < 5:
            cmd(client, host, "next_level", level)
    assert cmd(client, host, "next_level", 5).status_code == 409
    revealed = cmd(client, host, "reveal", 5).json()
    assert revealed["original_url"].endswith("sentence_01_original.wav")
    assert [r["score"] for r in revealed["leaderboard"]] == [0,0]
    assert answer(client, two, SENTENCES[0], 5).status_code == 409
    assert cmd(client, host, "next_sentence", 5).json()["turn"] == 6


def test_replay_and_audio_failure_recovery(client):
    host, one, two = setup(client)
    cmd(client, host, "start")
    playing = cmd(client, host, "play").json()
    assert cmd(client, host, "audio_end", play_id="wrong").status_code == 409
    reset = cmd(client, host, "audio_error", play_id=playing["play_id"]).json()
    assert reset["phase"] == "ready" and reset["plays"] == 0
    open_answers(client, host)
    answer(client, one, "wrong")
    open_answers(client, host)
    assert answer(client, one, SENTENCES[0]).status_code == 409
    assert cmd(client, host, "play").status_code == 409


def test_state_and_websocket_reconnect_do_not_leak_solutions(client):
    host, one, two = setup(client)
    with client.websocket_connect(f"/ws/{host['code']}") as ws:
        ws.send_json({"token":one["token"]})
        first = ws.receive_json()
        assert first["me"]["nickname"] == "Gianluigi"
        assert "players" not in first and "answer" not in first
        assert "token" not in str(first) and "SENTENCES" not in str(first)
        cmd(client, host, "start")
        assert ws.receive_json()["phase"] == "ready"
    open_answers(client, host)
    answer(client, one, SENTENCES[0])
    with client.websocket_connect(f"/ws/{host['code']}") as ws:
        ws.send_json({"token":one["token"]})
        assert ws.receive_json()["me"]["score"] == 100


def test_csv_escaping_and_qr(client):
    host = client.post("/api/rooms").json()
    player = client.post(f"/api/rooms/{host['code']}/join", json={"nickname":"=1+1"}).json()
    path = f"/api/rooms/{host['code']}/scores.csv"
    assert client.get(path, headers=credentials(player)).status_code == 403
    assert "'=1+1" in client.get(path, headers=credentials(host)).text
    qr = client.get(f"/api/rooms/{host['code']}/qr")
    assert qr.status_code == 200 and "svg" in qr.headers["content-type"]
    assert "/multiplayer/rules.py" not in client.get("/healthz").text
    assert client.get("/multiplayer/rules.py").status_code == 404


def test_concurrent_duplicate_answer_cannot_double_award(client):
    host, one, two = setup(client)
    cmd(client, host, "start")
    open_answers(client, host)

    async def send_twice():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=server.app), base_url="http://test") as ac:
            return await asyncio.gather(*[ac.post(f"/api/rooms/{host['code']}/answer",
                headers=credentials(one), json={"text":SENTENCES[0],"turn":0}) for _ in range(2)])

    results = asyncio.run(send_twice())
    assert sorted(r.status_code for r in results) == [200,409]
    assert server.ROOMS[host["code"]].players[one["token"]].score == 100


@pytest.mark.parametrize("index,points", list(enumerate([100,90,80,70,60,50])))
def test_each_level_score(index, points):
    player = Player("A", "token")
    game = Round(phase="answering", level=index)
    game.answer(player, SENTENCES[0], game.turn)
    assert player.score == points

# Can You Hear It? — live classroom mode

This extension adds a shared listening game to the existing `game` branch.
Python owns rooms, rounds and scores. The host plays the existing WAV files;
participants use their phones to submit answers. The interface uses the solo
game's pastel palette and ear coin.

## 1. Add the files to your existing project

Use a branch based on the current `game` branch, for example
`feature/multiplayer`. If that branch already exists, switch to it rather than
creating it again. Commit your current work before switching branches.

Copy this package's files into the **repository root**, the folder that contains
`run_game.py`. Merge the `game` and `tests` folders with their existing folders.
**Do not replace or delete the existing folders.** These are additional files;
the solo game's `app.js`, `model.js`, `style.css` and `index.html` are unchanged.

| Path | Purpose |
| --- | --- |
| `run_multiplayer.py` | Local launcher |
| `multiplayer/server.py` | FastAPI routes, WebSockets, rooms, QR codes and CSV export |
| `multiplayer/rules.py` | Sentences, levels, scoring and round transitions |
| `game/web/live.html` | Multiplayer landing page |
| `game/web/host.html` | Host controls and shared leaderboard |
| `game/web/join.html` | Mobile participant screen |
| `game/web/multiplayer.js` | UI updates, playback and reconnection |
| `game/web/multiplayer.css` | Responsive pastel design |
| `game/web/live-coin.svg` | Copy of the existing ear coin |
| `requirements_multiplayer.txt` | Server dependencies |
| `render.yaml` | Optional Render Blueprint configuration |
| `tests/test_multiplayer.py` | Rules and API regression tests |

The package does not duplicate the audio. It uses the existing files in
`game/assets/processed/`: `sentence_01_ch_1.wav` through
`sentence_05_ch_32.wav`, plus the five `sentence_XX_original.wav` files.
There are **35 WAV files** in total. All must be committed to the deployed branch.
The server checks them before allowing a room to be created. Existing
metadata JSON files and the DSP pipeline are not needed to run a live session.

## 2. Start locally on macOS or Windows

Use the project's Python environment (Python 3.12 recommended). Open a terminal
in the repository root and run:

```bash
python -m pip install -r requirements_multiplayer.txt
python run_multiplayer.py
```

Open **http://127.0.0.1:8000** in a browser. Choose **Host a game**.
Create a room and open the join link in a second browser tab. For a second test
player, use another fresh tab, a private window, or a different browser. Do not
duplicate an already joined tab, as browsers can copy its session storage.

In PyCharm, select `run_multiplayer.py` as the script, not a file inside `game/`.
If port 8000 is occupied, use `python run_multiplayer.py --port 8001` and open
http://127.0.0.1:8001 instead.

The old solo launcher `python run_game.py` remains available. When using the
multiplayer server, the solo version is also at `/web/`.

### Testing with phones before deployment

```bash
python run_multiplayer.py --host 0.0.0.0
```

Connect the computer and phones to the same Wi-Fi. Open the host page using
the computer's LAN address, for example `http://192.168.1.20:8000/host`, replacing
the example IP with your actual IP. The QR then contains that address.
`127.0.0.1` on a phone refers to the phone itself, not your computer.
University Wi-Fi may block device-to-device connections. In that case, test
through the Render URL after deployment. There is no need to open router ports.

## 3. Run a classroom session

1. Create a room on the host computer and project its QR and six-digit code.
2. Players enter unique nicknames. New players can join only while the room is
   in the lobby. Existing players can reconnect during the game.
3. Click **Start game**, then **Play audio**. Audio comes only from the host's
   speakers. Answers open automatically when playback ends.
4. Each player gets one nonempty answer per level. Case, punctuation and extra
   whitespace are ignored. Word order and spelling must match the transcript.
5. A correct answer awards points once and locks that player for the sentence.
   A wrong answer waits for the host to choose **Next level**. The host can
   replay the same audio once; a replay does not give another answer attempt.
6. At Rookie, choose **Reveal sentence**. You may reveal earlier if everyone
   has solved it. Revealing closes answers and shows the original-audio button.
7. Click **Next sentence**. After sentence five, show the final leaderboard.
8. Download the CSV before closing the game or restarting the server.

| Level | Channels | Points |
| --- | ---: | ---: |
| Legend | 1 | 100 |
| Champion | 2 | 90 |
| Pro | 4 | 80 |
| Skilled | 8 | 70 |
| Beginner | 16 | 60 |
| Rookie | 32 | 50 |

An unsolved sentence earns zero. Maximum total is 500. Equal totals share the
same rank. The host advances manually, with a confirmation if some players
have not answered. No speed bonus or automatic timer is used.

Refreshing the same tab restores its session while the server is still
running. Keep that tab open: session credentials are stored in `sessionStorage`.
After a host refresh during playback, choose **Retry interrupted playback**
and play the audio again. This restores the listen consumed by the interruption.
Use one active host tab per room.

## 4. Deploy on Render

After copying and testing the files, commit them and push `feature/multiplayer`.
No deployment or GitHub push is performed by extracting this package.

In Render, create a **Web Service**, select the existing repository and use:

| Setting | Value |
| --- | --- |
| Branch | `feature/multiplayer`, or the branch where you committed these files |
| Runtime / Language | Python 3 |
| Root Directory | Leave empty: the repository root |
| Build Command | `pip install -r requirements_multiplayer.txt` |
| Start Command | `uvicorn multiplayer.server:app --host 0.0.0.0 --port $PORT --workers 1` |
| Instance Type | Free |
| Health Check Path | `/healthz` |
| Environment variable | `PYTHON_VERSION=3.12.10` |

The `$PORT` expression is for Render's Linux Start Command, not for a Windows
terminal. Use `run_multiplayer.py` locally.

`render.yaml` supplies the same configuration when creating a Render Blueprint.
For an ordinary Web Service created through the form, fill the settings above;
merely adding `render.yaml` does not update an already-created service.

Once Render reports the service as live, open its HTTPS URL. The landing page
offers Host / Join / Solo. The host QR is generated **for the current room**.
It automatically uses Render's public URL. For a custom domain, optionally set
`PUBLIC_BASE_URL` to the full HTTPS base URL, without a trailing path.

Use **one worker and one instance**: room state lives in that process. Running
multiple workers would send players to independent room stores.
Avoid pushes/redeployments during a live session. For the presentation, select
manual deployment if you do not want a teammate's push to restart the server.

## 5. Storage and practical limits

This first version uses temporary memory, with a six-hour maximum room lifetime,
up to 30 rooms and 100 players per room. These are application limits, not a
guarantee of performance with 3,000 simultaneous players. There is no permanent
online score history. Server restarts erase rooms and scores; a browser refresh
does not erase them. CSV export is the way to save the results from a session.

Render Free can suspend after 15 minutes without incoming traffic and may
restart instances. A cold start can take about a minute. Open the site before
the presentation and verify that a phone can join. The active game uses a
WebSocket connection with a heartbeat and retries interrupted connections.
Monthly free quotas still apply. A later version can use a persistent database
if scores and active games must survive server restarts.

Answers are checked on the server, and the host controls require a separate
secret session token. This is a classroom demonstration, not a secure exam:
the repository and solo game already contain the transcripts and audio.

## 6. Tests and troubleshooting

```bash
python -m pip install -r requirements_multiplayer_test.txt
python -m pytest tests/test_multiplayer.py -q
```

These tests cover scoring, duplicate submissions, all six levels, the five-
sentence game, permissions, isolated rooms, reconnection, QR generation and CSV.
They use temporary synthetic WAV files and do not modify your recordings.

- **Missing WAV files:** open `/api/readiness` to see exactly which files are
  missing. Restore the prepared files from your `game` branch.
- **ModuleNotFoundError:** install the requirements with the same Python
  interpreter you use to start `run_multiplayer.py`.
- **404 at `/host` or `/api/rooms`:** use the multiplayer server's URL.
  GitHub Pages and `run_game.py` serve the solo version only.
- **Room not found after a deploy:** create a new room. In-memory sessions do
  not survive deployments.
- **QR opens localhost on a phone:** use the LAN host address for local testing,
  or the HTTPS Render URL after deployment.
- **Audio finishes but answers remain closed:** reconnect the host and use
  Retry interrupted playback, then play again.

References for the deployment configuration:
- https://render.com/docs/deploy-fastapi
- https://render.com/docs/environment-variables
- https://render.com/docs/free
- https://fastapi.tiangolo.com/advanced/websockets/

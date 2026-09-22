# Validation record

Validated on 22 September 2026. This package extends the existing game; no
deployment to Render or push to GitHub was performed during validation.

## Rules and API tests

Command: `python -m pytest tests/test_multiplayer.py -q`

Result: **17 passed**, with two upstream deprecation warnings in the
Starlette/httpx test tooling. No failed tests.

Covered:

- All six channel-to-score mappings, five sentences, maximum 500 points, ties.
- One answer per level and no duplicate awards under concurrent requests.
- Host-only controls, player-only answers, tokens scoped to their own room.
- Rejection of early, stale, repeated, empty and late-joining requests.
- Playback completion, two-listen limit and interrupted playback recovery.
- Original audio revealed only after the host reveals the sentence.
- WebSocket reconnection retaining scores; snapshots omit unrevealed answers.
- Missing audio detection, QR generation and CSV formula escaping.

These tests create temporary synthetic WAV files; the project recordings are
not changed.

## Browser integration

Ran Uvicorn and Chromium with six independent browser contexts: **two hosts and
four players**, two players in each room. Desktop viewport: 1440 × 1000; player
viewport: 390 × 844, also checked at 320 pixels wide.

Both rooms completed all five sentences. The test used the project's real
precomputed WAV files through HTMLAudioElement. Playback was accelerated to 8×
for automation; production playback remains at the normal rate. This verifies
file loading and playback events, not subjective audio quality.

| Room | Player | Expected points | Actual points |
| --- | --- | ---: | ---: |
| A | Alice | 500 | 500 |
| A | Bob | 490 | 490 |
| B | Carol | 400 | 400 |
| B | Dave | 500 | 500 |

Verified that starting, advancing and revealing one room did not advance the
other. Tested a correct answer, a wrong answer, the second channel level, all
six failed levels, original-audio playback, a player reload, final standings
and the host's CSV download. The CSV contained only its own room's players.

No JavaScript page errors occurred. The mobile checks found no horizontal
overflow at 320 pixels. Visually inspected the landing page, host lobby and
final standings, and phone answer, reward and final standings screens. The
existing solo page also loaded at `/web/` through the new server.

## Scope and remaining deployment checks

This is a functional classroom-demo test, not a high-concurrency load test.
The configured maximum number of rooms/players is not a measured capacity.
Physical phones, Safari and a live Render deployment were not tested here.

After deployment, perform one short rehearsal on the actual host computer and
two phones: join via QR, play audio, submit different answers, advance, reveal
the original and download scores. Keep the same host tab open and avoid
deploying changes during the presentation. Rooms and scores are temporary and
are erased when the server restarts.

Runtime used for tests: Python 3.12.14, FastAPI 0.141.1, Uvicorn 0.53.0,
qrcode 8.2, pytest 9.1.1, httpx 0.28.1, Playwright 1.63.0 with Chromium 153.

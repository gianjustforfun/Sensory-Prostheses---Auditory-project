/* Live mode: the browser renders state; the server owns answers and scores. */
"use strict";
(() => {
  const $ = id => document.getElementById(id);
  const role = document.body.dataset.role;
  const key = `listening-live-${role}`;
  let session = null, state = null, socket = null, online = false, busy = false;
  let heartbeat = null, retry = null, ended = false, retryCount = 0;
  let inputTurn = null, rewardSentence = null, localPlay = null;
  const audio = $("audio");
  const escape = text => String(text).replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
  const error = message => { $("error").textContent = message || ""; };

  async function api(path, body, options = {}) {
    const response = await fetch(path, {
      method: body === undefined ? "GET" : "POST",
      headers: {"Content-Type":"application/json", ...(session ? {Authorization:`Bearer ${session.token}`} : {})},
      body: body === undefined ? undefined : JSON.stringify(body), cache:"no-store",
      signal:AbortSignal.timeout(15000), ...options
    });
    if (!response.ok) {
      let data = {};
      try { data = await response.json(); } catch (_) { /* An unavailable host may return HTML. */ }
      throw new Error(typeof data.detail === "string" ? data.detail : `Request failed (${response.status}). Please try again.`);
    }
    return response.json();
  }

  function remember(value) {
    session = value;
    try { sessionStorage.setItem(key, JSON.stringify(value)); }
    catch (_) { error("This browser cannot save the session. Keep this tab open during the game."); }
  }

  function stopSession(message) {
    ended = true; online = false;
    clearInterval(heartbeat); clearTimeout(retry);
    if (socket) socket.close();
    if (audio) audio.pause();
    try { sessionStorage.removeItem(key); } catch (_) {}
    error(message);
    $("reset").hidden = false;
    render();
  }

  function connect() {
    if (ended) return;
    clearInterval(heartbeat);
    const protocol = location.protocol === "https:" ? "wss:" : "ws:";
    socket = new WebSocket(`${protocol}//${location.host}/ws/${session.code}`);
    socket.onopen = () => {
      socket.send(JSON.stringify({token:session.token}));
      heartbeat = setInterval(() => {
        if (socket.readyState === WebSocket.OPEN) socket.send(JSON.stringify({type:"ping"}));
      }, 20000);
    };
    socket.onmessage = event => {
      const value = JSON.parse(event.data);
      if (value.type === "expired") return stopSession("This room expired. Ask the host for a new room.");
      if (value.type === "state") { online = true; retryCount = 0; apply(value); }
    };
    socket.onclose = event => {
      online = false; clearInterval(heartbeat); render();
      if (ended) return;
      if ([4001,4004].includes(event.code)) return stopSession("The session is no longer available. Please join a new room.");
      retry = setTimeout(connect, Math.min(1000 * 2 ** retryCount++, 10000));
    };
    socket.onerror = () => socket.close();
  }

  function apply(value) {
    if (state && value.version < state.version) return;
    state = value;
    $("setup").hidden = true;
    $("session").hidden = false;
    if (role === "host") {
      $("room-code").textContent = session.code;
      const joinUrl = `${location.origin}/join?room=${session.code}`;
      if (!$("qr").getAttribute("src")) $("qr").src = `/api/rooms/${session.code}/qr`;
      $("join-link").href = joinUrl;
      $("join-link").textContent = joinUrl;
    }
    render();
  }

  function button(id, visible, enabled = true) {
    const node = $(id);
    node.hidden = !visible;
    node.disabled = !enabled || !online || busy || ended;
  }

  function table(rows, name = "") {
    return `<div class="tablewrap"><table><thead><tr><th>Rank</th><th>Player</th><th>Points</th></tr></thead><tbody>${rows.map(r =>
      `<tr class="${r.nickname === name ? "me" : ""}"><td>${r.rank}</td><td>${escape(r.nickname)}</td><td>${r.score}</td></tr>`).join("")}</tbody></table></div>`;
  }

  function render() {
    if (!state) return;
    $("connection").textContent = ended ? "SESSION ENDED" : online ? "CONNECTED" : "RECONNECTING…";
    $("progress").textContent = state.phase === "lobby" ? `ROOM ${state.code}` : `SENTENCE ${state.sentence} / ${state.sentences}`;
    if (role === "host") renderHost(); else renderPlayer();
  }

  function renderHost() {
    const s = state, phase = s.phase;
    const active = ["ready","listening","answering"].includes(phase);
    $("stage-label").textContent = phase === "lobby" ? "YOUR CLASSROOM, CONNECTED" : phase.toUpperCase();
    $("stage-title").textContent = phase === "lobby" ? "Ready when you are." : phase === "finished" ? "The results are in!" : phase === "reveal" ? "Here’s what you heard." : `${s.level.name} · ${s.level.channels} ${s.level.channels === 1 ? "channel" : "channels"}`;
    const hints = {lobby:"Invite everyone to scan the QR. Start once all players have joined.", ready:"Play the audio. Answers open automatically when it finishes.", listening:"Listening together. Answers open after playback.", answering:"Give everyone time to answer, then move to the next level.", reveal:"Play the original if you like, then continue together.", finished:"Download the scores before closing this session. Equal scores share a rank."};
    $("stage-help").textContent = hints[phase];
    $("join-note").textContent = phase === "lobby" ? "Enter a nickname. No account needed." : phase === "finished" ? "This game has finished. Create a new room to play again." : "Game in progress. Existing players can reconnect in their original tab.";
    $("levels").hidden = !active;
    $("levels").innerHTML = s.levels.map((l,i) => `<div class="level ${i === s.level_index ? "current" : ""}" style="background:${l.color}"><strong>${l.name}</strong><span>${l.channels} ch · ${l.points}</span></div>`).join("");
    button("start", phase === "lobby", s.player_count > 0);
    button("play", active, ["ready","answering"].includes(phase) && s.plays < s.max_plays);
    $("play").textContent = s.plays ? "▶ Replay audio" : "▶ Play audio";
    button("next-level", phase === "answering" && s.level_index < 5);
    button("reveal", phase === "answering", s.level_index === 5 || (s.player_count > 0 && s.solved_count === s.player_count));
    button("original", phase === "reveal", !localPlay);
    button("next-sentence", phase === "reveal", !localPlay);
    $("next-sentence").textContent = s.sentence === s.sentences ? "Final leaderboard" : "Next sentence";
    button("recover", phase === "listening" && !localPlay);
    $("listen-count").textContent = active ? `${s.plays} / ${s.max_plays} listens · ${s.level.points} points available` : "";
    $("answered").textContent = active ? `${s.answered_count} / ${s.player_count} answered or solved · ${s.solved_count} solved this sentence` : `${s.player_count} players`;
    $("solution").hidden = !s.answer;
    $("solution").textContent = s.answer || "";
    $("roster-title").textContent = phase === "finished" ? "Final leaderboard" : phase === "reveal" ? "Standings" : `Players · ${s.player_count}`;
    $("roster").innerHTML = s.leaderboard ? table(s.leaderboard) : s.players.length ? `<div class="roster-grid">${s.players.map(p => `<div class="player-chip">${escape(p.nickname)} <small>· ${p.score} pts<br>${p.solved ? "Solved ✓" : p.answered ? "Answered" : "Waiting"}${p.connected ? "" : " · offline"}</small></div>`).join("")}</div>` : "<p>Your players will appear here.</p>";
    button("export", true, s.player_count > 0);
  }

  function renderPlayer() {
    const s = state, me = s.me, phase = s.phase;
    $("nickname-label").textContent = me.nickname;
    $("total").textContent = me.score;
    let title = "You’re in!", hint = "Wait for the host to start the game.";
    if (phase === "lobby") { title = "You’re in!"; hint = "Wait for the host to start the game."; }
    else if (phase === "finished") { title = "That’s a wrap!"; hint = `You earned ${me.score} out of 500 points.`; }
    else if (phase === "reveal") { title = "The sentence was…"; hint = "Here are the standings. The next sentence starts when the host is ready."; }
    else if (me.solved) { title = "You got it!"; hint = "Your points are saved for this sentence."; }
    else if (phase === "ready") { title = "Get ready to listen."; hint = "The audio will play through the host’s speakers."; }
    else if (phase === "listening") { title = "Listen closely."; hint = me.attempted ? "You already answered at this level. Wait for the next one." : "You can send your answer when the audio finishes."; }
    else if (me.attempted) { title = "Not quite. Keep listening."; hint = s.level_index === 5 ? "This was the final level. Wait for the host to reveal the sentence." : "Wait for the host to move to the next level."; }
    else { title = "What did you hear?"; hint = "Type the whole sentence. Capital letters and punctuation don’t matter."; }
    if (!s.host_connected && phase !== "finished") hint = "The host is reconnecting. Keep this tab open.";
    $("stage-title").textContent = title;
    $("stage-help").textContent = hint;
    $("level-summary").hidden = ["lobby","finished","reveal"].includes(phase);
    $("level-summary").textContent = `${s.level.name} · ${s.level.channels} ${s.level.channels === 1 ? "channel" : "channels"} · ${s.level.points} points`;
    $("level-summary").style.background = s.level.color;
    const canAnswer = phase === "answering" && !me.solved && !me.attempted;
    $("answer-form").hidden = !canAnswer;
    $("submit").disabled = !online || busy || ended;
    $("answer").disabled = !online || busy || ended;
    if (inputTurn !== s.turn) { $("answer").value = ""; inputTurn = s.turn; error(""); }
    $("solution").hidden = !s.answer;
    $("solution").textContent = s.answer || "";
    $("leaderboard").innerHTML = s.leaderboard ? table(s.leaderboard, me.nickname) : "";
    const celebrating = me.solved && !["reveal","finished"].includes(phase);
    $("celebration").hidden = !celebrating;
    if (celebrating) {
      $("earned").textContent = `+${me.points}`;
      if (rewardSentence !== s.sentence) {
        rewardSentence = s.sentence;
        document.querySelector(".confetti").innerHTML = Array.from({length:32}, (_,i) => `<i style="--x:${Math.random()*100}%;--delay:${Math.random()*.6}s;--turn:${Math.random()*500}deg;background:${s.levels[i%6].color}"></i>`).join("");
      }
    }
  }

  async function command(action, extra = {}) {
    const result = await api(`/api/rooms/${session.code}/control`, {action, turn:state.turn, ...extra});
    apply(result);
    return result;
  }

  async function guarded(work) {
    if (busy) return;
    busy = true; error(""); render();
    try { await work(); }
    catch (e) { error(e.message || "Connection failed. Please try again."); }
    finally { busy = false; render(); }
  }

  if (role === "host") {
    $("create").onclick = () => guarded(async () => {
      $("create").disabled = true;
      try { remember(await api("/api/rooms", {})); connect(); }
      finally { $("create").disabled = false; }
    });
    $("new-room").onclick = () => {
      if (confirm("Create a new room? Download the current scores first if you need them.")) {
        sessionStorage.removeItem(key); location.href = "/host";
      }
    };
    $("copy-link").onclick = async () => {
      try { await navigator.clipboard.writeText($("join-link").href); $("copy-link").textContent = "Copied!"; }
      catch (_) { error("Copy the join link shown above manually."); }
    };
    for (const [id,action] of [["start","start"],["reveal","reveal"],["next-sentence","next_sentence"]]) {
      $(id).onclick = () => guarded(() => command(action));
    }
    $("next-level").onclick = () => {
      if (state.answered_count < state.player_count && !confirm("Some players have not answered. Move to the next level anyway?")) return;
      guarded(() => command("next_level"));
    };
    $("recover").onclick = () => guarded(() => command("audio_error", {play_id:state.play_id}));
    $("play").onclick = () => guarded(async () => {
      const value = await command("play");
      localPlay = {turn:value.turn, play_id:value.play_id};
      audio.src = value.audio_url;
      try { await audio.play(); }
      catch (e) { localPlay = null; await command("audio_error", {play_id:value.play_id}); throw new Error("Audio could not start. Check your sound settings and press Play again."); }
    });
    $("original").onclick = () => guarded(async () => {
      localPlay = {original:true}; audio.src = state.original_url;
      try { await audio.play(); } catch (e) { localPlay = null; throw new Error("The original audio could not play. Try again."); }
    });
    audio.onended = async () => {
      const play = localPlay; localPlay = null;
      // Playback completion must be sent even if a CSV download is in progress.
      if (play && !play.original) {
        try { await command("audio_end", {play_id:play.play_id}); }
        catch (_) { error("Could not open answers. Reconnect, then use Retry interrupted playback."); }
      }
      render();
    };
    audio.onerror = async () => {
      const play = localPlay; localPlay = null;
      if (play && !play.original && state.phase === "listening") {
        try { await command("audio_error", {play_id:play.play_id}); } catch (_) { /* Recovery button remains available. */ }
      }
      error("Audio is unavailable. Check that the processed WAV files are in game/assets/processed."); render();
    };
    $("export").onclick = () => guarded(async () => {
      const response = await fetch(`/api/rooms/${session.code}/scores.csv`, {headers:{Authorization:`Bearer ${session.token}`}});
      if (!response.ok) throw new Error("Could not download the scores. Please try again.");
      const url = URL.createObjectURL(await response.blob());
      const link = document.createElement("a"); link.href = url; link.download = `scores-${session.code}.csv`;
      link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
    });
  } else {
    $("code").value = new URLSearchParams(location.search).get("room") || "";
    $("join-form").onsubmit = event => {
      event.preventDefault();
      guarded(async () => {
        $("join-button").disabled = true;
        try { remember(await api(`/api/rooms/${$("code").value.trim()}/join`, {nickname:$("nickname").value.trim()})); connect(); }
        finally { $("join-button").disabled = false; }
      });
    };
    $("answer-form").onsubmit = event => {
      event.preventDefault();
      guarded(async () => {
        const result = await api(`/api/rooms/${session.code}/answer`, {text:$("answer").value, turn:state.turn});
        apply(result.state);
      });
    };
  }

  async function boot() {
    try { session = JSON.parse(sessionStorage.getItem(key) || "null"); } catch (_) {}
    const requested = new URLSearchParams(location.search).get("room");
    if (session && requested && session.code !== requested) session = null;
    if (session) {
      try { apply(await api(`/api/rooms/${session.code}/state`)); connect(); return; }
      catch (e) { session = null; sessionStorage.removeItem(key); error(e.message); }
    }
    if (role === "host") {
      try {
        const value = await api("/api/readiness");
        $("readiness").textContent = value.ready ? "All 35 audio files are ready." : `Missing or invalid audio: ${value.missing.join(", ")}`;
        $("create").disabled = !value.ready;
      } catch (_) { error("Could not reach the multiplayer server. Start it with python run_multiplayer.py."); }
    }
  }
  boot();
})();

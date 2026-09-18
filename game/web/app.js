const app=document.getElementById('app');
let audio=document.getElementById('audio');
// Keep earlier demo scores separate from processed-audio rounds.
const SCORE_KEY='listening-game-cis-320k-v1';
let playback=null, assetCheck=null;
let game=null, answer='', notice='', busy=false, page='home';
let storageWarning='';
const esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function stopAudio(){
 playback=null;
 audio.onplaying=null;audio.onended=null;audio.onerror=null;
 audio.pause();
 try{audio.currentTime=0;}catch(e){}
 audio.removeAttribute('src');audio.load();busy=false;
}
function cancelAssetCheck(){
 if(assetCheck){assetCheck.abort();assetCheck=null;}
}
function levels(active=-1){return `<div class="levels">${LEVELS.map((l,i)=>`<div class="level ${i===active?'active':i>active&&active>=0?'future':''}" style="background:${l.color}"><strong>${l.name}</strong><small>${l.channels} ${l.channels===1?'channel':'channels'} · ${l.points} pts</small></div>`).join('')}</div>`;}
function wave(){return `<div class="wave" aria-hidden="true">${[22,38,60,82,54,98,72,44,64,36,20].map(n=>`<i style="height:${n}px"></i>`).join('')}</div>`;}
function showHome(){
 cancelAssetCheck();stopAudio();page='home';
 app.innerHTML=`<section class="hero"><span class="eyebrow">LESS SIGNAL. MORE CHALLENGE.</span>${wave()}<h1>Can you<br>hear it?</h1><p>Five sentences. Six levels.<br>How few channels do you need?</p><div class="actions"><button class="big" id="start">▶ &nbsp; Play</button><button class="secondary" id="board">Leaderboard</button></div><div class="home-credits"><p class="team-names"><span>Gianluigi D'Antonio</span><span>Gabriele Colò</span><span>Yelizaveta Semikina</span></p></div>${levels()}<p id="audio-status" role="status" aria-live="polite"></p><p class="note">Listen with 1, 2, 4, 8, 16 or 32 channels.<br><a href="audio_check.html">Compare the audio levels</a></p></section>`;
 document.getElementById('start').onclick=startRound;
 document.getElementById('board').onclick=()=>showBoard();
}
function showUsername(){
 cancelAssetCheck();stopAudio();page='username';
 app.innerHTML=`<section class="card narrow"><span class="eyebrow">MAKE YOURSELF HEARD</span><h2>What's your name?</h2><p>Listen and type what you hear. Each incorrect answer unlocks more channels, but fewer points.</p><form id="username-form"><label for="username">Enter your username</label><input id="username" maxlength="24" autocomplete="off" placeholder="Your name" required><p class="hint">Two listens and one answer per level. Five sentences in total.</p><button class="full">Start game →</button></form><button class="link" id="back">Back</button><p class="note">Scores stay in this browser. Earlier demo scores are kept separately.</p></section>`;
 const input=document.getElementById('username');input.focus();
 document.getElementById('username-form').onsubmit=e=>{e.preventDefault();if(!input.value.trim()){input.setCustomValidity('Enter a username.');input.reportValidity();return;}game=new Game(input.value.trim());answer='';notice='';showGame();};
 input.oninput=()=>input.setCustomValidity('');document.getElementById('back').onclick=showHome;
}
/* Sentence indices are zero-based in the game, one-based in WAV filenames. */
function originalAudioPath(sentence){
 return `../assets/processed/sentence_${String(sentence+1).padStart(2,'0')}_original.wav`;
}
function audioPath(sentence,channels){
 return `../assets/processed/sentence_${String(sentence+1).padStart(2,'0')}_ch_${channels}.wav`;
}
async function startRound(){
 if(assetCheck)return;
 const controller=new AbortController();assetCheck=controller;
 const button=document.getElementById('start');
 const status=document.getElementById('audio-status');
 button.disabled=true;button.textContent='Checking audio';
 status.textContent='Getting your round ready.';
 const paths=SENTENCES.flatMap((_,sentence)=>[
  ...LEVELS.map(level=>audioPath(sentence,level.channels)),originalAudioPath(sentence)
 ]);
 const timeout=setTimeout(()=>controller.abort(),10000);
 let missing;
 try{
  missing=(await Promise.all(paths.map(async path=>{
   try{
    const response=await fetch(path,{method:'HEAD',cache:'no-store',signal:controller.signal});
    const type=response.headers.get('content-type')||'';
    const length=response.headers.get('content-length');
    return response.ok&&type.startsWith('audio/')&&(length===null||Number(length)>44)?null:path;
   }catch(e){return path;}
  }))).filter(Boolean);
 }finally{clearTimeout(timeout);}
 // Ignore completion after the player navigates away or starts another check.
 if(assetCheck!==controller)return;
 assetCheck=null;
 if(missing.length){
  button.disabled=false;button.textContent='Retry audio check';
  status.textContent='Some recordings are missing or unavailable. Ask the host to prepare the audio, then try again.';
  console.warn('Audio check failed:',missing);
  return;
 }
 showUsername();
}
function showGame(focus=false){
 page='game';const l=LEVELS[game.level];
 app.innerHTML=`<div class="topline"><div><span class="eyebrow">${esc(game.username)}</span><h2>Sentence ${game.sentence+1} <span style="color:#858596">of 5</span></h2></div><div class="score">Total <strong>${game.score}</strong> / 500</div></div><div class="progress"><span style="width:${game.sentence/5*100}%"></span></div><section class="card"><div class="topline"><div><span class="eyebrow">CURRENT LEVEL</span><h2>${l.name}</h2></div><span class="badge" style="background:${l.color}">${l.channels} ${l.channels===1?'channel':'channels'} · ${l.points} points</span></div>${levels(game.level)}<div class="challenge"><div class="listen"><button id="play" class="play" aria-label="Play sentence" ${game.resolved||game.plays>=2||busy?'disabled':''}>${busy?'♫':'▶'}</button><p>${game.plays} / 2 listens used</p></div><form id="answer-form"><label for="answer">What did you hear?</label><input id="answer" placeholder="Type the sentence here…" autocomplete="off" spellcheck="false" value="${esc(answer)}" ${game.resolved?'disabled':''}><div class="actions" style="justify-content:flex-start;margin-top:15px"><button ${game.resolved||busy?'disabled':''}>Submit answer</button><button type="button" class="secondary" id="more" ${game.resolved||busy?'disabled':''}>${game.level===5?'Skip sentence':'More channels'}</button></div></form></div><div class="feedback ${game.resolved&&game.results.at(-1).points?'success':''}" role="status" aria-live="polite">${notice}</div>${game.resolved && !game.results.at(-1).points?'<button id="original" class="secondary" '+(busy?'disabled':'')+'>'+(busy?'♫ Playing original':'▶ Listen to original')+'</button><p class="hint">For comparison only · no extra points</p>':''}${game.resolved?'<button id="next" class="full">'+(game.sentence===4?'See my results →':'Next sentence →')+'</button>':''}</section><p class="note">More channels reveal more spectral detail.<br>Capitalization, punctuation and extra spaces do not affect your answer.</p>`;
 document.getElementById('answer').oninput=e=>answer=e.target.value;
 document.getElementById('play').onclick=play;
 document.getElementById('more').onclick=()=>{if(!busy)handleOutcome(game.advance(),true);};
 document.getElementById('answer-form').onsubmit=e=>{e.preventDefault();if(!busy)handleOutcome(game.submit(answer));};
 if(game.resolved)document.getElementById('next').onclick=nextSentence;
 if(document.getElementById('original'))document.getElementById('original').onclick=playOriginal;
 if(focus&&!game.resolved)document.getElementById('answer').focus();
}
async function play(){
 if(page!=='game'||busy||!game||game.resolved||game.plays>=2)return;
 await startPlayback('level');
}
async function startPlayback(kind){
 stopAudio();
 const request={kind,round:game,sentence:game.sentence,level:game.level,counted:false};
 const player=new Audio();
 audio=player;playback=request;busy=true;
 player.src=kind==='original'?originalAudioPath(game.sentence):audioPath(game.sentence,LEVELS[game.level].channels);
 const isCurrent=()=>playback===request&&game===request.round&&page==='game';
 player.onplaying=()=>{
  if(!isCurrent())return;
  if(kind==='level'&&!request.counted){game.plays++;request.counted=true;}
  showGame();
 };
 player.onended=()=>{
  if(!isCurrent())return;
  playback=null;busy=false;showGame(kind==='level');
 };
 const failed=()=>{
  if(!isCurrent())return;
  if(kind==='level'&&request.counted)game.plays=Math.max(0,game.plays-1);
  stopAudio();
  notice=kind==='original'?'The original could not be played. Try again or ask the host to check the recording.':'This recording could not be played. Your listen was not used. Try again or ask the host to check the recording.';
  showGame();
 };
 player.onerror=failed;
 showGame();
 try{await player.play();}catch(e){failed();}
}
function handleOutcome(outcome,skipped=false){
 if(outcome==='locked')return;
 if(outcome==='empty')notice='Type your answer first. This does not use a turn.';
 if(outcome==='listen')notice='Listen to the sentence before submitting your answer.';
 if(outcome==='advance')notice=skipped?'Try the next level. Your answer has been kept.':'Not quite. Try the next level and update your answer.';
 if(outcome==='correct')notice=`Correct! +${game.results.at(-1).points} points.`;
 if(outcome==='exhausted')notice=`No points this time. The sentence was: “${esc(SENTENCES[game.sentence])}”`;
 stopAudio();if(outcome==='correct'){showCelebration();return;}showGame(outcome==='advance'||outcome==='empty');
}
function readScores(){
 try{const data=JSON.parse(localStorage.getItem(SCORE_KEY)||'[]');return Array.isArray(data)?data.filter(r=>r&&typeof r.username==='string'&&Number.isFinite(r.score)&&typeof r.id==='string'):[];}catch(e){storageWarning='Saved scores could not be read in this browser.';return [];}
}
function saveScore(){
 if(game.recordId)return;
 const record={id:crypto.randomUUID(),username:game.username,score:game.score,date:new Date().toISOString(),results:game.results,audioVersion:'cis-320k-v1'};game.recordId=record.id;
 try{localStorage.setItem(SCORE_KEY,JSON.stringify([...readScores(),record]));}catch(e){storageWarning='Your result is shown, but could not be saved. Browser storage may be unavailable or full.';}
}
function boardTable(){
 const scores=readScores().sort((a,b)=>b.score-a.score);let rank=0,last=null;
 if(!scores.length)return '<p class="empty">The first spot is yours. Finish a game to join the board.</p>';
 return `<div class="tablewrap"><table><thead><tr><th>Rank</th><th>Player</th><th>Score</th><th>Date</th></tr></thead><tbody>${scores.map((r,i)=>{if(r.score!==last)rank=i+1;last=r.score;return `<tr class="${r.id===game?.recordId?'me':''}"><td>${rank}</td><td>${esc(r.username)}</td><td><strong>${r.score}</strong> / 500</td><td>${esc(new Date(r.date).toLocaleDateString())}</td></tr>`;}).join('')}</tbody></table></div>`;
}
function showResults(){
 page='results';
 app.innerHTML=`<section class="card"><div class="result-head"><span class="eyebrow">FIVE SENTENCES, ONE FINISH LINE</span><h2>Nicely played, ${esc(game.username)}.</h2><div class="result-score">${game.score}<small> / 500</small></div><span class="badge">Round complete</span></div><div class="tablewrap"><table><thead><tr><th>Sentence</th><th>Level reached</th><th>Channels</th><th>Points</th></tr></thead><tbody>${game.results.map(r=>`<tr><td>${r.sentence}</td><td>${r.level}</td><td>${r.channels}</td><td>+${r.points}</td></tr>`).join('')}</tbody></table></div><h3>Leaderboard</h3>${boardTable()}<p class="hint">${esc(storageWarning||'Saved in this browser. Each completed game is a separate entry. Equal scores share a rank.')}</p><div class="actions"><button id="again">Play again</button><button id="home" class="secondary">Home</button></div></section><p class="note">Replaying familiar sentences can improve your score through memory.</p>`;
 document.getElementById('again').onclick=showUsername;document.getElementById('home').onclick=showHome;
}
function showBoard(){cancelAssetCheck();stopAudio();page='board';app.innerHTML=`<section class="card"><span class="eyebrow">THE LOCAL LINEUP</span><h2>Leaderboard</h2><p>Every completed round, saved in this browser.</p>${boardTable()}<p role="status">${esc(storageWarning)}</p><button id="home">Back home</button></section>`;document.getElementById('home').onclick=showHome;}
document.getElementById('brand').onclick=e=>{e.preventDefault();if(!['game','celebration'].includes(page)||confirm('Leave this round? Unfinished progress will not be saved.'))showHome();};
showHome();

function nextSentence(){
 if(!game||!game.resolved||!['game','celebration'].includes(page))return;
 stopAudio();
 if(game.next()){answer='';notice='';showGame();}
 else{saveScore();showResults();}
}
function showCelebration(){
 page='celebration';
 const points=game.results.at(-1).points;
 const confetti=Array.from({length:55},(_,i)=>`<i style="--x:${(i*37)%100}%;--delay:${(i%11)*0.11}s;--turn:${i%2?420:-390}deg;background:${LEVELS[i%6].color}"></i>`).join('');
 app.innerHTML=`<section class="celebration card"><div class="confetti" aria-hidden="true">${confetti}</div><span class="eyebrow">YOU GOT IT!</span><h1>That's the one.</h1><p>Sentence ${game.sentence+1} complete · ${LEVELS[game.level].name}</p><div class="reward" role="status" aria-live="polite"><img src="coin.svg" alt="" width="110" height="110"><strong>+${points}</strong></div><p class="reward-caption">points earned</p><span class="badge">Total score: ${game.score} / 500</span><div class="actions" style="margin-top:32px"><button id="next" class="big">${game.sentence===4?'See my results':'Next sentence'} →</button></div><p class="note">Fewer channels, more points.</p></section>`;
 document.getElementById('next').onclick=nextSentence;
 document.getElementById('next').focus();
}
async function playOriginal(){
 if(page!=='game'||busy||!game||!game.resolved||game.results.at(-1).points)return;
 await startPlayback('original');
}

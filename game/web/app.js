const app=document.getElementById('app');
const audio=document.getElementById('audio');
const SCORE_KEY='listening-game-demo-v1';
let game=null, answer='', notice='', busy=false, page='home';
let storageWarning='';
const esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function stopAudio(){audio.pause();audio.currentTime=0;busy=false;}
function levels(active=-1){return `<div class="levels">${LEVELS.map((l,i)=>`<div class="level ${i===active?'active':i>active&&active>=0?'future':''}" style="background:${l.color}"><strong>${l.name}</strong><small>${l.channels} ${l.channels===1?'channel':'channels'} · ${l.points} pts</small></div>`).join('')}</div>`;}
function wave(){return `<div class="wave" aria-hidden="true">${[22,38,60,82,54,98,72,44,64,36,20].map(n=>`<i style="height:${n}px"></i>`).join('')}</div>`;}
function showHome(){
 stopAudio();page='home';
 app.innerHTML=`<section class="hero"><span class="eyebrow">LESS SIGNAL. MORE CHALLENGE.</span>${wave()}<h1>Can you<br>hear it?</h1><p>Five sentences. Six levels.<br>How few channels do you need?</p><div class="actions"><button class="big" id="start">▶ &nbsp; Play</button><button class="secondary" id="board">Leaderboard</button></div><div class="home-credits"><p class="team-names"><span>Gianluigi D'Antonio</span><span>Gabriele Colò</span><span>Yelizaveta Semikina</span></p></div>${levels()}<p class="note">Demo mode uses the original recordings at every level.<br>Channel-processed audio is coming next.</p></section>`;
 document.getElementById('start').onclick=showUsername;
 document.getElementById('board').onclick=()=>showBoard();
}
function showUsername(){
 page='username';
 app.innerHTML=`<section class="card narrow"><span class="eyebrow">MAKE YOURSELF HEARD</span><h2>What's your name?</h2><p>Listen and type what you hear. Each incorrect answer unlocks more channels, but fewer points.</p><form id="username-form"><label for="username">Enter your username</label><input id="username" maxlength="24" autocomplete="off" placeholder="Your name" required><p class="hint">Two listens and one answer per level. Five sentences in total.</p><button class="full">Start game →</button></form><button class="link" id="back">Back</button><p class="note">Demo scores stay in this browser and are separate from future real-game scores.</p></section>`;
 const input=document.getElementById('username');input.focus();
 document.getElementById('username-form').onsubmit=e=>{e.preventDefault();if(!input.value.trim()){input.setCustomValidity('Enter a username.');input.reportValidity();return;}game=new Game(input.value.trim());answer='';notice='';showGame();};
 input.oninput=()=>input.setCustomValidity('');document.getElementById('back').onclick=showHome;
}
/* Integration point: replace the original path with the appropriate processed
   WAV for sentence + channels when the CIS reconstruction pipeline is ready.
   Keep demo mode and its score key until all 30 processed files are available. */
function originalAudioPath(sentence){return `../assets/audio/sentence_${String(sentence+1).padStart(2,'0')}.mp3`;}
function audioPath(sentence,channels){return originalAudioPath(sentence);}
function showGame(focus=false){
 page='game';const l=LEVELS[game.level];
 app.innerHTML=`<div class="topline"><div><span class="eyebrow">${esc(game.username)}</span><h2>Sentence ${game.sentence+1} <span style="color:#858596">of 5</span></h2></div><div class="score">Total <strong>${game.score}</strong> / 500</div></div><div class="progress"><span style="width:${game.sentence/5*100}%"></span></div><section class="card"><div class="topline"><div><span class="eyebrow">CURRENT LEVEL</span><h2>${l.name}</h2></div><span class="badge" style="background:${l.color}">${l.channels} ${l.channels===1?'channel':'channels'} · ${l.points} points</span></div>${levels(game.level)}<div class="challenge"><div class="listen"><button id="play" class="play" aria-label="Play sentence" ${game.resolved||game.plays>=2||busy?'disabled':''}>${busy?'♫':'▶'}</button><p>${game.plays} / 2 listens used</p></div><form id="answer-form"><label for="answer">What did you hear?</label><input id="answer" placeholder="Type the sentence here…" autocomplete="off" spellcheck="false" value="${esc(answer)}" ${game.resolved?'disabled':''}><div class="actions" style="justify-content:flex-start;margin-top:15px"><button ${game.resolved||busy?'disabled':''}>Submit answer</button><button type="button" class="secondary" id="more" ${game.resolved||busy?'disabled':''}>${game.level===5?'Skip sentence':'More channels'}</button></div></form></div><div class="feedback ${game.resolved&&game.results.at(-1).points?'success':''}" role="status" aria-live="polite">${notice}</div>${game.resolved && !game.results.at(-1).points?'<button id="original" class="secondary">▶ Listen to original</button><p class="hint">For comparison only · no extra points</p>':''}${game.resolved?'<button id="next" class="full">'+(game.sentence===4?'See my results →':'Next sentence →')+'</button>':''}</section><p class="note">Demo · You hear the same original recording at every level.<br>Capitalization, punctuation and extra spaces do not affect your answer.</p>`;
 document.getElementById('answer').oninput=e=>answer=e.target.value;
 document.getElementById('play').onclick=play;
 document.getElementById('more').onclick=()=>handleOutcome(game.advance(),true);
 document.getElementById('answer-form').onsubmit=e=>{e.preventDefault();if(!busy)handleOutcome(game.submit(answer));};
 if(game.resolved)document.getElementById('next').onclick=nextSentence;
 if(document.getElementById('original'))document.getElementById('original').onclick=playOriginal;
 if(focus&&!game.resolved)document.getElementById('answer').focus();
}
async function play(){
 if(busy||game.resolved||game.plays>=2)return;
 busy=true;audio.src=audioPath(game.sentence,LEVELS[game.level].channels);
 game.plays++;showGame();
 try{await audio.play();}catch(e){if(busy)game.plays=Math.max(0,game.plays-1);busy=false;notice='Audio could not be played. Check that the MP3 files are in game/assets/audio, then try again.';showGame();}
}
audio.onended=()=>{busy=false;if(page==='game')showGame(true);};
audio.onerror=()=>{if(!busy&&page==='game'&&game.resolved){const b=document.getElementById('original');if(b){b.disabled=false;b.textContent='▶ Retry original';document.querySelector('.feedback').textContent='Original audio could not be loaded. Please check the file.';}}if(busy){busy=false;game.plays=Math.max(0,game.plays-1);notice='Audio could not be loaded. Check the audio folder and try again.';if(page==='game')showGame();}};
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
 const record={id:crypto.randomUUID(),username:game.username,score:game.score,date:new Date().toISOString(),results:game.results};game.recordId=record.id;
 try{localStorage.setItem(SCORE_KEY,JSON.stringify([...readScores(),record]));}catch(e){storageWarning='Your result is shown, but could not be saved. Browser storage may be unavailable or full.';}
}
function boardTable(){
 const scores=readScores().sort((a,b)=>b.score-a.score);let rank=0,last=null;
 if(!scores.length)return '<p class="empty">The first spot is yours. Finish a game to join the board.</p>';
 return `<div class="tablewrap"><table><thead><tr><th>Rank</th><th>Player</th><th>Score</th><th>Date</th></tr></thead><tbody>${scores.map((r,i)=>{if(r.score!==last)rank=i+1;last=r.score;return `<tr class="${r.id===game?.recordId?'me':''}"><td>${rank}</td><td>${esc(r.username)}</td><td><strong>${r.score}</strong> / 500</td><td>${esc(new Date(r.date).toLocaleDateString())}</td></tr>`;}).join('')}</tbody></table></div>`;
}
function showResults(){
 page='results';
 app.innerHTML=`<section class="card"><div class="result-head"><span class="eyebrow">FIVE SENTENCES, ONE FINISH LINE</span><h2>Nicely played, ${esc(game.username)}.</h2><div class="result-score">${game.score}<small> / 500</small></div><span class="badge">Demo result</span></div><div class="tablewrap"><table><thead><tr><th>Sentence</th><th>Level reached</th><th>Channels</th><th>Points</th></tr></thead><tbody>${game.results.map(r=>`<tr><td>${r.sentence}</td><td>${r.level}</td><td>${r.channels}</td><td>+${r.points}</td></tr>`).join('')}</tbody></table></div><h3>Demo leaderboard</h3>${boardTable()}<p class="hint">${esc(storageWarning||'Saved in this browser. Each completed game is a separate entry. Equal scores share a rank.')}</p><div class="actions"><button id="again">Play again</button><button id="home" class="secondary">Home</button></div></section><p class="note">Replaying familiar sentences can improve your score through memory.</p>`;
 document.getElementById('again').onclick=showUsername;document.getElementById('home').onclick=showHome;
}
function showBoard(){page='board';app.innerHTML=`<section class="card"><span class="eyebrow">THE LOCAL LINEUP</span><h2>Demo leaderboard</h2><p>Every completed round, saved in this browser.</p>${boardTable()}<p role="status">${esc(storageWarning)}</p><button id="home">Back home</button></section>`;document.getElementById('home').onclick=showHome;}
document.getElementById('brand').onclick=e=>{e.preventDefault();if(!['game','celebration'].includes(page)||confirm('Leave this round? Unfinished progress will not be saved.'))showHome();};
showHome();

function nextSentence(){
 stopAudio();
 if(game.next()){answer='';notice='';showGame();}
 else{saveScore();showResults();}
}
function showCelebration(){
 page='celebration';
 const points=game.results.at(-1).points;
 const confetti=Array.from({length:55},(_,i)=>`<i style="--x:${(i*37)%100}%;--delay:${(i%11)*0.11}s;--turn:${i%2?420:-390}deg;background:${LEVELS[i%6].color}"></i>`).join('');
 app.innerHTML=`<section class="celebration card"><div class="confetti" aria-hidden="true">${confetti}</div><span class="eyebrow">YOU GOT IT!</span><h1>That's the one.</h1><p>Sentence ${game.sentence+1} complete · ${LEVELS[game.level].name}</p><div class="reward" role="status" aria-live="polite"><img src="coin.svg" alt="" width="110" height="110"><strong>+${points}</strong></div><p class="reward-caption">points earned</p><span class="badge">Total score: ${game.score} / 500</span><div class="actions" style="margin-top:32px"><button id="next" class="big">${game.sentence===4?'See my results':'Next sentence'} →</button></div><p class="note">Demo result · original audio</p></section>`;
 document.getElementById('next').onclick=nextSentence;
 document.getElementById('next').focus();
}
async function playOriginal(){
 if(!game.resolved || game.results.at(-1).points)return;
 const button=document.getElementById('original');
 if(!button||button.disabled)return;
 stopAudio();button.disabled=true;button.textContent='♫ Playing original';
 audio.src=originalAudioPath(game.sentence);
 try{await audio.play();}catch(e){
  if(page==='game'&&document.getElementById('original')===button){button.disabled=false;button.textContent='▶ Retry original';document.querySelector('.feedback').textContent='Original audio could not be played. Check the audio file and try again.';}
 }
}

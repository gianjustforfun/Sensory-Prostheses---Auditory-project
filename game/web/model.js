/* Rules are kept separate from the interface and audio playback. */
const LEVELS = [
  {name:'Legend',channels:1,points:100,color:'#ddd4f4'},
  {name:'Champion',channels:2,points:90,color:'#cddff6'},
  {name:'Pro',channels:4,points:80,color:'#cce7dd'},
  {name:'Skilled',channels:8,points:70,color:'#f4e7b9'},
  {name:'Beginner',channels:16,points:60,color:'#f4d5c3'},
  {name:'Rookie',channels:32,points:50,color:'#edcddd'}
];
const SENTENCES = [
  'The small dog is sleeping on the bed.',
  'Please put the red book on the table.',
  'My sister drinks coffee every morning.',
  'We can walk to the park together.',
  'There is a blue car outside the house.'
];
function normalize(text) {
  return text.toLowerCase().replace(/[^a-z0-9\s]/g,'').trim().replace(/\s+/g,' ');
}
class Game {
  constructor(username) {
    this.username=username; this.sentence=0; this.level=0;
    this.plays=0; this.results=[]; this.resolved=false;
  }
  get score(){return this.results.reduce((sum,r)=>sum+r.points,0);}
  finish(correct){
    this.results.push({sentence:this.sentence+1,level:LEVELS[this.level].name,
      channels:LEVELS[this.level].channels,points:correct?LEVELS[this.level].points:0});
    this.resolved=true;
    return correct?'correct':'exhausted';
  }
  advance(){
    if(this.resolved) return 'locked';
    if(this.level===LEVELS.length-1) return this.finish(false);
    this.level++; this.plays=0; return 'advance';
  }
  submit(answer){
    if(this.resolved) return 'locked';
    if(!normalize(answer)) return 'empty';
    if(!this.plays) return 'listen';
    return normalize(answer)===normalize(SENTENCES[this.sentence])?this.finish(true):this.advance();
  }
  next(){
    if(!this.resolved) return false;
    this.sentence++; this.level=0; this.plays=0; this.resolved=false;
    return this.sentence<SENTENCES.length;
  }
}
if(typeof module!=='undefined') module.exports={Game,normalize,LEVELS,SENTENCES};

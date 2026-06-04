// ─── Microphone recording ──────────────────────────────────────
var recCtx=null,recStream=null,recAudioChunks=[],recTimer=null
function toggleRecord(){
  var btn=id('record-btn')
  if(recCtx){stopRecording();return}
  if(!navigator.mediaDevices){toast('Microphone not available','err');return}
  navigator.mediaDevices.getUserMedia({audio:{echoCancellation:false,noiseSuppression:false,autoGainControl:false}}).then(function(s){
    recStream=s;recAudioChunks=[]
    recCtx=new AudioContext({sampleRate:44100})
    var src=recCtx.createMediaStreamSource(s)
    var node=recCtx.createScriptProcessor(4096,1,1)
    node.onaudioprocess=function(e){recAudioChunks.push(new Float32Array(e.inputBuffer.getChannelData(0)))}
    src.connect(node);node.connect(recCtx.destination)
    btn.innerHTML='<i class="fas fa-stop"></i> '+T('stop')
    var sec=0;id('record-timer').style.display='inline';id('record-timer').textContent='00:00'
    recTimer=setInterval(function(){sec++;var m=String(Math.floor(sec/60)).padStart(2,'0');var s=String(sec%60).padStart(2,'0');id('record-timer').textContent=m+':'+s},1000)
  }).catch(function(){toast('Microphone access denied','err')})
}
function stopRecording(){
  if(recTimer){clearInterval(recTimer);recTimer=null}
  id('record-timer').style.display='none'
  recCtx.close().then(function(){
    recStream.getTracks().forEach(function(t){t.stop()});recStream=null
    var sr=recCtx.sampleRate,len=0
    recAudioChunks.forEach(function(c){len+=c.length})
    var merged=new Float32Array(len),off=0
    recAudioChunks.forEach(function(c){merged.set(c,off);off+=c.length})
    var buf=new ArrayBuffer(44+merged.length*2),dv=new DataView(buf)
    dv.setUint32(0,0x52494646,false);dv.setUint32(4,36+merged.length*2,true);dv.setUint32(8,0x57415645,false)
    dv.setUint32(12,0x666D7420,false);dv.setUint32(16,16,true);dv.setUint16(20,1,true);dv.setUint16(22,1,true)
    dv.setUint32(24,sr,true);dv.setUint32(28,sr*2,true);dv.setUint16(32,2,true);dv.setUint16(34,16,true)
    dv.setUint32(36,0x64617461,false);dv.setUint32(40,merged.length*2,true)
    for(var i=0;i<merged.length;i++){var s=Math.max(-1,Math.min(1,merged[i]));dv.setInt16(44+i*2,s<0?s*0x8000:s*0x7FFF,true)}
    var blob=new Blob([buf],{type:'audio/wav'}),url=URL.createObjectURL(blob)
    id('recorded-preview').src=url;id('record-preview').style.display='block';id('audio-file').value=''
    id('recorded-preview').dataset.recordedBlob=url
    id('record-btn').innerHTML='<i class="fas fa-microphone"></i> '+T('record_mic');recCtx=null
  })
}
function clearRecording(){id('record-preview').style.display='none';id('recorded-preview').src='';delete id('recorded-preview').dataset.recordedBlob}

// ─── MIDI Piano Roll ───────────────────────────────────────────
function showPianoRoll(midiUrl){
  var file=midiUrl.split('/').pop(),cont=id('midi-piano'),img=id('piano-img')
  img.src='/api/midi/pianoroll?file='+encodeURIComponent(file)
  img.onerror=function(){cont.style.display='none'}
  img.onload=function(){cont.style.display='block'}
  cont.style.display='block'
}

// ─── Process ────────────────────────────────────────────────────
async function processAudio(){
  var file=id('audio-file').files[0],btn=id('process-btn');btn.disabled=true
  status('process-status','<span class="spinner"></span> '+T('processing'),'wait')
  id('audio-out-box').innerHTML='<div class="empty-state">'+T('processing')+'</div>'
  id('midi-out-box').innerHTML='<div class="empty-state">'+T('processing')+'</div>'
  id('midi-piano').style.display='none'
  var fd=new FormData(),recUrl=id('recorded-preview').dataset.recordedBlob
  if(file){fd.append('audio',file)
  }else if(recUrl){var r=await fetch(recUrl),b=await r.blob();fd.append('audio',b,'recording.wav')
  }else{toast(T('select_file'),'err');btn.disabled=false;return}
  fd.append('reverb',id('reverb').checked)
  fetch('/api/process',{method:'POST',body:fd}).then(function(r){return r.json()}).then(function(d){
    btn.disabled=false
    if(!d.ok){status('process-status','Error: '+d.error,'err');toast(T('toast_error'),'err');return}
    status('process-status','','ok');toast(T('toast_done'),'ok')
    var audioFile=d.audio.split('/').pop()
    id('audio-out-box').innerHTML='<div class="out-row"><audio src="'+d.audio+'" controls></audio><a href="'+d.audio+'" download class="btn-icon" title="Download"><i class="fas fa-download"></i></a></div>'
    var midiFile=d.midi.split('/').pop()
    id('midi-out-box').innerHTML='<div class="out-row" id="midi-player-row"><i class="fas fa-spinner fa-spin"></i> '+T('processing')+'</div>'
    fetch(midiRenderUrl(midiFile)).then(function(r){if(!r.ok)throw Error();return r.blob()}).then(function(blob){
      var url=URL.createObjectURL(blob)
      id('midi-player-row').innerHTML='<audio src="'+url+'" controls style="width:100%"></audio><a href="'+d.midi+'" download class="btn-icon" title="Download"><i class="fas fa-download"></i></a>'
    }).catch(function(){id('midi-player-row').innerHTML='<a href="'+d.midi+'" download class="btn-icon" title="Download"><i class="fas fa-download"></i></a>'})
    showPianoRoll(d.midi)
    _histOffset=0;_histTotal=0
    loadHistory(true)
  }).catch(function(e){btn.disabled=false;status('process-status','Error: '+e,'err');toast(T('toast_error'),'err')})
}

// ─── Ratings ────────────────────────────────────────────────────
function loadRatings(){
  fetch('/api/ratings').then(function(r){return r.json()}).then(function(d){
    var el=id('ratings-log');el.innerHTML=''
    d.rows.forEach(function(r){el.innerHTML+='<span class="info">'+r.join(' | ')+'</span>\n'})
  })
}
if(id('ratings-log'))loadRatings()
function saveRating(){
  var fd=new FormData();fd.append('audio',(id('eval-file').files[0]||{}).name||'')
  fd.append('rating',id('eval-rating').value);fd.append('note',id('eval-note').value)
  fetch('/api/rate',{method:'POST',body:fd}).then(function(r){return r.json()}).then(function(){toast(T('toast_saved'),'ok');loadRatings()})
}
if(id('eval-file'))id('eval-file').addEventListener('change',function(){
  if(this.files[0]){id('eval-player').src=URL.createObjectURL(this.files[0]);id('eval-player').style.display='block'}
})

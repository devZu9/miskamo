// ─── History ────────────────────────────────────────────────────
var _histOffset=0,_histTotal=0
function loadHistory(reset){
  if(reset){_histOffset=0;_histTotal=0}
  var el=id('history-list')
  if(_histOffset===0)el.innerHTML=''
  if(_histOffset>0&&_histOffset>=_histTotal){var lm=id('load-more');if(lm)lm.remove();return}
  fetch('/api/history?limit=20&offset='+_histOffset).then(function(r){return r.json()}).then(function(d){
    if(!d.ok){el.innerHTML='<div class="empty-state">'+T('history_empty')+'</div>';return}
    _histTotal=d.total
    if(_histOffset===0)el.innerHTML=''
    if(!d.entries.length&&_histOffset===0){el.innerHTML='<div class="empty-state">'+T('history_empty')+'</div>';return}
    var oldLm=id('load-more');if(oldLm)oldLm.remove()
    d.entries.forEach(function(e){
      var row=document.createElement('div');row.className='hist-item'
      var durStr=e.duration?e.duration+'s':''
      var midiFile=e.midi.split('/').pop()
      row.innerHTML=
        '<div class="hist-left">'+
          '<span class="fname">'+e.uid+'.wav</span>'+
          '<span class="dur-label">'+durStr+'</span>'+
          '<button class="btn-icon play-btn" onclick="togglePlayHist(this,\''+e.audio+'\')"><i class="fas fa-play"></i></button>'+
          '<a href="'+e.audio+'" download class="btn-icon dl-btn"><i class="fas fa-download"></i></a>'+
        '</div>'+
        '<div class="hist-right">'+
          '<span class="fname">'+e.uid+'.mid</span>'+
          '<span class="dur-label">'+durStr+'</span>'+
          '<button class="btn-icon midi-play-btn" onclick="togglePlayMidiHist(this,\''+midiFile+'\')"><i class="fas fa-play"></i></button>'+
          '<a href="'+e.midi+'" download class="btn-icon dl-btn"><i class="fas fa-download"></i></a>'+
          '<span class="hist-sep">|</span>'+
          '<button class="btn-icon del-btn" onclick="deleteGeneration(\''+e.uid+'\')"><i class="fas fa-trash"></i></button>'+
        '</div>'
      el.appendChild(row)
    })
    _histOffset+=d.entries.length
    if(_histOffset<_histTotal){
      var lm=document.createElement('div');lm.id='load-more';lm.textContent='Load more...'
      lm.onclick=function(){loadHistory(false)}
      el.appendChild(lm)
    }
  })
}
function togglePlayHist(btn,url){
  if(btn.classList.contains('playing')){
    btn.classList.remove('playing');btn.innerHTML='<i class="fas fa-play"></i>'
    if(window._curHistAudio){window._curHistAudio.pause();window._curHistAudio=null}
    return
  }
  if(window._curHistAudio){window._curHistAudio.pause();window._curHistAudio=null}
  document.querySelectorAll('.hist-block .play-btn.playing').forEach(function(b){b.classList.remove('playing');b.innerHTML='<i class="fas fa-play"></i>'})
  var a=new Audio(url)
  a.onended=function(){btn.classList.remove('playing');btn.innerHTML='<i class="fas fa-play"></i>';window._curHistAudio=null}
  a.onerror=function(){btn.classList.remove('playing');btn.innerHTML='<i class="fas fa-play"></i>';window._curHistAudio=null}
  a.play().then(function(){btn.classList.add('playing');btn.innerHTML='<i class="fas fa-stop"></i>';window._curHistAudio=a}).catch(function(){btn.classList.remove('playing')})
}
// ─── MIDI render (server-side FluidSynth → WAV) ──────────────
var _midiCtx={} // {blobUrl, audio}
function togglePlayMidiHist(btn,midiFile){
  if(btn.classList.contains('loading'))return
  var key='midi_'+midiFile
  if(_midiCtx[key]&&_midiCtx[key].playing){
    _midiCtx[key].audio.pause();_midiCtx[key].playing=false
    btn.classList.remove('playing');btn.innerHTML='<i class="fas fa-play"></i>'
    return
  }
  Object.keys(_midiCtx).forEach(function(k){
    if(_midiCtx[k].playing){_midiCtx[k].audio.pause();_midiCtx[k].playing=false}
  })
  document.querySelectorAll('.midi-play-btn.playing').forEach(function(b){b.classList.remove('playing');b.innerHTML='<i class="fas fa-play"></i>'})
  if(_midiCtx[key]&&_midiCtx[key].blobUrl){
    _midiCtx[key].audio.play().then(function(){_midiCtx[key].playing=true;btn.classList.add('playing');btn.innerHTML='<i class="fas fa-stop"></i>'}).catch(function(){})
    return
  }
  btn.classList.add('loading');btn.innerHTML='<i class="fas fa-spinner fa-spin"></i>'
  var url=midiRenderUrl(midiFile)
  fetch(url).then(function(r){if(!r.ok)throw Error();return r.blob()}).then(function(blob){
    var blobUrl=URL.createObjectURL(blob)
    var a=new Audio(blobUrl)
    a.onended=function(){btn.classList.remove('playing');btn.innerHTML='<i class="fas fa-play"></i>';_midiCtx[key].playing=false}
    _midiCtx[key]={blobUrl:blobUrl,audio:a,playing:false}
    btn.classList.remove('loading')
    a.play().then(function(){_midiCtx[key].playing=true;btn.classList.add('playing');btn.innerHTML='<i class="fas fa-stop"></i>'}).catch(function(){btn.classList.remove('playing');btn.innerHTML='<i class="fas fa-play"></i>'})
  }).catch(function(){btn.classList.remove('loading');btn.innerHTML='<i class="fas fa-play"></i>';toast(T('toast_error'),'err')})
}
function deleteGeneration(uid){
  var cb=id('settings-confirm-del')
  if(cb&&cb.checked&&!confirm(T('history_confirm')))return
  var fd=new FormData();fd.append('uid',uid)
  fetch('/api/history/delete',{method:'POST',body:fd}).then(function(r){return r.json()}).then(function(){toast(T('toast_deleted'),'ok');loadHistory(true)})
}
function clearHistory(){
  var cb=id('settings-confirm-del')
  if(cb&&cb.checked&&!confirm('Удалить все генерации?'))return
  fetch('/api/history/clear',{method:'POST'}).then(function(){toast('Cleared','ok');loadHistory(true)})
}

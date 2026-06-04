// ─── MIDI Generator ────────────────────────────────────────────────
function mgTsigChange(el){
  id('mg-tsig').value=el.value
  try{localStorage.setItem('mg_tsig',el.value)}catch(e){}
  toast(el.value+' ('+T('midigen_tsig')+')','ok')
  mgResetPresetDropdown()
}
function mgVal(el){
  el.parentElement.querySelector('.val').textContent=el.value
}
function mgBpmBarsChanged(el){
  toast(el.value+' '+T('midigen_'+(el.id==='mg-bpm'?'bpm':'bars')),'ok')
  mgSaveBpmBars()
  mgResetPresetDropdown()
}
function mgSaveBpmBars(){
  try{
    localStorage.setItem('mg_bpm',id('mg-bpm').value)
    localStorage.setItem('mg_bars',id('mg-bars').value)
  }catch(e){}
}
function mgRestoreBpmBars(){
  try{
    var bpm=localStorage.getItem('mg_bpm');if(bpm){var el=id('mg-bpm');if(el){el.value=bpm;el.parentElement.querySelector('.val').textContent=bpm}}
    var bars=localStorage.getItem('mg_bars');if(bars){var el=id('mg-bars');if(el){el.value=bars;el.parentElement.querySelector('.val').textContent=bars}}
  }catch(e){}
}
function mgAlgoChange(showToast){
  var sel=id('mg-algo'),algo=sel.value
  document.querySelectorAll('.mg-algo-panel').forEach(function(p){p.style.display='none'})
  var panel=id('mg-panel-'+algo)
  if(panel)panel.style.display='block'
  if(showToast!==false)toast(sel.options[sel.selectedIndex].textContent.trim(),'ok')
  try{localStorage.setItem('mg_algo',algo)}catch(e){}
}
function mgMassToggle(){
  var mass=id('mg-mass').checked,count=id('mg-count')
  count.disabled=!mass;count.style.opacity=mass?1:.4
  id('mg-preview-card').style.display=mass?'none':'block'
  id('mg-log-card').style.display=mass?'block':'none'
  try{localStorage.setItem('mg_mass',mass?'1':'');localStorage.setItem('mg_mass_count',count.value)}catch(e){}
  var sr=id('mg-seed-row');if(sr){sr.style.opacity=mass?.4:1;sr.querySelectorAll('input,button').forEach(function(e){e.disabled=mass})}
}
function mgInstrChange(){
  var v=id('mg-instr').value
  try{localStorage.setItem('mg_instr',v)}catch(e){}
}
function mgSeedNew(){
  var seed=Math.floor(Math.random()*2147483647)
  id('mg-seed').value=seed
  toast(T('midigen_seed')+': '+seed,'ok')
  try{localStorage.setItem('mg_seed',String(seed))}catch(e){}
}
function mgSeedReset(){
  id('mg-seed').value='-1'
  toast(T('midigen_seed')+': -1 ('+T('midigen_seed_random')+')','ok')
  try{localStorage.setItem('mg_seed','-1')}catch(e){}
}
function mgSeedRestore(){
  if(window._mgLastSeed===undefined){toast(T('midigen_seed_none'),'err');return}
  id('mg-seed').value=window._mgLastSeed
  toast(T('midigen_seed')+': '+window._mgLastSeed,'ok')
  try{localStorage.setItem('mg_seed',String(window._mgLastSeed))}catch(e){}
}
function mgSaveCount(){
  try{localStorage.setItem('mg_mass_count',id('mg-count').value)}catch(e){}
}
function mgCountAdjust(delta){
  var inp=id('mg-count')
  var v=parseInt(inp.value)||1
  v=Math.max(1,Math.min(1000,v+delta))
  inp.value=v
  mgSaveCount()
}
// Scroll on count input
document.addEventListener('DOMContentLoaded',function(){
  var ci=id('mg-count')
  if(ci){ci.addEventListener('wheel',function(e){if(document.activeElement===ci){e.preventDefault();mgCountAdjust(e.deltaY<0?1:-1)}})}
  // Restore mass gen state
  try{
    var saved=localStorage.getItem('mg_mass')
    if(saved==='1'){id('mg-mass').checked=true;id('mg-count').disabled=false;id('mg-count').style.opacity=1;id('mg-preview-card').style.display='none';id('mg-log-card').style.display='block'}
    var cnt=localStorage.getItem('mg_mass_count')
    if(cnt){var n=parseInt(cnt);if(n>0&&n<=1000)id('mg-count').value=n}
  }catch(e){}
  // Restore seed
  try{var seed=localStorage.getItem('mg_seed');if(seed){id('mg-seed').value=seed}}catch(e){}
  // Dim seed row if mass gen active
  try{var mass=id('mg-mass').checked;var sr=id('mg-seed-row');if(sr){sr.style.opacity=mass?.4:1;sr.querySelectorAll('input,button').forEach(function(e){e.disabled=mass})}}catch(e){}
  // Load presets (restore saved selection)
  var savedPreset='';try{savedPreset=localStorage.getItem('mg_preset')||''}catch(e){}
  mgInitPresets(savedPreset||undefined)
  // Restore BPM/Bars
  mgRestoreBpmBars()
  // Restore algorithm
  try{var algo=localStorage.getItem('mg_algo');if(algo){id('mg-algo').value=algo;var p=id('mg-panel-'+algo);document.querySelectorAll('.mg-algo-panel').forEach(function(x){x.style.display='none'});if(p)p.style.display='block'}}catch(e){}
  // Restore instrument
  try{var instr=localStorage.getItem('mg_instr');if(instr){id('mg-instr').value=instr}}catch(e){}
  // Restore tsig
  try{var tsig=localStorage.getItem('mg_tsig');if(tsig){id('mg-tsig').value=tsig;var r=document.querySelector('.tsig-radio-group input[value="'+tsig+'"]');if(r)r.checked=true}}catch(e){}
  // Save count on page unload
  window.addEventListener('beforeunload',function(){try{localStorage.setItem('mg_mass_count',id('mg-count').value);mgSaveBpmBars();localStorage.setItem('mg_algo',id('mg-algo').value);localStorage.setItem('mg_instr',id('mg-instr').value);localStorage.setItem('mg_seed',id('mg-seed').value);localStorage.setItem('mg_tsig',id('mg-tsig').value)}catch(e){}})
  // Restore key/scale toggle state
  mgRestoreKeyScaleState()
})
function mgToggleKey(el,val){
  el.classList.toggle('active')
  var on=el.classList.contains('active')
  toast(val+' ('+T('midigen_key')+' '+T(on?'toggle_on':'toggle_off')+')',on?'ok':'err')
  mgSaveKeyScaleState()
  mgResetPresetDropdown()
}
function mgToggleScale(el,val){
  el.classList.toggle('active')
  var on=el.classList.contains('active')
  toast(el.textContent.trim()+' ('+T('midigen_scale')+' '+T(on?'toggle_on':'toggle_off')+')',on?'ok':'err')
  mgSaveKeyScaleState()
  mgResetPresetDropdown()
}
function mgSaveKeyScaleState(){
  try{
    var keys=[],scales=[]
    document.querySelectorAll('#mg-key-group .tgl-btn.active').forEach(function(b){keys.push(b.getAttribute('data-value'))})
    document.querySelectorAll('#mg-scale-group .tgl-btn.active').forEach(function(b){scales.push(b.getAttribute('data-value'))})
    localStorage.setItem('mg_keys',JSON.stringify(keys))
    localStorage.setItem('mg_scales',JSON.stringify(scales))
  }catch(e){}
}
function mgRestoreKeyScaleState(){
  try{
    var keys=JSON.parse(localStorage.getItem('mg_keys'))
    if(keys&&Array.isArray(keys)&&keys.length){
      document.querySelectorAll('#mg-key-group .tgl-btn').forEach(function(b){
        b.classList.toggle('active',keys.indexOf(b.getAttribute('data-value'))>=0)
      })
    }
    var scales=JSON.parse(localStorage.getItem('mg_scales'))
    if(scales&&Array.isArray(scales)&&scales.length){
      document.querySelectorAll('#mg-scale-group .tgl-btn').forEach(function(b){
        b.classList.toggle('active',scales.indexOf(b.getAttribute('data-value'))>=0)
      })
    }
  }catch(e){}
  mgRestoreOctaveState()
}
function mgToggleOctave(el){
  el.classList.toggle('active')
  var off=el.getAttribute('data-offset')
  var on=el.classList.contains('active')
  toast(off+' ('+T('midigen_octave')+' '+T(on?'toggle_on':'toggle_off')+')',on?'ok':'err')
  mgSaveOctaveState()
  mgResetPresetDropdown()
}
function mgOctaveChanged(){
  toast(id('mg-octave').value+' ('+T('midigen_octave')+')','ok')
  mgSaveOctaveState()
  mgResetPresetDropdown()
}
function mgSaveOctaveState(){
  try{
    var offs=[]
    document.querySelectorAll('.octave-btn.active').forEach(function(b){offs.push(b.getAttribute('data-offset'))})
    localStorage.setItem('mg_octave_offsets',JSON.stringify(offs))
    localStorage.setItem('mg_octave_base',id('mg-octave').value)
  }catch(e){}
}
function mgRestoreOctaveState(){
  try{
    var offs=JSON.parse(localStorage.getItem('mg_octave_offsets'))
    if(offs&&Array.isArray(offs)){
      document.querySelectorAll('.octave-btn').forEach(function(b){
        b.classList.toggle('active',offs.indexOf(b.getAttribute('data-offset'))>=0)
      })
    }
    var base=localStorage.getItem('mg_octave_base')
    if(base){var el=id('mg-octave');if(el)el.value=base}
  }catch(e){}
}
function mgCollectParams(){
  var keys=[],scales=[],octOffs=[]
  document.querySelectorAll('#mg-key-group .tgl-btn.active').forEach(function(b){keys.push(b.getAttribute('data-value'))})
  document.querySelectorAll('#mg-scale-group .tgl-btn.active').forEach(function(b){scales.push(b.getAttribute('data-value'))})
  document.querySelectorAll('.octave-btn.active').forEach(function(b){octOffs.push(parseInt(b.getAttribute('data-offset')))})
  return JSON.stringify({
    algorithm:id('mg-algo').value,
    key:keys,
    scale:scales,
    octave_base:parseInt(id('mg-octave').value),
    octave_offsets:octOffs,
    bpm:parseInt(id('mg-bpm').value),
    instrument:id('mg-instr').value,
    time_signature:id('mg-tsig').value,
    total_bars:parseInt(id('mg-bars').value),
    max_interval:parseInt(id('mg-max_int')?.value||7),
    rest_probability:parseInt(id('mg-rest_prob')?.value||10)/100,
    progression:id('mg-progression')?.value||'pop',
    chord_tone_bias:parseInt(id('mg-chord_bias')?.value||60)/100,
    notes_per_chord:parseInt(id('mg-notes_pc')?.value||2),
    markov_matrix:id('mg-markov_mat')?.value||'generic',
    markov_rest:parseInt(id('mg-markov_rest')?.value||8)/100,
    climax_bar:parseInt(id('mg-climax')?.value||5),
    cadence_rest_prob:parseInt(id('mg-cadence_rest')?.value||10)/100,
    _seed:parseInt(id('mg-seed')?.value)||-1,
    note_offset: document.getElementById('settings-ableton')?.checked?24:12,
  })
}
function mgApplyParams(p){
  ['mg-instr','mg-tsig'].forEach(function(k){
    var el=id(k);if(el&&p[k]!==undefined)el.value=p[k]
  })
  var tsigEl=id('mg-tsig');if(tsigEl){
    var r=document.querySelector('.tsig-radio-group input[value="'+tsigEl.value+'"]')
    if(r)r.checked=true
  }
  if(p.algorithm!==undefined){var el=id('mg-algo');if(el)el.value=p.algorithm}
  if(p.key!==undefined){
    var vals=Array.isArray(p.key)?p.key:[p.key]
    document.querySelectorAll('#mg-key-group .tgl-btn').forEach(function(b){
      b.classList.toggle('active',vals.indexOf(b.getAttribute('data-value'))>=0)
    })
  }
  if(p.scale!==undefined){
    var vals=Array.isArray(p.scale)?p.scale:[p.scale]
    document.querySelectorAll('#mg-scale-group .tgl-btn').forEach(function(b){
      b.classList.toggle('active',vals.indexOf(b.getAttribute('data-value'))>=0)
    })
  }
  if(p.octave_base!==undefined){
    var el=id('mg-octave');if(el)el.value=p.octave_base
  }
  if(p.octave_offsets!==undefined&&Array.isArray(p.octave_offsets)){
    var offs=p.octave_offsets.map(function(v){return String(v)})
    document.querySelectorAll('.octave-btn').forEach(function(b){
      b.classList.toggle('active',offs.indexOf(b.getAttribute('data-offset'))>=0)
    })
  }
  ;[['mg-bpm','bpm'],['mg-bars','total_bars'],['mg-max_int','max_interval'],['mg-rest_prob','rest_probability'],
   ['mg-chord_bias','chord_tone_bias'],['mg-notes_pc','notes_per_chord'],
   ['mg-markov_rest','markov_rest'],['mg-climax','climax_bar'],['mg-cadence_rest','cadence_rest_prob'],
  ].forEach(function(pair){
    var el=id(pair[0]),key=pair[1]
    if(el&&p[key]!==undefined){
      var v=key==='rest_probability'||key==='chord_tone_bias'||key==='cadence_rest_prob'||key==='markov_rest' ? Math.round(p[key]*100) : p[key]
      el.value=v
      var sv=el.parentElement.querySelector('.val')
      if(sv)sv.textContent=v
    }
  })
  mgAlgoChange(false)
}
function mgGenerate(){
  var btn=id('mg-gen-btn');btn.disabled=true
  var mass=id('mg-mass').checked
  if(mass){
    mgBatchGen()
    return
  }
  status('mg-status','<span class="spinner"></span> '+T('midigen_genning'),'wait')
  id('mg-preview').style.display='none';id('mg-empty').style.display='block'
  var fd=new FormData();fd.append('params',mgCollectParams())
  fetch('/api/midi_gen/generate',{method:'POST',body:fd}).then(function(r){return r.json()}).then(function(d){
    btn.disabled=false
    if(!d.ok){status('mg-status',d.error||'Error','err');return}
    id('mg-empty').style.display='none';id('mg-preview').style.display='block'
    var audioUrl='/api/midi/render?file='+encodeURIComponent(d.filename)
    if(document.getElementById('settings-ableton')?.checked)audioUrl+='&transpose=-12'
    id('mg-audio').src=audioUrl
    var prUrl='/api/midi/pianoroll?file='+encodeURIComponent(d.filename)
    if(d.pitch_low!=null&&d.pitch_high!=null)prUrl+='&pitch_low='+d.pitch_low+'&pitch_high='+d.pitch_high
    if(d.total_bars!=null)prUrl+='&total_bars='+d.total_bars
    if(d.note_offset)prUrl+='&note_offset='+d.note_offset
    id('mg-pianoroll').src=prUrl
    status('mg-status',T('midigen_done'),'ok')
    toast(T('midigen_done'),'ok')
    window._mgFilename=d.filename
    window._mgLastSeed=d.seed
    var sfd=new FormData();sfd.append('params',mgCollectParams());sfd.append('bank_name','generated')
    fetch('/api/midi_gen/save_to_bank',{method:'POST',body:sfd}).then(function(r){return r.json()}).then(function(sd){
      if(sd.ok)toast(T('midigen_saved_to_bank'),'ok')
    })
  }).catch(function(e){btn.disabled=false;status('mg-status','Error: '+e,'err')})
}
function mgBatchGen(){
  var btn=id('mg-gen-btn'),log=id('mg-log')
  status('mg-status','<span class="spinner"></span> '+T('midigen_genning'),'wait')
  log.innerHTML=''
  var count=parseInt(id('mg-count').value)||8
  try{localStorage.setItem('mg_mass_count',count)}catch(e){}
  var fd=new FormData();fd.append('params',mgCollectParams());fd.append('count',count)
  fetch('/api/midi_gen/generate_batch',{method:'POST',body:fd}).then(function(r){return r.json()}).then(function(d){
    btn.disabled=false
    if(!d.ok){status('mg-status',d.error||'Error','err');return}
    log.innerHTML+=T('midigen_batch_done')+': '+d.count+' files → '+d.path+'\n'
    status('mg-status',T('midigen_done'),'ok')
    toast(d.count+' '+T('midigen_genned'),'ok')
  }).catch(function(e){btn.disabled=false;status('mg-status','Error: '+e,'err')})
}
function mgDownloadMidi(){
  if(!window._mgFilename){toast(T('midigen_empty'),'err');return}
  var fn=window._mgFilename
  if(document.getElementById('settings-ableton')?.checked){
    var dot=fn.lastIndexOf('.')
    fn=fn.slice(0,dot)+'_a'+fn.slice(dot)
  }
  window.open('/api/file/'+encodeURIComponent(window._mgFilename)+'?dl='+encodeURIComponent(fn),'_blank')
}
function mgInitPresets(selectName){
  return fetch('/api/midi_gen/presets').then(function(r){return r.json()}).then(function(d){
    var sel=id('mg-preset');if(!sel)return
    sel.innerHTML='<option value="">'+T('preset_placeholder')+'</option>'
    d.presets.forEach(function(p){
      var o=document.createElement('option');o.value=p.name;o.textContent=p.name;sel.appendChild(o)
    })
    if(selectName){
      for(var i=0;i<sel.options.length;i++){
        if(sel.options[i].value===selectName){sel.value=selectName;break}
      }
      try{localStorage.setItem('mg_preset',sel.value||'')}catch(e){}
    }
  })
}
function mgPresetChanged(){
  var sel=id('mg-preset'),name=sel.value
  if(!name){try{localStorage.setItem('mg_preset','')}catch(e){};return}
  try{localStorage.setItem('mg_preset',name)}catch(e){}
  fetch('/api/midi_gen/presets/load?name='+encodeURIComponent(name)).then(function(r){return r.json()}).then(function(d){
    if(!d.ok){toast(T('toast_error'),'err');return}
    mgApplyParams(d.data)
    mgSaveKeyScaleState()
    mgSaveOctaveState()
    mgSaveBpmBars()
    try{localStorage.setItem('mg_instr',id('mg-instr').value)}catch(e){}
    toast(T('preset_loaded'),'ok')
  })
}
function mgPresetSave(){
  var name=prompt(T('preset_name'))
  if(!name)return
  var sel=id('mg-preset')
  for(var i=0;i<sel.options.length;i++){
    if(sel.options[i].value===name){
      if(!confirm(T('preset_name_exists')+'\n'+T('preset_old_will_replace')))return
      break
    }
  }
  var raw=mgCollectParams();var p=JSON.parse(raw);delete p._seed;var params=JSON.stringify(p)
  var fd=new FormData();fd.append('name',name);fd.append('params',params);fd.append('overwrite','true')
  fetch('/api/midi_gen/presets/save',{method:'POST',body:fd}).then(function(r){return r.json()}).then(function(d){
    if(d.ok){toast(T('preset_saved'),'ok');mgInitPresets(name)}
    else if(d.error==='exists'){toast(T('preset_err_exists'),'err')}
  })
}
function mgPresetRename(){
  var sel=id('mg-preset'),old=sel.value
  if(!old){toast(T('preset_err_exists'),'err');return}
  var name=prompt(T('preset_new_name'),old)
  if(!name||name===old)return
  for(var i=0;i<sel.options.length;i++){
    if(sel.options[i].value===name){
      if(!confirm(T('preset_name_exists')+'\n'+T('preset_old_will_replace')))return
    }
  }
  var fd=new FormData();fd.append('old_name',old);fd.append('new_name',name)
  fetch('/api/midi_gen/presets/rename',{method:'POST',body:fd}).then(function(r){return r.json()}).then(function(d){
    if(d.ok){toast(T('preset_renamed'),'ok');mgInitPresets(name)}
    else if(d.error==='exists'){toast(T('preset_err_exists'),'err')}
  })
}
function mgPresetDelete(){
  var sel=id('mg-preset'),name=sel.value
  if(!name){toast(T('preset_err_exists'),'err');return}
  if(!confirm(T('preset_confirm_delete').replace('{n}',name)))return
  var fd=new FormData();fd.append('name',name)
  fetch('/api/midi_gen/presets/delete',{method:'POST',body:fd}).then(function(r){return r.json()}).then(function(d){
    if(d.ok){toast(T('preset_deleted'),'ok');mgInitPresets()}
  })
}
function mgResetPresetDropdown(){
  var sel=id('mg-preset');if(sel){sel.value='';try{localStorage.setItem('mg_preset','')}catch(e){}}
}

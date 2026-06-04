// ─── Dataset ────────────────────────────────────────────────────
var _datasetSaveTimer=null
var _paramLabels={pd:'drift',dp:'drift_prob',tj:'jitter',jp:'jitter_prob',bn:'bad',nd:'noise',np:'noise_prob',md:'duration'}
var _paramPairs={pd:'dp',tj:'jp',nd:'np',md:'row-split'}
var _genCancelled=false

function toggleParam(mainId){
  var cb=id('cb-'+mainId)
  var row=id('row-'+mainId)
  if(row)row.classList.toggle('dimmed',!cb.checked)
  var pair=_paramPairs[mainId]
  if(pair){
    if(mainId==='md'){
      var scb=id('cb-split');var srow=id('row-split')
      scb.disabled=!cb.checked
      if(!cb.checked)scb.checked=false
      if(srow)srow.classList.toggle('dimmed',!cb.checked)
    }else{
      var pr=id('row-'+pair)
      if(pr)pr.classList.toggle('dimmed',!cb.checked)
    }
  }
  saveParamEnabled()
  resetPresetDropdown()
  toast(T(_paramLabels[mainId])+' '+T('toast_saved_param'),'ok')
}

function splitChanged(){
  var cb=id('cb-split')
  try{localStorage.setItem('dataset_split',cb.checked?'1':'0')}catch(e){}
  resetPresetDropdown()
  toast(T('split')+' '+T('toast_saved_param'),'ok')
}
function saveParamEnabled(){
  var obj={}
  ;['pd','tj','bn','nd','md'].forEach(function(k){obj[k]=id('cb-'+k).checked})
  try{localStorage.setItem('dataset_enabled',JSON.stringify(obj))}catch(e){}
}

function datasetParamChange(el){
  el.parentElement.querySelector('.val').textContent=el.value
  resetPresetDropdown()
  if(_datasetSaveTimer)clearTimeout(_datasetSaveTimer)
  _datasetSaveTimer=setTimeout(function(){datasetAutoSave(el.id)},400)
}
function resetSlider(sliderId,val){
  var el=id(sliderId);el.value=val
  el.parentElement.querySelector('.val').textContent=val
  resetPresetDropdown()
  datasetAutoSave(sliderId)
}
function datasetAutoSave(paramId){
  var data={}
  ;['pd','dp','tj','jp','bn','nd','np','md'].forEach(function(k){
    data[k]=id(k).value
  })
  try{localStorage.setItem('dataset_params',JSON.stringify(data))}catch(e){}
  if(paramId&&_paramLabels[paramId]){
    toast(T(_paramLabels[paramId])+' '+T('toast_saved_param'),'ok')
  }else{
    toast(T('toast_saved'),'ok')
  }
}
// Restore dataset params + checkboxes from localStorage
;(function(){
  try{
    var raw=localStorage.getItem('dataset_params')
    if(raw){
      var data=JSON.parse(raw)
      Object.keys(data).forEach(function(k){
        var el=id(k)
        if(el){el.value=data[k];el.parentElement.querySelector('.val').textContent=data[k]}
      })
    }
    var en=localStorage.getItem('dataset_enabled')
    if(en){
      var enabled=JSON.parse(en)
      Object.keys(enabled).forEach(function(k){
        var cb=id('cb-'+k);if(!cb)return
        cb.checked=enabled[k]
        var row=id('row-'+k)
        if(row)row.classList.toggle('dimmed',!cb.checked)
        if(k==='md'){
          var scb=id('cb-split')
          scb.disabled=!cb.checked
          var srow=id('row-split')
          if(!cb.checked && scb){scb.checked=false}
          if(srow)srow.classList.toggle('dimmed',!cb.checked)
        }else{
          var pair=_paramPairs[k]
          if(pair){
            var pr=id('row-'+pair)
            if(pr)pr.classList.toggle('dimmed',!cb.checked)
          }
        }
      })
    }
    var sp=localStorage.getItem('dataset_split')
    if(sp){
      var cb=id('cb-split')
      if(cb)cb.checked=sp==='1'
    }
    initPresets().then(function(){
      var saved=localStorage.getItem('dataset_preset')
      if(saved){
        var sel=id('preset-select')
        for(var i=0;i<sel.options.length;i++){
          if(sel.options[i].value===saved){sel.value=saved;presetChanged();break}
        }
      }
    })
  }catch(e){}
})()
function generateDataset(){
  _genCancelled=false;var btn=id('gen-btn');btn.disabled=true
  id('gen-cancel').style.display='block'
  status('gen-status','<span class="spinner"></span> '+T('gen_wait'),'wait')
  var log=id('gen-log');log.innerHTML=''
  function v(id){return document.getElementById(id).value}
  function enabled(id){return document.getElementById('cb-'+id).checked}
  var fd=new FormData()
  fd.append('bank',id('bank-select').value)
  fd.append('pitch_drift',  enabled('pd') ? v('pd') : 0)
  fd.append('drift_prob',   enabled('pd') ? v('dp') : 0)
  fd.append('timing_jitter',enabled('tj') ? v('tj') : 0)
  fd.append('jitter_prob',  enabled('tj') ? v('jp') : 0)
  fd.append('bad_notes',    enabled('bn') ? v('bn') : 0)
  fd.append('noise',        enabled('nd') ? v('nd') : 0)
  fd.append('noise_prob',   enabled('nd') ? v('np') : 0)
  fd.append('max_dur',      enabled('md') ? v('md') : 999999)
  fd.append('split_midi',   enabled('md') ? (id('cb-split').checked?'true':'false') : 'false')
  fetch('/api/dataset/generate',{method:'POST',body:fd}).then(async function(r){
    if(!r.ok){btn.disabled=false;id('gen-cancel').style.display='none';status('gen-status','HTTP '+r.status,'err');return}
    var reader=r.body.getReader(),decoder=new TextDecoder(),buf=''
    while(true){
      var {done,value}=await reader.read()
      if(done)break
      buf+=decoder.decode(value,{stream:true})
      var lines=buf.split('\n')
      buf=lines.pop()||''
      for(var i=0;i<lines.length;i++){
        var line=lines[i]
        if(line.startsWith('log:')){
          log.innerHTML+=line.substring(4)+'\n'
          log.scrollTop=log.scrollHeight
        }else if(line.startsWith('result:')){
          var d=JSON.parse(line.substring(7))
          btn.disabled=false;id('gen-cancel').style.display='none'
          if(d.error==='cancelled'){
            status('gen-status',T('gen_cancelled'),'info')
            toast(T('gen_cancelled'),'info')
          }else if(d.ok){
            status('gen-status',T('gen_pairs').replace('{n}',d.count).replace('{s}',d.skipped),'ok')
            toast(d.count+' '+T('genned'),'ok')
          }else{
            status('gen-status',T('gen_error')+': '+d.error,'err')
          }
        }
      }
    }
  }).catch(function(e){btn.disabled=false;id('gen-cancel').style.display='none';status('gen-status','Error: '+e,'err')})
}
function cancelGeneration(){
  fetch('/api/dataset/cancel',{method:'POST'})
  id('gen-cancel').style.display='none'
  status('gen-status','<span class="spinner"></span> '+T('gen_stopping'),'wait')
}
function autoSaveBank(){
  var fd=new FormData();fd.append('midi_bank',id('bank-select').value)
  fetch('/api/save_bank',{method:'POST',body:fd})
}
function refreshBanks(selectName){
  fetch('/api/banks').then(function(r){return r.json()}).then(function(d){
    var sel=id('bank-select');sel.innerHTML=''
    d.banks.forEach(function(b){
      var o=document.createElement('option');o.value=b.name;o.textContent=b.name+' ('+b.count+' files)';sel.appendChild(o)
    })
    if(selectName){
      for(var i=0;i<sel.options.length;i++){
        if(sel.options[i].value===selectName){sel.value=selectName;break}
      }
    }
  })
}
function renameBank(){
  var sel=id('bank-select'),old=sel.value
  if(!old){toast(T('midigen_bank_name'),'err');return}
  var name=prompt(T('preset_new_name'),old)
  if(!name||name===old)return
  var fd=new FormData();fd.append('old_name',old);fd.append('new_name',name)
  fetch('/api/banks/rename',{method:'POST',body:fd}).then(function(r){return r.json()}).then(function(d){
    if(d.ok){
      toast(T('preset_renamed'),'ok')
      refreshBanks(d.name)
    }else if(d.error==='exists'){toast(T('preset_name_exists'),'err')}
    else{toast(T('toast_error'),'err')}
  })
}
function deleteBank(){
  var sel=id('bank-select'),name=sel.value
  if(!name){toast(T('midigen_bank_name'),'err');return}
  if(!confirm(T('confirm_delete_bank').replace('{n}',name)))return
  var fd=new FormData();fd.append('name',name)
  fetch('/api/banks/delete',{method:'POST',body:fd}).then(function(r){return r.json()}).then(function(d){
    if(d.ok){toast(T('bank_deleted'),'ok');refreshBanks()}
    else{toast(T('toast_error'),'err')}
  })
}

// ─── Presets ──────────────────────────────────────────────────────
var _presetKeyMap={
  pitch_drift:'pd', drift_prob:'dp',
  timing_jitter:'tj', jitter_prob:'jp',
  bad_notes:'bn',
  noise:'nd', noise_prob:'np',
  max_dur:'md',
}
var _presetCheckMap={
  cb_pd:'cb-pd', cb_tj:'cb-tj', cb_bn:'cb-bn', cb_nd:'cb-nd', cb_md:'cb-md',
}

function resetPresetDropdown(){
  var sel=id('preset-select')
  if(sel&&sel.value!==''){sel.value=''}
  try{localStorage.setItem('dataset_preset','')}catch(e){}
}

function initPresets(selectName){
  return fetch('/api/presets').then(function(r){return r.json()}).then(function(d){
    var sel=id('preset-select');if(!sel)return
    sel.innerHTML='<option value="">'+T('preset_placeholder')+'</option>'
    if(!d||!d.presets)return
    d.presets.forEach(function(n){
      var o=document.createElement('option');o.value=n;o.textContent=n;sel.appendChild(o)
    })
    if(selectName){
      for(var i=0;i<sel.options.length;i++){
        if(sel.options[i].value===selectName){sel.value=selectName;break}
      }
      try{localStorage.setItem('dataset_preset',sel.value||'')}catch(e){}
    }
  })
}
function presetChanged(){
  var sel=id('preset-select'),name=sel.value
  if(!name){try{localStorage.setItem('dataset_preset','')}catch(e){};return}
  try{localStorage.setItem('dataset_preset',name)}catch(e){}
  fetch('/api/presets/load?name='+encodeURIComponent(name)).then(function(r){return r.json()}).then(function(d){
    if(!d.ok){toast(T('toast_error'),'err');return}
    var p=d.params
    Object.keys(_presetKeyMap).forEach(function(k){
      if(p[k]===undefined)return
      var el=id(_presetKeyMap[k])
      if(el){el.value=p[k];el.parentElement.querySelector('.val').textContent=p[k]}
    })
    ;['pd','tj','bn','nd','md'].forEach(function(k){
      var cb=id('cb-'+k);if(!cb)return
      cb.checked=p['cb_'+k]!==undefined?p['cb_'+k]:true
      var row=id('row-'+k);if(row)row.classList.toggle('dimmed',!cb.checked)
      if(k==='md'){
        var scb=id('cb-split');var srow=id('row-split')
        scb.disabled=!cb.checked
        if(!cb.checked)scb.checked=false
        if(srow)srow.classList.toggle('dimmed',!cb.checked)
      }else{
        var pr=id('row-'+_paramPairs[k]);if(pr)pr.classList.toggle('dimmed',!cb.checked)
      }
    })
    var scb=id('cb-split')
    if(scb&&p.split_midi!==undefined)scb.checked=p.split_midi
    toast(T('preset_loaded'),'ok')
  })
}
function presetSave(){
  var name=prompt(T('preset_name'))
  if(!name)return
  var sel=id('preset-select')
  for(var i=0;i<sel.options.length;i++){
    if(sel.options[i].value===name){
      if(!confirm(T('preset_name_exists')+'\n'+T('preset_old_will_replace')))return
      break
    }
  }
  var fd=new FormData()
  function v(id){return document.getElementById(id).value}
  function enabled(id){return document.getElementById('cb-'+id).checked}
  fd.append('name',name)
  fd.append('overwrite','true')
  fd.append('pitch_drift',  v('pd'));fd.append('drift_prob',   v('dp'))
  fd.append('timing_jitter',v('tj'));fd.append('jitter_prob',  v('jp'))
  fd.append('bad_notes',    v('bn'))
  fd.append('noise',        v('nd'));fd.append('noise_prob',   v('np'))
  fd.append('max_dur',v('md'))
  fd.append('split_midi',id('cb-split').checked?'true':'false')
  fd.append('cb_pd',enabled('pd')?'true':'false');fd.append('cb_tj',enabled('tj')?'true':'false')
  fd.append('cb_bn',enabled('bn')?'true':'false');fd.append('cb_nd',enabled('nd')?'true':'false')
  fd.append('cb_md',enabled('md')?'true':'false')
  fetch('/api/presets/save',{method:'POST',body:fd}).then(function(r){return r.json()}).then(function(d){
    if(d.ok){
      toast(T('preset_saved'),'ok')
      initPresets(name)
    }else if(d.error==='exists'){
      toast(T('preset_err_exists'),'err')
    }
  })
}
function presetRename(){
  var sel=id('preset-select'),old=sel.value
  if(!old){toast(T('preset_err_exists'),'err');return}
  var name=prompt(T('preset_new_name'),old)
  if(!name||name===old)return
  for(var i=0;i<sel.options.length;i++){
    if(sel.options[i].value===name){
      if(!confirm(T('preset_name_exists')+'\n'+T('preset_old_will_replace')))return
      break
    }
  }
  var fd=new FormData()
  fd.append('old_name',old);fd.append('new_name',name);fd.append('overwrite','true')
  fetch('/api/presets/rename',{method:'POST',body:fd}).then(function(r){return r.json()}).then(function(d){
    if(d.ok){
      toast(T('preset_renamed'),'ok')
      initPresets(name)
    }else if(d.error==='exists'){
      toast(T('preset_err_exists'),'err')
    }
  })
}
function presetDelete(){
  var sel=id('preset-select'),name=sel.value
  if(!name){toast(T('preset_err_exists'),'err');return}
  if(!confirm(T('preset_confirm_delete').replace('{n}',name)))return
  var fd=new FormData();fd.append('name',name)
  fetch('/api/presets/delete',{method:'POST',body:fd}).then(function(r){return r.json()}).then(function(d){
    if(d.ok){
      toast(T('preset_deleted'),'ok')
      initPresets()
      try{localStorage.setItem('dataset_preset','')}catch(e){}
    }
  })
}
function presetUpload(){
  id('preset-file-input').click()
}
function presetUploadFile(input){
  var file=input.files[0];if(!file)return
  var fd=new FormData();fd.append('file',file)
  fetch('/api/presets/upload',{method:'POST',body:fd}).then(function(r){return r.json()}).then(function(d){
    if(d.ok){
      toast(T('preset_uploaded'),'ok')
      initPresets(d.name)
    }else{
      toast(T('toast_error')+': '+(d.error||'?'),'err')
    }
  })
  input.value=''
}

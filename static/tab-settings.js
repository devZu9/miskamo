// ─── Settings ───────────────────────────────────────────────────
function autoSave(cursorMsg){
  var fd=new FormData()
  fd.append('lang',id('settings-lang').value);fd.append('midi_bank','')
  fd.append('confirm_delete',id('settings-confirm-del').checked?'true':'')
  fd.append('clear_tmp',id('settings-clear-tmp').checked?'true':'')
  fd.append('toast_sec',id('settings-toast').value)
  fd.append('default_instrument',id('settings-instr').value)
  fd.append('cursor_size',id('settings-cursor').value)
  fd.append('cursor_enabled',id('settings-cursor-enable').checked?'true':'')
  fd.append('cursor_shape',document.querySelector('[name="cursor-shape"]:checked').value)
  fd.append('cursor_angle',id('settings-cursor-angle').value)
  fd.append('cursor_rotation',id('settings-cursor-rotation').checked?'true':'')
  fd.append('cursor_rotation_speed',id('settings-cursor-rotation-speed').value)
  fd.append('cursor_rotation_reverse',id('settings-cursor-rotation-reverse').checked?'true':'')
  fd.append('cursor_shadow',id('settings-cursor-shadow').checked?'true':'')
  fd.append('cursor_shadow_length',id('settings-cursor-shadow-length').value)
  fd.append('ableton',id('settings-ableton').checked?'true':'')
  fetch('/api/settings',{method:'POST',body:fd}).then(function(r){return r.json()}).then(function(d){
    if(cursorMsg==='cursor_on'){toast(T('settings_cursor_enable')+': '+T('toggle_on'),'ok')}
    else if(cursorMsg==='cursor_off'){toast(T('settings_cursor_enable')+': '+T('toggle_off'),'err')}
    else if(cursorMsg==='ableton_on'){toast(T('settings_ableton_on'),'ok')}
    else if(cursorMsg==='ableton_off'){toast(T('settings_ableton_off'),'err')}
    else{toast(T('toast_saved'),'ok')}
    _cursorEnabled=id('settings-cursor-enable').checked
    var cs=parseInt(id('settings-cursor').value);
    mgCursorShapeChange(document.querySelector('[name="cursor-shape"]:checked').value)
    mgCursorToggleDim(_cursorEnabled)
    mgCursorPreview(cs);
    if(_cursorEnabled&&cs>0&&!window._cursorListening){window._cursorListening=true;document.addEventListener('mousemove',_updateCursor)}
  })
}

// ─── Tab visibility ──────────────────────────────────────────────
var _ALL_TABS=['process','eval','midigen','dataset','history','train','tests']
var _TAB_LABELS={}

function _getTabOrder(){
  try{
    var raw=localStorage.getItem('tab_order')
    if(raw){var arr=JSON.parse(raw);if(Array.isArray(arr)&&arr.length)return arr}
  }catch(e){}
  return ['process','midigen','dataset','history','train','tests']
}
function _saveTabOrder(arr){
  try{localStorage.setItem('tab_order',JSON.stringify(arr))}catch(e){}
}
function _tabName(t){return _TAB_LABELS[t]||t}

function rebuildTabs(){
  var order=_getTabOrder(),cont=id('tabs'),sel=id('settings-tab-order')
  // Build nav
  var html=''
  order.forEach(function(t){
    html+='<div class="tab" data-tab="'+t+'"><i class="fas '+_TAB_ICONS[t]+'"></i> '+_tabName(t)+'</div>'
  })
  // Settings always last
  html+='<div class="tab tab-settings" data-tab="settings"><i class="fas fa-cog"></i></div>'
  cont.innerHTML=html
  // Attach click handlers
  cont.querySelectorAll('.tab').forEach(function(t){
    t.addEventListener('click',function(){switchTab(t.dataset.tab)})
  })
  // Rebuild settings preview
  if(sel)_buildTabPreview(sel)
  // Restore active tab from hash, fallback to first
  var order2=_getTabOrder()
  var tab=location.hash&&location.hash.slice(1)
  if(!tab||!document.querySelector('.tab[data-tab="'+tab+'"]')){
    tab=order2.length>0?order2[0]:'settings'
  }
  switchTab(tab,true)
}

var _TAB_ICONS={
  'process':'fa-microphone',
  'eval':'fa-pencil-alt',
  'midigen':'fa-music',
  'dataset':'fa-database',
  'history':'fa-folder',
  'train':'fa-brain',
  'tests':'fa-vial',
  'settings':'fa-cog'
}

function _buildTabPreview(container){
  var order=_getTabOrder()
  container.innerHTML=''
  // Visible tabs in user's saved order
  order.forEach(function(t){
    var row=_makePreviewItem(t,true)
    container.appendChild(row)
  })
  // Hidden tabs at the end
  _ALL_TABS.forEach(function(t){
    if(order.indexOf(t)>=0)return
    var row=_makePreviewItem(t,false)
    container.appendChild(row)
  })
  container.ondragend=function(){
    var items=container.querySelectorAll('.tab-preview-item'),order=[]
    items.forEach(function(item){
      var cb=item.querySelector('input[type="checkbox"]')
      if(cb&&cb.checked)order.push(item.dataset.tab)
    })
    _saveTabOrder(order)
    rebuildTabs()
    toast(T('toast_saved'),'ok')
  }
}
function _makePreviewItem(t,visible){
  var row=document.createElement('div')
  row.className='tab-preview-item'
  row.draggable=visible
  row.dataset.tab=t
  if(!visible)row.style.opacity=.4
  row.innerHTML=
    '<i class="fas fa-grip-vertical" style="cursor:'+(visible?'grab':'not-allowed')+';color:var(--muted);margin-right:.5rem"></i>'+
    '<i class="fas '+_TAB_ICONS[t]+'" style="min-width:1.2rem"></i> '+
    '<span style="flex:1">'+_tabName(t)+'</span>'+
    '<input type="checkbox" '+(visible?'checked':'')+' onchange="_toggleTabVis(this,\''+t+'\')">'
  if(visible){
    row.addEventListener('dragstart',function(e){
      e.dataTransfer.setData('text/plain',t)
      this.classList.add('dragging')
    })
    row.addEventListener('dragend',function(e){
      this.classList.remove('dragging')
    })
    row.addEventListener('dragover',function(e){
      e.preventDefault()
      var cont=this.parentElement
      if(!cont)return
      var dragging=cont.querySelector('.dragging')
      if(!dragging||dragging===this)return
      var rect=this.getBoundingClientRect(),mid=rect.left+rect.width/2
      cont.insertBefore(dragging,e.clientX<mid?this:this.nextSibling)
    })
  }
  return row
}

function _toggleTabVis(cb,tab){
  var order=_getTabOrder()
  if(cb.checked){
    if(order.indexOf(tab)<0)order.push(tab)
  }else{
    var idx=order.indexOf(tab)
    if(idx>=0)order.splice(idx,1)
  }
  _saveTabOrder(order)
  rebuildTabs()
  toast(_tabName(tab)+' '+T(cb.checked?'toggle_on':'toggle_off'),cb.checked?'ok':'err')
}

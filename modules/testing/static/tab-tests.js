// ─── Tests ──────────────────────────────────────────────────────
function runTests(){
  var log=id('test-log')
  log.textContent=T('test_running')+'\n'
  var btns=document.querySelectorAll('.test-header .btn')
  btns.forEach(function(b){b.disabled=true})
  
  fetch('/api/tests/run',{method:'POST'}).then(function(r){
    if(!r.ok){
      log.textContent+=T('toast_error')+': '+r.status+'\n'
      btns.forEach(function(b){b.disabled=false})
      return
    }
    var reader=r.body.getReader(),decoder=new TextDecoder()
    function read(){
      reader.read().then(function(result){
        if(result.done){
          btns.forEach(function(b){b.disabled=false})
          return
        }
        var text=decoder.decode(result.value,{stream:true}),lines=text.split('\n')
        lines.forEach(function(line){
          if(line.startsWith('result:')){
            try{
              var data=JSON.parse(line.slice(7))
              log.textContent+='\n=== '+T('test_exit_code')+': '+data.returncode+' ===\n'
            }catch(e){}
          }else if(line.startsWith('log:')){
            log.textContent+=line.slice(4)+'\n'
          }
        })
        log.scrollTop=log.scrollHeight
        read()
      })
    }
    read()
  }).catch(function(e){
    log.textContent+='\n'+T('toast_error')+': '+e.message+'\n'
    btns.forEach(function(b){b.disabled=false})
  })
}

function clearTestLog(){
  id('test-log').textContent=T('test_ready')
}

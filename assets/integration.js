/* Integração de mesma origem: nunca acessa o agente a partir do site hospedado. */
(() => {
if(!window.ingestLocal)return;
let online=false, health={}, sources=[], bindings=[], history=[], pending=false, refreshing, firstRead=true;
const pilotSlots=[0,1];
records=[];recording=[false,false,false,false];
const label={scheduled:'Agendada',running:'Em gravação',completed:'Concluída',failed:'Falha',interrupted:'Interrompida',missed:'Perdida',canceled:'Cancelada',recording:'Processo de gravação ativo'};
const safe=escapeHTML;
const source=i=>pilotSlots.includes(i)?sources.find(s=>s.id===bindings.find(b=>b.slot===i)?.source_id):undefined;
const active=i=>history.find(r=>r.source_id===source(i)?.id&&r.status==='recording');
async function api(path,data){
 const r=await fetch('/api/'+path,{method:data===undefined?'GET':'POST',headers:data===undefined?{}:{'Content-Type':'application/json'},body:data===undefined?undefined:JSON.stringify(data),signal:AbortSignal.timeout(35000)});
 if(!r.headers.get('content-type')?.includes('application/json'))throw Error('Agente local não encontrado. Inicie INICIAR_INGEST.bat.');
 const body=await r.json();if(!r.ok)throw Error(body.error||'Falha no agente');return body;
}
const duration=seconds=>[Math.floor(seconds/3600),Math.floor(seconds/60)%60,seconds%60]
 .map(value=>String(value).padStart(2,'0')).join(':');
const fileSize=bytes=>bytes==null?'—':bytes>=1024**2?(bytes/1024**2).toFixed(1)+' MB':Math.ceil(bytes/1024)+' KB';
function clock(r){return r.status==='recording'
 ? '<time data-started="'+safe(r.started_at)+'">'+duration(r.duration_seconds)+'</time>'
 : duration(r.duration_seconds);}
function updateClocks(){
 for(const timer of document.querySelectorAll('[data-started]')){
  timer.textContent=duration(Math.max(0,Math.floor((Date.now()-Date.parse(timer.dataset.started))/1000)));
 }
}
function status(){
 document.querySelector('.side-pill').textContent=online?'Agente local conectado · '+(health.ffmpeg?'FFmpeg disponível':'FFmpeg ausente'):'Agente local indisponível';
 document.querySelector('.mode-description').textContent=online?'Operação local · REC e STOP controlam o FFmpeg.':'Operação local · aguardando conexão com o agente.';
 const canRecord=online&&health.ffmpeg&&pilotSlots.some(i=>source(i)&&!active(i));
 const canStop=online&&pilotSlots.some(active);
 for(const button of document.querySelectorAll('[onclick="chooseRecord()"],[onclick="recordAll()"]'))button.disabled=pending||!canRecord;
 for(const button of document.querySelectorAll('[onclick="stopAll()"]'))button.disabled=pending||!canStop;
 document.querySelector('.system-list').textContent=online?'API online · '+(health.ffmpeg?'FFmpeg disponível':'FFmpeg ausente'):'API indisponível';
 const stats=document.querySelectorAll('.stats .stat');
 stats[0].querySelector('.stat-number').textContent=online?pilotSlots.filter(source).length:'—';stats[0].querySelector('.stat-sub').textContent='Fontes vinculadas ao agente';
 stats[1].querySelector('.stat-sub').textContent=online?'Processos informados pelo agente':'Estado desconhecido';
 stats[2].querySelector('.stat-sub').textContent='Banco do agente local';
 stats[3].querySelector('.stat-number').textContent=online&&health.disk_free_bytes!=null?(health.disk_free_bytes/1024**3).toFixed(1)+' GB':'—';stats[3].querySelector('.stat-sub').textContent=online?'Espaço livre no computador':'Agente indisponível';
 $('stat-rec').textContent=online?history.filter(r=>r.status==='recording').length:'—';
 $('stat-agenda').textContent=online?records.filter(r=>r.status==='scheduled').length:'—';
 $('local-history-count').textContent=online?history.length:'—';
 $('local-error-count').textContent=online?history.filter(r=>['failed','interrupted'].includes(r.status)).length:'—';
 $('schedule-form').querySelector('button[type="submit"]').disabled=pending||!online||!pilotSlots.some(source);
 const input=$('input-device');
 for (const option of input.options) {
  const signal = source(Number(option.value.slice(-1)) - 1);
  option.disabled = !signal;
  option.textContent = signal ? option.value + ' · ' + signal.name : option.value + ' · sem fonte';
 }
 for (const button of document.querySelectorAll('[data-config-slot]')) {
  const slot = Number(button.dataset.configSlot);
  button.disabled = !online || pending;
  button.textContent = 'Canal ' + (slot + 1) + ' · ' + (source(slot)?.name || 'Vincular fonte');
 }
 if(!input.selectedOptions[0]||input.selectedOptions[0].disabled){
  input.selectedIndex=Array.from(input.options).findIndex(option=>!option.disabled);
 }
}
channelCard=function(i){
 const s=source(i),r=active(i),pilot=pilotSlots.includes(i);
 const state=!pilot?'Não integrado':!online?'Agente indisponível':!s?'Sem fonte vinculada':r?'Processo ativo':channelAlert[i]?'Falha na última gravação':'Standby';
 return `<article class="channel local-channel"><div class="channel-head">
  <strong>Canal ${i+1} · ${safe(s?.name||NAMES[i].split(' – ')[1])}</strong><span class="signal">${safe((s?.protocol||FEEDS[i]).toUpperCase())}</span>
 </div><div class="channel-meter">
  <span class="rec-state ${r&&online?'recording':''}"><span class="rec-dot"></span>${state}</span>
  <strong class="capture-clock">${r&&online?clock(r):'—'}</strong>
 </div><div class="channel-controls"><small>${pilot?(s?.preview_path?'Preview local':'Preview indisponível'):'Fora do piloto'}</small>
  <div class="channel-btns">${pilot?`<button class="mini-control" data-capture="${i}" data-recording="${Boolean(r)}" ${!online||pending||!s||(!r&&!health.ffmpeg)?'disabled':''} onclick="toggleRecord(${i})" aria-label="${r?'Parar':'Gravar'} canal ${i+1}">${r?'■ STOP':'● REC'}</button>
  <button class="mini-control" onclick="channelDetails(${i})" aria-label="Configurar canal ${i+1}" ${!online?'disabled':''}>⚙</button>`:''}</div>
 </div></article>`;
};
showNotice=()=>openModal('Integração local','Comandos reais no agente local. Preview, recorrência, SDI e acesso remoto ainda indisponíveis. O indicador REC confirma o processo FFmpeg; valide o arquivo gerado.');
async function action(fn){if(!online||pending)return;pending=true;render();try{await fn();}catch(e){toast(e.message);}finally{await refresh();pending=false;render();}}
toggleRecord=i=>action(async()=>{const s=source(i),r=active(i);if(!s)throw Error('Configure uma fonte primeiro.');const result=await api(r?'recordings/'+r.id+'/stop':'recordings/start',r?{}:{source_id:s.id,title:s.name});toast(!r?'FFmpeg iniciado.':result.status==='completed'?'Gravação finalizada.':'Gravação encerrada com falha. Confira o histórico.');});
recordAll=()=>action(async()=>{const errors=[];for(const i of pilotSlots){const s=source(i);if(s&&!active(i)){try{await api('recordings/start',{source_id:s.id,title:s.name});}catch(e){errors.push('Canal '+(i+1)+': '+e.message);}}}toast(errors.length?errors.join(' · '):'Comandos enviados às fontes configuradas.');});
stopAll=()=>action(async()=>{const errors=[];for(const r of pilotSlots.map(active).filter(Boolean)){try{const res=await api('recordings/'+r.id+'/stop',{});if(res.status!=='completed')errors.push('Falha ao finalizar '+r.source_name);}catch(e){errors.push(e.message);}}toast(errors.length?errors.join(' · '):'Paradas enviadas ao agente.');});
chooseRecord=()=>{if(!online)return toast('Inicie o agente local.');openModal('Gravação no computador local',pilotSlots.filter(i=>source(i)&&!active(i)).map(i=>`<button class="btn" onclick="closeModal();toggleRecord(${i})">Canal ${i+1}: ${safe(source(i)?.name||'Sem fonte')}</button>`).join(''),true);};
channelDetails=i=>{
 if(!pilotSlots.includes(i)||!online)return;
 const options=list=>list.map(s=>`<option value="${safe(s.id)}">${safe(s.name)} · ${safe(s.protocol.toUpperCase())}</option>`).join('');
 const ids=JSON.parse(localStorage.getItem('recent-source-ids')||'[]');
 const recent=ids.map(id=>sources.find(s=>s.id===id)).filter(Boolean);
 openModal('Fonte do canal '+(i+1),`<form id="bind-form"><label>Fonte cadastrada<select name="existing"><option value="">Escolha uma fonte</option>${options(sources)}</select></label><button class="btn primary">Usar fonte cadastrada</button></form><details ${sources.length?'':'open'}><summary>Cadastrar nova fonte</summary><form id="new-source"><label>Nome<input name="name" required maxlength="100"></label><label>Protocolo<select name="protocol"><option>rtmp</option><option>rtmps</option><option>srt</option></select></label><label>Endereços recentes<select name="recent"><option value="">Digitar URL</option>${options(recent)}</select></label><button type="button" class="btn small" id="clear-recent">Limpar histórico</button><label>URL<input name="url" type="password" autocomplete="off" required></label><button class="btn primary">Cadastrar e usar</button></form></details><p id="bind-error" role="alert"></p>`,true);
 const saved=$('bind-form'),form=$('new-source');
 saved.existing.value=source(i)?.id||'';
 form.recent.onchange=()=>{const item=sources.find(s=>s.id===form.recent.value);form.url.disabled=!!item;if(item)form.protocol.value=item.protocol;};
 $('clear-recent').onclick=()=>{ids.length=0;localStorage.removeItem('recent-source-ids');form.recent.length=1;form.recent.onchange();};
 saved.onsubmit=form.onsubmit=async e=>{
  e.preventDefault();const button=e.submitter;button.disabled=true;
  try{
   const id=e.target===saved?saved.existing.value:(await api('sources',{name:form.elements.namedItem('name').value,protocol:form.protocol.value,url:form.url.value,reuse_source_id:form.recent.value})).id;
   if(!id)throw Error('Selecione uma fonte.');
   await api('channels',{slot:i,source_id:id});
   localStorage.setItem('recent-source-ids',JSON.stringify([id,...ids.filter(v=>v!==id)].slice(0,30)));
   closeModal();await refresh();
  }catch(err){$('bind-error').textContent=err.message;}finally{button.disabled=false;}
 };
};
schedEvents=()=>records.map((r,index)=>({...r,index,demo:false}));
renderRecords=()=>{$('records').innerHTML=records.map((r,i)=>`<tr><td>${safe(r.program)}</td><td>${safe(r.date)}</td><td>${safe(r.start)}–${safe(r.end)}</td><td>${safe(r.source_name)}</td><td>MP4</td><td>${safe(label[r.status]||r.status)}</td><td><button class="btn small" onclick="details(${i})">Detalhes</button>${r.status==='scheduled'?`<button class="btn small" onclick="removeRecord(${i})">Cancelar</button>`:''}</td></tr>`).join('')||'<tr><td colspan="7">Nenhum agendamento no agente.</td></tr>';$('stat-agenda').textContent=records.filter(r=>r.status==='scheduled').length;$('reports-count').textContent=records.length;};
details=i=>{const r=records[i];if(r)openModal(r.program,`${r.source_name}\n${new Date(r.begins_at).toLocaleString('pt-BR')} até ${new Date(r.ends_at).toLocaleString('pt-BR')}\n${label[r.status]||r.status}\nSalvo no agente local.`);};
removeRecord=i=>action(async()=>{const r=records[i];if(r&&confirm('Cancelar '+r.program+'?')){await api('jobs/'+r.id+'/cancel',{});toast('Agendamento cancelado.');}});
const table=(columns,rows,empty)=>`<div class="table-wrap"><table class="data-table">
 <thead><tr>${columns.map(name=>`<th scope="col">${name}</th>`).join('')}</tr></thead>
 <tbody>${rows||`<tr><td colspan="${columns.length}">${empty}</td></tr>`}</tbody></table></div>`;
const download=r=>r.downloadable?`<a class="btn small" href="/api/recordings/${encodeURIComponent(r.id)}/file" download>Baixar MP4</a>`:'—';
const recordingRow=r=>`<tr><td><b>${safe(r.title)}</b><small>${safe(r.source_name)}</small></td>
 <td>${safe(new Date(r.started_at).toLocaleString('pt-BR'))}</td><td>${clock(r)}</td>
 <td>${safe(label[r.status]||r.status)}<small>${safe(r.error||'')}</small></td><td>${download(r)}</td></tr>`;
renderRecent=()=>{
 const headers=['Gravação','Início','Tempo decorrido','Estado','Arquivo'];
 const empty=online?'Nenhuma gravação no agente.':'Agente local indisponível.';
 $('recent-recordings').innerHTML=table(headers,history.slice(0,6).map(recordingRow).join(''),empty);
 const running=history.filter(r=>r.status==='recording'),finished=history.filter(r=>r.status!=='recording');
 $('all-recordings').innerHTML=(running.length?'<h3>Gravando agora</h3>'+table(headers,running.map(recordingRow).join(''),empty):'')+'<h3>Sessões encerradas</h3>'+table(headers,finished.map(recordingRow).join(''),empty);
 const files=history.filter(r=>r.file_size_bytes>0).map(r=>`<tr>
  <td><b>${safe(r.file_name)}</b><small>${safe(r.title)}</small></td><td>${fileSize(r.file_size_bytes)}</td>
  <td>${safe(label[r.status]||r.status)}</td><td>${download(r)}</td></tr>`).join('');
 $('page-files').querySelector('article').innerHTML=table(['Arquivo','Tamanho','Estado','Download'],files,online?'Nenhum arquivo encontrado na pasta de gravações.':empty);
};
window.submitLocalSchedule=()=>action(async()=>{const i=Number($('input-device').value.match(/[1-4]/)?.[0])-1,s=source(i);if(!s)throw Error('Configure a fonte desse canal pelo botão ⚙.');const start=new Date($('date').value+'T'+$('start').value),end=new Date($('date').value+'T'+$('end').value);if(!Number.isFinite(+start)||!Number.isFinite(+end)||end<=start)throw Error('Confira a data e os horários.');await api('jobs',{program:$('program').value,source_id:s.id,calendar_event_id:selectedEvent||null,begins_at:start.toISOString(),ends_at:end.toISOString(),pre_seconds:Number($('pre').value)*60,post_seconds:Number($('post').value)*60});selectedEvent='';selectedDate=$('date').value;view('list');toast('Agendamento salvo no agente. Mantenha o computador e o serviço ligados.');});
// Opções futuras podem ser exploradas, sem promessa de execução pelo agente.
const fixed={repeat:'Não repetir',codec:'Copiar sem reencodar',format:'MP4',resolution:'Igual à origem',fps:'Igual à origem',bitrate:'Automático',audio:'AAC estéreo',channels:'Estéreo 2.0',profile:'Padrão Ingest',backup:'Nenhuma',split:'Não dividir',secondary:'Desativada',retention:'Manter até exclusão manual',notify:'Desativadas'};
for(const [id,value] of Object.entries(fixed)){const node=$(id);node.value=value;node.title='Em desenvolvimento: esta escolha não será aplicada pelo agente.';const note=document.createElement('small');node.disabled=true;note.textContent='Em desenvolvimento · não aplicado';node.parentElement.append(note);}
for(const id of ['signal-name','signal-url','feed','loss','multisignal','destination','filename','emails','requester','notes','category','priority']){$(id).disabled=true;$(id).title='Em desenvolvimento: não aplicado. Fontes reais são configuradas nos canais.';const note=document.createElement('small');note.textContent='Em desenvolvimento · não aplicado';$(id).parentElement.append(note);}
$('input-device').replaceChildren(...pilotSlots.map(i=>new Option('Canal '+(i+1),'Canal '+(i+1))));
document.querySelectorAll('#signal-chips button').forEach(b=>{b.disabled=true;b.title='A gravação usa o protocolo da fonte vinculada.';});
document.querySelector('#schedule-form .foot small').textContent='Agendamento real no agente · MP4, vídeo copiado e áudio AAC 128 kb/s; sem conversão de resolução ou frame rate.';
const descriptions={
 operation:'Acompanhe e controle os dois canais do piloto.',
 signals:'Vincule fontes RTMP, RTMPS ou SRT aos canais 1 e 2.',
 list:'Consulte os agendamentos salvos no agente local.',
 recordings:'Acompanhe o estado e o tempo decorrido das sessões.',
 settings:'Configuração do agente neste computador.',
 reports:'Indicadores do banco de dados local.',
};
for(const [id,description] of Object.entries(descriptions))$('page-'+id).querySelector('.page-head p').textContent=description;
const settings = $('page-settings');
const shortcut = settings.querySelector('button[onclick*="signals"]');
const sourceControls = shortcut.parentElement;
shortcut.remove();
for (const slot of pilotSlots) {
 const button = document.createElement('button');
 button.type = 'button';
 button.className = 'btn';
 button.dataset.configSlot = slot;
 button.onclick = () => channelDetails(slot);
 sourceControls.append(button);
}
settings.querySelector('.card h2:last-of-type').textContent = 'Atualizações no Windows';
settings.querySelectorAll('.status-row').forEach(row => row.remove());
settings.querySelector('.note-text').textContent = 'Na primeira vez, execute ATUALIZAR_E_ABRIR_INGEST.bat. Depois, use o atalho Ingest Control na área de trabalho. Finalize as gravações e feche o agente antes de atualizar.';
$('page-recordings').querySelector('button').textContent='● Gravar agora';
$('page-recordings').querySelector('.box-head').textContent='Histórico do agente';
document.querySelector('.recents-subtitle').textContent='Últimas sessões registradas pelo agente local.';
$('page-reports').querySelectorAll('.status-tile')[1].innerHTML='<span class="note-text">GRAVAÇÕES NO AGENTE</span><div class="value" id="local-history-count">—</div>';
$('page-reports').querySelectorAll('.status-tile')[2].innerHTML='<span class="note-text">FALHAS REGISTRADAS</span><div class="value" id="local-error-count">—</div>';
$('page-reports').querySelector('.badge').textContent='Banco do agente';
function refresh(){
 if(refreshing)return refreshing;
 refreshing=(async()=>{
  try{
   const result=await api('dashboard');
   const stable=items=>items.map(({duration_seconds,...rest})=>rest);
   const changed=!online||JSON.stringify([health,sources,bindings,stable(history)])!==
    JSON.stringify([result.health,result.sources,result.channels,stable(result.recordings)]);
   const jobsChanged=JSON.stringify(records.map(({id,status})=>({id,status})))!==
    JSON.stringify(result.jobs.map(({id,status})=>({id,status})));
   ({health,sources,channels:bindings,recordings:history}=result);
   records=result.jobs.map(v=>{
    const d=new Date(v.begins_at),e=new Date(v.ends_at);
    return {...v,date:localDate(d),endDate:localDate(e),start:d.toTimeString().slice(0,5),end:e.toTimeString().slice(0,5),
     channel:pilotSlots.find(i=>source(i)?.id===v.source_id)??-1};
   });
   online=true;
   recording=NAMES.map((_,i)=>!!active(i));
   channelAlert=NAMES.map((_,i)=>{const last=history.find(r=>r.source_id===source(i)?.id);return ['failed','interrupted'].includes(last?.status);});
   if(changed||jobsChanged)render();
  }catch(e){
   if(online||firstRead){
    online=false;
    health={};sources=[];bindings=[];history=[];records=[];
    recording=NAMES.map(()=>false);channelAlert=NAMES.map(()=>false);
    render();
   }
  }finally{firstRead=false;refreshing=null;}
 })();
 return refreshing;
}
const signalGrid = $('signals-channels');
signalGrid.closest('.card').querySelector('.badge').remove();
const signalCards = [];
const dashboardCards = [];
$('dashboard-channels').replaceChildren();
signalGrid.replaceChildren();

window.renderLocalSignalCards = function () {
 for(const [grid,cards,page] of [[signalGrid,signalCards,'signals'],[$('dashboard-channels'),dashboardCards,'dashboard']]){
 for (const [slot] of NAMES.entries()) {
  const template = document.createElement('template');
  template.innerHTML = channelCard(slot);
  const nextCard = template.content.firstElementChild;
  let card = cards[slot];
  if (!card) {
   card = nextCard;
   cards[slot] = card;
   grid.append(card);
  } else {
   for (const selector of ['.channel-head', '.channel-meter', '.channel-controls']) {
    const current = card.querySelector(selector);
    const next = nextCard.querySelector(selector);
    if (!current.isEqualNode(next)) current.replaceWith(next);
   }
  }

  const signal = source(slot);
  const path = signal?.preview_path;
  const player = card.querySelector('.channel-preview');
  const visible=page==='signals'||filter==='all'||filter==='rec'&&recording[slot]||filter==='idle'&&!recording[slot]||filter==='alert'&&channelAlert[slot];
  card.style.display=visible?'':'none';
  const showPreview = visible && currentPage === page && online && ['live/test', 'live/teste', 'live/stream'].includes(path);
  if (!showPreview || (player && player.dataset.path !== path)) player?.remove();
  card.classList.toggle('has-preview', showPreview);
  if (!showPreview) continue;
  const title = 'Preview ao vivo — Canal ' + (slot + 1) + ' · ' + signal.name;
  if (player?.dataset.path === path) {
   player.title = title;
   continue;
  }
  const frame = document.createElement('iframe');
  frame.className = 'channel-preview';
  frame.dataset.path = path;
  frame.title = title;
  frame.src = 'http://127.0.0.1:8889/' + path + '?muted=true';
  frame.allow = 'autoplay; fullscreen';
  frame.allowFullscreen = true;
  card.querySelector('.channel-meter').before(frame);
 }
 }
};
let selectedEvent='',token='',expires=0;
const calendar='c_18847iu0dupakig6grob3boj1cf22@resource.calendar.google.com';
const calendarBox=document.createElement('section');
calendarBox.className='card';
calendarBox.innerHTML='<h2>Reservas do Estúdio SP</h2><button class="btn" id="load-reservations">Consultar próximos eventos</button><select aria-label="Reserva do Google" id="google-reservation"><option value="">Selecione uma reserva</option></select><details><summary>Criar evento e convidar equipe</summary><form id="invite-form"><label>Programa<input name="title" required></label><label>Início<input type="datetime-local" name="begin" required></label><label>Término<input type="datetime-local" name="end" required></label><label>E-mails dos convidados<input type="email" multiple name="guests" placeholder="Separe os e-mails por vírgula"></label><button class="btn primary">Criar evento e enviar convites</button></form></details><p id="calendar-status" role="status"></p>';
$('studio-title').closest('.secthead').after(calendarBox);
const config=document.createElement('label');
config.textContent='Google Agenda · ID do cliente OAuth para Web';
const client=document.createElement('input');
client.value=localStorage.getItem('google-calendar-client')||'';
client.onchange=()=>{localStorage.setItem('google-calendar-client',client.value.trim());token='';};
config.append(client);settings.querySelector('.card').append(config);
let sdk,events=[];
async function authorize(){
 if(token&&Date.now()<expires)return;
 if(!client.value.trim())throw Error('Em Configurações, informe o ID do cliente OAuth da emissora.');
 if(!window.google?.accounts?.oauth2){
  if(!sdk)sdk=new Promise((resolve,reject)=>{const script=document.createElement('script');script.src='https://accounts.google.com/gsi/client';script.onload=resolve;script.onerror=()=>{sdk=null;reject(Error('Falha ao conectar ao Google.'));};document.head.append(script);});
  await sdk;
 }
 const auth=await new Promise((resolve,reject)=>google.accounts.oauth2.initTokenClient({client_id:client.value.trim(),scope:'https://www.googleapis.com/auth/calendar.events',callback:r=>r.error?reject(Error(r.error)):resolve(r),error_callback:()=>reject(Error('Autorização interrompida.'))}).requestAccessToken());
 token=auth.access_token;expires=Date.now()+(auth.expires_in-60)*1000;
}
async function calendarRequest(query,body){
 const res=await fetch('https://www.googleapis.com/calendar/v3/calendars/'+encodeURIComponent(calendar)+'/events?'+query,{method:body?'POST':'GET',headers:{Authorization:'Bearer '+token,...(body?{'Content-Type':'application/json'}:{})},body:body?JSON.stringify(body):undefined});
 if(!res.ok){if(res.status===401)token='';throw Error('Google Agenda ('+res.status+'). Confira o acesso ao calendário do estúdio.');}
 return res.json();
}
const picker=$('google-reservation'),message=$('calendar-status');
function fillReservation(event){
 selectedEvent='';
 if(!event)return;
 const a=new Date(event.start.dateTime),b=new Date(event.end.dateTime);
 if(localDate(a)!==localDate(b)){message.textContent='A agenda de gravação aceita início e fim no mesmo dia.';return;}
 selectedEvent=event.id;
 $('program').value=event.summary||'Reserva do estúdio';$('date').value=localDate(a);$('start').value=a.toTimeString().slice(0,5);$('end').value=b.toTimeString().slice(0,5);
 message.textContent='Reserva selecionada. Confira o canal e confirme no formulário de gravação.';$('input-device').focus();
}
picker.onchange=()=>fillReservation(events.find(v=>v.id===picker.value));
$('load-reservations').onclick=async e=>{
 const button=e.currentTarget;button.disabled=true;
 try{await authorize();const q=new URLSearchParams({timeMin:new Date().toISOString(),timeMax:new Date(Date.now()+30*86400000).toISOString(),singleEvents:'true',orderBy:'startTime'});const list=[];let page;
 do{page=await calendarRequest(q);list.push(...(page.items||[]));if(page.nextPageToken)q.set('pageToken',page.nextPageToken);}while(page.nextPageToken);
 events=list.filter(v=>v.start?.dateTime&&v.end?.dateTime);selectedEvent='';picker.replaceChildren(new Option('Selecione uma reserva',''),...events.map(v=>new Option(new Date(v.start.dateTime).toLocaleString('pt-BR')+' · '+(v.summary||'Reservado'),v.id)));message.textContent=events.length+' reservas nos próximos 30 dias.';
 }catch(err){message.textContent=err.message;}finally{button.disabled=false;}
};
$('invite-form').onsubmit=async e=>{
 e.preventDefault();const form=e.target,button=e.submitter;button.disabled=true;
 try{const data=new FormData(form),start=new Date(data.get('begin')),end=new Date(data.get('end'));if(end<=start)throw Error('Confira o término do evento.');
 await authorize();const created=await calendarRequest('sendUpdates=all',{summary:data.get('title'),start:{dateTime:start.toISOString()},end:{dateTime:end.toISOString()},attendees:String(data.get('guests')).split(',').map(v=>v.trim()).filter(Boolean).map(email=>({email}))});
 events.push(created);picker.add(new Option(created.summary,created.id));picker.value=created.id;form.reset();fillReservation(created);
 }catch(err){message.textContent=err.message;}finally{button.disabled=false;}
};
const oldRender=render;render=()=>{
 const button=document.activeElement;
 const key=button?.dataset.capture;
 const page=button?.closest('.page');
 oldRender();status();updateClocks();
 if(key!==undefined)page?.querySelector('[data-capture="'+key+'"]')?.focus({preventScroll:true});
};
render();refresh();setInterval(refresh,2500);setInterval(updateClocks,1000);
})();

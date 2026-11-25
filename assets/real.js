const el=id=>document.getElementById(id);
let sources=[],jobs=[],recordings=[];
const esc=s=>String(s??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const date=s=>s?new Date(s).toLocaleString("pt-BR"):"—";
function notify(message,error=false){const n=el("message");n.hidden=false;n.textContent=message;n.className="notice"+(error?" error":"");}
async function api(path,data){const options=data===undefined?{}:{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(data)};const response=await fetch("/api"+path,options);const body=await response.json();if(!response.ok)throw new Error(body.error||"Erro "+response.status);return body;}
function fillSelect(id){const select=el(id),value=select.value;select.replaceChildren(new Option("Selecione um sinal",""));for(const s of sources)select.add(new Option(s.name+" ("+s.protocol.toUpperCase()+")",s.id));select.value=sources.some(s=>s.id===value)?value:"";}
function render(){
  el("count-sources").textContent=sources.length;
  el("count-jobs").textContent=jobs.filter(j=>j.status==="scheduled").length;
  fillSelect("job-source");fillSelect("manual-source");
  el("sources").innerHTML=sources.length?sources.map(s=>'<div class="item"><div><strong>'+esc(s.name)+'</strong><small>'+esc(s.protocol.toUpperCase())+' · ID '+esc(s.id.slice(0,8))+'</small></div><span class="status">Cadastrado</span></div>').join(""):"Nenhum sinal cadastrado.";
  const active=recordings.filter(r=>r.status==="recording");
  el("active").innerHTML=active.length?active.map(r=>'<div class="item"><div><strong>'+esc(r.title)+'</strong><small>'+esc(r.source_name)+' · desde '+esc(date(r.started_at))+'</small></div><button class="stop" data-stop="'+esc(r.id)+'">■ Parar</button></div>').join(""):"Nenhuma sessão ativa.";
  el("jobs").innerHTML=jobs.length?jobs.map(j=>'<tr><td><strong>'+esc(j.program)+'</strong><small>'+esc(j.source_name)+'</small></td><td>'+esc(date(j.begins_at))+'</td><td>'+esc(date(j.ends_at))+'</td><td><span class="status '+esc(j.status)+'">'+esc(j.status)+'</span></td><td>'+(j.status==="scheduled"?'<button class="outline" data-cancel="'+esc(j.id)+'">Cancelar</button>':"—")+'</td></tr>').join(""):'<tr><td colspan="5">Nenhum agendamento.</td></tr>';
  el("history").innerHTML=recordings.length?recordings.map(r=>'<tr><td><strong>'+esc(r.title)+'</strong><small>'+esc(r.file_path)+'</small></td><td>'+esc(r.source_name)+'</td><td>'+esc(date(r.started_at))+'</td><td><span class="status '+esc(r.status)+'">'+esc(r.status)+'</span>'+(r.error?'<small>'+esc(r.error)+'</small>':"")+'</td></tr>').join(""):'<tr><td colspan="4">Nenhuma gravação.</td></tr>';
}
async function refresh(){
  try {
    const health=await api("/health");
    el("service").textContent="● Serviço online";el("service").className="chip good";
    el("ffmpeg").textContent=health.ffmpeg?"● FFmpeg disponível":"● FFmpeg não encontrado";
    el("ffmpeg").className="chip "+(health.ffmpeg?"good":"bad");
    el("count-active").textContent=health.active;
    el("disk").textContent=health.disk_free_bytes==null?"—":(health.disk_free_bytes/(1024**3)).toFixed(1)+" GB";
    el("location").textContent=health.data_folder;
    [sources,jobs,recordings]=await Promise.all([api("/sources"),api("/jobs"),api("/recordings")]);
    render();
  }catch(e){el("service").textContent="● Serviço indisponível";el("service").className="chip bad";notify("Falha ao consultar o agente: "+e.message,true);}
}
function formData(form){return Object.fromEntries(new FormData(form));}
async function submit(form,action){const button=form.querySelector("button[type=submit]");button.disabled=true;try{await action(formData(form));notify("Operação realizada no agente local.");form.reset();await refresh();}catch(e){notify(e.message,true);}finally{button.disabled=false;}}
el("source-form").addEventListener("submit",e=>{e.preventDefault();submit(e.currentTarget,v=>api("/sources",v));});
el("manual-form").addEventListener("submit",e=>{e.preventDefault();submit(e.currentTarget,v=>api("/recordings/start",v));});
el("job-form").addEventListener("submit",e=>{e.preventDefault();submit(e.currentTarget,v=>{
  if(!v.begins_at||!v.ends_at)throw new Error("Informe início e término.");
  return api("/jobs",{program:v.program,source_id:v.source_id,begins_at:new Date(v.begins_at).toISOString(),ends_at:new Date(v.ends_at).toISOString(),pre_seconds:Number(v.pre)*60,post_seconds:Number(v.post)*60});
});});
document.addEventListener("click",async e=>{
  const stop=e.target.closest("[data-stop]"),cancel=e.target.closest("[data-cancel]");
  if(!stop&&!cancel)return;
  const id=(stop||cancel).dataset[stop?"stop":"cancel"];
  if(!confirm(stop?"Encerrar esta gravação real?":"Cancelar este agendamento?"))return;
  try{await api(stop?"/recordings/"+id+"/stop":"/jobs/"+id+"/cancel",{});notify("Operação concluída.");await refresh();}catch(err){notify(err.message,true);}
});
el("refresh").addEventListener("click",refresh);
refresh();
setInterval(refresh,5000);

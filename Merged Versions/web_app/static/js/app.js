let DATA = {patients:[],metadata:{}};
let SURVEY_BY_PID = {};
let CLUSTER_SURVEY_TRAJECTORIES = {};
const CLUSTER_META = {
  0:{name:"Autonomically flexible / resilient",insight:"High HRV driven by strong parasympathetic activity, combined with sympathetic responsiveness — a well-regulated autonomic nervous system."},
  1:{name:"Low-reactivity / fragmented sleep",insight:"Reduced overall HRV and low spectral power indicating a blunted autonomic profile. Despite adequate sleep duration, frequent night-time wake events."},
  2:{name:"Dysregulated / sleep-impaired",insight:"Reduced vagal tone with parasympathetic shift suggesting an imbalanced autonomic state. Worst sleep efficiency and highest insomnia severity."}
};
const SURVEY_TIMEPOINTS=["t0","t2w","t4w"];
const NAME_MAP={
ab60:{first:"Alice",last:"Baker",age:60},
am77:{first:"Arthur",last:"Mitchell",age:77},
av54:{first:"Anna",last:"Vasquez",age:54},
ba30:{first:"Brandon",last:"Adams",age:30},
bp16:{first:"Bella",last:"Patterson",age:16},
br74:{first:"Bernard",last:"Reynolds",age:74},
ca37:{first:"Carlos",last:"Alvarez",age:37},
dk68:{first:"Diane",last:"Kim",age:68},
ea80:{first:"Eleanor",last:"Ashford",age:80},
ej27:{first:"Ethan",last:"Jensen",age:27},
ev76:{first:"Evelyn",last:"Vargas",age:76},
ga64:{first:"Gloria",last:"Archer",age:64},
gd81:{first:"George",last:"Douglas",age:81},
gm49:{first:"Grace",last:"Miller",age:49},
gw39:{first:"Gabriel",last:"Watson",age:39},
gw57:{first:"Gerald",last:"Williams",age:57},
hk52:{first:"Helen",last:"Kim",age:52},
hp91:{first:"Harold",last:"Park",age:91},
it48:{first:"Irene",last:"Torres",age:48},
ka67:{first:"Karen",last:"Abbott",age:67},
kb24:{first:"Kyle",last:"Brooks",age:24},
kn13:{first:"Kai",last:"Nguyen",age:13},
md23:{first:"Maya",last:"Daniels",age:23},
mg25:{first:"Marcus",last:"Green",age:25},
mh40:{first:"Michelle",last:"Harris",age:40},
nd56:{first:"Nathan",last:"Davis",age:56},
pg18:{first:"Priya",last:"Gonzalez",age:18},
pm96:{first:"Patricia",last:"Morrison",age:96},
pw85:{first:"Peter",last:"Wallace",age:85},
rb86:{first:"Robert",last:"Bennett",age:86},
rw83:{first:"Ruth",last:"Walker",age:83},
ry23:{first:"Ryan",last:"Yang",age:23},
sc27:{first:"Sarah",last:"Chen",age:27},
sh29:{first:"Samuel",last:"Hernandez",age:29},
sm34:{first:"Sophia",last:"Martinez",age:34},
sp33:{first:"Sean",last:"Park",age:33},
te43:{first:"Thomas",last:"Evans",age:43},
ub12:{first:"Uma",last:"Benson",age:12},
us73:{first:"Ursula",last:"Santos",age:73},
uz94:{first:"Ulysses",last:"Zimmerman",age:94},
vc10:{first:"Valentina",last:"Cruz",age:10},
vh17:{first:"Victor",last:"Huang",age:17},
vs14:{first:"Vivian",last:"Sanchez",age:14},
wc58:{first:"William",last:"Chen",age:58},
we59:{first:"Wendy",last:"Edwards",age:59},
xp20:{first:"Xavier",last:"Phillips",age:20},
xw99:{first:"Xena",last:"Walsh",age:99},
ya71:{first:"Yolanda",last:"Archer",age:71},
zk41:{first:"Zachary",last:"Kim",age:41}
};
function pName(pid){const n=NAME_MAP[pid];return n?n.first+" "+n.last:pid}
function pNameFull(pid){const n=NAME_MAP[pid];return n?n.first+" "+n.last+", "+n.age:pid}
function pInitials(pid){const n=NAME_MAP[pid];return n?(n.first[0]+n.last[0]):pid.slice(0,2).toUpperCase()}
const STATE={sortKey:"status_order",sortDir:"asc",selected:null};
const DEMO_PATIENTS=[
  {id:"demo-pat-001",displayName:"Jordan A.",initials:"JA",nextReview:"2026-04-15"},
  {id:"demo-pat-002",displayName:"Morgan B.",initials:"MB",nextReview:"2026-04-22"},
  {id:"demo-pat-003",displayName:"Riley C.",initials:"RC",nextReview:"2026-05-01"}
];
const CODES_KEY="signalcare_demo_access_codes";
const UPLOADS_KEY="signalcare_demo_uploads";
const INFERENCES_KEY="signalcare_demo_ai_inferences";
const SESSION_KEY="signalcare_patient_session";

/* ── Utilities ── */
function badge(n){return n?`<span class="badge red">${n}</span>`:`<span class="badge zero">0</span>`}
function statusPill(s){return`<span class="status ${s}">${s[0].toUpperCase()+s.slice(1)}</span>`}
function dot(s){return`<span class="dot ${s}"></span>`}
function esc(s){return String(s).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;")}
function chips(t,k){const p=String(t||"").split(";").map(s=>s.trim()).filter(Boolean);if(!p.length)return"";return`<div class="chip-wrap">${p.map(x=>`<span class="chip ${k}">${esc(x)}</span>`).join("")}</div>`}
function fmt(v,d){if(d===undefined)d=1;const n=Number(v);return Number.isFinite(n)?n.toFixed(d):"N/A"}
function getCluster(p){const n=Number(p.cluster);return Number.isInteger(n)&&n>=0&&n<=2?n:0}
function clusterMeta(i){return CLUSTER_META[i]||CLUSTER_META[0]}
function safeParse(j,f){try{const v=JSON.parse(j);return Array.isArray(v)?v:f}catch{return f}}
function ago(iso){const t=new Date(iso).getTime();if(isNaN(t))return"";const d=Date.now()-t;if(d<60000)return"Just now";if(d<3600000)return Math.floor(d/60000)+"m ago";if(d<86400000)return Math.floor(d/3600000)+"h ago";return Math.floor(d/86400000)+"d ago"}

/* ── Navigation ── */
function showPage(id){
  document.querySelectorAll(".page").forEach(p=>p.classList.remove("active"));
  document.getElementById("page-"+id).classList.add("active");
  document.querySelectorAll(".sidebar nav a").forEach(a=>a.classList.remove("active"));
  const link=document.querySelector(`.sidebar nav a[data-page="${id}"]`);
  if(link)link.classList.add("active");
  const titles={dashboard:"Dashboard",biosignal:"BioSignal Monitor",patients:"Patients",access:"Patient Access",portal:"Patient Portal"};
  document.getElementById("top-bar-title").textContent=titles[id]||id;
  closeSidebar();
  if(id==="dashboard")renderTriage();
  if(id==="patients")renderPatientsDirectory();
  if(id==="access"){renderAccessCodes();populateCodePatientSelect()}
  if(id==="portal")checkPortalSession();
}
function toggleSidebar(){document.getElementById("sidebar").classList.toggle("open");document.getElementById("sidebar-overlay").classList.toggle("show")}
function closeSidebar(){document.getElementById("sidebar").classList.remove("open");document.getElementById("sidebar-overlay").classList.remove("show")}
document.getElementById("sidebar-overlay").addEventListener("click",closeSidebar);

/* ── Triage ── */
function renderTriage(){
  const uploads=safeParse(localStorage.getItem(UPLOADS_KEY)||"[]",[]).filter(u=>!u.reviewedAt);
  document.getElementById("triage-upload-count").textContent=uploads.length;
  const ub=document.getElementById("triage-uploads");
  if(!uploads.length){ub.innerHTML=`<div class="triage-empty">No new uploads awaiting review. When a patient uploads from the portal, the file appears here.</div>`}
  else{ub.innerHTML=uploads.map(u=>{const dp=DEMO_PATIENTS.find(x=>x.id===u.patientId);const label=dp?dp.displayName:u.patientId;return`<div class="triage-row" onclick="goToPatientDetail('${esc(u.patientId)}')"><div><div class="primary">${label}</div><div class="secondary">${esc(u.fileName)}</div></div><div class="meta">${ago(u.uploadedAt)}</div></div>`}).join("")}
  const declining=DATA.patients.filter(p=>p.status==="declining");
  document.getElementById("triage-call-count").textContent=declining.length;
  const cb=document.getElementById("triage-calls");
  if(!declining.length){cb.innerHTML=`<div class="triage-empty">No patients flagged for outreach right now.</div>`}
  else{cb.innerHTML=declining.map(p=>`<div class="triage-row" onclick="goToPatientDetail('${p.pid}')"><div><div class="primary">${pName(p.pid)}</div><div class="secondary">${p.alerts} alert${p.alerts!==1?"s":""} · Stress ${fmt(p.metrics.stress,3)}</div></div><div class="meta" style="color:#c62828;font-weight:700">Declining</div></div>`).join("")}
  const upcoming=DATA.patients.filter(p=>p.status==="stable").slice(0,5);
  document.getElementById("triage-review-count").textContent=upcoming.length;
  const rb=document.getElementById("triage-reviews");
  if(!upcoming.length){rb.innerHTML=`<div class="triage-empty">No reviews due in the current window.</div>`}
  else{rb.innerHTML=upcoming.map(p=>`<div class="triage-row" onclick="goToPatientDetail('${p.pid}')"><div><div class="primary">${pName(p.pid)}</div><div class="secondary">Stable · ${p.days} days</div></div><div class="meta">Review</div></div>`).join("")}
  document.getElementById("triage-review-count").textContent="0";
  document.getElementById("stat-total").textContent=DATA.patients.length;
  document.getElementById("stat-declining").textContent=DATA.patients.filter(p=>p.status==="declining").length;
  document.getElementById("stat-stable").textContent=DATA.patients.filter(p=>p.status==="stable").length;
  document.getElementById("stat-improving").textContent=DATA.patients.filter(p=>p.status==="improving").length;
}

/* ── Patient Directory ── */
function goToPatientDetail(pid){showPage('biosignal');openPatient(pid)}
function renderPatientsDirectory(){
  const el=document.getElementById("patients-list");
  const sorted=[...DATA.patients].sort((a,b)=>a.status_order-b.status_order||a.pid.localeCompare(b.pid));
  el.innerHTML=sorted.map(p=>{
    const ci=getCluster(p);const cm=clusterMeta(ci);
    return`<div class="patient-card" onclick="goToPatientDetail('${p.pid}')"><div style="display:flex;align-items:center"><div class="avatar">${pInitials(p.pid)}</div><div class="info"><div class="name">${dot(p.status)} ${pName(p.pid)}</div><div class="review">${p.pid} · Age ${NAME_MAP[p.pid]?.age||"—"} · ${esc(cm.name)} · ${p.days} days</div></div></div><div style="display:flex;align-items:center">${p.alerts?`<span class="upload-pill" style="background:#fde8e8;color:#c62828">${p.alerts} alert${p.alerts>1?"s":""}</span>`:""} ${statusPill(p.status)} <span style="margin-left:8px;color:#9CA3AF">&#8250;</span></div></div>`
  }).join("");
}

/* ── Access Codes ── */
function readCodes(){return safeParse(localStorage.getItem(CODES_KEY)||"[]",[])}
function writeCodes(c){localStorage.setItem(CODES_KEY,JSON.stringify(c))}
function populateCodePatientSelect(){
  const sel=document.getElementById("code-patient");
  sel.innerHTML=DATA.patients.map(p=>`<option value="${p.pid}">${pName(p.pid)}, ${p.pid}</option>`).join("");
}
function generateCodeString(){const c="ABCDEFGHJKLMNPQRSTUVWXYZ23456789";let s="SC-";for(let i=0;i<4;i++)s+=c[Math.floor(Math.random()*c.length)];s+="-";for(let i=0;i<4;i++)s+=c[Math.floor(Math.random()*c.length)];return s}
document.getElementById("gen-code-form").addEventListener("submit",function(e){
  e.preventDefault();
  const pid=document.getElementById("code-patient").value;
  const days=Number(document.getElementById("code-days").value)||14;
  const code=generateCodeString();
  const entry={id:crypto.randomUUID(),code,patientId:pid,createdAt:new Date().toISOString(),expiresAt:new Date(Date.now()+days*864e5).toISOString(),revoked:false,redeemedAt:null};
  const codes=readCodes();writeCodes([entry,...codes]);
  const p=DEMO_PATIENTS.find(x=>x.id===pid);
  const d=document.getElementById("new-code-display");
  d.classList.remove("hidden");
  d.innerHTML=`<div class="code-display"><div class="muted" style="margin-bottom:6px;text-transform:uppercase;font-weight:700;letter-spacing:1px">New code (share securely)</div><code>${code}</code><div style="margin-top:8px"><button class="btn sm" onclick="navigator.clipboard.writeText('${code}');this.textContent='Copied!'">Copy</button></div><div class="muted" style="margin-top:8px">For ${p?p.displayName:pNameFull(pid)}. Patient enters this code in the Patient Portal.</div></div>`;
  renderAccessCodes();
});
function renderAccessCodes(){
  const codes=readCodes();
  const w=document.getElementById("codes-table-wrap");
  if(!codes.length){w.innerHTML=`<p class="muted" style="margin-top:12px">No codes yet. Generate one above.</p>`;return}
  w.innerHTML=`<table class="codes-table"><thead><tr><th>Code</th><th>Patient</th><th>Expires</th><th>Status</th><th></th></tr></thead><tbody>${codes.map(c=>{
    const p=DEMO_PATIENTS.find(x=>x.id===c.patientId);const expired=Date.now()>=new Date(c.expiresAt).getTime();
    let st="Active";if(c.revoked)st="Revoked";else if(c.redeemedAt)st="Redeemed";else if(expired)st="Expired";
    return`<tr><td class="code-mono">${c.code}</td><td>${p?p.displayName:pName(c.patientId)||c.patientId||"—"}</td><td class="muted">${new Date(c.expiresAt).toLocaleDateString()}</td><td>${st}</td><td>${!c.revoked?`<button class="btn danger sm" onclick="revokeCode('${c.id}')">Revoke</button>`:""}</td></tr>`
  }).join("")}</tbody></table>`;
}
function revokeCode(id){const codes=readCodes();writeCodes(codes.map(c=>c.id===id?{...c,revoked:true}:c));renderAccessCodes()}
function purgeAllCodes(){if(!confirm("Remove all demo access codes?"))return;writeCodes([]);renderAccessCodes();document.getElementById("new-code-display").classList.add("hidden")}

/* ── Patient Portal ── */
function checkPortalSession(){
  const raw=sessionStorage.getItem(SESSION_KEY);
  if(!raw){showPortalGate();return}
  try{const sess=JSON.parse(raw);const codes=readCodes();const entry=codes.find(c=>c.id===sess.codeId);if(!entry||entry.revoked||!entry.redeemedAt||Date.now()>=new Date(entry.expiresAt).getTime()){showPortalGate();return}showPortalDashboard(sess)}catch{showPortalGate()}
}
function showPortalGate(){document.getElementById("portal-gate").classList.remove("hidden");document.getElementById("portal-dashboard").classList.add("hidden")}
function showPortalDashboard(sess){
  document.getElementById("portal-gate").classList.add("hidden");
  document.getElementById("portal-dashboard").classList.remove("hidden");
  const p=DEMO_PATIENTS.find(x=>x.id===sess.patientId);
  const resolvedName=sess.displayName&&sess.displayName!=="Patient"?sess.displayName:p?.displayName||pName(sess.patientId);
  document.getElementById("portal-name").textContent=resolvedName;
  document.getElementById("portal-chart-info").innerHTML=`<div class="fact"><strong>Name on chart</strong><span>${resolvedName}</span></div><div class="fact"><strong>Next review</strong><span>${p?.nextReview||"—"}</span></div>`;
  renderPortalUploads(sess.patientId);
}
function renderPortalUploads(pid){
  const uploads=safeParse(localStorage.getItem(UPLOADS_KEY)||"[]",[]).filter(u=>u.patientId===pid);
  const el=document.getElementById("portal-uploads");
  if(!uploads.length){el.innerHTML=`<p class="muted">No files yet. Upload an export to share with your care team.</p>`;return}
  el.innerHTML=`<ul class="upload-history" style="list-style:none;padding:0">${uploads.map(u=>`<li><span style="font-family:monospace;font-size:12px">${esc(u.fileName)}</span><span class="muted">${ago(u.uploadedAt)}${u.reviewedAt?" · Reviewed":""}</span></li>`).join("")}</ul>`;
}
function redeemCode(){
  const input=document.getElementById("portal-code-input").value.trim().toUpperCase().replace(/\s+/g,"");
  const consent=document.getElementById("portal-consent").checked;
  const errEl=document.getElementById("portal-error");
  errEl.classList.add("hidden");
  if(!consent){errEl.textContent="Please confirm you understand how your data will be used.";errEl.classList.remove("hidden");return}
  const codes=readCodes();const entry=codes.find(c=>c.code===input);
  if(!entry){errEl.textContent="Code not found. Check with your care team.";errEl.classList.remove("hidden");return}
  if(entry.revoked||entry.redeemedAt||Date.now()>=new Date(entry.expiresAt).getTime()){errEl.textContent="This code is no longer valid.";errEl.classList.remove("hidden");return}
  writeCodes(codes.map(c=>c.id===entry.id?{...c,redeemedAt:new Date().toISOString()}:c));
  const p=DEMO_PATIENTS.find(x=>x.id===entry.patientId);
  const sess={codeId:entry.id,patientId:entry.patientId,displayName:p?.displayName||pName(entry.patientId),redeemedAt:new Date().toISOString()};
  sessionStorage.setItem(SESSION_KEY,JSON.stringify(sess));
  showPortalDashboard(sess);
}
document.getElementById("portal-file-input").addEventListener("change",function(e){
  const file=e.target.files?.[0];e.target.value="";
  const raw=sessionStorage.getItem(SESSION_KEY);if(!raw||!file)return;
  const sess=JSON.parse(raw);
  const upload={id:crypto.randomUUID(),patientId:sess.patientId,fileName:file.name,sizeBytes:file.size,uploadedAt:new Date().toISOString(),reviewedAt:null,source:"patient_portal"};
  const uploads=safeParse(localStorage.getItem(UPLOADS_KEY)||"[]",[]);
  localStorage.setItem(UPLOADS_KEY,JSON.stringify([upload,...uploads]));
  const variants=[
    {summaryLine:"Overnight HRV slightly above prior 7-day average.",hrvVsPriorWeek:"+4% vs prior week",restingHrVsPrior:"-1 bpm vs prior week",sleepNote:"Sleep duration within typical range.",stressRecoveryNote:"Recovery minutes modestly improved."},
    {summaryLine:"HRV flat vs baseline; resting HR unchanged.",hrvVsPriorWeek:"±0% vs prior week",restingHrVsPrior:"+0 bpm vs prior week",sleepNote:"Mid-sleep wake episodes unchanged.",stressRecoveryNote:"Afternoon stress load similar."},
    {summaryLine:"HRV down vs prior week; suggest clinical correlation.",hrvVsPriorWeek:"-8% vs prior week",restingHrVsPrior:"+3 bpm vs prior week",sleepNote:"Later bedtimes 2/7 nights.",stressRecoveryNote:"Recovery minutes lower Mon-Wed."}
  ];
  const pick=variants[(file.name.length+sess.patientId.length)%3];
  const inference={id:crypto.randomUUID(),uploadId:upload.id,patientId:sess.patientId,fileName:file.name,createdAt:new Date().toISOString(),modelRunId:"stub-heuristic-v0",modelStatus:"stub",...pick};
  const infs=safeParse(localStorage.getItem(INFERENCES_KEY)||"[]",[]);
  localStorage.setItem(INFERENCES_KEY,JSON.stringify([inference,...infs]));
  const toast=document.getElementById("portal-toast");
  toast.classList.remove("hidden");
  toast.innerHTML=`<div class="toast">&#10003; Uploaded "${esc(file.name)}". Your clinician will see it on their dashboard.</div>`;
  setTimeout(()=>toast.classList.add("hidden"),5000);
  renderPortalUploads(sess.patientId);
});
function portalSignOut(){sessionStorage.removeItem(SESSION_KEY);document.getElementById("portal-code-input").value="";document.getElementById("portal-consent").checked=false;showPortalGate()}

/* ════════════════════════════════════════════
   BioSignal Monitor (charts + table from merge 01)
   ════════════════════════════════════════════ */
/* ── Clinical Notes ── */
const NOTES_KEY="signalcare_clinical_notes";
function readNotes(){return safeParse(localStorage.getItem(NOTES_KEY)||"[]",[])}
function writeNotes(n){localStorage.setItem(NOTES_KEY,JSON.stringify(n))}
function getNotesForPatient(pid){return readNotes().filter(n=>n.patientId===pid).sort((a,b)=>b.createdAt.localeCompare(a.createdAt))}
function renderNotes(pid){
  const notes=getNotesForPatient(pid);
  const el=document.getElementById("notes-history");
  if(!notes.length){el.innerHTML=`<div class="notes-empty">No notes yet for this patient. Add one above.</div>`;return}
  el.innerHTML=notes.map(n=>{
    const typeClass=n.type==="Phone call"?"Phone":n.type==="Alert review"?"Alert":n.type;
    return`<div class="note-entry"><div class="note-header"><div><span class="note-date">${esc(n.date)}</span> <span class="note-type ${typeClass}">${esc(n.type)}</span></div><span class="muted">${ago(n.createdAt)}</span></div><div class="note-body">${esc(n.text)}</div><button class="note-delete" onclick="deleteNote('${n.id}')" title="Delete note">&times;</button></div>`
  }).join("")
}
function deleteNote(id){
  if(!confirm("Delete this note?"))return;
  writeNotes(readNotes().filter(n=>n.id!==id));
  if(STATE.selected)renderNotes(STATE.selected)
}
document.getElementById("note-form").addEventListener("submit",function(e){
  e.preventDefault();
  if(!STATE.selected)return;
  const text=document.getElementById("note-text").value.trim();
  if(!text)return;
  const date=document.getElementById("note-date").value||new Date().toISOString().slice(0,10);
  const type=document.getElementById("note-type").value;
  const note={id:crypto.randomUUID(),patientId:STATE.selected,date,type,text,createdAt:new Date().toISOString(),author:"Clinician"};
  const notes=readNotes();writeNotes([note,...notes]);
  document.getElementById("note-text").value="";
  renderNotes(STATE.selected)
});

const SORT_GETTERS={pid:p=>p.pid.toLowerCase(),hrv:p=>Number(p.metrics.hrv)||-1,hr:p=>Number(p.metrics.hr)||-1,stress:p=>Number(p.metrics.stress)||-1,isi:p=>Number(p.metrics.isi)||-1,phq9:p=>Number(p.metrics.phq9)||-1,gad7:p=>Number(p.metrics.gad7)||-1,alerts:p=>Number(p.alerts),status_order:p=>Number(p.status_order)};
function renderSortHeaders(){document.querySelectorAll(".data-table thead th[data-sort]").forEach(th=>{th.classList.remove("active");const icon=th.querySelector(".sort");if(!icon)return;if(th.dataset.sort===STATE.sortKey){th.classList.add("active");icon.textContent=STATE.sortDir==="asc"?"\u25B2":"\u25BC"}else{icon.textContent="\u25B2\u25BC"}})}
function getFilteredPatients(){const q=document.getElementById("search").value.trim().toLowerCase();const status=document.getElementById("statusFilter").value;const cluster=document.getElementById("clusterFilter").value;const alerts=document.getElementById("alertFilter").value;let rows=[...DATA.patients];if(q)rows=rows.filter(p=>p.pid.toLowerCase().includes(q));if(status)rows=rows.filter(p=>p.status===status);if(cluster!=="")rows=rows.filter(p=>getCluster(p)===Number(cluster));if(alerts==="has")rows=rows.filter(p=>p.alerts>0);if(alerts==="none")rows=rows.filter(p=>p.alerts===0);const getter=SORT_GETTERS[STATE.sortKey]||SORT_GETTERS.status_order;rows.sort((a,b)=>{const ka=getter(a),kb=getter(b);if(ka<kb)return STATE.sortDir==="asc"?-1:1;if(ka>kb)return STATE.sortDir==="asc"?1:-1;return 0});return rows}
function renderTable(){const body=document.getElementById("patient-table-body");const rows=getFilteredPatients();renderSortHeaders();body.innerHTML=rows.map(p=>`<tr data-pid="${p.pid}"><td>${dot(p.status)}<span style="font-weight:700">${pName(p.pid)}</span> <span class="muted">${p.pid}</span></td><td><div class="metric">${p.sparks.hrv||""}<span class="val">${fmt(p.metrics.hrv)}</span></div></td><td><div class="metric">${p.sparks.hr||""}<span class="val">${fmt(p.metrics.hr)}</span></div></td><td><div class="metric">${p.sparks.stress||""}<span class="val">${fmt(p.metrics.stress,3)}</span></div></td><td><div class="metric">${p.sparks.isi||""}<span class="val">${fmt(p.metrics.isi)}</span></div></td><td><div class="metric">${p.sparks.phq9||""}<span class="val">${fmt(p.metrics.phq9)}</span></div></td><td><div class="metric">${p.sparks.gad7||""}<span class="val">${fmt(p.metrics.gad7)}</span></div></td><td style="text-align:center">${badge(p.alerts)}</td><td>${statusPill(p.status)}</td></tr>`).join("");body.querySelectorAll("tr").forEach(row=>{row.addEventListener("click",()=>openPatient(row.dataset.pid))})}
const plotBase={paper_bgcolor:"#fff",plot_bgcolor:"#fff",template:"plotly_white",margin:{t:44,b:40,l:50,r:50},legend:{orientation:"h",y:1.16,x:0}};
function drawSmallPlot(id,days,vals,color,yT){if(!vals||!vals.length)return;Plotly.newPlot(id,[{x:days,y:vals,mode:"lines+markers",line:{color,width:2},marker:{size:4},connectgaps:false}],{...plotBase,margin:{t:6,b:30,l:38,r:12},height:170,showlegend:false,xaxis:{title:"Day",tickfont:{size:10}},yaxis:{title:yT,tickfont:{size:10}}},{displayModeBar:false,responsive:true})}
function drawPhysio(p){const es=p.emma_series||{};const d=es.days||p.sander_series?.days||[];drawSmallPlot("plot-hr",d,es.heart_rate||[],"#E53935","HR");drawSmallPlot("plot-rmssd",d,es.rmssd||[],"#2196F3","RMSSD");drawSmallPlot("plot-lfhf",d,es.lf_hf||[],"#00897B","LF/HF");drawSmallPlot("plot-sleep-hrs",d,es.sleep_hours||[],"#00695C","Hours");drawSmallPlot("plot-light",d,es.light_avg||[],"#FB8C00","Light");drawSmallPlot("plot-cal",d,es.calories||[],"#7E57C2","Cal")}
function drawDual(d,l,r){if(!d||!d.length)return;Plotly.newPlot("chart-main",[{x:d,y:l,name:"HRV (RMSSD)",line:{color:"#2196F3",width:2},mode:"lines+markers",marker:{size:4}},{x:d,y:r,name:"Stress",line:{color:"#FF9800",width:2},mode:"lines+markers",marker:{size:4},yaxis:"y2"}],{...plotBase,height:320,xaxis:{title:"Day"},yaxis:{title:"RMSSD"},yaxis2:{title:"Stress",overlaying:"y",side:"right",range:[0,1]}},{displayModeBar:false,responsive:true})}
function drawSleep(d,s){if(!d||!d.length)return;Plotly.newPlot("chart-sleep",[{x:d,y:s,name:"Sleep",line:{color:"#00897B",width:2},mode:"lines+markers",marker:{size:4},fill:"tozeroy",fillcolor:"rgba(0,137,123,0.08)"}],{...plotBase,height:280,xaxis:{title:"Day"},yaxis:{title:"Rest Proxy"}},{displayModeBar:false,responsive:true})}
function drawForecast(fs){const panel=document.getElementById("forecast-panel");const h=Object.keys(fs||{});if(!h.length){panel.classList.add("hidden");return}panel.classList.remove("hidden");const colors={"1":"#43A047","3":"#FF9800","7":"#E53935"};const traces=[];h.sort((a,b)=>a-b).forEach(k=>{const rows=fs[k]||[];traces.push({x:rows.map(r=>r.day),y:rows.map(r=>r.pred),name:`+${k}d`,mode:"lines+markers",marker:{size:3},line:{width:2,color:colors[k]||"#999"}})});const ob=fs[h[0]]||[];traces.push({x:ob.map(r=>r.day),y:ob.map(r=>r.true),name:"Observed",mode:"lines",line:{color:"#333",width:2,dash:"dot"},opacity:.5});Plotly.newPlot("chart-forecast",traces,{...plotBase,height:300,xaxis:{title:"Day"},yaxis:{title:"Stress"}},{displayModeBar:false,responsive:true})}
function drawMental(p){const es=p.emma_series||{};const cd=es.chart_days||es.days||[];if(!cd.length)return;const hI=es.isi_historical_chart||es.isi||[],hP=es.phq9_historical_chart||es.phq9||[],hG=es.gad7_historical_chart||es.gad7||[],fI=es.isi_forecast_chart||[],fP=es.phq9_forecast_chart||[],fG=es.gad7_forecast_chart||[];const sm=es.survey_day_mask_chart||es.survey_day_mask||[];const fd=(p.emma_forecast&&p.emma_forecast.forecast_days)||[];function sp(vals){const x=[],y=[];for(let i=0;i<cd.length;i++){if(!sm[i])continue;const v=vals[i];if(v===null||v===undefined||!Number.isFinite(v))continue;x.push(cd[i]);y.push(v)}return{x,y}}function vn(v){return(v||[]).filter(x=>x!==null&&x!==undefined&&Number.isFinite(x))}const yv=[...vn(hI),...vn(hP),...vn(hG),...vn(fI),...vn(fP),...vn(fG)];const yr=(()=>{if(!yv.length)return[0,10];const mn=Math.min(...yv),mx=Math.max(...yv);const s=Math.max(1,mx-mn);const pad=Math.max(1,s*.2);const lo=Math.max(0,Math.floor((mn-pad)*10)/10);let hi=Math.ceil((mx+pad+.5)*10)/10;if(hi<=lo)hi=lo+1;return[lo,hi]})();function ss(v,c,n){const pts=sp(v);return{x:pts.x,y:pts.y,name:n+" (Survey)",mode:"markers",marker:{size:10,symbol:"diamond-open",color:c,line:{width:2}}}}Plotly.newPlot("chart-mental",[{x:cd,y:hI,name:"ISI Hist",mode:"lines+markers",line:{color:"#7E57C2",width:2},marker:{size:4},connectgaps:false},{x:cd,y:fI,name:"ISI Forecast",mode:"lines+markers",line:{color:"#7E57C2",width:2,dash:"dot"},marker:{size:4},connectgaps:false},{x:cd,y:hP,name:"PHQ-9 Hist",mode:"lines+markers",line:{color:"#FB8C00",width:2},marker:{size:4},connectgaps:false},{x:cd,y:fP,name:"PHQ-9 Forecast",mode:"lines+markers",line:{color:"#FB8C00",width:2,dash:"dot"},marker:{size:4},connectgaps:false},{x:cd,y:hG,name:"GAD-7 Hist",mode:"lines+markers",line:{color:"#00897B",width:2},marker:{size:4},connectgaps:false},{x:cd,y:fG,name:"GAD-7 Forecast",mode:"lines+markers",line:{color:"#00897B",width:2,dash:"dot"},marker:{size:4},connectgaps:false},ss(hI,"#7E57C2","ISI"),ss(hP,"#FB8C00","PHQ-9"),ss(hG,"#00897B","GAD-7")],{...plotBase,height:320,xaxis:{title:"Day",range:[1,36],dtick:2},yaxis:{title:"Score",range:yr},shapes:(()=>{if(!fd.length)return[];const f=Math.min(...fd);return[{type:"line",x0:f-1,x1:f-1,y0:0,y1:1,xref:"x",yref:"paper",line:{color:"#9CA3AF",dash:"dot"}}]})(),annotations:(()=>{if(!fd.length)return[];const f=Math.min(...fd);return[{x:f-1,y:.97,xref:"x",yref:"paper",text:"Forecast →",showarrow:false,font:{size:9,color:"#9CA3AF"},xanchor:"left"}]})(),legend:{orientation:"h",y:1.28,x:0,font:{size:10}}},{displayModeBar:false,responsive:true})}
function drawSurvey(patient){const ps=SURVEY_BY_PID[patient.pid];const el=document.getElementById("chart-survey");if(!ps){el.innerHTML=`<div class="fact" style="margin-top:20px"><strong>No survey data</strong><span>Not available for this patient.</span></div>`;return}const ci=getCluster(patient);const traces=[];const ct=CLUSTER_SURVEY_TRAJECTORIES[String(ci)];if(ct){["ISI","PHQ9","GAD7"].forEach((m,i)=>{traces.push({x:SURVEY_TIMEPOINTS,y:ct[m],name:"Cluster",legendgroup:"cl",mode:"lines",line:{color:"#B0BEC5",width:1.8},opacity:.8,showlegend:i===0})})}traces.push({x:SURVEY_TIMEPOINTS,y:ps.ISI,name:"ISI",mode:"lines+markers",line:{color:"#3949AB",width:3},marker:{size:6}});traces.push({x:SURVEY_TIMEPOINTS,y:ps.PHQ9,name:"PHQ-9",mode:"lines+markers",line:{color:"#D84315",width:3},marker:{size:6}});traces.push({x:SURVEY_TIMEPOINTS,y:ps.GAD7,name:"GAD-7",mode:"lines+markers",line:{color:"#00897B",width:3},marker:{size:6}});Plotly.newPlot("chart-survey",traces,{...plotBase,height:320,xaxis:{title:"Timepoint",type:"category"},yaxis:{title:"Score"},legend:{orientation:"h",y:1.22,x:0}},{displayModeBar:false,responsive:true})}

function initTabs(){document.querySelectorAll("#chart-tabs .tab").forEach(tab=>{tab.addEventListener("click",()=>{document.querySelectorAll("#chart-tabs .tab").forEach(t=>t.classList.remove("active"));document.querySelectorAll(".tab-panel").forEach(p=>p.classList.remove("active"));tab.classList.add("active");const panel=document.getElementById("panel-"+tab.dataset.tab);panel.classList.add("active");panel.querySelectorAll(".js-plotly-plot").forEach(el=>{Plotly.Plots.resize(el)})})})}

function openPatient(pid){
  const p=DATA.patients.find(x=>x.pid===pid);if(!p)return;
  const ci=getCluster(p),cm=clusterMeta(ci);STATE.selected=pid;
  document.getElementById("bio-list-view").classList.add("hidden");
  document.getElementById("bio-detail-view").classList.remove("hidden");
  document.getElementById("patient-banner").innerHTML=`<div class="pid-label">${dot(p.status)} ${pName(p.pid)}</div><div class="stat" style="color:#6b7280">${p.pid} · Age ${NAME_MAP[p.pid]?.age||"—"}</div><div class="stat"><b>Status:</b> ${statusPill(p.status)}</div><div class="stat"><b>Cluster:</b> ${esc(cm.name)}</div><div class="stat"><b>Days:</b> ${p.days}</div><div class="stat"><b>Alerts:</b> ${badge(p.alerts)}</div>`;
  document.getElementById("mini-grid").innerHTML=`<div class="mini"><div class="k">Stress</div><div class="v">${fmt(p.metrics.stress,3)}</div></div><div class="mini"><div class="k">HRV</div><div class="v">${fmt(p.metrics.hrv)}</div></div><div class="mini"><div class="k">HR</div><div class="v">${fmt(p.metrics.hr)}</div></div><div class="mini"><div class="k">Sleep</div><div class="v">${fmt(p.metrics.sleep,2)}</div></div><div class="mini"><div class="k">ISI</div><div class="v">${fmt(p.metrics.isi)}</div></div><div class="mini"><div class="k">PHQ-9</div><div class="v">${fmt(p.metrics.phq9)}</div></div><div class="mini"><div class="k">GAD-7</div><div class="v">${fmt(p.metrics.gad7)}</div></div>`;
  document.getElementById("cluster-card").innerHTML=`<div class="fact"><strong>${esc(cm.name)}</strong><span>${esc(cm.insight)}</span></div>`;

  // ── Summary tab: Why surfaced now ──
  const sex=p.explanation||{},eex=p.emma_explanation||{};
  let whyHtml=`<div class="section-label-text">Why surfaced now</div>`;
  if(sex.risk||eex.risk){whyHtml+=`<div class="section-label-text" style="margin-top:8px">Risk factors</div>${chips(sex.risk||eex.risk,"risk")}`}
  if(sex.trajectory){whyHtml+=`<div class="fact"><strong>Trajectory</strong><span>${esc(sex.trajectory)}</span></div>`}
  if(sex.comment){whyHtml+=`<div class="fact"><strong>Clinical comment</strong><span>${esc(sex.comment)}</span></div>`}
  if(eex.risk&&!sex.risk){whyHtml+=`<div class="fact"><strong>Risk context</strong><span>${esc(eex.risk)}</span></div>`}
  if(!sex.risk&&!eex.risk&&!sex.trajectory&&!sex.comment){whyHtml+=`<div class="fact"><span>No risk signals surfaced for this patient at this time.</span></div>`}
  document.getElementById("summary-why").innerHTML=whyHtml;

  // ── Summary tab: Suggested follow-up ──
  const followUpMap={declining:"Review recent trend changes and prioritize follow-up if elevated signals persist or worsen.",stable:"Continue routine monitoring and reassess at the next review milestone.",improving:"Continue monitoring and confirm that improvement persists with new data."};
  const followUpText=followUpMap[p.status]||followUpMap.stable;
  document.getElementById("summary-followup").innerHTML=`<div class="section-label-text">Suggested follow-up</div><div class="fact"><span>${followUpText}</span></div>`;

  // ── Summary tab: Recent alerts ──
  const sa=(p.forecast&&p.forecast.alerts)||[],ea=(p.emma_forecast&&p.emma_forecast.alerts)||[];
  let alertsHtml=`<div class="section-label-text">Recent alerts</div>`;
  if(!sa.length&&!ea.length){alertsHtml+=`<div class="fact"><span style="color:#2e7d32">All metrics within expected thresholds — no alerts.</span></div>`}
  else{alertsHtml+=`<div class="fact"><strong>Alert state</strong><span style="color:#c62828;font-weight:700">Alerts detected</span></div>`;alertsHtml+=`<div style="max-height:220px;overflow-y:auto">`;sa.forEach(a=>{alertsHtml+=`<div class="alert-row"><div><div class="alert-title">Day ${a.day} +${a.horizon}d</div><div class="alert-meta">Stress ${a.pred}</div></div><div class="alert-pill">${esc(a.band)}</div></div>`});ea.forEach(a=>{alertsHtml+=`<div class="alert-row"><div><div class="alert-title">Day ${a.day} (${a.source||"model"})</div><div class="alert-meta">${esc(a.reason||"")}</div></div><div class="alert-pill">Alert</div></div>`});alertsHtml+=`</div>`}
  document.getElementById("summary-alerts").innerHTML=alertsHtml;

  // ── Summary tab: Protective context ──
  const protText=sex.protective||eex.protective;
  if(protText){document.getElementById("summary-protective").innerHTML=`<div class="section-label-text">Supporting context</div>${chips(protText,"protective")}`}
  else{document.getElementById("summary-protective").innerHTML=""}
  const nb=p.neighbors||[];document.getElementById("neighbors-card").innerHTML=nb.length?nb.map(n=>`<div class="neighbor" data-neighbor="${n.pid}" role="button" tabindex="0"><div class="neighbor-left"><span class="rank">#${n.rank}</span><div><a href="#" data-neighbor-link="${n.pid}">${pName(n.pid)}</a><div class="muted">${n.pid} · Distance: ${n.distance}</div></div></div><div class="muted">View profile</div></div>`).join(""):`<div class="fact"><strong>Similarity</strong><span>No neighbors found</span></div>`;
  document.querySelectorAll("[data-neighbor]").forEach(el=>{el.addEventListener("click",()=>openPatient(el.dataset.neighbor))});
  document.querySelectorAll("[data-neighbor-link]").forEach(el=>el.addEventListener("click",e=>{e.preventDefault();e.stopPropagation();openPatient(el.dataset.neighborLink)}));
  document.querySelectorAll("#chart-tabs .tab").forEach(t=>t.classList.remove("active"));document.querySelectorAll(".tab-panel").forEach(p=>p.classList.remove("active"));document.querySelector('#chart-tabs .tab[data-tab="summary"]').classList.add("active");document.getElementById("panel-summary").classList.add("active");
  const ss=p.sander_series||{};drawPhysio(p);drawDual(ss.days||[],ss.hrv||[],ss.stress||[]);drawSleep(ss.days||[],ss.sleep||[]);drawForecast((p.forecast&&p.forecast.series)||{});drawMental(p);drawSurvey(p);
  document.getElementById("note-date").value=new Date().toISOString().slice(0,10);
  document.getElementById("note-text").value="";
  renderNotes(pid);
  window.scrollTo({top:0,behavior:"smooth"});
}
function goList(){STATE.selected=null;document.getElementById("bio-detail-view").classList.add("hidden");document.getElementById("bio-list-view").classList.remove("hidden");window.scrollTo({top:0,behavior:"smooth"})}

document.getElementById("search").addEventListener("input",renderTable);
document.getElementById("statusFilter").addEventListener("change",renderTable);
document.getElementById("clusterFilter").addEventListener("change",renderTable);
document.getElementById("alertFilter").addEventListener("change",renderTable);
document.getElementById("resetBtn").addEventListener("click",()=>{document.getElementById("search").value="";document.getElementById("statusFilter").value="";document.getElementById("clusterFilter").value="";document.getElementById("alertFilter").value="";STATE.sortKey="status_order";STATE.sortDir="asc";renderTable()});
document.querySelectorAll(".data-table thead th[data-sort]").forEach(th=>{th.addEventListener("click",()=>{const k=th.dataset.sort;if(STATE.sortKey===k)STATE.sortDir=STATE.sortDir==="asc"?"desc":"asc";else{STATE.sortKey=k;STATE.sortDir="asc"}renderTable()})});
document.getElementById("backBtn").addEventListener("click",goList);

if(!sessionStorage.getItem("_sc_cleaned")){localStorage.removeItem(UPLOADS_KEY);localStorage.removeItem(INFERENCES_KEY);sessionStorage.setItem("_sc_cleaned","1")}

async function loadData(){
  const [dRes,sRes,cRes]=await Promise.all([
    fetch("/api/patients"),fetch("/api/survey"),fetch("/api/cluster-survey")
  ]);
  DATA=await dRes.json();
  SURVEY_BY_PID=await sRes.json();
  CLUSTER_SURVEY_TRAJECTORIES=await cRes.json();
  initTabs();renderTable();renderTriage();
}
loadData();
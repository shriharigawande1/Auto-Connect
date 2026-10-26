document.addEventListener("DOMContentLoaded",()=>{
 const role=document.getElementById("role"), wf=document.getElementById("workerFields");
 if(role){const f=()=>wf.classList.toggle("hidden",role.value!=="worker");role.addEventListener("change",f);f();}
 const form=document.getElementById("analysisForm");
 if(form){form.addEventListener("submit",async e=>{e.preventDefault();const box=document.getElementById("analysisResult");box.classList.remove("hidden");box.innerHTML="Analyzing...";const r=await fetch("/analyze",{method:"POST",headers:{"Content-Type":"application/x-www-form-urlencoded"},body:new URLSearchParams(new FormData(form))});const x=await r.json();box.innerHTML=`<h3>🤖 Smart Analysis Result</h3><p><b>Service:</b> ${x.service}</p><p><b>Urgency:</b> ${x.urgency}</p><p><b>Estimated Cost:</b> ₹${x.min} – ₹${x.max}</p><a class="btn" href="/workers?service=${encodeURIComponent(x.service)}">Find Workers</a>`;});}
});
async function findEmergency(type){
 const box=document.getElementById("emergencyResult"), list=document.getElementById("emergencyList"); box.classList.remove("hidden"); list.innerHTML="<p>Finding nearest available workers...</p>";
 const r=await fetch("/api/emergency"); const rows=await r.json(); list.innerHTML=rows.length?rows.map(w=>`<article class="worker-card"><div class="avatar">${w.name[0]}</div><div><h3>${w.name}</h3><p>${w.skill} · ⭐ ${Number(w.rating).toFixed(1)}</p><p>📍 ${w.location} · 🟢 Available</p><a class="btn" href="/worker/${w.id}">View Worker</a></div></article>`).join(""):"<p>No available workers right now.";
}
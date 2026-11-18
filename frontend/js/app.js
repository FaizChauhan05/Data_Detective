const SESSION = localStorage.getItem('dd-session') || crypto.randomUUID();
localStorage.setItem('dd-session', SESSION);
const headers = {'X-Session-Id': SESSION};
let datasets = [], selectedOverview = null, anomalyData = null;
const $ = id => document.getElementById(id);
const fmt = n => Number(n || 0).toLocaleString();
const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));

async function api(url, options={}) {
  const response = await fetch(url, {...options, headers: {...headers, ...(options.headers || {})}});
  if (!response.ok) { let msg = `Request failed (${response.status})`; try { msg = (await response.json()).detail || msg; } catch {} throw new Error(msg); }
  return response;
}
function toast(message) { const el=$('toast'); el.textContent=message; el.classList.add('show'); setTimeout(()=>el.classList.remove('show'),2800); }
function tableHTML(columns, rows, options={}) {
  if (!columns?.length) return '<div class="empty-inline">No records to display.</div>';
  const head = `<thead><tr>${columns.map(c=>`<th>${esc(c)}</th>`).join('')}</tr></thead>`;
  const body = (rows||[]).map((row,i)=>`<tr>${columns.map(c=> options.editable ? `<td contenteditable="true" data-row="${i}" data-col="${esc(c)}">${esc(row[c])}</td>` : `<td>${esc(row[c])}</td>`).join('')}</tr>`).join('');
  return `<table class="${options.editable?'editable':''}">${head}<tbody>${body || `<tr><td colspan="${columns.length}">No records found.</td></tr>`}</tbody></table>`;
}
function setPage(page) {
  document.querySelectorAll('.page').forEach(el=>el.classList.toggle('active',el.id===`page-${page}`));
  document.querySelectorAll('.nav-item').forEach(el=>el.classList.toggle('active',el.dataset.page===page));
  $('page-title').textContent = ({overview:'Overview',cleaning:'Data cleaning',anomalies:'Anomaly detection'})[page];
  if(page==='cleaning') loadClean();
  if(page==='anomalies') loadAnomalyPage();
}
document.querySelectorAll('.nav-item').forEach(btn=>btn.addEventListener('click',()=>setPage(btn.dataset.page)));

async function refreshDatasets() {
  const data = await (await api('/api/datasets')).json(); datasets=data.datasets;
  $('dataset-count').textContent=`${datasets.length} dataset${datasets.length===1?'':'s'}`;
  const opts = `<option value="">Select a dataset</option>` + datasets.map(d=>`<option value="${d.id}">${esc(d.name)}</option>`).join('');
  $('clean-dataset').innerHTML=opts; $('anomaly-dataset').innerHTML=opts;
  renderOverview();
}
function renderOverview() {
  const totalRows=datasets.reduce((a,d)=>a+d.rows,0), missing=datasets.reduce((a,d)=>a+d.missing,0), cells=datasets.reduce((a,d)=>a+d.cells,0);
  const completeness=cells?((cells-missing)/cells*100).toFixed(1)+'%':'—';
  const cards=[['DATASETS',fmt(datasets.length),'In this session'],['TOTAL ROWS',fmt(totalRows),'Across uploaded datasets'],['MISSING VALUES',fmt(missing),'Null cells'],['COMPLETENESS',completeness,'Across uploaded datasets']];
  $('overview-metrics').innerHTML=cards.map(c=>`<div class="metric-card"><span>${c[0]}</span><strong>${c[1]}</strong><small>${c[2]}</small></div>`).join('');
  $('empty-state').classList.toggle('hidden',datasets.length>0); $('dataset-table-wrap').classList.toggle('hidden',!datasets.length);
  $('dataset-table-wrap').innerHTML=datasets.length?`<table><thead><tr><th>Dataset</th><th>Rows</th><th>Columns</th><th>Missing</th><th>Duplicates</th><th>Completeness</th><th></th></tr></thead><tbody>${datasets.map(d=>`<tr><td>${esc(d.name)}</td><td>${fmt(d.rows)}</td><td>${fmt(d.columns)}</td><td>${fmt(d.missing)}</td><td>${fmt(d.duplicates)}</td><td>${d.completeness}%</td><td><button class="table-action" data-profile="${d.id}">View profile →</button></td></tr>`).join('')}</tbody></table>`:'';
  document.querySelectorAll('[data-profile]').forEach(btn=>btn.addEventListener('click',()=>loadProfile(btn.dataset.profile)));
}
async function upload(input) {
  if(!input.files?.length)return;
  const form=new FormData(); [...input.files].forEach(file=>form.append('files',file));
  try { const data=await (await api('/api/upload',{method:'POST',body:form})).json(); await refreshDatasets();
    if(data.added.length)toast(`${data.added.length} dataset(s) uploaded`);
    if(data.errors.length)toast(data.errors.map(e=>`${e.name}: ${e.error}`).join(' | '));
  } catch(e){toast(e.message)} input.value='';
}
$('file-input').addEventListener('change',e=>upload(e.target)); document.querySelector('.empty-upload').addEventListener('change',e=>upload(e.target));

async function loadProfile(id) {
  try {
    const d = await (await api(`/api/datasets/${id}`)).json();
    selectedOverview = id;
    $('profile-section').classList.remove('hidden');
    $('profile-name').textContent = d.name;

    // Keep the preview useful without making the page excessively long.
    $('preview-note').textContent = `Showing the first ${fmt(d.preview.rows.length)} of ${fmt(d.preview.total_rows)} rows`;
    $('data-preview').innerHTML = tableHTML(d.preview.columns, d.preview.rows);

    // Pie chart: category distribution for a selected categorical column.
    const distributions = d.distributions || {};
    const distributionColumns = Object.keys(distributions);
    $('distribution-column').innerHTML = distributionColumns.map(c => `<option value="${esc(c)}">${esc(c)}</option>`).join('');
    if (distributionColumns.length) {
      $('distribution-panel').classList.remove('hidden');
      const drawDistribution = () => {
        const column = $('distribution-column').value;
        const dist = distributions[column];
        Plotly.newPlot('distribution-chart', [{
          type: 'pie', labels: dist.labels, values: dist.values, hole: .42,
          textinfo: 'percent', sort: false,
          marker: {colors: ['#78866f','#a6b19d','#c5cbbd','#d8d9cf','#b7a88f','#d0c0a8','#9caa91','#c9c6ba']},
          hovertemplate: '<b>%{label}</b><br>Records: %{value:,}<br>Share: %{percent}<extra></extra>'
        }], {
          margin: {t: 8, r: 8, b: 8, l: 8}, showlegend: true,
          legend: {orientation: 'h', y: -.12}, paper_bgcolor: 'transparent',
          font: {family: 'DM Sans', color: '#55594f'}
        }, {displayModeBar: false, responsive: true});
      };
      $('distribution-column').onchange = drawDistribution;
      drawDistribution();
    } else {
      $('distribution-panel').classList.remove('hidden');
      $('distribution-column').innerHTML = '';
      $('distribution-chart').innerHTML = '<div class="empty-inline">No categorical columns are available for a pie chart.</div>';
    }

    // Missing values: hide the chart panel entirely when the dataset is complete.
    const missing = (d.missing_profile || []).filter(x => x.Missing > 0);
    if (missing.length) {
      $('missing-panel').classList.remove('hidden');
      document.querySelector('.profile-charts').classList.remove('single');
      $('missing-status').classList.add('hidden');
      Plotly.newPlot('missing-chart', [{
        type: 'bar', x: missing.map(x => x.Column), y: missing.map(x => x.Missing),
        marker: {color: '#87977d'},
        hovertemplate: '<b>%{x}</b><br>Missing values: %{y:,}<extra></extra>'
      }], {
        margin: {t: 10, r: 12, b: 65, l: 42}, paper_bgcolor: 'transparent',
        plot_bgcolor: 'transparent', font: {family: 'DM Sans', color: '#55594f'},
        yaxis: {gridcolor: '#eeeee8', rangemode: 'tozero'},
        xaxis: {tickangle: -25}
      }, {displayModeBar: false, responsive: true});
    } else {
      $('missing-panel').classList.add('hidden');
      document.querySelector('.profile-charts').classList.add('single');
      $('missing-status').textContent = 'This dataset has no missing values.';
      $('missing-status').classList.remove('hidden');
    }
    $('profile-section').scrollIntoView({behavior: 'smooth', block: 'start'});
  } catch (e) { toast(e.message); }
}

async function loadClean() {
  const id=$('clean-dataset').value;
  $('clean-workspace').classList.toggle('hidden',!id); $('clean-empty').classList.toggle('hidden',!!id);
  if(!id)return;
  try { const data=await (await api(`/api/datasets/${id}/cleaned`)).json();
    $('undo-btn').disabled=!data.undo; $('redo-btn').disabled=!data.redo; $('reset-btn').disabled=false;
    $('type-column').innerHTML=data.preview.columns.map(c=>`<option>${esc(c)}</option>`).join('');
    $('edit-table').innerHTML=tableHTML(data.preview.columns,data.preview.rows,{editable:true});
    $('clean-history').innerHTML=data.history.length?data.history.slice().reverse().map(h=>`<div class="history-item"><strong>${esc(h.action)}</strong><span>${esc(h.details)}</span></div>`).join(''):'No changes recorded yet.';
  } catch(e){toast(e.message)}
}
$('clean-dataset').addEventListener('change',loadClean);
$('apply-type').addEventListener('click',async()=>{const id=$('clean-dataset').value;if(!id)return;try{await api(`/api/datasets/${id}/type`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({column:$('type-column').value,type:$('type-value').value})});toast('Column type updated');loadClean()}catch(e){toast(e.message)}});
$('save-edits').addEventListener('click',async()=>{const id=$('clean-dataset').value;if(!id)return;try{const table=$('edit-table').querySelector('table');const columns=[...table.querySelectorAll('thead th')].map(th=>th.textContent);const rows=[...table.querySelectorAll('tbody tr')].map(tr=>{const vals=[...tr.querySelectorAll('td')].map(td=>td.textContent.trim());return Object.fromEntries(columns.map((c,i)=>[c,vals[i]===''?null:vals[i]]))});const r=await (await api(`/api/datasets/${id}/edit`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({rows})})).json();toast(r.changed?'Edits applied':'No changes detected');loadClean()}catch(e){toast(e.message)}});
async function historyAction(action){const id=$('clean-dataset').value;if(!id)return;try{await api(`/api/datasets/${id}/history/${action}`,{method:'POST'});loadClean()}catch(e){toast(e.message)}}
$('undo-btn').addEventListener('click',()=>historyAction('undo'));$('redo-btn').addEventListener('click',()=>historyAction('redo'));
$('reset-btn').addEventListener('click',async()=>{const id=$('clean-dataset').value;if(!id)return;try{await api(`/api/datasets/${id}/reset`,{method:'POST'});toast('Dataset reset to original');loadClean()}catch(e){toast(e.message)}});
$('export-btn').addEventListener('click',async()=>{const id=$('clean-dataset').value;if(!id)return;try{const response=await api(`/api/datasets/${id}/export?format=${$('export-format').value}`);const blob=await response.blob();const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download=response.headers.get('content-disposition')?.match(/filename="?([^";]+)"?/)?.[1]||`cleaned.${$('export-format').value}`;a.click();URL.revokeObjectURL(url)}catch(e){toast(e.message)}});

async function loadAnomalyPage(){if(!$('anomaly-dataset').value&&datasets.length)$('anomaly-dataset').value=datasets[0].id;}
$('anomaly-dataset').addEventListener('change',()=>{$('anomaly-output').classList.add('hidden');$('anomaly-empty').classList.remove('hidden')});
$('run-anomaly').addEventListener('click',async()=>{const id=$('anomaly-dataset').value;if(!id){toast('Upload and select a dataset first');return}const btn=$('run-anomaly');btn.disabled=true;btn.textContent='Analysing…';try{anomalyData=await (await api(`/api/datasets/${id}/analyze`,{method:'POST'})).json();renderAnomalies(anomalyData)}catch(e){toast(e.message)}finally{btn.disabled=false;btn.textContent='Run detection'}});
function renderAnomalies(d){$('anomaly-output').classList.remove('hidden');$('anomaly-empty').classList.add('hidden');const s=d.summary;
  $('anomaly-metrics').innerHTML=[['TOTAL RECORDS',fmt(s.total)],['ANOMALIES',fmt(s.anomalies)],['NORMAL RECORDS',fmt(s.normal)],['ANOMALY RATE',`${s.rate}%`]].map(x=>`<div class="metric-card"><span>${x[0]}</span><strong>${x[1]}</strong><small>Model results</small></div>`).join('');
  Plotly.newPlot('anomaly-pie',[{type:'pie',labels:['Normal','Anomaly'],values:[s.normal,s.anomalies],hole:.58,marker:{colors:['#a9b7a0','#bd765e']},textinfo:'label+percent',hovertemplate:'<b>%{label}</b><br>Records: %{value:,}<br>Share: %{percent}<extra></extra>'}],{margin:{t:8,b:8,l:8,r:8},showlegend:true,legend:{orientation:'h',y:-.08},paper_bgcolor:'transparent',font:{family:'DM Sans',color:'#55594f'}},{displayModeBar:false,responsive:true});
  const normal=d.score_groups.Normal||[], anomaly=d.score_groups.Anomaly||[];
  Plotly.newPlot('anomaly-hist',[{type:'histogram',x:normal,name:'Normal',marker:{color:'#9eae95'},opacity:.78,hovertemplate:'Score: %{x:.4f}<br>Records: %{y}<extra></extra>'},{type:'histogram',x:anomaly,name:'Anomaly',marker:{color:'#bd765e'},opacity:.8,hovertemplate:'Score: %{x:.4f}<br>Records: %{y}<extra></extra>'}],{barmode:'overlay',nbinsx:38,margin:{t:10,b:42,l:42,r:10},xaxis:{title:'Anomaly score',gridcolor:'#eeeee8'},yaxis:{title:'Records',gridcolor:'#eeeee8'},paper_bgcolor:'transparent',plot_bgcolor:'transparent',font:{family:'DM Sans',color:'#55594f'},legend:{orientation:'h',y:1.15}},{displayModeBar:false,responsive:true});
  const cols=d.numeric_columns||[];$('scatter-x').innerHTML=cols.map(c=>`<option>${esc(c)}</option>`).join('');$('scatter-y').innerHTML=cols.map((c,i)=>`<option ${i===1?'selected':''}>${esc(c)}</option>`).join('');
  $('scatter-x').onchange=drawScatter;$('scatter-y').onchange=drawScatter;drawScatter();$('anomaly-count-label').textContent=`${fmt(s.anomalies)} flagged`; $('anomaly-table').innerHTML=tableHTML(d.anomalies.columns,d.anomalies.rows);
  $('anomaly-output').scrollIntoView({behavior:'smooth',block:'start'});
}
function drawScatter(){if(!anomalyData)return;const x=$('scatter-x').value,y=$('scatter-y').value;if(!x||!y){$('anomaly-scatter').innerHTML='<div class="empty-inline">At least two numeric columns are needed for a scatter plot.</div>';return}const rows=anomalyData.result.rows;const traces=['Normal','Anomaly'].map((label,i)=>{const r=rows.filter(v=>v.Anomaly===label);return {type:'scatter',mode:'markers',name:label,x:r.map(v=>v[x]),y:r.map(v=>v[y]),customdata:r.map(v=>v['Anomaly Score']),marker:{size:7,opacity:.72,color:i?'#bd765e':'#899b80'},hovertemplate:`${x}: %{x}<br>${y}: %{y}<br>Score: %{customdata:.4f}<extra>${label}</extra>`}});Plotly.newPlot('anomaly-scatter',traces,{margin:{t:10,b:48,l:55,r:12},xaxis:{title:x,gridcolor:'#eeeee8'},yaxis:{title:y,gridcolor:'#eeeee8'},paper_bgcolor:'transparent',plot_bgcolor:'transparent',font:{family:'DM Sans',color:'#55594f'},legend:{orientation:'h',y:1.12}},{displayModeBar:false,responsive:true})}

refreshDatasets().catch(e=>toast(e.message));

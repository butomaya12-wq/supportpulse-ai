/* Client-side demo UI: session-scoped token, synthetic-only API, no third-party scripts. */
(() => {
  let token = '';
  let currentCase = null;
  const $ = id => document.getElementById(id);
  const show = (id, visible) => $(id).classList.toggle('hidden', !visible);
  const safe = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const number = n => Number(n ?? 0).toLocaleString('ru-RU');
  const fmt = iso => iso ? new Date(iso).toLocaleString('ru-RU', {timeZone:'Europe/Moscow',day:'2-digit',month:'2-digit',hour:'2-digit',minute:'2-digit'}) + ' MSK' : 'нет данных';
  const chip = state => {
    const label = {INSUFFICIENT_DATA:'Нужны данные',CANDIDATE_OVERDUE:'На проверку',CONFIRMED_OVERDUE:'Просрочка подтверждена',CORRECTED_LATE:'Отправлено поздно',FULFILLED_LATE:'Отправлено поздно',ON_TIME:'В срок',DISMISSED:'Отклонён',NOT_DUE:'В работе',SENT_UNCONFIRMED_DELIVERY:'Доставка не подтверждена'}[state] || state;
    const cls = ['CONFIRMED_OVERDUE','CANDIDATE_OVERDUE'].includes(state) ? 'warn' : ['ON_TIME','CORRECTED_LATE'].includes(state) ? 'good' : state === 'INSUFFICIENT_DATA' ? 'bad' : '';
    return `<span class="chip ${cls}">${safe(label)}</span>`;
  };
  async function api(path, method='GET', body) {
    if (!token) throw Error('Сначала введите локальный демо-токен');
    const response = await fetch('/api/v1/' + path, {method, headers:{Authorization:'Bearer '+token, ...(body ? {'Content-Type':'application/json'} : {})},body:body ? JSON.stringify(body) : undefined});
    let data;try{data=await response.json()}catch{data={detail:'Ошибка сервера'}}
    if (!response.ok) throw Error(typeof data.detail === 'string'?data.detail:JSON.stringify(data.detail));
    return data;
  }
  function toast(message, error=false){const el=$('message');el.textContent=message;el.classList.toggle('error',error);show('message',true)}
  async function exec(fn){try{await fn()}catch(e){toast(e.message,true)}}
  async function refresh() {
    const [overview, cases] = await Promise.all([api('overview'),api('findings')]);
    $('reviewCount').textContent=number(overview.counts.review_backlog);
    $('confirmedCount').textContent=number(overview.counts.confirmed_overdue);
    $('verifiedCount').textContent=number(overview.counts.actions_verified);
    $('onTimeRate').textContent=overview.on_time.value === null ? '—' : Math.round(overview.on_time.value*100) + '%';
    $('rateBasis').textContent=overview.on_time.denominator ? `Доказательств: ${overview.on_time.numerator}/${overview.on_time.denominator}` : 'Нет достаточных данных';
    $('sourceHealthHeadline').textContent=overview.sources.length?overview.sources.every(s=>s.health==='HEALTHY')?'Синхронизация OK':'Проверить источник':'Нет данных';
    $('sourceList').innerHTML=overview.sources.length?overview.sources.map(s=>`<div class="source-item"><div><div class="source-name">${safe(s.channel)}</div><div class="source-sub">${safe(s.id)} · ${safe(fmt(s.watermark))}</div></div><span class="source-status">${safe(s.health)}</span></div>`).join(''):'<div class="empty">Источники ещё не загружены</div>';
    $('casesList').innerHTML=cases.data.length?cases.data.map(f=>`<div class="case-row"><div class="case-body"><strong>Кейс #${number(f.id)} · ${safe(f.commitment.conversation_id)}</strong><small>Обещание: отправить расчёт · ${safe(f.commitment.actor_id)} · до ${safe(fmt(f.commitment.due_at))}</small></div>${chip(f.state)}<button class="button outline" data-case="${f.id}">Открыть →</button></div>`).join(''):'<div class="empty big">Нет кейсов. Загрузите синтетический пример.</div>';
    document.querySelectorAll('[data-case]').forEach(b=>b.addEventListener('click',()=>exec(()=>loadCase(Number(b.dataset.case)))));
    if(currentCase!==null && cases.data.some(x=>x.id===currentCase)) await loadCase(currentCase);
  }
  async function loadCase(id) {
    const f=await api('findings/'+id);currentCase=id;
    show('detailPanel',true);$('detailTitle').textContent=`Кейс #${f.id} · ${f.commitment.conversation_id}`;
    const evidence=f.evidence.map(e=>`<div class="evidence"><small>${safe(e.kind)} · ${safe(e.external_id)} · ${safe(fmt(e.event_time))}</small><p>${safe(e.message || 'Нет текста')}</p></div>`).join('');
    $('detailContent').innerHTML=`<div class="detail-grid"><div><div class="eyebrow">SOURCE EVIDENCE</div>${evidence}</div><div><div class="eyebrow">VERIFIED CONTEXT</div><p class="fact">Статус: ${chip(f.state)}<br>Срок: <b>${safe(fmt(f.commitment.due_at))}</b><br>Ответственный: <b>${safe(f.commitment.actor_id)}</b><br>Доказательство обещания: <b>${safe(f.commitment.basis.external_id)}</b><br>Надёжность данных: <b>${safe(f.quality_state)}</b><br>AI-оценка: <b>не применяется</b><br>Финансовая потеря: <b>неизвестна</b><br>Пересмотр: ${number(f.revision)}</p>${f.review?`<div class="evidence"><small>РЕШЕНИЕ РУКОВОДИТЕЛЯ</small><p>${safe(f.review.by)}: ${safe(f.review.reason)}</p></div>`:''}${f.corrective_action?`<div class="evidence"><small>КОРРЕКТИРУЮЩЕЕ ДЕЙСТВИЕ</small><p>#${f.corrective_action.id} · ${safe(f.corrective_action.owner_id)} · ${safe(f.corrective_action.state)}</p></div>`:''}</div></div>`;
    const controls=[];
    if(f.state==='CANDIDATE_OVERDUE') controls.push(`<button class="button primary" id="confirm">Подтвердить нарушение</button><button class="button outline" id="dismiss">Отклонить сигнал</button>`);
    if(f.state==='CONFIRMED_OVERDUE'&&!f.corrective_action)controls.push('<button class="button primary" id="assign">Назначить исправление</button>');
    if(f.corrective_action && f.corrective_action.state==='OPEN')controls.push('<button class="button primary" id="verify">Проверить исправление</button>');
    $('detailActions').innerHTML=controls.join('');
    if($('confirm'))$('confirm').onclick=()=>exec(async()=>{const reason=prompt('Укажите подтверждённое основание проверки (минимум 8 символов):','Обещание не выполнено до указанного срока; источник синхронизирован.');if(!reason)return;await api(`findings/${id}/review`,'POST',{decision:'CONFIRM',reason});toast('Сигнал подтверждён человеком');await refresh()});
    if($('dismiss'))$('dismiss').onclick=()=>exec(async()=>{const reason=prompt('Основание отклонения (минимум 8 символов):');if(!reason)return;await api(`findings/${id}/review`,'POST',{decision:'DISMISS',reason});toast('Сигнал отклонён с записью причины');await refresh()});
    if($('assign'))$('assign').onclick=()=>exec(async()=>{await api(`findings/${id}/actions`,'POST',{owner_id:f.commitment.actor_id});toast('Исправление назначено');await refresh()});
    if($('verify'))$('verify').onclick=()=>exec(async()=>{const evidence=prompt('Внешний идентификатор подтверждающего события (пример: msg-003):','msg-003');if(!evidence)return;await api(`actions/${f.corrective_action.id}/verify`,'POST',{proof_external_id:evidence});toast('Отправка подтверждена событием источника; доставка клиенту не подтверждается');await refresh()});
    $('detailPanel').scrollIntoView({behavior:'smooth',block:'start'});
  }
  $('connect').onclick=()=>exec(async()=>{token=$('token').value.trim();await api('me');$('token').value='';toast('Подключено: локальная синтетическая демонстрация');await refresh()});
  $('seed').onclick=()=>exec(async()=>{await api('demo/seed','POST');toast('Первый синтетический кейс загружен');await refresh()});
  $('followup').onclick=()=>exec(async()=>{await api('demo/followup','POST');toast('Импортирован подтверждённый факт отправки (не факт доставки)');await refresh()});
  $('refresh').onclick=()=>exec(refresh);
  $('closeDetail').onclick=()=>{show('detailPanel',false);currentCase=null};
})();

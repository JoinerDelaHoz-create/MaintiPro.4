/**
 * CMMS Industrial - Frontend Single Page Application Logic
 * Vanilla JavaScript communicating with Python HTTP Server REST API.
 */

// Application State
const state = {
  equipments: [],
  workOrders: [],
  kpis: null,
  activeTab: 'tab-dashboard',
  equipmentFilter: 'ALL',
  woFilter: 'ALL',
  searchQuery: '',
};

// =============================================================================
// INITIALIZATION & TAB NAVIGATION
// =============================================================================
document.addEventListener('DOMContentLoaded', () => {
  if (window.AuthClient && !window.AuthClient.guardRoute('ADMIN')) {
    return;
  }
  setupUserProfile();
  initNavigation();
  initModals();
  initEventListeners();
  loadAllData();
});

function setupUserProfile() {
  const user = window.AuthClient ? window.AuthClient.getUser() : null;
  const nameEl = document.getElementById('admin-user-name');
  if (nameEl && user) {
    nameEl.textContent = user.full_name || user.username;
  }
  const logoutBtn = document.getElementById('btn-admin-logout');
  if (logoutBtn) {
    logoutBtn.addEventListener('click', () => {
      window.AuthClient.logout();
    });
  }
}

function initNavigation() {
  const navButtons = document.querySelectorAll('.nav-item');
  navButtons.forEach((btn) => {
    btn.addEventListener('click', () => {
      const targetTab = btn.getAttribute('data-tab');
      switchTab(targetTab);
    });
  });
}

function switchTab(tabId) {
  state.activeTab = tabId;

  // Update sidebar active buttons
  document.querySelectorAll('.nav-item').forEach((btn) => {
    btn.classList.toggle('active', btn.getAttribute('data-tab') === tabId);
  });

  // Update tab panes
  document.querySelectorAll('.tab-pane').forEach((pane) => {
    pane.classList.toggle('active', pane.id === tabId);
  });

  // View specific refreshes
  if (tabId === 'tab-dashboard') {
    fetchKPIs();
  } else if (tabId === 'tab-equipments') {
    renderEquipmentsTable();
  } else if (tabId === 'tab-work-orders') {
    renderWorkOrdersTable();
  } else if (tabId === 'tab-iot') {
    populateEquipmentSelects();
  }
}

// =============================================================================
// DATA FETCHING & API HELPERS
// =============================================================================
async function apiRequest(endpoint, options = {}) {
  try {
    const token = window.AuthClient ? window.AuthClient.getToken() : '';
    const headers = {
      'Content-Type': 'application/json',
      ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
      ...(options.headers || {}),
    };
    const res = await fetch(endpoint, {
      ...options,
      headers,
    });
    if (res.status === 401 && window.AuthClient) {
      window.AuthClient.logout();
      return;
    }
    const data = await res.json();
    if (!res.ok || data.success === false) {
      throw new Error(data.error || 'Error al comunicarse con el servidor.');
    }
    return data;
  } catch (err) {
    showToast('Error', err.message, 'error');
    throw err;
  }
}

async function loadAllData() {
  await Promise.all([fetchEquipments(), fetchWorkOrders(), fetchKPIs()]);
}

async function fetchEquipments() {
  try {
    const res = await apiRequest('/api/equipments');
    state.equipments = res.equipments || [];
    renderEquipmentsTable();
    populateEquipmentSelects();
  } catch (e) {
    console.error('Error fetching equipments:', e);
  }
}

async function fetchWorkOrders() {
  try {
    const res = await apiRequest('/api/work-orders');
    state.workOrders = res.work_orders || [];
    renderWorkOrdersTable();
  } catch (e) {
    console.error('Error fetching work orders:', e);
  }
}

async function fetchKPIs() {
  try {
    const res = await apiRequest('/api/kpis');
    state.kpis = res.kpis || {};
    renderKPIs();
  } catch (e) {
    console.error('Error fetching KPIs:', e);
  }
}

// =============================================================================
// TAB 1: DASHBOARD & KPIS RENDERING
// =============================================================================
function renderKPIs() {
  if (!state.kpis) return;
  const k = state.kpis;

  // Global metric summary cards
  document.getElementById('kpi-total-equipments').textContent = k.total_equipments ?? 0;
  document.getElementById('kpi-total-hours').textContent = `${(k.total_operating_hours ?? 0).toLocaleString()} h`;
  document.getElementById('kpi-active-wos').textContent = k.active_work_orders ?? 0;
  document.getElementById('kpi-corrective-failures').textContent = k.corrective_failures ?? 0;
  document.getElementById('kpi-downtime').textContent = `${k.corrective_downtime_hours ?? 0} h`;
  document.getElementById('kpi-total-cost').textContent = `$${(k.total_cost ?? 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

  // Availability Gauge & Status
  const avail = k.availability_pct ?? 100.0;
  document.getElementById('kpi-availability-pct').textContent = `${avail.toFixed(1)}%`;

  const circle = document.getElementById('availability-gauge-circle');
  const circumference = 2 * Math.PI * 52; // 326.72
  const offset = circumference - (avail / 100) * circumference;
  circle.style.strokeDashoffset = offset;

  // Dynamic color for gauge
  const tag = document.getElementById('gauge-status-tag');
  if (avail >= 90) {
    circle.style.stroke = '#10b981';
    tag.textContent = 'Disponibilidad Óptima (World Class)';
    tag.style.backgroundColor = 'rgba(16, 185, 129, 0.15)';
    tag.style.color = '#10b981';
  } else if (avail >= 75) {
    circle.style.stroke = '#f59e0b';
    tag.textContent = 'Disponibilidad Media (Requiere Atención)';
    tag.style.backgroundColor = 'rgba(245, 158, 11, 0.15)';
    tag.style.color = '#f59e0b';
  } else {
    circle.style.stroke = '#ef4444';
    tag.textContent = 'Alerta de Disponibilidad Crítica';
    tag.style.backgroundColor = 'rgba(239, 68, 68, 0.15)';
    tag.style.color = '#ef4444';
  }

  // MTBF and MTTR
  document.getElementById('kpi-mtbf').textContent = typeof k.mtbf_hours === 'number' ? `${k.mtbf_hours.toFixed(1)} h` : k.mtbf_hours;
  document.getElementById('kpi-mttr').textContent = typeof k.mttr_hours === 'number' ? `${k.mttr_hours.toFixed(1)} h` : k.mttr_hours;

  // Status Distribution Bar
  renderDistributionBar(k.status_distribution || {});
}

function renderDistributionBar(dist) {
  const op = dist['OPERATIONAL'] || 0;
  const mt = dist['MAINTENANCE'] || 0;
  const wr = dist['WARNING'] || 0;
  const dw = dist['DOWN'] || 0;
  const total = op + mt + wr + dw || 1;

  const bar = document.getElementById('status-distribution-bar');
  bar.innerHTML = `
    <div class="dist-segment dist-operational" style="width: ${(op / total) * 100}%;" title="Operativos: ${op}"></div>
    <div class="dist-segment dist-maintenance" style="width: ${(mt / total) * 100}%;" title="En Mantenimiento: ${mt}"></div>
    <div class="dist-segment dist-warning" style="width: ${(wr / total) * 100}%;" title="Advertencia: ${wr}"></div>
    <div class="dist-segment dist-down" style="width: ${(dw / total) * 100}%;" title="Fuera de Servicio: ${dw}"></div>
  `;

  document.getElementById('status-dist-summary').textContent =
    `Operativos: ${op} | Mantenimiento: ${mt} | Advertencia: ${wr} | Fuera de Servicio: ${dw}`;
}

async function loadEquipmentKPI(code) {
  const container = document.getElementById('equipment-kpi-details');
  if (!code) {
    container.innerHTML = '<div class="empty-state-sm">Seleccione un equipo arriba para consultar sus indicadores específicos.</div>';
    return;
  }

  try {
    const res = await apiRequest(`/api/kpis/${encodeURIComponent(code)}`);
    const k = res.kpi;
    const statusBadge = getStatusBadge(k.status);

    container.innerHTML = `
      <div style="margin-bottom: 12px; display: flex; justify-content: space-between; align-items: center;">
        <div>
          <strong style="color:#fff; font-size:14px;">${k.name}</strong>
          <span style="font-family:var(--font-mono); color:#60a5fa; margin-left:6px;">[${k.code}]</span>
        </div>
        ${statusBadge}
      </div>
      <div class="kpi-detail-grid">
        <div class="kpi-detail-item">
          <div class="kpi-detail-label">Disponibilidad Operativa</div>
          <div class="kpi-detail-val ${k.availability >= 90 ? 'text-emerald' : 'text-amber'}">${k.availability}%</div>
        </div>
        <div class="kpi-detail-item">
          <div class="kpi-detail-label">MTBF (Horas Entre Fallas)</div>
          <div class="kpi-detail-val text-cyan">${k.mtbf} ${typeof k.mtbf === 'number' ? 'h' : ''}</div>
        </div>
        <div class="kpi-detail-item">
          <div class="kpi-detail-label">MTTR (Tiempo Reparación)</div>
          <div class="kpi-detail-val text-amber">${k.mttr} ${typeof k.mttr === 'number' ? 'h' : ''}</div>
        </div>
        <div class="kpi-detail-item">
          <div class="kpi-detail-label">Fallas Correctivas</div>
          <div class="kpi-detail-val text-red">${k.corrective_failures}</div>
        </div>
        <div class="kpi-detail-item">
          <div class="kpi-detail-label">Tiempo Paro Acumulado</div>
          <div class="kpi-detail-val">${k.downtime_hours} h</div>
        </div>
        <div class="kpi-detail-item">
          <div class="kpi-detail-label">Costo Mantenimiento</div>
          <div class="kpi-detail-val text-emerald">$${k.total_cost.toFixed(2)}</div>
        </div>
      </div>
    `;
  } catch (err) {
    container.innerHTML = `<div class="empty-state-sm text-red">Error al cargar ficha del activo: ${err.message}</div>`;
  }
}

// =============================================================================
// TAB 2: INVENTARIO DE ACTIVOS (EQUIPOS)
// =============================================================================
function renderEquipmentsTable() {
  const tbody = document.getElementById('equipments-tbody');
  const countLabel = document.getElementById('equipments-count-label');

  let list = state.equipments;

  // Filter by status chip
  if (state.equipmentFilter !== 'ALL') {
    list = list.filter((e) => e.status === state.equipmentFilter);
  }

  // Filter by search query
  if (state.searchQuery) {
    const q = state.searchQuery.toLowerCase();
    list = list.filter(
      (e) =>
        e.code.toLowerCase().includes(q) ||
        e.name.toLowerCase().includes(q) ||
        e.type.toLowerCase().includes(q) ||
        e.location.toLowerCase().includes(q)
    );
  }

  countLabel.textContent = `Total de activos listados: ${list.length} (de ${state.equipments.length})`;

  if (list.length === 0) {
    tbody.innerHTML = `<tr><td colspan="8" class="text-center py-4 text-muted">No se encontraron activos con los filtros aplicados.</td></tr>`;
    return;
  }

  tbody.innerHTML = list
    .map(
      (eq) => `
    <tr>
      <td class="code-cell">${escapeHtml(eq.code)}</td>
      <td><strong>${escapeHtml(eq.name)}</strong></td>
      <td>${escapeHtml(eq.type)}</td>
      <td>${escapeHtml(eq.location)}</td>
      <td style="font-family:var(--font-mono);">${eq.operating_hours.toFixed(1)} h</td>
      <td>${getStatusBadge(eq.status)}</td>
      <td style="font-size:11px; color:var(--text-dim);">${eq.created_at || 'N/A'}</td>
      <td class="text-right">
        <div class="row-actions">
          <button class="btn btn-secondary btn-xs" onclick="openEditEquipmentModal('${escapeHtml(eq.code)}')">Editar</button>
          <button class="btn btn-accent btn-xs" onclick="quickCreateWOForEquipment('${escapeHtml(eq.code)}')">+ OT</button>
          <button class="btn btn-danger btn-xs" onclick="deleteEquipment('${escapeHtml(eq.code)}')">Eliminar</button>
        </div>
      </td>
    </tr>
  `
    )
    .join('');
}

// =============================================================================
// TAB 3: ÓRDENES DE TRABAJO (OT)
// =============================================================================
function renderWorkOrdersTable() {
  const tbody = document.getElementById('work-orders-tbody');
  const countLabel = document.getElementById('wo-count-label');

  let list = state.workOrders;

  if (state.woFilter === 'ACTIVE') {
    list = list.filter((w) => w.status === 'PENDING' || w.status === 'IN_PROGRESS');
  } else if (state.woFilter !== 'ALL') {
    list = list.filter((w) => w.status === state.woFilter);
  }

  countLabel.textContent = `Total de órdenes listadas: ${list.length} (de ${state.workOrders.length})`;

  if (list.length === 0) {
    tbody.innerHTML = `<tr><td colspan="11" class="text-center py-4 text-muted">No se encontraron órdenes de trabajo para este filtro.</td></tr>`;
    return;
  }

  tbody.innerHTML = list
    .map((wo) => {
      let actionsHtml = '';
      if (wo.status === 'PENDING') {
        actionsHtml = `
          <button class="btn btn-primary btn-xs" onclick="startWorkOrder(${wo.id})">Iniciar</button>
          <button class="btn btn-secondary btn-xs" onclick="openCloseWOModal(${wo.id})">Cerrar</button>
          <button class="btn btn-danger btn-xs" onclick="cancelWorkOrder(${wo.id})">Cancelar</button>
        `;
      } else if (wo.status === 'IN_PROGRESS') {
        actionsHtml = `
          <button class="btn btn-primary btn-xs" onclick="openCloseWOModal(${wo.id})">Cerrar / Finalizar</button>
          <button class="btn btn-danger btn-xs" onclick="cancelWorkOrder(${wo.id})">Cancelar</button>
        `;
      } else {
        actionsHtml = `<span style="font-size:11px; color:var(--text-dim);">Liquidada</span>`;
      }

      return `
      <tr>
        <td style="font-family:var(--font-mono); font-weight:700;">#${wo.id}</td>
        <td class="code-cell">${escapeHtml(wo.equipment_code)}</td>
        <td>
          <div style="font-weight:600;">${escapeHtml(wo.title)}</div>
          <div style="font-size:11px; color:var(--text-muted);">${escapeHtml(wo.description || 'Sin notas')}</div>
        </td>
        <td>${getWOTypeBadge(wo.type)}</td>
        <td>${getPriorityBadge(wo.priority)}</td>
        <td>${getWOStatusBadge(wo.status)}</td>
        <td>${escapeHtml(wo.assigned_technician)}</td>
        <td style="font-family:var(--font-mono);">${wo.downtime_hours ? wo.downtime_hours.toFixed(1) + 'h' : '0.0h'}</td>
        <td style="font-family:var(--font-mono); color:#34d399;">$${wo.cost.toFixed(2)}</td>
        <td style="font-size:11px; color:var(--text-dim);">${wo.created_at || 'N/A'}</td>
        <td class="text-right">
          <div class="row-actions">${actionsHtml}</div>
        </td>
      </tr>
    `;
    })
    .join('');
}

// Work Order Action Triggers
async function startWorkOrder(id) {
  try {
    await apiRequest(`/api/work-orders/${id}/start`, { method: 'POST' });
    showToast('Éxito', `La OT #${id} ha sido iniciada y el activo pasó a mantenimiento.`, 'success');
    await loadAllData();
  } catch (e) {
    // Handled in apiRequest
  }
}

async function cancelWorkOrder(id) {
  if (!confirm(`¿Está seguro de cancelar la Orden de Trabajo OT #${id}?`)) return;
  try {
    await apiRequest(`/api/work-orders/${id}/cancel`, { method: 'POST' });
    showToast('Orden Cancelada', `La OT #${id} fue cancelada exitosamente.`, 'warning');
    await loadAllData();
  } catch (e) {
    // Handled
  }
}

function openCloseWOModal(id) {
  const wo = state.workOrders.find((w) => w.id === id);
  if (!wo) return;

  document.getElementById('close-wo-id').value = id;
  document.getElementById('close-wo-summary').innerHTML = `
    <strong>OT #${wo.id}</strong>: ${escapeHtml(wo.title)}<br>
    <span style="font-size:11px;">Activo: <strong>${escapeHtml(wo.equipment_code)}</strong> | Tipo: ${wo.type}</span>
  `;
  document.getElementById('close-wo-downtime').value = '1.5';
  document.getElementById('close-wo-cost').value = '120.00';

  openModal('modal-close-wo');
}

// =============================================================================
// TAB 4: MONITOR IOT & TELEMETRÍA ARDUINO
// =============================================================================
async function triggerTelemetrySimulation(injectAnomaly = false) {
  const eqSelect = document.getElementById('select-iot-equipment');
  const code = eqSelect.value || (state.equipments[0] && state.equipments[0].code);

  if (!code) {
    showToast('Aviso', 'Registre equipos antes de simular telemetría.', 'warning');
    return;
  }

  try {
    const res = await apiRequest('/api/iot/simulate', {
      method: 'POST',
      body: JSON.stringify({ equipment_code: code, inject_anomaly: injectAnomaly }),
    });

    const r = res.reading;
    const severity = res.severity;
    const woId = res.work_order_id;

    // Update gauge values in UI
    document.getElementById('live-temp-val').textContent = r.temperature.toFixed(1);
    document.getElementById('live-vib-val').textContent = r.vibration.toFixed(2);
    document.getElementById('live-curr-val').textContent = r.current.toFixed(1);

    // Update meter fill bars
    const tempPct = Math.min(100, Math.max(10, (r.temperature / 100) * 100));
    const vibPct = Math.min(100, Math.max(10, (r.vibration / 12) * 100));
    const currPct = Math.min(100, Math.max(10, (r.current / 40) * 100));

    document.getElementById('meter-temp-fill').style.width = `${tempPct}%`;
    document.getElementById('meter-vib-fill').style.width = `${vibPct}%`;
    document.getElementById('meter-curr-fill').style.width = `${currPct}%`;

    // Sensor tags
    const tempTag = document.getElementById('tag-temp');
    const vibTag = document.getElementById('tag-vib');

    if (r.temperature >= 85) {
      tempTag.textContent = 'CRÍTICO';
      tempTag.className = 'sensor-tag tag-critical';
    } else if (r.temperature >= 70) {
      tempTag.textContent = 'ALERTA';
      tempTag.className = 'sensor-tag tag-warning';
    } else {
      tempTag.textContent = 'NORMAL';
      tempTag.className = 'sensor-tag';
    }

    if (r.vibration >= 7.1) {
      vibTag.textContent = 'PELIGRO ISO';
      vibTag.className = 'sensor-tag tag-critical';
    } else if (r.vibration >= 4.5) {
      vibTag.textContent = 'ALERTA ISO';
      vibTag.className = 'sensor-tag tag-warning';
    } else {
      vibTag.textContent = 'NORMAL';
      vibTag.className = 'sensor-tag';
    }

    // Diagnosis Card
    const diagText = document.getElementById('diagnosis-text');
    const diagDetail = document.getElementById('diagnosis-detail');
    const alarmBanner = document.getElementById('iot-alarm-banner');
    const tempCard = document.getElementById('sensor-temp-card');
    const vibCard = document.getElementById('sensor-vib-card');

    if (severity === 'CRITICAL' || severity === 'WARNING') {
      diagText.textContent = `ANOMALÍA DETECTADA (${severity})`;
      diagText.className = 'diagnosis-status text-red';
      diagDetail.textContent = `Alerta disparada por exceso en tolerancias sensoriales. Se generó automáticamente la OT Predictiva #${woId}.`;

      // Trigger visual alarm banner
      alarmBanner.style.display = 'flex';
      document.getElementById('alarm-banner-title').textContent = `¡ALERTA PREDICTIVA EN ${r.equipment_code}!`;
      document.getElementById('alarm-banner-desc').textContent =
        `Temperatura: ${r.temperature}°C, Vibración RMS: ${r.vibration} mm/s. Generada automáticamente Orden de Trabajo Predictiva #${woId}.`;

      tempCard.classList.add('anomaly-active');
      vibCard.classList.add('anomaly-active');

      appendTelemetryLog(`[ALERTA ${severity}] ${r.equipment_code} -> Temp: ${r.temperature}°C, Vib: ${r.vibration} mm/s. Generada OT #${woId}`, 'critical');
      showToast('Alerta Predictiva', `Se generó automáticamente la OT #${woId} para el equipo ${r.equipment_code}.`, 'error');

      // Refresh DB data to reflect machine status change and new work order
      fetchEquipments();
      fetchWorkOrders();
      fetchKPIs();
    } else {
      diagText.textContent = 'OPERACIÓN NORMAL';
      diagText.className = 'diagnosis-status text-emerald';
      diagDetail.textContent = 'Condición mecánica y térmica dentro de los límites seguros de la norma ISO 10816.';

      tempCard.classList.remove('anomaly-active');
      vibCard.classList.remove('anomaly-active');

      appendTelemetryLog(`[NORMAL] ${r.equipment_code} -> Temp: ${r.temperature}°C, Vib: ${r.vibration} mm/s, Curr: ${r.current}A`, 'normal');
      showToast('Telemetría Recibida', `Lectura normal registrada para el equipo ${r.equipment_code}.`, 'success');
    }
  } catch (err) {
    // Handled
  }
}

function appendTelemetryLog(text, type = 'normal') {
  const box = document.getElementById('telemetry-log-stream');
  const time = new Date().toLocaleTimeString();
  const entry = document.createElement('div');
  entry.className = `log-entry ${type === 'critical' ? 'log-critical' : 'log-normal'}`;
  entry.innerHTML = `<span class="log-time">[${time}]</span> ${escapeHtml(text)}`;
  box.prepend(entry);
}

// =============================================================================
// TAB 5: REPORTES CSV & EXPORTACIÓN
// =============================================================================
async function exportCSVReports() {
  try {
    const res = await apiRequest('/api/export', { method: 'POST' });
    const area = document.getElementById('export-results-area');
    area.style.display = 'block';

    const linkEq = document.getElementById('link-download-eq');
    const linkWo = document.getElementById('link-download-wo');

    linkEq.href = res.equipments_url;
    linkEq.setAttribute('download', res.equipments_file);
    document.getElementById('name-download-eq').textContent = `Descargar: ${res.equipments_file}`;

    linkWo.href = res.work_orders_url;
    linkWo.setAttribute('download', res.work_orders_file);
    document.getElementById('name-download-wo').textContent = `Descargar: ${res.work_orders_file}`;

    showToast('Reportes Listos', 'Archivos CSV generados y listos para descarga.', 'success');
  } catch (err) {
    // Handled
  }
}

// =============================================================================
// DEMO DATA LOADER
// =============================================================================
async function loadDemoData() {
  try {
    const res = await apiRequest('/api/demo', { method: 'POST' });
    showToast('Datos Demo', res.message, 'success');
    await loadAllData();
  } catch (err) {
    // Handled
  }
}

// =============================================================================
// MODALS LOGIC & FORM HANDLERS
// =============================================================================
function initModals() {
  document.querySelectorAll('[data-close-modal]').forEach((btn) => {
    btn.addEventListener('click', () => {
      closeAllModals();
    });
  });

  // Close on backdrop click
  document.querySelectorAll('.modal-backdrop').forEach((backdrop) => {
    backdrop.addEventListener('click', (e) => {
      if (e.target === backdrop) closeAllModals();
    });
  });

  // Close on Esc key
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') closeAllModals();
  });
}

function openModal(modalId) {
  closeAllModals();
  const modal = document.getElementById(modalId);
  if (modal) modal.classList.add('show');
}

function closeAllModals() {
  document.querySelectorAll('.modal-backdrop').forEach((m) => m.classList.remove('show'));
}

function populateEquipmentSelects() {
  const selects = [
    document.getElementById('select-kpi-equipment'),
    document.getElementById('wo-equipment-code'),
    document.getElementById('select-iot-equipment'),
  ];

  selects.forEach((sel) => {
    if (!sel) return;
    const currentVal = sel.value;
    sel.innerHTML = '<option value="">-- Seleccionar Equipo --</option>';
    state.equipments.forEach((e) => {
      const opt = document.createElement('option');
      opt.value = e.code;
      opt.textContent = `${e.code} - ${e.name} (${e.location})`;
      sel.appendChild(opt);
    });
    if (currentVal) sel.value = currentVal;
  });
}

function quickCreateWOForEquipment(code) {
  openModal('modal-create-wo');
  const select = document.getElementById('wo-equipment-code');
  if (select) select.value = code;
}

function openEditEquipmentModal(code) {
  const eq = state.equipments.find((e) => e.code === code);
  if (!eq) return;

  document.getElementById('edit-eq-code').value = eq.code;
  document.getElementById('edit-eq-name').value = eq.name;
  document.getElementById('edit-eq-type').value = eq.type;
  document.getElementById('edit-eq-location').value = eq.location;
  document.getElementById('edit-eq-status').value = eq.status;
  document.getElementById('edit-eq-hours').value = eq.operating_hours;

  openModal('modal-edit-equipment');
}

async function deleteEquipment(code) {
  if (!confirm(`¿Está seguro de eliminar el equipo '${code}' y todo su historial de OTs? Esta acción no se puede deshacer.`)) return;

  try {
    await apiRequest(`/api/equipments/${encodeURIComponent(code)}`, { method: 'DELETE' });
    showToast('Equipo Eliminado', `El activo '${code}' ha sido eliminado.`, 'success');
    await loadAllData();
  } catch (err) {
    // Handled
  }
}

// Form Submissions
function initEventListeners() {
  // Global buttons
  document.getElementById('btn-load-demo').addEventListener('click', loadDemoData);
  document.getElementById('btn-quick-new-equipment').addEventListener('click', () => openModal('modal-create-equipment'));
  document.getElementById('btn-quick-new-wo').addEventListener('click', () => openModal('modal-create-wo'));
  document.getElementById('btn-open-create-equipment').addEventListener('click', () => openModal('modal-create-equipment'));
  document.getElementById('btn-open-create-wo').addEventListener('click', () => openModal('modal-create-wo'));
  document.getElementById('btn-refresh-kpis').addEventListener('click', () => {
    fetchKPIs();
    showToast('Actualizado', 'Indicadores de planta recalculados.', 'info');
  });

  // Equipment search & filter chips
  const searchInput = document.getElementById('equipment-search-input');
  searchInput.addEventListener('input', (e) => {
    state.searchQuery = e.target.value.trim();
    renderEquipmentsTable();
  });

  document.getElementById('equipment-status-filters').addEventListener('click', (e) => {
    if (e.target.classList.contains('chip')) {
      document.querySelectorAll('#equipment-status-filters .chip').forEach((c) => c.classList.remove('active'));
      e.target.classList.add('active');
      state.equipmentFilter = e.target.getAttribute('data-status');
      renderEquipmentsTable();
    }
  });

  // Work orders filter chips
  document.getElementById('wo-status-filters').addEventListener('click', (e) => {
    if (e.target.classList.contains('chip')) {
      document.querySelectorAll('#wo-status-filters .chip').forEach((c) => c.classList.remove('active'));
      e.target.classList.add('active');
      state.woFilter = e.target.getAttribute('data-wo-filter');
      renderWorkOrdersTable();
    }
  });

  // KPI individual equipment selector
  document.getElementById('select-kpi-equipment').addEventListener('change', (e) => {
    loadEquipmentKPI(e.target.value);
  });

  // IoT Buttons
  document.getElementById('btn-simulate-normal').addEventListener('click', () => triggerTelemetrySimulation(false));
  document.getElementById('btn-inject-anomaly').addEventListener('click', () => triggerTelemetrySimulation(true));
  document.getElementById('btn-dismiss-alarm').addEventListener('click', () => {
    document.getElementById('iot-alarm-banner').style.display = 'none';
  });

  // Real Arduino Serial Reader
  document.getElementById('btn-read-serial').addEventListener('click', async () => {
    const port = document.getElementById('serial-port-input').value.trim() || 'COM3';
    try {
      const res = await apiRequest('/api/iot/serial', {
        method: 'POST',
        body: JSON.stringify({ port }),
      });
      if (res.data) {
        showToast('Arduino Conectado', `Dato recibido: ${res.data}`, 'success');
        appendTelemetryLog(`[SERIAL ${port}] ${res.data}`, 'normal');
      } else {
        showToast('Arduino', `No se recibieron datos en ${port}. Verifique baudrate 9600.`, 'warning');
      }
    } catch (e) {
      // Handled
    }
  });

  // Export CSV
  document.getElementById('btn-export-csv').addEventListener('click', exportCSVReports);

  // Modal Form 1: Create Equipment
  document.getElementById('form-create-equipment').addEventListener('submit', async (e) => {
    e.preventDefault();
    const payload = {
      code: document.getElementById('eq-code').value.trim().toUpperCase(),
      name: document.getElementById('eq-name').value.trim(),
      type: document.getElementById('eq-type').value.trim() || 'General',
      location: document.getElementById('eq-location').value.trim() || 'Planta Principal',
      operating_hours: parseFloat(document.getElementById('eq-hours').value || 0),
    };

    try {
      await apiRequest('/api/equipments', {
        method: 'POST',
        body: JSON.stringify(payload),
      });
      showToast('Activo Creado', `Equipo '${payload.code}' registrado con éxito.`, 'success');
      closeAllModals();
      e.target.reset();
      await loadAllData();
    } catch (err) {
      // Handled
    }
  });

  // Modal Form 2: Edit Equipment
  document.getElementById('form-edit-equipment').addEventListener('submit', async (e) => {
    e.preventDefault();
    const code = document.getElementById('edit-eq-code').value;
    const payload = {
      name: document.getElementById('edit-eq-name').value.trim(),
      type: document.getElementById('edit-eq-type').value.trim(),
      location: document.getElementById('edit-eq-location').value.trim(),
      status: document.getElementById('edit-eq-status').value,
      operating_hours: parseFloat(document.getElementById('edit-eq-hours').value || 0),
    };

    try {
      await apiRequest(`/api/equipments/${encodeURIComponent(code)}`, {
        method: 'PUT',
        body: JSON.stringify(payload),
      });
      showToast('Equipo Actualizado', `Los cambios en '${code}' fueron guardados.`, 'success');
      closeAllModals();
      await loadAllData();
    } catch (err) {
      // Handled
    }
  });

  // Modal Form 3: Create Work Order
  document.getElementById('form-create-wo').addEventListener('submit', async (e) => {
    e.preventDefault();
    const payload = {
      equipment_code: document.getElementById('wo-equipment-code').value,
      title: document.getElementById('wo-title').value.trim(),
      description: document.getElementById('wo-description').value.trim(),
      type: document.getElementById('wo-type').value,
      priority: document.getElementById('wo-priority').value,
      assigned_technician: document.getElementById('wo-technician').value.trim() || 'Técnico de Turno',
    };

    try {
      const res = await apiRequest('/api/work-orders', {
        method: 'POST',
        body: JSON.stringify(payload),
      });
      showToast('OT Generada', `Orden de Trabajo #${res.work_order.id} creada en estado PENDING.`, 'success');
      closeAllModals();
      e.target.reset();
      await loadAllData();
    } catch (err) {
      // Handled
    }
  });

  // Modal Form 4: Close Work Order
  document.getElementById('form-close-wo').addEventListener('submit', async (e) => {
    e.preventDefault();
    const id = document.getElementById('close-wo-id').value;
    const payload = {
      downtime_hours: parseFloat(document.getElementById('close-wo-downtime').value || 0),
      cost: parseFloat(document.getElementById('close-wo-cost').value || 0),
    };

    try {
      await apiRequest(`/api/work-orders/${id}/close`, {
        method: 'POST',
        body: JSON.stringify(payload),
      });
      showToast('OT Liquidada', `La OT #${id} ha sido completada y liquidada.`, 'success');
      closeAllModals();
      await loadAllData();
    } catch (err) {
      // Handled
    }
  });

  // Mobile / Wi-Fi Access Modal
  const btnMobile = document.getElementById('btn-open-mobile-access');
  if (btnMobile) {
    btnMobile.addEventListener('click', async () => {
      try {
        const netRes = await apiRequest('/api/network-info');
        document.getElementById('net-technician-url').value = netRes.technician_url;
        document.getElementById('btn-open-tech-portal').href = netRes.technician_url;

        // Load current notification config
        const notifRes = await apiRequest('/api/notifications/config');
        const cfg = notifRes.config || {};
        document.getElementById('notif-enabled').checked = !!cfg.enabled;
        document.getElementById('notif-telegram-token').value = cfg.telegram_bot_token || '';
        document.getElementById('notif-telegram-chat').value = cfg.telegram_chat_id || '';

        openModal('modal-mobile-access');
      } catch (e) {
        // Handled
      }
    });
  }

  // Form Notifications Config Submit
  const formNotif = document.getElementById('form-notifications-config');
  if (formNotif) {
    formNotif.addEventListener('submit', async (e) => {
      e.preventDefault();
      const payload = {
        enabled: document.getElementById('notif-enabled').checked,
        telegram_enabled: document.getElementById('notif-enabled').checked,
        telegram_bot_token: document.getElementById('notif-telegram-token').value.trim(),
        telegram_chat_id: document.getElementById('notif-telegram-chat').value.trim(),
      };

      try {
        await apiRequest('/api/notifications/config', {
          method: 'POST',
          body: JSON.stringify(payload),
        });
        showToast('Configuración Guardada', 'Preferencias de notificaciones actualizadas.', 'success');
      } catch (err) {
        // Handled
      }
    });
  }

  // Test Notification Button
  const btnTestNotif = document.getElementById('btn-test-notification');
  if (btnTestNotif) {
    btnTestNotif.addEventListener('click', async () => {
      try {
        showToast('Enviando...', 'Despachando alerta de prueba.', 'info');
        const res = await apiRequest('/api/notifications/test', { method: 'POST' });
        showToast('Prueba Enviada', 'Alerta de prueba despachada. Verifica tu Telegram/Móvil.', 'success');
      } catch (err) {
        // Handled
      }
    });
  }
}

// =============================================================================
// UI HELPERS & BADGE FORMATTERS
// =============================================================================
function getStatusBadge(status) {
  const map = {
    OPERATIONAL: '<span class="badge badge-operational">OPERATIVO</span>',
    MAINTENANCE: '<span class="badge badge-maintenance">MANTENIMIENTO</span>',
    WARNING: '<span class="badge badge-warning">ADVERTENCIA</span>',
    DOWN: '<span class="badge badge-down">FUERA SERVICIO</span>',
  };
  return map[status] || `<span class="badge">${escapeHtml(status)}</span>`;
}

function getWOStatusBadge(status) {
  const map = {
    PENDING: '<span class="badge badge-pending">PENDIENTE</span>',
    IN_PROGRESS: '<span class="badge badge-in_progress">EN PROGRESO</span>',
    COMPLETED: '<span class="badge badge-completed">COMPLETADA</span>',
    CANCELLED: '<span class="badge badge-cancelled">CANCELADA</span>',
  };
  return map[status] || `<span class="badge">${escapeHtml(status)}</span>`;
}

function getWOTypeBadge(type) {
  const map = {
    PREVENTIVE: '<span class="badge badge-preventive">PREVENTIVO</span>',
    CORRECTIVE: '<span class="badge badge-corrective">CORRECTIVO</span>',
    PREDICTIVE: '<span class="badge badge-predictive">PREDICTIVO</span>',
  };
  return map[type] || `<span class="badge">${escapeHtml(type)}</span>`;
}

function getPriorityBadge(priority) {
  const map = {
    LOW: '<span class="badge-prio-low">BAJA</span>',
    MEDIUM: '<span class="badge-prio-medium">MEDIA</span>',
    HIGH: '<span class="badge-prio-high">ALTA</span>',
    CRITICAL: '<span class="badge-prio-critical">CRÍTICA</span>',
  };
  return map[priority] || priority;
}

function showToast(title, message, type = 'info') {
  const container = document.getElementById('toast-container');
  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;

  const iconSvg =
    type === 'success'
      ? '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#10b981" stroke-width="2"><polyline points="20 6 9 17 4 12"></polyline></svg>'
      : type === 'error'
      ? '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#ef4444" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><line x1="15" y1="9" x2="9" y2="15"></line><line x1="9" y1="9" x2="15" y2="15"></line></svg>'
      : '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#3b82f6" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="16" x2="12" y2="12"></line><line x1="12" y1="8" x2="12.01" y2="8"></line></svg>';

  toast.innerHTML = `
    <div class="toast-icon">${iconSvg}</div>
    <div class="toast-body">
      <div class="toast-title">${escapeHtml(title)}</div>
      <div class="toast-msg">${escapeHtml(message)}</div>
    </div>
  `;

  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateX(50px)';
    setTimeout(() => toast.remove(), 350);
  }, 4000);
}

function escapeHtml(str) {
  if (str === null || str === undefined) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

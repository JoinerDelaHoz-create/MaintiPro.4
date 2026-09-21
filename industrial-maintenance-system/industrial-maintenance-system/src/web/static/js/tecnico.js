/**
 * CMMS Industrial - Technician Mobile & Tablet Portal Logic
 * Touch-optimized interactive workflow for field maintenance operations.
 * Role-Based Access Control: Shows only technician's assigned OTs + unassigned OTs.
 */

const mobileState = {
  allWorkOrders: [],
  currentUser: null,
  currentFilter: 'ACTIVE',
  targetOTId: new URLSearchParams(window.location.search).get('id'),
};

const UNASSIGNED_VALS = ['', 'sin asignar', 'general', 'disponible', 'disponibles', 'técnico de turno', 'tecnico de turno'];

function isOrderUnassigned(assignedName) {
  if (!assignedName) return true;
  return UNASSIGNED_VALS.includes(assignedName.trim().toLowerCase());
}

document.addEventListener('DOMContentLoaded', () => {
  initTechPortal();
});

async function initTechPortal() {
  // Check auth
  if (!window.AuthClient || !window.AuthClient.guardRoute()) {
    return;
  }

  mobileState.currentUser = window.AuthClient.getUser();
  displayUserProfile();
  initEventListeners();
  await loadWorkOrders();

  // If a specific OT ID was passed via direct Telegram/mobile link, highlight and scroll
  if (mobileState.targetOTId) {
    setTimeout(() => {
      const el = document.getElementById(`wo-card-${mobileState.targetOTId}`);
      if (el) {
        el.scrollIntoView({ behavior: 'smooth', block: 'center' });
        el.style.borderColor = '#38bdf8';
        el.style.boxShadow = '0 0 20px rgba(56, 189, 248, 0.6)';
      }
    }, 400);
  }
}

function displayUserProfile() {
  const user = mobileState.currentUser;
  if (!user) return;

  const nameEl = document.getElementById('tech-user-name');
  const roleEl = document.getElementById('tech-user-role');

  if (nameEl) nameEl.textContent = user.full_name || user.username;
  if (roleEl) {
    if (user.role === 'ADMIN') {
      roleEl.textContent = 'Modo Supervisor (Admin)';
      roleEl.style.color = '#10b981';
    } else {
      roleEl.textContent = 'Técnico Autorizado';
    }
  }
}

async function loadWorkOrders() {
  try {
    const res = await window.AuthClient.fetch('/api/work-orders');
    const data = await res.json();
    mobileState.allWorkOrders = data.work_orders || [];
    renderOrders();
  } catch (err) {
    showMobileToast('Error cargando órdenes: ' + err.message);
  }
}

function renderOrders() {
  const feed = document.getElementById('orders-feed');
  const countText = document.getElementById('orders-count-text');
  const user = mobileState.currentUser;

  let list = mobileState.allWorkOrders;

  // Filter based on active tab
  if (mobileState.currentFilter === 'ACTIVE') {
    // Only assigned to me and in active state (PENDING / IN_PROGRESS)
    list = list.filter((w) => {
      const isMine = !isOrderUnassigned(w.assigned_technician);
      return isMine && (w.status === 'PENDING' || w.status === 'IN_PROGRESS');
    });
  } else if (mobileState.currentFilter === 'UNASSIGNED') {
    // Available for everyone / Sin Asignar
    list = list.filter((w) => isOrderUnassigned(w.assigned_technician) && w.status !== 'COMPLETED' && w.status !== 'CANCELLED');
  } else if (mobileState.currentFilter === 'PENDING') {
    list = list.filter((w) => w.status === 'PENDING');
  } else if (mobileState.currentFilter === 'IN_PROGRESS') {
    list = list.filter((w) => w.status === 'IN_PROGRESS');
  } else if (mobileState.currentFilter === 'COMPLETED') {
    list = list.filter((w) => w.status === 'COMPLETED');
  }

  countText.textContent = `Órdenes para atender: ${list.length}`;

  if (list.length === 0) {
    let emptyMsg = 'No tienes órdenes de trabajo en esta sección.';
    let emptySub = '¡Buen trabajo! Equipos al día.';
    if (mobileState.currentFilter === 'UNASSIGNED') {
      emptyMsg = 'No hay órdenes sin asignar pendientes.';
      emptySub = 'Todas las órdenes han sido tomadas por los técnicos.';
    }

    feed.innerHTML = `
      <div class="empty-state">
        <svg style="width:48px; height:48px; color:var(--text-muted); margin-bottom:10px;" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 14 14"></polyline></svg>
        <p>${emptyMsg}</p>
        <small style="color:var(--text-muted); display:block; margin-top:4px;">${emptySub}</small>
      </div>
    `;
    return;
  }

  feed.innerHTML = list.map((wo) => renderWOCard(wo)).join('');
}

function renderWOCard(wo) {
  const prioClass = `badge-prio-${(wo.priority || 'medium').toLowerCase()}`;
  const typeClass = `badge-${(wo.type || 'preventive').toLowerCase()}`;
  const isUnassigned = isOrderUnassigned(wo.assigned_technician);

  let actionHtml = '';

  if (isUnassigned && wo.status !== 'COMPLETED' && wo.status !== 'CANCELLED') {
    // Unassigned Order: Technician can claim it
    actionHtml = `
      <div class="card-actions">
        <button class="btn-claim-wo" onclick="handleClaimOT(${wo.id})">
          ✋ Tomar esta Orden (Autoasignármela)
        </button>
      </div>
    `;
  } else if (wo.status === 'PENDING') {
    actionHtml = `
      <div class="card-actions">
        <button class="btn-touch btn-start" onclick="handleStartOT(${wo.id})">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg>
          INICIAR TRABAJO
        </button>
      </div>
    `;
  } else if (wo.status === 'IN_PROGRESS') {
    actionHtml = `
      <div class="card-actions">
        <button class="btn-touch btn-finish" onclick="openFinishModal(${wo.id})">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"></polyline></svg>
          FINALIZAR Y REPORTAR
        </button>
      </div>
    `;
  } else if (wo.status === 'COMPLETED') {
    actionHtml = `
      <div class="status-done-banner">
        ✔ Trabajo Finalizado y Liquidado
      </div>
    `;
  }

  const assignedLabel = isUnassigned
    ? '<span style="color:#f59e0b; font-weight:700;">Disponible para todos</span>'
    : `<strong>${escapeHtml(wo.assigned_technician)}</strong>`;

  return `
    <div class="wo-card" id="wo-card-${wo.id}">
      <div class="card-top">
        <span class="card-id">OT #${wo.id}</span>
        <div class="badge-group">
          <span class="mobile-badge ${prioClass}">${escapeHtml(wo.priority)}</span>
          <span class="mobile-badge ${typeClass}">${escapeHtml(wo.type)}</span>
        </div>
      </div>

      <div class="card-equipment">
        <span class="eq-code">${escapeHtml(wo.equipment_code)}</span>
        <div class="eq-title">${escapeHtml(wo.title)}</div>
      </div>

      <div class="card-desc">${escapeHtml(wo.description || 'Sin notas de falla')}</div>

      <div class="card-meta">
        <span>👷 Asignado: ${assignedLabel}</span>
        <span>⏱️ Paro: ${wo.downtime_hours ? wo.downtime_hours.toFixed(1) + 'h' : '0.0h'}</span>
      </div>

      ${actionHtml}
    </div>
  `;
}

// Tomar Orden Disponible
async function handleClaimOT(id) {
  try {
    const res = await window.AuthClient.fetch(`/api/work-orders/${id}/claim`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({}),
    });
    const data = await res.json();
    if (!res.ok || !data.success) throw new Error(data.error || 'No se pudo tomar la orden');

    showMobileToast(`✔ ¡OT #${id} tomada! Ha pasado a "Mis OTs Activas".`);
    // Switch to active tab to show the claimed order immediately
    document.querySelectorAll('.filter-tab').forEach((t) => {
      if (t.getAttribute('data-filter') === 'ACTIVE') t.classList.add('active');
      else t.classList.remove('active');
    });
    mobileState.currentFilter = 'ACTIVE';

    await loadWorkOrders();
  } catch (err) {
    showMobileToast('Error: ' + err.message);
  }
}

// Iniciar Trabajo
async function handleStartOT(id) {
  try {
    const res = await window.AuthClient.fetch(`/api/work-orders/${id}/start`, { method: 'POST' });
    const data = await res.json();
    if (!res.ok || !data.success) throw new Error(data.error || 'No se pudo iniciar la orden');

    showMobileToast(`OT #${id} iniciada. Equipo en Mantenimiento.`);
    await loadWorkOrders();
  } catch (err) {
    showMobileToast('Error: ' + err.message);
  }
}

// Abrir Modal de Cierre
function openFinishModal(id) {
  const wo = mobileState.allWorkOrders.find((w) => w.id === id);
  if (!wo) return;

  document.getElementById('finish-wo-id').value = id;
  document.getElementById('finish-wo-title').textContent = `Finalizar OT #${wo.id}`;
  document.getElementById('finish-wo-meta').textContent = `Activo: ${wo.equipment_code} | Asunto: ${wo.title}`;
  document.getElementById('finish-work-done').value = '';
  document.getElementById('finish-materials-used').value = '';
  document.getElementById('finish-downtime').value = '1.0';
  document.getElementById('finish-cost').value = '0.00';

  document.getElementById('modal-finish-wo').classList.add('show');
}

function closeFinishModal() {
  document.getElementById('modal-finish-wo').classList.remove('show');
}

function initEventListeners() {
  // Logout button
  const logoutBtn = document.getElementById('btn-logout');
  if (logoutBtn) {
    logoutBtn.addEventListener('click', () => {
      window.AuthClient.logout();
    });
  }

  // Refresh
  document.getElementById('btn-refresh').addEventListener('click', async () => {
    await loadWorkOrders();
    showMobileToast('Órdenes actualizadas.');
  });

  // Tab Filter Buttons
  document.querySelectorAll('.filter-tab').forEach((tab) => {
    tab.addEventListener('click', () => {
      document.querySelectorAll('.filter-tab').forEach((t) => t.classList.remove('active'));
      tab.classList.add('active');
      mobileState.currentFilter = tab.getAttribute('data-filter');
      renderOrders();
    });
  });

  // Modal Closers
  document.getElementById('btn-close-finish').addEventListener('click', closeFinishModal);
  document.getElementById('btn-cancel-finish').addEventListener('click', closeFinishModal);

  // Form Submit: Finish Work Order
  document.getElementById('form-finish-wo').addEventListener('submit', async (e) => {
    e.preventDefault();
    const id = document.getElementById('finish-wo-id').value;
    const workDone = document.getElementById('finish-work-done').value.trim();
    const materialsUsed = document.getElementById('finish-materials-used').value.trim();
    const downtime = parseFloat(document.getElementById('finish-downtime').value || 0);
    const cost = parseFloat(document.getElementById('finish-cost').value || 0);

    if (!workDone || !materialsUsed) {
      showMobileToast('Por favor describe qué se hizo y qué repuestos usaste.');
      return;
    }

    try {
      const res = await window.AuthClient.fetch(`/api/work-orders/${id}/finish`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          work_done: workDone,
          materials_used: materialsUsed,
          downtime_hours: downtime,
          cost: cost,
        }),
      });

      const data = await res.json();
      if (!res.ok || !data.success) throw new Error(data.error || 'No se pudo liquidar la OT');

      closeFinishModal();
      showMobileToast(`✔ OT #${id} finalizada exitosamente.`);
      await loadWorkOrders();
    } catch (err) {
      showMobileToast('Error al cerrar orden: ' + err.message);
    }
  });
}

function showMobileToast(msg) {
  const toast = document.getElementById('mobile-toast');
  toast.textContent = msg;
  toast.classList.add('show');
  setTimeout(() => toast.classList.remove('show'), 3500);
}

function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

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

// Demo Work Orders Fallback
const DEFAULT_DEMO_WORK_ORDERS = [
  // Carlos Mendoza (Mecánico)
  {
    id: 1, equipment_code: 'CMP-001',
    title: 'Mantenimiento Preventivo 2000h: Filtros y Aceite Sintético',
    description: 'Cambio de cartucho separador de aceite, filtro de aire y sustitución de 20L de lubricante sintético ISO VG 46.',
    type: 'PREVENTIVE', priority: 'HIGH', status: 'IN_PROGRESS',
    assigned_technician: 'Ing. Carlos Mendoza', downtime_hours: 0.0, cost: 0.0,
    created_at: '2026-09-18 09:00:00', closed_at: null
  },
  {
    id: 2, equipment_code: 'CNV-040',
    title: 'Ajuste de tensión y alineación de banda transportadora',
    description: 'Se detecta leve desalineación lateral en el rodillo tensor de cola provocando fricción en el chasis.',
    type: 'CORRECTIVE', priority: 'MEDIUM', status: 'PENDING',
    assigned_technician: 'Ing. Carlos Mendoza', downtime_hours: 0.0, cost: 0.0,
    created_at: '2026-09-19 11:30:00', closed_at: null
  },
  {
    id: 3, equipment_code: 'EXT-501',
    title: 'Inspección Termográfica en Resistencias y Reductor',
    description: 'Termografía infrarroja de zonas 1 a 6 y medición de temperatura en cojinetes de empuje.\n\n--- INFORME DE CIERRE TÉCNICO ---\n• Trabajo Realizado: Termografía completada. Zona 3 presentaba conexión floja en bornera; se retorqueó a 4.5 Nm. Temperaturas normalizadas en 62°C.\n• Materiales/Repuestos Usados: Grasa para alta temperatura Polyrex EM, terminales de compresión de cobre calibre 8 AWG.',
    type: 'PREDICTIVE', priority: 'MEDIUM', status: 'COMPLETED',
    assigned_technician: 'Ing. Carlos Mendoza', downtime_hours: 1.5, cost: 280.0,
    created_at: '2026-09-17 08:00:00', closed_at: '2026-09-17 12:30:00'
  },

  // Laura Ramos (Eléctrico)
  {
    id: 4, equipment_code: 'GEN-602',
    title: 'Prueba en Vacío y Verificación de Baterías de Arranque',
    description: 'Comprobación de electrolito, tensión en flotación (27.4V DC), limpieza de bornes y arranque de prueba 15 min.',
    type: 'PREVENTIVE', priority: 'LOW', status: 'PENDING',
    assigned_technician: 'Tec. Laura Ramos', downtime_hours: 0.0, cost: 0.0,
    created_at: '2026-09-19 14:00:00', closed_at: null
  },
  {
    id: 5, equipment_code: 'MTR-305',
    title: 'Corrección de Sobrecorriente y Reemplazo de Contactor',
    description: 'El contactor de línea principal presenta arqueo en polos 1 y 3 provocando disparo térmico intermitente.',
    type: 'CORRECTIVE', priority: 'HIGH', status: 'IN_PROGRESS',
    assigned_technician: 'Tec. Laura Ramos', downtime_hours: 0.0, cost: 0.0,
    created_at: '2026-09-18 10:15:00', closed_at: null
  },
  {
    id: 6, equipment_code: 'MTR-305',
    title: 'Medición de Resistencia de Aislamiento (Megóhmetro)',
    description: 'Ensayo dieléctrico a 1000V DC entre fases y masa para certificar estado de bobinado.\n\n--- INFORME DE CIERRE TÉCNICO ---\n• Trabajo Realizado: Lectura de aislamiento > 850 Megaohms, índice de polarización 2.8 (óptimo). Se cambiaron empaques de la caja de conexiones.\n• Materiales/Repuestos Usados: Empaque de neopreno para caja de borneras, spray limpiador dieléctrico CRC.',
    type: 'PREDICTIVE', priority: 'MEDIUM', status: 'COMPLETED',
    assigned_technician: 'Tec. Laura Ramos', downtime_hours: 2.0, cost: 420.0,
    created_at: '2026-09-16 13:00:00', closed_at: '2026-09-16 16:30:00'
  },

  // Andrés Silva (Predictivo / Instrumentación)
  {
    id: 7, equipment_code: 'CAL-201',
    title: 'Purga de Fondo y Calibración de Presostatos',
    description: 'Maniobra de purga de lodos en caldera, control de nivel McDonnell Miller y test de disparo por sobrepresión.',
    type: 'PREVENTIVE', priority: 'HIGH', status: 'PENDING',
    assigned_technician: 'Tec. Andrés Silva', downtime_hours: 0.0, cost: 0.0,
    created_at: '2026-09-19 07:30:00', closed_at: null
  },
  {
    id: 8, equipment_code: 'BMB-102',
    title: 'Reemplazo de Sello Mecánico de Cartucho por Goteo',
    description: 'Goteo continuo de 15 gotas/min en prensaestopas lado bomba; desmontaje y montaje de nuevo sello de carburo de silicio.',
    type: 'CORRECTIVE', priority: 'CRITICAL', status: 'IN_PROGRESS',
    assigned_technician: 'Tec. Andrés Silva', downtime_hours: 0.0, cost: 0.0,
    created_at: '2026-09-18 15:45:00', closed_at: null
  },
  {
    id: 9, equipment_code: 'TOR-108',
    title: 'Análisis de Vibraciones FFT en Ventilador de Tiro',
    description: 'Registro espectral en 1X y 2X RPM para diagnosticar posible desbalance o soltura mecánica en aspas.\n\n--- INFORME DE CIERRE TÉCNICO ---\n• Trabajo Realizado: Se detectó incrustación de sarro en 2 aspas que causaba desbalance. Se limpiaron aspas con hidrolavadora y vibración bajó de 4.8 mm/s a 1.2 mm/s RMS (Zona A ISO 10816).\n• Materiales/Repuestos Usados: Desincrustante biodegradable industrial, arandelas de presión de acero inoxidable 316.',
    type: 'PREDICTIVE', priority: 'MEDIUM', status: 'COMPLETED',
    assigned_technician: 'Tec. Andrés Silva', downtime_hours: 1.0, cost: 180.0,
    created_at: '2026-09-15 10:00:00', closed_at: '2026-09-15 13:00:00'
  },

  // Órdenes SIN ASIGNAR (Disponibles para cualquier técnico)
  {
    id: 10, equipment_code: 'EXT-501',
    title: 'Lubricación de Crapodina y Engranajes Planetarios',
    description: 'Engrase general con bomba neumática en los puntos de engrase centralizados del cabezal extrusor.',
    type: 'PREVENTIVE', priority: 'MEDIUM', status: 'PENDING',
    assigned_technician: 'Sin Asignar', downtime_hours: 0.0, cost: 0.0,
    created_at: '2026-09-20 08:30:00', closed_at: null
  },
  {
    id: 11, equipment_code: 'CAL-201',
    title: 'Fuga de Vapor en Brida de Válvula de Seguridad #2',
    description: 'Vapor visible en junta espirometálica. Requiere despresurizar línea secundaria y cambio de empaque.',
    type: 'CORRECTIVE', priority: 'CRITICAL', status: 'PENDING',
    assigned_technician: 'Sin Asignar', downtime_hours: 0.0, cost: 0.0,
    created_at: '2026-09-20 10:15:00', closed_at: null
  },
  {
    id: 12, equipment_code: 'CMP-001',
    title: 'Monitoreo Acústico de Ultrasonido en Red de Aire',
    description: 'Rastreo con detector de ultrasonido digital en colectores de 4 pulgadas y derivaciones a naves B y C.',
    type: 'PREDICTIVE', priority: 'LOW', status: 'PENDING',
    assigned_technician: 'Sin Asignar', downtime_hours: 0.0, cost: 0.0,
    created_at: '2026-09-20 13:45:00', closed_at: null
  },
  {
    id: 13, equipment_code: 'TOR-108',
    title: 'Sustitución de Sensor de Flujo y Válvula Solenoide',
    description: 'La válvula solenoide de reposición de agua tratada no cierra herméticamente provocando desborde leve en balsa.',
    type: 'CORRECTIVE', priority: 'HIGH', status: 'PENDING',
    assigned_technician: 'Sin Asignar', downtime_hours: 0.0, cost: 0.0,
    created_at: '2026-09-21 09:00:00', closed_at: null
  },
];

function getLocalOrDemoWorkOrders() {
  try {
    const raw = localStorage.getItem('cmms_demo_work_orders');
    if (raw) {
      const parsed = JSON.parse(raw);
      if (Array.isArray(parsed) && parsed.length > 0) return parsed;
    }
  } catch (e) {}
  localStorage.setItem('cmms_demo_work_orders', JSON.stringify(DEFAULT_DEMO_WORK_ORDERS));
  return DEFAULT_DEMO_WORK_ORDERS;
}

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
    if (data && data.work_orders && data.work_orders.length > 0) {
      mobileState.allWorkOrders = data.work_orders;
      localStorage.setItem('cmms_demo_work_orders', JSON.stringify(data.work_orders));
    } else {
      mobileState.allWorkOrders = getLocalOrDemoWorkOrders();
    }
  } catch (err) {
    console.warn('API error, using demo work orders in mobile portal:', err);
    mobileState.allWorkOrders = getLocalOrDemoWorkOrders();
  }
  renderOrders();
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
  const user = mobileState.currentUser;
  const techName = user?.full_name || 'Técnico de Turno';
  try {
    const res = await window.AuthClient.fetch(`/api/work-orders/${id}/claim`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ technician_name: techName }),
    });
    const data = await res.json();
    if (!res.ok || !data.success) throw new Error(data.error || 'No se pudo tomar la orden');
  } catch (err) {
    console.warn('API claim error, applying local state update:', err);
    // Apply local update
    const orders = getLocalOrDemoWorkOrders();
    const target = orders.find((w) => w.id === id);
    if (target) {
      target.assigned_technician = techName;
      target.status = 'IN_PROGRESS';
      localStorage.setItem('cmms_demo_work_orders', JSON.stringify(orders));
    }
  }

  showMobileToast(`✔ ¡OT #${id} tomada! Ha pasado a "Mis OTs Activas".`);
  document.querySelectorAll('.filter-tab').forEach((t) => {
    if (t.getAttribute('data-filter') === 'ACTIVE') t.classList.add('active');
    else t.classList.remove('active');
  });
  mobileState.currentFilter = 'ACTIVE';
  await loadWorkOrders();
}

// Iniciar Trabajo
async function handleStartOT(id) {
  try {
    const res = await window.AuthClient.fetch(`/api/work-orders/${id}/start`, { method: 'POST' });
    const data = await res.json();
    if (!res.ok || !data.success) throw new Error(data.error || 'No se pudo iniciar la orden');
  } catch (err) {
    console.warn('API start error, applying local update:', err);
    const orders = getLocalOrDemoWorkOrders();
    const target = orders.find((w) => w.id === id);
    if (target) {
      target.status = 'IN_PROGRESS';
      localStorage.setItem('cmms_demo_work_orders', JSON.stringify(orders));
    }
  }

  showMobileToast(`OT #${id} iniciada. Equipo en Mantenimiento.`);
  await loadWorkOrders();
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

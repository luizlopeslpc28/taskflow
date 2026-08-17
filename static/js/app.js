/**
 * TaskFlow — Frontend (Flask API)
 * Workspaces + Kanban drag & drop
 */

(function () {
  'use strict';

  const THEME_KEY = 'taskflow_theme';
  const ACTIVE_WS_KEY = 'taskflow_active_ws';

  let state = {
    workspaces: [],
    tasks: [],
    activeWorkspaceId: null,
    editingWorkspaceId: null,
    editingTaskId: null,
    confirmAction: null,
  };

  const $ = (sel) => document.querySelector(sel);
  const $$ = (sel) => document.querySelectorAll(sel);

  const els = {
    workspaceList: $('#workspace-list'),
    emptyState: $('#empty-state'),
    workspaceView: $('#workspace-view'),
    workspaceTitle: $('#workspace-title'),
    taskCount: $('#task-count'),
    btnToggleTheme: $('#btn-toggle-theme'),
    btnCreateWorkspace: $('#btn-create-workspace'),
    btnEmptyCreate: $('#btn-empty-create'),
    btnEditWorkspace: $('#btn-edit-workspace'),
    btnDeleteWorkspace: $('#btn-delete-workspace'),
    btnAddTask: $('#btn-add-task'),
    modalWorkspace: $('#modal-workspace'),
    modalTask: $('#modal-task'),
    modalConfirm: $('#modal-confirm'),
    formWorkspace: $('#form-workspace'),
    formTask: $('#form-task'),
    workspaceName: $('#workspace-name'),
    taskTitle: $('#task-title'),
    taskDescription: $('#task-description'),
    taskStatus: $('#task-status'),
    modalWorkspaceTitle: $('#modal-workspace-title'),
    modalTaskTitle: $('#modal-task-title'),
    btnSaveWorkspace: $('#btn-save-workspace'),
    btnSaveTask: $('#btn-save-task'),
    confirmTitle: $('#confirm-title'),
    confirmMessage: $('#confirm-message'),
    btnConfirmDelete: $('#btn-confirm-delete'),
    countPendente: $('#count-pendente'),
    countEmProducao: $('#count-em_producao'),
    countFinalizado: $('#count-finalizado'),
    toast: $('#toast'),
  };

  // ---------- API ----------
  async function api(method, path, body) {
    const opts = {
      method,
      headers: { 'Content-Type': 'application/json' },
    };
    if (body !== undefined) opts.body = JSON.stringify(body);
    const res = await fetch(path, opts);
    if (res.status === 401) {
      window.location.href = '/login';
      throw new Error('Não autenticado');
    }
    let data = null;
    try {
      data = await res.json();
    } catch (_) {}
    if (!res.ok) {
      const msg = (data && data.error) || `Erro ${res.status}`;
      throw new Error(msg);
    }
    return data;
  }

  function showToast(message, isError) {
    els.toast.textContent = message;
    els.toast.classList.toggle('error', !!isError);
    els.toast.classList.remove('hidden');
    clearTimeout(showToast._t);
    showToast._t = setTimeout(() => els.toast.classList.add('hidden'), 2800);
  }

  // ---------- Utils ----------
  function formatDate(iso) {
    if (!iso) return '';
    const d = new Date(iso);
    return d.toLocaleDateString('pt-BR', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
    });
  }

  function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }

  function getActiveWorkspace() {
    return state.workspaces.find((w) => w.id === state.activeWorkspaceId) || null;
  }

  // ---------- Theme ----------
  function initTheme() {
    const saved = localStorage.getItem(THEME_KEY);
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    const theme = saved || (prefersDark ? 'dark' : 'light');
    document.documentElement.setAttribute('data-theme', theme);
  }

  function toggleTheme() {
    const current = document.documentElement.getAttribute('data-theme');
    const next = current === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', next);
    localStorage.setItem(THEME_KEY, next);
  }

  // ---------- Modals ----------
  function openModal(id) {
    const modal = document.getElementById(id);
    if (modal) modal.classList.remove('hidden');
  }

  function closeModal(id) {
    const modal = document.getElementById(id);
    if (modal) modal.classList.add('hidden');
  }

  function closeAllModals() {
    $$('.modal-overlay').forEach((m) => m.classList.add('hidden'));
  }

  // ---------- Data load ----------
  async function loadWorkspaces() {
    state.workspaces = await api('GET', '/api/workspaces');
    const saved = localStorage.getItem(ACTIVE_WS_KEY);
    if (saved && state.workspaces.some((w) => w.id === saved)) {
      state.activeWorkspaceId = saved;
    } else if (state.workspaces.length && !state.activeWorkspaceId) {
      state.activeWorkspaceId = state.workspaces[0].id;
    } else if (
      state.activeWorkspaceId &&
      !state.workspaces.some((w) => w.id === state.activeWorkspaceId)
    ) {
      state.activeWorkspaceId = state.workspaces.length
        ? state.workspaces[0].id
        : null;
    }
    if (state.activeWorkspaceId) {
      localStorage.setItem(ACTIVE_WS_KEY, state.activeWorkspaceId);
    }
  }

  async function loadTasks() {
    if (!state.activeWorkspaceId) {
      state.tasks = [];
      return;
    }
    state.tasks = await api(
      'GET',
      `/api/workspaces/${state.activeWorkspaceId}/tasks`
    );
  }

  // ---------- Workspace CRUD ----------
  function openCreateWorkspace() {
    state.editingWorkspaceId = null;
    els.modalWorkspaceTitle.textContent = 'Novo workspace';
    els.btnSaveWorkspace.textContent = 'Criar';
    els.workspaceName.value = '';
    openModal('modal-workspace');
    setTimeout(() => els.workspaceName.focus(), 50);
  }

  function openEditWorkspace() {
    const ws = getActiveWorkspace();
    if (!ws) return;
    state.editingWorkspaceId = ws.id;
    els.modalWorkspaceTitle.textContent = 'Editar workspace';
    els.btnSaveWorkspace.textContent = 'Salvar';
    els.workspaceName.value = ws.name;
    openModal('modal-workspace');
    setTimeout(() => {
      els.workspaceName.focus();
      els.workspaceName.select();
    }, 50);
  }

  async function saveWorkspace(e) {
    e.preventDefault();
    const name = els.workspaceName.value.trim();
    if (!name) return;

    try {
      if (state.editingWorkspaceId) {
        await api('PUT', `/api/workspaces/${state.editingWorkspaceId}`, { name });
        showToast('Workspace atualizado');
      } else {
        const ws = await api('POST', '/api/workspaces', { name });
        state.activeWorkspaceId = ws.id;
        localStorage.setItem(ACTIVE_WS_KEY, ws.id);
        showToast('Workspace criado');
      }
      closeModal('modal-workspace');
      await loadWorkspaces();
      await loadTasks();
      render();
    } catch (err) {
      showToast(err.message, true);
    }
  }

  function confirmDeleteWorkspace() {
    const ws = getActiveWorkspace();
    if (!ws) return;
    state.confirmAction = { type: 'workspace', id: ws.id };
    els.confirmTitle.textContent = 'Excluir workspace';
    els.confirmMessage.textContent = `Tem certeza que deseja excluir o workspace "${ws.name}"? Todas as tarefas nele serão removidas permanentemente.`;
    openModal('modal-confirm');
  }

  async function deleteWorkspace(id) {
    try {
      await api('DELETE', `/api/workspaces/${id}`);
      if (state.activeWorkspaceId === id) {
        state.activeWorkspaceId = null;
        localStorage.removeItem(ACTIVE_WS_KEY);
      }
      showToast('Workspace excluído');
      await loadWorkspaces();
      await loadTasks();
      render();
    } catch (err) {
      showToast(err.message, true);
    }
  }

  async function selectWorkspace(id) {
    state.activeWorkspaceId = id;
    localStorage.setItem(ACTIVE_WS_KEY, id);
    await loadTasks();
    render();
  }

  // ---------- Task CRUD ----------
  function openCreateTask() {
    if (!state.activeWorkspaceId) return;
    state.editingTaskId = null;
    els.modalTaskTitle.textContent = 'Nova tarefa';
    els.btnSaveTask.textContent = 'Criar tarefa';
    els.taskTitle.value = '';
    els.taskDescription.value = '';
    els.taskStatus.value = 'pendente';
    openModal('modal-task');
    setTimeout(() => els.taskTitle.focus(), 50);
  }

  function openEditTask(taskId) {
    const task = state.tasks.find((t) => t.id === taskId);
    if (!task) return;
    state.editingTaskId = taskId;
    els.modalTaskTitle.textContent = 'Editar tarefa';
    els.btnSaveTask.textContent = 'Salvar';
    els.taskTitle.value = task.title;
    els.taskDescription.value = task.description || '';
    els.taskStatus.value = task.status;
    openModal('modal-task');
    setTimeout(() => {
      els.taskTitle.focus();
      els.taskTitle.select();
    }, 50);
  }

  async function saveTask(e) {
    e.preventDefault();
    const title = els.taskTitle.value.trim();
    if (!title) return;

    const payload = {
      title,
      description: els.taskDescription.value.trim(),
      status: els.taskStatus.value,
    };

    try {
      if (state.editingTaskId) {
        await api('PUT', `/api/tasks/${state.editingTaskId}`, payload);
        showToast('Tarefa atualizada');
      } else {
        await api(
          'POST',
          `/api/workspaces/${state.activeWorkspaceId}/tasks`,
          payload
        );
        showToast('Tarefa criada');
      }
      closeModal('modal-task');
      await loadTasks();
      renderKanban();
      updateCounts();
    } catch (err) {
      showToast(err.message, true);
    }
  }

  function confirmDeleteTask(taskId) {
    const task = state.tasks.find((t) => t.id === taskId);
    if (!task) return;
    state.confirmAction = { type: 'task', id: taskId };
    els.confirmTitle.textContent = 'Excluir tarefa';
    els.confirmMessage.textContent = `Tem certeza que deseja excluir a tarefa "${task.title}"?`;
    openModal('modal-confirm');
  }

  async function deleteTask(id) {
    try {
      await api('DELETE', `/api/tasks/${id}`);
      showToast('Tarefa excluída');
      await loadTasks();
      renderKanban();
      updateCounts();
    } catch (err) {
      showToast(err.message, true);
    }
  }

  async function updateTaskStatus(taskId, newStatus) {
    const task = state.tasks.find((t) => t.id === taskId);
    if (!task || task.status === newStatus) return;
    try {
      await api('PATCH', `/api/tasks/${taskId}/status`, { status: newStatus });
      await loadTasks();
      renderKanban();
      updateCounts();
    } catch (err) {
      showToast(err.message, true);
    }
  }

  async function handleConfirmDelete() {
    if (!state.confirmAction) return;
    const { type, id } = state.confirmAction;
    closeModal('modal-confirm');
    if (type === 'workspace') await deleteWorkspace(id);
    else if (type === 'task') await deleteTask(id);
    state.confirmAction = null;
  }

  // ---------- Render ----------
  function renderWorkspaceList() {
    els.workspaceList.innerHTML = '';
    state.workspaces.forEach((ws) => {
      const btn = document.createElement('button');
      btn.className =
        'workspace-item' + (ws.id === state.activeWorkspaceId ? ' active' : '');
      btn.innerHTML = `
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round">
          <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>
        </svg>
        <span>${escapeHtml(ws.name)}</span>
      `;
      btn.addEventListener('click', () => selectWorkspace(ws.id));
      els.workspaceList.appendChild(btn);
    });
  }

  function renderKanban() {
    const statuses = ['pendente', 'em_producao', 'finalizado'];

    statuses.forEach((status) => {
      const body = $(`.column-body[data-status="${status}"]`);
      if (!body) return;
      body.innerHTML = '';

      const filtered = state.tasks.filter((t) => t.status === status);

      if (filtered.length === 0) {
        body.innerHTML = '<div class="column-empty">Nenhuma tarefa</div>';
        return;
      }

      filtered.forEach((task) => {
        body.appendChild(createTaskCard(task));
      });
    });
  }

  function createTaskCard(task) {
    const card = document.createElement('div');
    card.className = 'task-card';
    card.draggable = true;
    card.dataset.taskId = task.id;

    const descHtml = task.description
      ? `<p class="task-card-desc">${escapeHtml(task.description)}</p>`
      : '';

    card.innerHTML = `
      <div class="task-card-header">
        <div class="task-card-title">${escapeHtml(task.title)}</div>
        <div class="task-card-actions">
          <button class="task-action-btn" data-action="edit" title="Editar" aria-label="Editar tarefa">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round">
              <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
              <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
            </svg>
          </button>
          <button class="task-action-btn danger" data-action="delete" title="Excluir" aria-label="Excluir tarefa">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round">
              <polyline points="3 6 5 6 21 6"/>
              <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
            </svg>
          </button>
        </div>
      </div>
      ${descHtml}
      <div class="task-card-meta">
        <span class="task-card-date">${formatDate(task.created_at)}</span>
      </div>
    `;

    card.querySelector('[data-action="edit"]').addEventListener('click', (e) => {
      e.stopPropagation();
      openEditTask(task.id);
    });
    card.querySelector('[data-action="delete"]').addEventListener('click', (e) => {
      e.stopPropagation();
      confirmDeleteTask(task.id);
    });

    card.addEventListener('dragstart', handleDragStart);
    card.addEventListener('dragend', handleDragEnd);

    return card;
  }

  function updateCounts() {
    const counts = { pendente: 0, em_producao: 0, finalizado: 0 };
    state.tasks.forEach((t) => {
      if (counts[t.status] !== undefined) counts[t.status]++;
    });
    els.countPendente.textContent = counts.pendente;
    els.countEmProducao.textContent = counts.em_producao;
    els.countFinalizado.textContent = counts.finalizado;
    const total = state.tasks.length;
    els.taskCount.textContent = total === 1 ? '1 tarefa' : `${total} tarefas`;
  }

  function render() {
    renderWorkspaceList();
    const ws = getActiveWorkspace();
    if (!ws) {
      els.emptyState.classList.remove('hidden');
      els.workspaceView.classList.add('hidden');
      return;
    }
    els.emptyState.classList.add('hidden');
    els.workspaceView.classList.remove('hidden');
    els.workspaceTitle.textContent = ws.name;
    renderKanban();
    updateCounts();
  }

  // ---------- Drag & Drop ----------
  let draggedTaskId = null;

  function handleDragStart(e) {
    draggedTaskId = e.currentTarget.dataset.taskId;
    e.currentTarget.classList.add('dragging');
    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData('text/plain', draggedTaskId);
  }

  function handleDragEnd(e) {
    e.currentTarget.classList.remove('dragging');
    draggedTaskId = null;
    $$('.column-body').forEach((col) => col.classList.remove('drag-over'));
  }

  function setupDropZones() {
    $$('.column-body').forEach((col) => {
      col.addEventListener('dragover', (e) => {
        e.preventDefault();
        e.dataTransfer.dropEffect = 'move';
        col.classList.add('drag-over');
      });
      col.addEventListener('dragleave', (e) => {
        if (!col.contains(e.relatedTarget)) col.classList.remove('drag-over');
      });
      col.addEventListener('drop', (e) => {
        e.preventDefault();
        col.classList.remove('drag-over');
        const taskId = e.dataTransfer.getData('text/plain') || draggedTaskId;
        const newStatus = col.dataset.status;
        if (taskId && newStatus) updateTaskStatus(taskId, newStatus);
      });
    });
  }

  // ---------- Events ----------
  function bindEvents() {
    const btnLogout = document.getElementById('btn-logout');
    if (btnLogout) {
      btnLogout.addEventListener('click', async () => {
        try {
          await fetch('/api/auth/logout', { method: 'POST' });
        } catch (_) {}
        window.location.href = '/login';
      });
    }
    els.btnToggleTheme.addEventListener('click', toggleTheme);
    els.btnCreateWorkspace.addEventListener('click', openCreateWorkspace);
    els.btnEmptyCreate.addEventListener('click', openCreateWorkspace);
    els.btnEditWorkspace.addEventListener('click', openEditWorkspace);
    els.btnDeleteWorkspace.addEventListener('click', confirmDeleteWorkspace);
    els.btnAddTask.addEventListener('click', openCreateTask);

    els.formWorkspace.addEventListener('submit', saveWorkspace);
    els.formTask.addEventListener('submit', saveTask);
    els.btnConfirmDelete.addEventListener('click', handleConfirmDelete);

    $$('[data-close]').forEach((btn) => {
      btn.addEventListener('click', () => closeModal(btn.dataset.close));
    });

    $$('.modal-overlay').forEach((overlay) => {
      overlay.addEventListener('click', (e) => {
        if (e.target === overlay) overlay.classList.add('hidden');
      });
    });

    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') closeAllModals();
    });
  }

  // ---------- Init ----------
  async function init() {
    initTheme();
    bindEvents();
    setupDropZones();
    try {
      await loadWorkspaces();
      await loadTasks();
      render();
    } catch (err) {
      showToast('Erro ao carregar dados: ' + err.message, true);
      render();
    }
  }

  init();
})();

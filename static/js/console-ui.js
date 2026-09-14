(() => {
  const tabs = [...document.querySelectorAll('[role="tab"][data-panel]')];
  const panels = [...document.querySelectorAll('[role="tabpanel"]')];
  const sourceStatus = document.getElementById('status');
  const summary = document.getElementById('connectionStatus');

  function selectPanel(panelId) {
    tabs.forEach((tab) => {
      const selected = tab.dataset.panel === panelId;
      tab.setAttribute('aria-selected', String(selected));
      tab.tabIndex = selected ? 0 : -1;
    });
    panels.forEach((panel) => { panel.hidden = panel.id !== panelId; });
  }

  tabs.forEach((tab, index) => {
    tab.addEventListener('click', () => selectPanel(tab.dataset.panel));
    tab.addEventListener('keydown', (event) => {
      if (!['ArrowLeft', 'ArrowRight'].includes(event.key)) return;
      event.preventDefault();
      const nextIndex = (index + (event.key === 'ArrowRight' ? 1 : tabs.length - 1)) % tabs.length;
      tabs[nextIndex].focus();
      selectPanel(tabs[nextIndex].dataset.panel);
    });
  });

  function syncStatus() {
    if (!summary || !sourceStatus) return;
    const message = sourceStatus.textContent.trim();
    summary.textContent = message || 'Đang chuẩn bị kết nối thiết bị…';
    const normalized = message.toLocaleLowerCase('vi');
    summary.dataset.tone = normalized.includes('đã kết nối') ? 'success'
      : normalized.includes('mất kết nối') || normalized.includes('bị từ chối') ? 'danger'
      : normalized.includes('đang') ? 'connecting' : 'warning';
  }

  if (sourceStatus && summary) {
    new MutationObserver(syncStatus).observe(sourceStatus, { childList: true, characterData: true, subtree: true });
    syncStatus();
  }
})();

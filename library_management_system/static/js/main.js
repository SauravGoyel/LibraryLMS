// Sidebar toggle
const sidebar = document.getElementById('sidebar');
const toggleBtn = document.getElementById('sidebarToggle');
const body = document.body;

if (toggleBtn && sidebar) {
  toggleBtn.addEventListener('click', () => {
    if (window.innerWidth <= 768) {
      body.classList.toggle('sidebar-open');
    } else {
      body.classList.toggle('sidebar-collapsed');
    }
  });

  // Close sidebar on overlay click (mobile)
  document.addEventListener('click', (e) => {
    if (window.innerWidth <= 768 &&
        !sidebar.contains(e.target) &&
        !toggleBtn.contains(e.target) &&
        body.classList.contains('sidebar-open')) {
      body.classList.remove('sidebar-open');
    }
  });
}

// Auto-dismiss alerts after 4 seconds
document.querySelectorAll('.alert.alert-dismissible').forEach(alert => {
  setTimeout(() => {
    const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
    if (bsAlert) bsAlert.close();
  }, 4000);
});

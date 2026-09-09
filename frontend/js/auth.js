// Shared browser authentication helper used by every protected page.
const AUTH_STORAGE_KEY = 'currentUser';

function getCurrentUser() {
  // Corrupted browser storage is treated as a logged-out state.
  try {
    return JSON.parse(localStorage.getItem(AUTH_STORAGE_KEY) || 'null');
  } catch (error) {
    localStorage.removeItem(AUTH_STORAGE_KEY);
    return null;
  }
}

function requireAuth() {
  // Preserve the requested URL so login can return to the original workflow.
  if (getCurrentUser()) {
    return true;
  }

  const next = `${window.location.pathname}${window.location.search}`;
  window.location.replace(`/login?next=${encodeURIComponent(next)}`);
  return false;
}

function requireRole(...allowedRoles) {
  const user = getCurrentUser();
  if (user && allowedRoles.includes(user.role)) {
    return true;
  }

  const next = `${window.location.pathname}${window.location.search}`;
  window.location.replace(user ? '/' : `/login?next=${encodeURIComponent(next)}`);
  return false;
}

function logout() {
  // Clear identity and temporary detection previews before returning to login.
  fetch('/api/auth/logout', {method: 'POST', keepalive: true}).catch(() => {});
  localStorage.removeItem(AUTH_STORAGE_KEY);
  sessionStorage.removeItem('lastDetectedPlate');
  sessionStorage.removeItem('lastPreviewImg');
  window.location.replace('/login');
}

function applyPublicNavAuth() {
  // Guest links stay on public pages; logout appears only after login.
  const loggedIn = !!getCurrentUser();
  document.querySelectorAll('[data-auth]').forEach((el) => {
    el.hidden = !loggedIn;
  });
  document.querySelectorAll('[data-guest]').forEach((el) => {
    el.hidden = loggedIn;
  });
}

function openAdministrativeControl(event) {
  // Administrative Control is only available after a successful login.
  if (event) {
    event.preventDefault();
  }

  if (!getCurrentUser()) {
    window.location.replace(`/login?next=${encodeURIComponent('/dashboard')}`);
    return false;
  }

  window.location.assign('/dashboard');
  return false;
}

function redirectAfterAuth(defaultPath = null) {
  // Accept only local paths from the next parameter.
  const next = new URLSearchParams(window.location.search).get('next');
  const user = getCurrentUser();
  const roleDefault = user && user.role === 'Citizen'
    ? '/citizen'
    : (user && user.role === 'Admin' ? '/vehicles' : '/dashboard');
  let destination = next && next.startsWith('/') && !next.startsWith('//')
    ? next
    : (defaultPath || roleDefault);

  if (user && user.role === 'Citizen' && !['/', '/citizen', '/number-plate', '/traffic-rules'].some((path) => destination.startsWith(path))) {
    destination = '/citizen';
  }
  if (user && user.role === 'Admin' && destination !== '/vehicles' && !destination.startsWith('/vehicles/')) {
    destination = '/vehicles';
  }
  if (user && user.role === 'Officer' && destination.startsWith('/vehicles')) {
    destination = '/dashboard';
  }
  window.location.replace(destination);
}

function getActiveNavKey() {
  const nav = document.getElementById('appNav');
  if (nav && nav.dataset.active) {
    return nav.dataset.active;
  }

  const path = window.location.pathname;
  if (path === '/' || path.endsWith('/index.html')) return 'home';
  if (path.startsWith('/dashboard')) return 'dashboard';
  if (path.startsWith('/vehicles')) return 'vehicles';
  if (path.startsWith('/number-plate') || path.startsWith('/number_plate')) return 'number-plate';
  if (path.startsWith('/reports')) return 'reports';
  if (path.startsWith('/challans') || path.startsWith('/challan') || path.startsWith('/generate-challan')) {
    return 'challans';
  }
  return '';
}

function adminControlGroupHtml(user) {
  const isOfficer = user.role === 'Officer';
  const isAdmin = user.role === 'Admin';
  const vehicleLink = isAdmin
    ? '<a href="/vehicles" class="nav-item" data-nav="vehicles"><i class="fa-solid fa-car"></i> Vehicle Registration</a>'
    : (isOfficer
      ? '<a href="/vehicles" class="nav-item" data-nav="vehicles"><i class="fa-solid fa-car"></i> Registered Vehicles</a>'
      : '');
  const challanGroup = isOfficer ? `
          <div class="nav-dropdown">
            <button type="button" class="nav-item" data-nav="challans" aria-haspopup="true" aria-expanded="false">
              <i class="fa-solid fa-file-lines"></i> Challan Management
              <i class="fa-solid fa-chevron-down" style="font-size: 0.65rem;"></i>
            </button>
            <div class="nav-dropdown-menu">
              <a href="/generate-challan" class="nav-item" data-nav="generate-challan">Generate Challan</a>
              <a href="/challans" class="nav-item" data-nav="challan-history">Challan History</a>
            </div>
          </div>` : '';

  return `
    <div class="nav-cluster">
      <div class="nav-group">
        ${isOfficer ? '<a href="/dashboard" class="nav-item nav-parent" data-nav="dashboard"><img class="nav-parent-icon" src="/static/admin-control.svg?v=15" alt=""> Administrative Control</a>' : ''}
        <div class="nav-children" role="group" aria-label="Administrative Control modules">
          ${vehicleLink}
          ${isOfficer ? '<a href="/number-plate" class="nav-item" data-nav="number-plate"><i class="fa-solid fa-camera"></i> Number Plate Recognition</a>' : ''}
          ${challanGroup}
          ${isOfficer ? '<a href="/reports" class="nav-item" data-nav="reports"><i class="fa-solid fa-chart-column"></i> Reports</a>' : ''}
        </div>
      </div>
    </div>
    <a href="#" class="nav-item nav-logout" onclick="logout(); return false;"><i class="fa-solid fa-arrow-right-from-bracket"></i> Logout</a>
  `;
}

function closeNavDropdowns(except) {
  document.querySelectorAll('.nav-dropdown.open').forEach((dropdown) => {
    if (dropdown === except) {
      return;
    }
    dropdown.classList.remove('open');
    const trigger = dropdown.querySelector(':scope > .nav-item');
    if (trigger) {
      trigger.setAttribute('aria-expanded', 'false');
    }
  });
}

function placeNavDropdown(dropdown) {
  const trigger = dropdown.querySelector(':scope > .nav-item');
  const menu = dropdown.querySelector('.nav-dropdown-menu');
  if (!trigger || !menu) {
    return;
  }

  const rect = trigger.getBoundingClientRect();
  menu.style.top = `${Math.round(rect.bottom)}px`;
  menu.style.left = `${Math.round(rect.left)}px`;
}

function bindNavDropdowns() {
  document.querySelectorAll('.nav-dropdown').forEach((dropdown) => {
    const trigger = dropdown.querySelector(':scope > .nav-item');
    const menu = dropdown.querySelector('.nav-dropdown-menu');
    if (!trigger || !menu || trigger.dataset.dropdownBound === '1') {
      return;
    }

    trigger.dataset.dropdownBound = '1';
    trigger.setAttribute('aria-haspopup', 'true');
    trigger.setAttribute('aria-expanded', 'false');

    let hideTimer = 0;

    const open = () => {
      window.clearTimeout(hideTimer);
      closeNavDropdowns(dropdown);
      dropdown.classList.add('open');
      trigger.setAttribute('aria-expanded', 'true');
      placeNavDropdown(dropdown);
    };

    const close = () => {
      dropdown.classList.remove('open');
      trigger.setAttribute('aria-expanded', 'false');
    };

    const scheduleClose = () => {
      window.clearTimeout(hideTimer);
      hideTimer = window.setTimeout(close, 140);
    };

    dropdown.addEventListener('mouseenter', open);
    dropdown.addEventListener('mouseleave', scheduleClose);
    menu.addEventListener('mouseenter', open);
    menu.addEventListener('mouseleave', scheduleClose);

    trigger.addEventListener('click', (event) => {
      event.preventDefault();
      event.stopPropagation();
      const canHover = window.matchMedia('(hover: hover) and (pointer: fine)').matches;
      if (canHover) {
        open();
        return;
      }
      if (dropdown.classList.contains('open')) {
        close();
      } else {
        open();
      }
    });
  });
}

if (!window.__navDropdownListeners) {
  window.__navDropdownListeners = true;

  document.addEventListener('click', (event) => {
    if (!event.target.closest('.nav-dropdown')) {
      closeNavDropdowns();
    }
  });

  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') {
      closeNavDropdowns();
    }
  });

  window.addEventListener('resize', () => {
    document.querySelectorAll('.nav-dropdown.open').forEach(placeNavDropdown);
  });
}

function applyActiveNav() {
  const nav = document.getElementById('appNav');
  if (!nav) {
    return;
  }

  const active = nav.dataset.active || getActiveNavKey();
  const childKeys = ['vehicles', 'number-plate', 'challans', 'reports'];
  const parentActive = active === 'dashboard' || childKeys.includes(active);

  nav.querySelectorAll('.nav-parent, .nav-children > .nav-item, .nav-children > .nav-dropdown > .nav-item').forEach((el) => {
    const isParent = el.classList.contains('nav-parent') || el.dataset.nav === 'dashboard';
    const isActive = isParent ? parentActive : el.dataset.nav === active;
    el.classList.toggle('active', isActive);

    if (!isParent && isActive) {
      el.setAttribute('aria-current', 'page');
    } else if (isParent && active === 'dashboard') {
      el.setAttribute('aria-current', 'page');
    } else {
      el.removeAttribute('aria-current');
    }
  });

  const generateLink = nav.querySelector('[data-nav="generate-challan"]');
  const historyLink = nav.querySelector('[data-nav="challan-history"]');
  if (generateLink) {
    generateLink.classList.toggle('active', window.location.pathname.startsWith('/generate-challan'));
  }
  if (historyLink) {
    historyLink.classList.toggle('active', window.location.pathname.startsWith('/challans') || window.location.pathname.startsWith('/challan/'));
  }
}

function mountAppNav() {
  const nav = document.getElementById('appNav');
  if (!nav) {
    return;
  }

  const mode = nav.dataset.navMode || 'app';
  const loggedIn = !!getCurrentUser();

  if (mode === 'guest') {
    const path = window.location.pathname;
    nav.innerHTML = path.startsWith('/login')
      ? '<a href="/register" class="nav-item">Register</a>'
      : '<a href="/login" class="nav-item">Login</a>';
    return;
  }

  if (mode === 'public') {
    nav.innerHTML = `
      <a href="/login?next=${encodeURIComponent('/citizen')}" class="nav-item"><i class="fa-solid fa-wand-magic-sparkles"></i> AI Vehicle Check</a>
      <a href="/login" class="nav-item">Login</a>
      <a href="/register" class="nav-item">Sign up</a>`;
    return;
  }

  if (loggedIn || mode === 'app') {
    const user = getCurrentUser();
    if (!user) {
      nav.innerHTML = '<a href="/login" class="nav-item">Login</a>';
      return;
    }
    if (user.role === 'Citizen') {
      nav.innerHTML = `
        <a href="/number-plate" class="nav-item"><i class="fa-solid fa-car"></i> Citizen Portal</a>
        <a href="#" class="nav-item nav-logout" onclick="logout(); return false;"><i class="fa-solid fa-arrow-right-from-bracket"></i> Logout</a>`;
      return;
    }
    nav.innerHTML = adminControlGroupHtml(user);
    applyActiveNav();
    bindNavDropdowns();
    applyPublicNavAuth();
    return;
  }

  nav.innerHTML = `
    <a href="/login?next=${encodeURIComponent('/dashboard')}" class="nav-item" onclick="return openAdministrativeControl(event);">
      <img class="nav-parent-icon" src="/static/admin-control.svg?v=14" alt=""> Administrative Control
    </a>
    <a href="/login" class="nav-item" data-guest>Sign in</a>
    <a href="/register" class="nav-item" data-guest>Register</a>
  `;
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', mountAppNav);
} else {
  mountAppNav();
}

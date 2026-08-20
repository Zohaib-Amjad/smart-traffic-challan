const AUTH_STORAGE_KEY = 'currentUser';

function getCurrentUser() {
  try {
    return JSON.parse(localStorage.getItem(AUTH_STORAGE_KEY) || 'null');
  } catch (error) {
    localStorage.removeItem(AUTH_STORAGE_KEY);
    return null;
  }
}

function requireAuth() {
  if (getCurrentUser()) {
    return true;
  }

  const next = `${window.location.pathname}${window.location.search}`;
  window.location.replace(`/login?next=${encodeURIComponent(next)}`);
  return false;
}

function logout() {
  localStorage.removeItem(AUTH_STORAGE_KEY);
  sessionStorage.removeItem('lastDetectedPlate');
  sessionStorage.removeItem('lastPreviewImg');
  window.location.replace('/login');
}

function redirectAfterAuth(defaultPath = '/dashboard') {
  const next = new URLSearchParams(window.location.search).get('next');
  const destination = next && next.startsWith('/') && !next.startsWith('//') ? next : defaultPath;
  window.location.replace(destination);
}

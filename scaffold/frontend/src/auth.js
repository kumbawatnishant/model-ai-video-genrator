import axios from 'axios'

const EMAIL_KEY = 'auth.email'

export function saveEmail(email) {
  localStorage.setItem(EMAIL_KEY, email)
}

export function getEmail() {
  return localStorage.getItem(EMAIL_KEY)
}

export function logout() {
  localStorage.removeItem(EMAIL_KEY)
  // call backend to clear cookies
  try { fetch('/api/auth/logout', { method: 'POST', credentials: 'include' }) } catch(e){}
}

export function isAuthenticated() {
  // rely on /api/auth/me check via AuthProvider; this helper remains shallow
  return !!getEmail()
}

// axios will be configured in AuthProvider to use withCredentials:true
export default { getEmail, logout, isAuthenticated, saveEmail }

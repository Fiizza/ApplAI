const BASE = 'http://localhost:8000';

function getToken() {
  return localStorage.getItem('token');
}
function setToken(t) {
  if (t) localStorage.setItem('token', t);
  else localStorage.removeItem('token');
}

async function request(path, opts = {}) {
  const headers = { ...(opts.headers || {}) };
  const token = getToken();
  if (token) headers['Authorization'] = `Bearer ${token}`;
  if (opts.body && !(opts.body instanceof FormData)) {
    headers['Content-Type'] = 'application/json';
  }

  const res = await fetch(`${BASE}${path}`, { ...opts, headers });

  if (!res.ok) {
    let detail = res.statusText;
    try {
      const data = await res.json();
      detail = data.detail || detail;
    } catch {}
    throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail));
  }
  if (res.status === 204) return null;
  const text = await res.text();
  return text ? JSON.parse(text) : null;
}

export const api = {
  // auth
  register: (email, password) =>
    request('/auth/register', { method: 'POST', body: JSON.stringify({ email, password }) }),
  login: async (email, password) => {
    const form = new URLSearchParams();
    form.append('username', email);
    form.append('password', password);
    const res = await fetch(`${BASE}/auth/login`, {
      method: 'POST',
      body: form,
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    });
    if (!res.ok) {
      let detail = 'Incorrect email or password';
      try {
        detail = (await res.json()).detail || detail;
      } catch {}
      throw new Error(detail);
    }
    const data = await res.json();
    setToken(data.access_token);
    return data;
  },
  logout: () => setToken(null),
  me: () => request('/auth/me'),

  // jobs / applications
  parseJob: (payload) => request('/parse-job', { method: 'POST', body: JSON.stringify(payload) }),
  listApplications: () => request('/applications'),
  createApplication: (payload) =>
    request('/applications', { method: 'POST', body: JSON.stringify(payload) }),
  updateApplication: (id, payload) =>
    request(`/applications/${id}`, { method: 'PATCH', body: JSON.stringify(payload) }),
  deleteApplication: (id) => request(`/applications/${id}`, { method: 'DELETE' }),

  // per-application AI actions
  match: (id) => request(`/applications/${id}/match`),
  coverLetter: (id) => request(`/applications/${id}/cover-letter`, { method: 'POST' }),
  interviewPrep: (id) => request(`/applications/${id}/interview-prep`, { method: 'POST' }),
  followUpEmail: (id) => request(`/applications/${id}/follow-up-email`, { method: 'POST' }),
  tailorResume: (id) => request(`/applications/${id}/tailor-resume`, { method: 'POST' }),
  learningRecs: (id) => request(`/applications/${id}/learning-recommendations`),
  resumeVersions: (id) => request(`/applications/${id}/resume-versions`),
  appEmailSummaries: (id) => request(`/applications/${id}/email-summaries`),

  // reminders + digest
  getReminders: (lookaheadDays = 3) => request(`/reminders?lookahead_days=${lookaheadDays}`),
  sendDigestNow: () => request('/reminders/send-digest', { method: 'POST' }),

  // gmail
  gmailAuthUrl: () => request('/auth/gmail/connect'),
  getEmailAccount: () => request('/email-account').catch(() => null),
  disconnectEmailAccount: () => request('/email-account', { method: 'DELETE' }),
  syncGmailNow: () => request('/gmail/sync', { method: 'POST' }),
  listEmailSummaries: (unmatchedOnly = false) =>
    request(`/email-summaries${unmatchedOnly ? '?unmatched_only=true' : ''}`),

  // skills
  listSkills: () => request('/skills'),
  addSkill: (payload) => request('/skills', { method: 'POST', body: JSON.stringify(payload) }),
  deleteSkill: (id) => request(`/skills/${id}`, { method: 'DELETE' }),

  // resume
  getResume: () => request('/resume').catch(() => null),
  saveResumeText: (content) =>
    request('/resume', { method: 'POST', body: JSON.stringify({ content }) }),
  uploadResume: (file) => {
    const fd = new FormData();
    fd.append('file', file);
    return request('/resume/upload', { method: 'POST', body: fd });
  },
};

export { getToken };
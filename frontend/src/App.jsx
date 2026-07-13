import React, { useState, useEffect, useLayoutEffect, useRef } from 'react';
import Splash3D from './components/Splash3D.jsx';

const API = import.meta.env.VITE_API_URL;

const STATUS_COLOR = {
  Applied: 'var(--stage-applied)',
  Interview: 'var(--stage-interview)',
  Offer: 'var(--stage-offer)',
  Rejected: 'var(--stage-rejected)',
};

export default function ApplAI() {
  const [splash, setSplash] = useState(true);
  const [splashLeaving, setSplashLeaving] = useState(false);
  const [auth, setAuth] = useState(null);
  const [loading, setLoading] = useState(false);
  const [view, setView] = useState('applications');
  const [apps, setApps] = useState([]);
  const [skills, setSkills] = useState([]);
  const [resume, setResume] = useState(null);
  const [modal, setModal] = useState(null);
  const [modalData, setModalData] = useState(null);
  const [modalClosing, setModalClosing] = useState(false);
  const [toasts, setToasts] = useState([]);
  const splashTimers = useRef({});
  const toastTimers = useRef({});
  const [isReplay, setIsReplay] = useState(false);
  const [reminders, setReminders] = useState(null);
  const [remindersLoading, setRemindersLoading] = useState(false);
  const [emailAccount, setEmailAccount] = useState(null);
  const [emailSummaries, setEmailSummaries] = useState([]);

  const showToast = (message, type = 'default') => {
    const id = Date.now() + Math.random();
    setToasts((t) => [...t, { id, message, type, leaving: false }]);
    toastTimers.current[id] = setTimeout(() => {
      setToasts((t) => t.map((x) => (x.id === id ? { ...x, leaving: true } : x)));
      setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), 280);
    }, 3600);
  };

  const closeModal = () => {
    setModalClosing(true);
    setTimeout(() => {
      setModal(null);
      setModalClosing(false);
    }, 190);
  };

  const enterApp = () => {
    setSplashLeaving(true);
    setTimeout(() => { setSplash(false); setIsReplay(false); }, 500);
  };

  const runSplash = (leaveAt = 2200, hideAt = 2700) => {
    setIsReplay(true);
    clearTimeout(splashTimers.current.leave);
    clearTimeout(splashTimers.current.hide);
    setSplashLeaving(false);
    setSplash(true);
    splashTimers.current.leave = setTimeout(() => setSplashLeaving(true), leaveAt);
    splashTimers.current.hide = setTimeout(() => { setSplash(false); setIsReplay(false); }, hideAt);
  };

  // Auth persistence — splash stays until user clicks "Try it out"
  useEffect(() => {
    const token = localStorage.getItem('token');
    const email = localStorage.getItem('email');
    if (token && email) {
      setAuth({ token, email });
    }
    return () => {
      clearTimeout(splashTimers.current.leave);
      clearTimeout(splashTimers.current.hide);
    };
  }, []);

  const apiFetch = async (path, opts = {}) => {
    const headers = { 'Content-Type': 'application/json' };
    if (auth?.token) headers.Authorization = `Bearer ${auth.token}`;
    const res = await fetch(`${API}${path}`, { ...opts, headers });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  };

  const handleRegister = async (email, password) => {
    setLoading(true);
    try {
      const res = await fetch(`${API}/auth/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      });
      if (!res.ok) {
        const error = await res.json();
        throw new Error(error.detail || 'Registration failed');
      }

      // Now login
      const body = new URLSearchParams();
      body.append('username', email);
      body.append('password', password);

      const loginRes = await fetch(`${API}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: body.toString(),
      });
      if (!loginRes.ok) {
        throw new Error('Login after registration failed');
      }
      const { access_token } = await loginRes.json();
      localStorage.setItem('token', access_token);
      localStorage.setItem('email', email);
      setAuth({ token: access_token, email });
      loadDashboard();
    } catch (e) {
      throw e;
    } finally {
      setLoading(false);
    }
  };

  const handleLogin = async (email, password) => {
    setLoading(true);
    try {
      const body = new URLSearchParams();
      body.append('username', email);
      body.append('password', password);

      const res = await fetch(`${API}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: body.toString(),
      });
      if (!res.ok) {
        const error = await res.json();
        throw new Error(error.detail || 'Login failed');
      }
      const { access_token } = await res.json();
      localStorage.setItem('token', access_token);
      localStorage.setItem('email', email);
      setAuth({ token: access_token, email });
      loadDashboard();
    } catch (e) {
      throw e;
    } finally {
      setLoading(false);
    }
  };

  const loadDashboard = async () => {
    try {
      const [a, s, r] = await Promise.all([
        apiFetch('/applications'),
        apiFetch('/skills'),
        apiFetch('/resume').catch(() => null),
      ]);
      setApps(a);
      setSkills(s);
      setResume(r);
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    if (auth) loadDashboard();
  }, [auth]);

  useEffect(() => {
    if (auth && view === 'reminders' && reminders === null) loadReminders();
  }, [auth, view]);

  const handleSignOut = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('email');
    setAuth(null);
    setApps([]);
    setSkills([]);
    setResume(null);
    setModal(null);
    setReminders(null);
    setEmailAccount(null);
    setEmailSummaries([]);
  };

  const handleAddApp = async (formData) => {
    try {
      const payload = {
        company: formData.company,
        role: formData.role,
        job_url: formData.job_url || null,
        key_skills: formData.key_skills ? formData.key_skills.split(',').map(s => s.trim()).filter(Boolean) : [],
        recruiter_name: formData.recruiter_name || null,
        recruiter_email: formData.recruiter_email || null,
        oa_deadline: formData.oa_deadline ? new Date(formData.oa_deadline).toISOString() : null,
        interview_date: formData.interview_date ? new Date(formData.interview_date).toISOString() : null,
      };
      const created = await apiFetch('/applications', { method: 'POST', body: JSON.stringify(payload) });
      setApps([...apps, created]);
    } catch (e) {
      showToast('Failed to add application: ' + e.message, 'error');
    }
  };

  const handleUpdateStatus = async (id, status) => {
    try {
      await apiFetch(`/applications/${id}`, { method: 'PATCH', body: JSON.stringify({ status }) });
      setApps(apps.map(a => a.id === id ? { ...a, status } : a));
    } catch (e) {
      showToast('Failed to update: ' + e.message, 'error');
    }
  };

  const handleEditApp = async (id, formData) => {
    try {
      const payload = {
        company: formData.company,
        role: formData.role,
        job_url: formData.job_url || null,
        key_skills: formData.key_skills ? formData.key_skills.split(',').map(s => s.trim()).filter(Boolean) : [],
        recruiter_name: formData.recruiter_name || null,
        recruiter_email: formData.recruiter_email || null,
        oa_deadline: formData.oa_deadline ? new Date(formData.oa_deadline).toISOString() : null,
        interview_date: formData.interview_date ? new Date(formData.interview_date).toISOString() : null,
      };
      const updated = await apiFetch(`/applications/${id}`, { method: 'PATCH', body: JSON.stringify(payload) });
      setApps(apps.map(a => (a.id === id ? updated : a)));
      showToast('Application updated', 'success');
    } catch (e) {
      showToast('Failed to update application: ' + e.message, 'error');
    }
  };

  const handleDeleteApp = async (id) => {
    try {
      await apiFetch(`/applications/${id}`, { method: 'DELETE' });
      setApps(apps.filter((a) => a.id !== id));
      showToast('Application deleted', 'default');
    } catch (e) {
      showToast('Failed to delete application: ' + e.message, 'error');
    }
  };

  const handleAddSkill = async (name, category, proficiency, years) => {
    try {
      const skill = await apiFetch('/skills', {
        method: 'POST',
        body: JSON.stringify({ name, category: category || null, proficiency: proficiency || null, years_experience: years ? parseInt(years) : null }),
      });
      setSkills([...skills, skill]);
    } catch (e) {
      showToast('Failed to add skill: ' + e.message, 'error');
    }
  };

  const handleUpdateSkill = async (id, name, category, proficiency, years) => {
    try {
      const updated = await apiFetch(`/skills/${id}`, {
        method: 'PATCH',
        body: JSON.stringify({ name, category: category || null, proficiency: proficiency || null, years_experience: years ? parseInt(years) : null }),
      });
      setSkills(skills.map((s) => (s.id === id ? updated : s)));
      showToast('Skill updated', 'success');
    } catch (e) {
      showToast('Failed to update skill: ' + e.message, 'error');
    }
  };

  const handleDeleteSkill = async (id) => {
    try {
      await apiFetch(`/skills/${id}`, { method: 'DELETE' });
      setSkills(skills.filter((s) => s.id !== id));
    } catch (e) {
      showToast('Failed to delete skill: ' + e.message, 'error');
    }
  };

  const handleSaveResume = async (content) => {
    try {
      await apiFetch('/resume', { method: 'POST', body: JSON.stringify({ content }) });
      setResume({ content });
      showToast('Resume saved!', 'success');
    } catch (e) {
      showToast('Failed to save: ' + e.message, 'error');
    }
  };

  const handleGenerateCoverLetter = async (appId) => {
    try {
      const { opener, why_these_skills } = await apiFetch(`/applications/${appId}/cover-letter`, { method: 'POST' });
      setModalData({ ...modalData, coverLetter: opener, coverLetterWhy: why_these_skills });
    } catch (e) {
      showToast('Failed: ' + e.message, 'error');
    }
  };

  const handleGenerateInterviewPrep = async (appId) => {
    try {
      const { questions, talking_points, reasoning } = await apiFetch(`/applications/${appId}/interview-prep`, { method: 'POST' });
      setModalData({ ...modalData, interviewPrep: { questions, talking_points, reasoning } });
    } catch (e) {
      showToast('Failed: ' + e.message, 'error');
    }
  };

  const handleGenerateFollowUp = async (appId) => {
    try {
      const { subject, body } = await apiFetch(`/applications/${appId}/follow-up-email`, { method: 'POST' });
      setModalData({ ...modalData, followUp: { subject, body } });
    } catch (e) {
      showToast('Failed: ' + e.message, 'error');
    }
  };

  const handleGenerateLearning = async (appId) => {
    try {
      const { recommendations } = await apiFetch(`/applications/${appId}/learning-recommendations`);
      setModalData({ ...modalData, learning: recommendations });
    } catch (e) {
      showToast('Failed: ' + e.message, 'error');
    }
  };

  const handleGenerateTailorResume = async (appId) => {
    try {
      const { tailored_resume } = await apiFetch(`/applications/${appId}/tailor-resume`, { method: 'POST' });
      const versions = await apiFetch(`/applications/${appId}/resume-versions`).catch(() => []);
      setModalData((d) => ({ ...d, tailoredResume: tailored_resume, resumeVersions: versions }));
    } catch (e) {
      showToast('Failed: ' + e.message, 'error');
    }
  };

  const handleLoadResumeVersions = async (appId) => {
    try {
      const versions = await apiFetch(`/applications/${appId}/resume-versions`);
      setModalData((d) => ({ ...d, resumeVersions: versions }));
    } catch (e) {
      // quietly ignore — this loads automatically when the tab opens
    }
  };

  const handleLoadAppEmailSummaries = async (appId) => {
    try {
      const summaries = await apiFetch(`/applications/${appId}/email-summaries`);
      setModalData((d) => ({ ...d, appEmailSummaries: summaries }));
    } catch (e) {
      // quietly ignore — this loads automatically when the tab opens
    }
  };

  const loadReminders = async () => {
    setRemindersLoading(true);
    try {
      const [rem, acct] = await Promise.all([
        apiFetch('/reminders'),
        apiFetch('/email-account').catch(() => null),
      ]);
      setReminders(rem);
      setEmailAccount(acct);
      if (acct) {
        const summaries = await apiFetch('/email-summaries').catch(() => []);
        setEmailSummaries(summaries);
      }
    } catch (e) {
      showToast('Failed to load reminders: ' + e.message, 'error');
    } finally {
      setRemindersLoading(false);
    }
  };

  const handleSendDigest = async () => {
    try {
      const res = await apiFetch('/reminders/send-digest', { method: 'POST' });
      showToast(res.detail, res.sent ? 'success' : 'default');
    } catch (e) {
      showToast('Failed to send digest: ' + e.message, 'error');
    }
  };

  const handleGmailConnect = async () => {
    try {
      const { auth_url } = await apiFetch('/auth/gmail/connect');
      window.open(auth_url, '_blank', 'noopener,noreferrer');
      showToast('Finish connecting in the new tab, then come back and hit Sync.', 'default');
    } catch (e) {
      showToast('Failed to start Gmail connect: ' + e.message, 'error');
    }
  };

  const handleGmailSync = async () => {
    try {
      const res = await apiFetch('/gmail/sync', { method: 'POST' });
      showToast(`Synced — ${res.new_emails_found} new email(s) found`, 'success');
      loadReminders();
    } catch (e) {
      showToast('Sync failed: ' + e.message, 'error');
    }
  };

  const handleGmailDisconnect = async () => {
    try {
      await apiFetch('/email-account', { method: 'DELETE' });
      setEmailAccount(null);
      setEmailSummaries([]);
      showToast('Gmail disconnected', 'default');
    } catch (e) {
      showToast('Failed to disconnect: ' + e.message, 'error');
    }
  };

  if (splash) return <SplashScreen leaving={splashLeaving} onEnter={!isReplay ? enterApp : undefined} />;
  if (!auth) return <AuthScreen onRegister={handleRegister} onLogin={handleLogin} loading={loading} />;

  return (
    <div className="app-shell">
      <div className="app-ambient"><Splash3D ambient /></div>

      <div className="topbar">
        <div className="topbar-left">
          {view !== 'applications' && (
            <button
              className="topbar-back"
              onClick={() => setView('applications')}
              title="Back to pipeline"
              aria-label="Back to pipeline"
            >
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none">
                <path d="M15 5L8 12L15 19" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </button>
          )}
          <button className="brand-btn" onClick={() => runSplash(2200, 2700)} title="Replay intro">
            <div className="brand"><span className="orbit" /> ApplAI</div>
          </button>
        </div>
        <TabBar view={view} setView={setView} />
        <div className="topbar-right">
          <ProfileMenu email={auth.email} onSignOut={handleSignOut} />
        </div>
      </div>

      <div className="main">
        <div key={view} className="page-transition">
          {view === 'applications' && (
            <ApplicationsView
              apps={apps}
              onAddApp={handleAddApp}
              onStatusChange={handleUpdateStatus}
              onEditApp={handleEditApp}
              onDeleteApp={handleDeleteApp}
              onOpenModal={(app) => { setModal('details'); setModalData(app); }}
            />
          )}
          {view === 'skills' && (
            <SkillsView
              skills={skills}
              onAddSkill={handleAddSkill}
              onUpdateSkill={handleUpdateSkill}
              onDeleteSkill={handleDeleteSkill}
            />
          )}
          {view === 'resume' && (
            <ResumeView resume={resume} onSave={handleSaveResume} />
          )}
          {view === 'reminders' && (
            <RemindersView
              reminders={reminders}
              loading={remindersLoading}
              onRefresh={loadReminders}
              onSendDigest={handleSendDigest}
              emailAccount={emailAccount}
              emailSummaries={emailSummaries}
              onGmailConnect={handleGmailConnect}
              onGmailSync={handleGmailSync}
              onGmailDisconnect={handleGmailDisconnect}
            />
          )}
        </div>
      </div>

      <ToastStack toasts={toasts} />

      {modal === 'details' && (
        <DetailModal
          app={modalData}
          closing={modalClosing}
          onClose={closeModal}
          onGenerateCoverLetter={handleGenerateCoverLetter}
          onGenerateInterviewPrep={handleGenerateInterviewPrep}
          onGenerateFollowUp={handleGenerateFollowUp}
          onGenerateLearning={handleGenerateLearning}
          onGenerateTailorResume={handleGenerateTailorResume}
          onLoadResumeVersions={handleLoadResumeVersions}
          onLoadEmailSummaries={handleLoadAppEmailSummaries}
          data={modalData}
        />
      )}
    </div>
  );
}

const VIEWS = ['applications', 'skills', 'resume', 'reminders'];

const TabBar = ({ view, setView }) => {
  const containerRef = useRef(null);
  const btnRefs = useRef({});
  const [style, setStyle] = useState({ width: 0, transform: 'translateX(0px)' });

  useLayoutEffect(() => {
    const el = btnRefs.current[view];
    const container = containerRef.current;
    if (el && container) {
      const elRect = el.getBoundingClientRect();
      const containerRect = container.getBoundingClientRect();
      setStyle({
        width: elRect.width,
        transform: `translateX(${elRect.left - containerRect.left}px)`,
      });
    }
  }, [view]);

  return (
    <div className="tabs" ref={containerRef}>
      <span className="tab-indicator" style={style} />
      {VIEWS.map((v) => (
        <button
          key={v}
          ref={(el) => (btnRefs.current[v] = el)}
          onClick={() => setView(v)}
          className={`tab${view === v ? ' active' : ''}`}
        >
          {v.charAt(0).toUpperCase() + v.slice(1)}
        </button>
      ))}
    </div>
  );
};

const BackButton = ({ onClick }) => (
  <button className="back-btn" onClick={onClick} title="Back to pipeline" aria-label="Back to pipeline">
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
      <path d="M15 5L8 12L15 19" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  </button>
);

const ProfileMenu = ({ email, onSignOut }) => {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);
  const initial = (email || '?').charAt(0).toUpperCase();

  useEffect(() => {
    const onDocClick = (e) => {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false);
    };
    document.addEventListener('mousedown', onDocClick);
    return () => document.removeEventListener('mousedown', onDocClick);
  }, []);

  return (
    <div className="profile-menu" ref={ref}>
      <button className="profile-avatar" onClick={() => setOpen((o) => !o)} title={email}>
        {initial}
      </button>
      {open && (
        <div className="profile-dropdown">
          <div className="profile-dropdown-email">{email}</div>
          <button
            className="profile-dropdown-item danger"
            onClick={() => { setOpen(false); onSignOut(); }}
          >
            Sign out
          </button>
        </div>
      )}
    </div>
  );
};

const ToastStack = ({ toasts }) => (
  <div className="toast-stack">
    {toasts.map((t) => (
      <div key={t.id} className={`toast ${t.type}${t.leaving ? ' leaving' : ''}`}>
        <span className="dot" style={{ color: t.type === 'error' ? 'var(--stage-rejected)' : t.type === 'success' ? 'var(--stage-offer)' : 'var(--accent)' }} />
        <span>{t.message}</span>
      </div>
    ))}
  </div>
);

const SplashScreen = ({ leaving, onEnter }) => (
  <div className={`splash-wrap${leaving ? ' splash-fade-out' : ''}`}>
    <Splash3D />
    <div className="splash-content">
      <p className="eyebrow">Welcome to</p>
      <h1>ApplAI</h1>
      <p className="tagline">Track applications, tailor resumes, and prep for interviews — all in one place.</p>
      {onEnter && (
        <button className="btn btn-primary splash-cta" onClick={onEnter}>
          Try it out →
        </button>
      )}
    </div>
  </div>
);

const AuthScreen = ({ onRegister, onLogin, loading }) => {
  const [isRegister, setIsRegister] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPwd, setShowPwd] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async () => {
    setError('');
    try {
      if (isRegister) {
        await onRegister(email, password);
      } else {
        await onLogin(email, password);
      }
    } catch (e) {
      setError(e.message || 'Login failed');
    }
  };

  const switchMode = (val) => {
    setIsRegister(val);
    setError('');
  };

  return (
    <div className="auth-wrap">
      <div className="auth-ambient"><Splash3D ambient /></div>
      <div className="auth-card">
        <h1>ApplAI</h1>
        <p className="sub">{isRegister ? 'Create your account' : 'Sign in to your tracker'}</p>

        {error && <div className="error-box shake">{error}</div>}

        <div className="auth-fields" key={isRegister ? 'register' : 'login'}>
          <div className="field">
            <label>Email</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleSubmit()}
              placeholder="name@company.com"
              autoFocus
            />
          </div>

          <div className="field">
            <label>Password</label>
            <div className="pwd-wrap">
              <input
                type={showPwd ? 'text' : 'password'}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && handleSubmit()}
              />
              <button type="button" className="pwd-toggle" onClick={() => setShowPwd(!showPwd)}>
                {showPwd ? 'Hide' : 'Show'}
              </button>
            </div>
          </div>
        </div>

        <button
          onClick={handleSubmit}
          disabled={loading || !email || !password}
          className="btn btn-primary"
          style={{ width: '100%', marginBottom: '4px' }}
        >
          {loading && <span className="spinner" />}
          {loading ? 'Loading' : isRegister ? 'Create account' : 'Sign in'}
        </button>

        <div className="auth-switch">
          {isRegister ? (
            <>
              Already have an account?{' '}
              <button onClick={() => switchMode(false)}>Sign in</button>
            </>
          ) : (
            <>
              No account yet?{' '}
              <button onClick={() => switchMode(true)}>Register</button>
            </>
          )}
        </div>
      </div>
    </div>
  );
};

const ApplicationsView = ({ apps, onAddApp, onStatusChange, onEditApp, onDeleteApp, onOpenModal }) => {
  const [showForm, setShowForm] = useState(false);
  const [formClosing, setFormClosing] = useState(false);
  const [showMore, setShowMore] = useState(false);
  const emptyForm = {
    company: '', role: '', job_url: '', key_skills: '',
    recruiter_name: '', recruiter_email: '', oa_deadline: '', interview_date: '',
  };
  const [formData, setFormData] = useState(emptyForm);
  const [editingApp, setEditingApp] = useState(null);
  const [poppedId, setPoppedId] = useState(null);
  const [bumpedStatus, setBumpedStatus] = useState(null);

  const toDatetimeLocal = (iso) => {
    if (!iso) return '';
    const d = new Date(iso);
    const pad = (n) => String(n).padStart(2, '0');
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
  };

  const openForm = () => { setEditingApp(null); setFormData(emptyForm); setShowForm(true); };

  const openEditForm = (app) => {
    setEditingApp(app);
    setFormData({
      company: app.company || '',
      role: app.role || '',
      job_url: app.job_url || '',
      key_skills: Array.isArray(app.key_skills) ? app.key_skills.join(', ') : (app.key_skills || ''),
      recruiter_name: app.recruiter_name || '',
      recruiter_email: app.recruiter_email || '',
      oa_deadline: toDatetimeLocal(app.oa_deadline),
      interview_date: toDatetimeLocal(app.interview_date),
    });
    setShowMore(Boolean(app.recruiter_name || app.recruiter_email || app.oa_deadline || app.interview_date));
    setShowForm(true);
  };

  const closeForm = () => {
    setFormClosing(true);
    setTimeout(() => {
      setShowForm(false);
      setFormClosing(false);
      setShowMore(false);
      setFormData(emptyForm);
      setEditingApp(null);
    }, 190);
  };

  // Standard modal behavior: Escape always closes, matching the detail modal elsewhere in the app.
  useEffect(() => {
    if (!showForm) return;
    const onKeyDown = (e) => { if (e.key === 'Escape') closeForm(); };
    document.addEventListener('keydown', onKeyDown);
    return () => document.removeEventListener('keydown', onKeyDown);
  }, [showForm]);

  const handleAdd = () => {
    if (!formData.company || !formData.role) return;
    if (editingApp) {
      onEditApp(editingApp.id, formData);
    } else {
      onAddApp(formData);
    }
    closeForm();
  };

  const handleDelete = (e, app) => {
    e.stopPropagation();
    if (window.confirm(`Delete the application for ${app.role} at ${app.company}? This can't be undone.`)) {
      onDeleteApp(app.id);
    }
  };

  const handleStatusChange = (id, newStatus) => {
    onStatusChange(id, newStatus);
    setPoppedId(id);
    setBumpedStatus(newStatus);
    setTimeout(() => setPoppedId(null), 400);
    setTimeout(() => setBumpedStatus(null), 320);
  };

  const statuses = ['Applied', 'Interview', 'Offer', 'Rejected'];

  const handleTilt = (e) => {
    const card = e.currentTarget;
    const rect = card.getBoundingClientRect();
    const px = (e.clientX - rect.left) / rect.width;
    const py = (e.clientY - rect.top) / rect.height;
    card.style.setProperty('--rx', `${(0.5 - py) * 12}deg`);
    card.style.setProperty('--ry', `${(px - 0.5) * 12}deg`);
    card.style.setProperty('--ty', '-4px');
  };
  const resetTilt = (e) => {
    e.currentTarget.style.setProperty('--rx', '0deg');
    e.currentTarget.style.setProperty('--ry', '0deg');
    e.currentTarget.style.setProperty('--ty', '0px');
  };

  return (
    <div>
      <div className="board-header">
        <h1 className="reveal" style={{ '--reveal-delay': '0ms' }}>
          <span className="orbit orbit-inline" /> Applications Overview
        </h1>
        <button
          onClick={openForm}
          className="btn btn-primary reveal"
          style={{ '--reveal-delay': '90ms' }}
        >
          + Add application
        </button>
      </div>

      {showForm && (
        <div className={`modal-overlay${formClosing ? ' closing' : ''}`} onClick={closeForm}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-head">
              <div>
                <h2>{editingApp ? 'Edit application' : 'Add application'}</h2>
                <p className="role">{editingApp ? 'Update the details for this application.' : 'Track a new job — everything but company and role is optional.'}</p>
              </div>
              <button onClick={closeForm} className="close-x" aria-label="Close">×</button>
            </div>

            <div className="modal-body">
              <div style={{ display: 'flex', gap: '14px', flexWrap: 'wrap', marginBottom: '14px' }}>
                <div className="field-inline" style={{ flex: '1 1 220px' }}>
                  <label>Company</label>
                  <input
                    placeholder="e.g. Vista"
                    value={formData.company}
                    onChange={(e) => setFormData({ ...formData, company: e.target.value })}
                    autoFocus
                  />
                </div>
                <div className="field-inline" style={{ flex: '1 1 220px' }}>
                  <label>Role</label>
                  <input
                    placeholder="e.g. AI Engineer"
                    value={formData.role}
                    onChange={(e) => setFormData({ ...formData, role: e.target.value })}
                  />
                </div>
              </div>

              <div className="field-inline" style={{ marginBottom: '14px' }}>
                <label>Job URL (optional)</label>
                <input
                  placeholder="https://..."
                  value={formData.job_url}
                  onChange={(e) => setFormData({ ...formData, job_url: e.target.value })}
                />
              </div>

              <div className="field-inline" style={{ marginBottom: '14px' }}>
                <label>Key skills (comma-separated)</label>
                <input
                  placeholder="e.g. Python, Docker, AWS"
                  value={formData.key_skills}
                  onChange={(e) => setFormData({ ...formData, key_skills: e.target.value })}
                />
              </div>

              <button
                type="button"
                onClick={() => setShowMore(!showMore)}
                style={{ background: 'none', border: 'none', color: 'var(--accent)', fontSize: '12px', padding: '0', marginBottom: showMore ? '14px' : '4px', cursor: 'pointer' }}
              >
                {showMore ? '− Hide recruiter & deadline details' : '+ Add recruiter & deadline details (optional)'}
              </button>

              {showMore && (
                <div className="panel-collapse">
                  <div style={{ display: 'flex', gap: '14px', flexWrap: 'wrap', marginBottom: '14px' }}>
                    <div className="field-inline" style={{ flex: '1 1 220px' }}>
                      <label>Recruiter name</label>
                      <input
                        placeholder="optional"
                        value={formData.recruiter_name}
                        onChange={(e) => setFormData({ ...formData, recruiter_name: e.target.value })}
                      />
                    </div>
                    <div className="field-inline" style={{ flex: '1 1 220px' }}>
                      <label>Recruiter email</label>
                      <input
                        placeholder="optional"
                        value={formData.recruiter_email}
                        onChange={(e) => setFormData({ ...formData, recruiter_email: e.target.value })}
                      />
                    </div>
                  </div>
                  <div style={{ display: 'flex', gap: '14px', flexWrap: 'wrap', marginBottom: '4px' }}>
                    <div className="field-inline" style={{ flex: '1 1 220px' }}>
                      <label>OA deadline</label>
                      <input
                        type="datetime-local"
                        value={formData.oa_deadline}
                        onChange={(e) => setFormData({ ...formData, oa_deadline: e.target.value })}
                      />
                    </div>
                    <div className="field-inline" style={{ flex: '1 1 220px' }}>
                      <label>Interview date</label>
                      <input
                        type="datetime-local"
                        value={formData.interview_date}
                        onChange={(e) => setFormData({ ...formData, interview_date: e.target.value })}
                      />
                    </div>
                  </div>
                </div>
              )}

              <div style={{ display: 'flex', gap: '10px', marginTop: '20px' }}>
                <button onClick={handleAdd} disabled={!formData.company || !formData.role} className="btn btn-primary">
                  {editingApp ? 'Save changes' : 'Save'}
                </button>
                <button onClick={closeForm} className="btn btn-ghost">Cancel</button>
              </div>
            </div>
          </div>
        </div>
      )}

      <div className="board">
        {statuses.map((status, colIndex) => {
          const inStatus = apps.filter(a => a.status === status);
          return (
            <div key={status} className="column" style={{ '--enter-delay': `${colIndex * 60}ms` }}>
              <div className="column-head">
                <span className="node-dot" style={{ background: STATUS_COLOR[status], color: STATUS_COLOR[status] }} />
                {status}
                <span className={`count${bumpedStatus === status ? ' bump' : ''}`}>{inStatus.length}</span>
              </div>
              <div>
                {inStatus.length === 0 ? (
                  <p className="empty-col">Nothing here yet.</p>
                ) : (
                  inStatus.map((app, i) => (
                    <div
                      key={app.id}
                      onClick={() => onOpenModal(app)}
                      onMouseMove={handleTilt}
                      onMouseLeave={resetTilt}
                      className={`card${poppedId === app.id ? ' status-pop' : ''}`}
                      style={{ '--stage-color': STATUS_COLOR[status], '--enter-delay': `${colIndex * 60 + i * 50}ms`, cursor: 'pointer' }}
                    >
                      <h3>{app.company}</h3>
                      <div className="company">{app.role}</div>
                      {(app.needs_followup || app.oa_deadline || app.interview_date) && (
                        <div className="meta">
                          {app.needs_followup && <span className="pill warn">Needs follow-up</span>}
                          {app.oa_deadline && <span className="pill">OA due {new Date(app.oa_deadline).toLocaleDateString()}</span>}
                          {app.interview_date && <span className="pill">Interview {new Date(app.interview_date).toLocaleDateString()}</span>}
                        </div>
                      )}
                      <div className="card-actions">
                        <button
                          className="x"
                          title="Edit application"
                          aria-label={`Edit ${app.company} — ${app.role}`}
                          onClick={(e) => { e.stopPropagation(); openEditForm(app); }}
                          type="button"
                        >
                          ✎ Edit
                        </button>
                        <button
                          className="x"
                          title="Delete application"
                          aria-label={`Delete ${app.company} — ${app.role}`}
                          onClick={(e) => handleDelete(e, app)}
                          type="button"
                        >
                          × Delete
                        </button>
                      </div>
                      <select
                        className="status-select"
                        value={status}
                        onClick={(e) => e.stopPropagation()}
                        onChange={(e) => handleStatusChange(app.id, e.target.value)}
                      >
                        {statuses.map((s) => (
                          <option key={s} value={s}>{s}</option>
                        ))}
                      </select>
                    </div>
                  ))
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

const SkillsView = ({ skills, onAddSkill, onUpdateSkill, onDeleteSkill }) => {
  const [name, setName] = useState('');
  const [category, setCategory] = useState('');
  const [proficiency, setProficiency] = useState('Intermediate');
  const [years, setYears] = useState('');
  const [editingId, setEditingId] = useState(null);

  const resetForm = () => {
    setName('');
    setCategory('');
    setProficiency('Intermediate');
    setYears('');
    setEditingId(null);
  };

  const handleAdd = () => {
    if (!name) return;
    if (editingId != null) {
      onUpdateSkill(editingId, name, category, proficiency, years);
    } else {
      onAddSkill(name, category, proficiency, years);
    }
    resetForm();
  };

  const startEdit = (skill) => {
    setEditingId(skill.id);
    setName(skill.name || '');
    setCategory(skill.category || '');
    setProficiency(skill.proficiency || 'Intermediate');
    setYears(skill.years_experience != null ? String(skill.years_experience) : '');
  };

  const handleDelete = (id) => {
    if (editingId === id) resetForm();
    onDeleteSkill(id);
  };

  const categoryCounts = skills.reduce((acc, s) => {
    const key = s.category || 'Uncategorized';
    acc[key] = (acc[key] || 0) + 1;
    return acc;
  }, {});
  const topCategories = Object.entries(categoryCounts).sort((a, b) => b[1] - a[1]).slice(0, 5);

  return (
    <div>
      <div className="view-header">
        <h2 className="reveal" style={{ '--reveal-delay': '0ms' }}>
          <span className="orbit orbit-inline" /> Your skills
        </h2>
        <p className="sub reveal" style={{ '--reveal-delay': '70ms' }}>
          This is what job matches, gaps, and tailoring compare against.
        </p>
      </div>

      <div className="view-grid">
        <div className="panel-block reveal" style={{ '--reveal-delay': '120ms' }}>
          <div className="skill-form">
            <div className="field-inline" style={{ flex: '1 1 170px' }}>
              <label>Skill</label>
              <input placeholder="e.g. FastAPI" value={name} onChange={(e) => setName(e.target.value)} />
            </div>
            <div className="field-inline" style={{ flex: '1 1 150px' }}>
              <label>Category</label>
              <input placeholder="e.g. Backend" value={category} onChange={(e) => setCategory(e.target.value)} />
            </div>
            <div className="field-inline" style={{ width: '150px' }}>
              <label>Proficiency</label>
              <select value={proficiency} onChange={(e) => setProficiency(e.target.value)}>
                <option value="Beginner">Beginner</option>
                <option value="Intermediate">Intermediate</option>
                <option value="Expert">Expert</option>
              </select>
            </div>
            <div className="field-inline" style={{ width: '84px' }}>
              <label>Years</label>
              <input placeholder="0" type="number" value={years} onChange={(e) => setYears(e.target.value)} />
            </div>
            <button onClick={handleAdd} className="btn btn-primary">
              {editingId != null ? 'Save skill' : 'Add skill'}
            </button>
            {editingId != null && (
              <button onClick={resetForm} className="btn btn-ghost" type="button">Cancel</button>
            )}
          </div>

          <div className="skill-list">
            {skills.length === 0 ? (
              <p className="text-muted">No skills added yet.</p>
            ) : (
              skills.map((skill, i) => (
                <div
                  key={skill.id}
                  className={`skill-chip${editingId === skill.id ? ' editing' : ''}`}
                  style={{ '--chip-delay': `${Math.min(i, 14) * 35}ms` }}
                >
                  <span>{skill.name}</span>
                  {skill.category && <span className="text-muted">· {skill.category}</span>}
                  {skill.proficiency && <span className="text-muted">· {skill.proficiency}</span>}
                  {skill.years_experience != null && <span className="text-muted">· {skill.years_experience}y</span>}
                  <button
                    className="x"
                    title="Edit skill"
                    aria-label={`Edit ${skill.name}`}
                    onClick={() => startEdit(skill)}
                    type="button"
                  >
                    ✎
                  </button>
                  <button
                    className="x"
                    title="Delete skill"
                    aria-label={`Delete ${skill.name}`}
                    onClick={() => handleDelete(skill.id)}
                    type="button"
                  >
                    ×
                  </button>
                </div>
              ))
            )}
          </div>
        </div>

        <Panel3D className="reveal" style={{ '--reveal-delay': '190ms' }}>
          <h3>Snapshot</h3>
          <div className="stat-row">
            <span className="text-muted">Total skills</span>
            <span className="stat-value"><AnimatedNumber value={skills.length} /></span>
          </div>
          <div className="stat-row">
            <span className="text-muted">Categories</span>
            <span className="stat-value"><AnimatedNumber value={Object.keys(categoryCounts).length} /></span>
          </div>
          {topCategories.length > 0 && (
            <div className="stat-breakdown">
              {topCategories.map(([cat, count]) => (
                <div key={cat} className="stat-bar-row">
                  <span className="stat-bar-label">{cat}</span>
                  <div className="stat-bar-track">
                    <div className="stat-bar-fill" style={{ width: `${(count / skills.length) * 100}%` }} />
                  </div>
                  <span className="stat-bar-count">{count}</span>
                </div>
              ))}
            </div>
          )}
        </Panel3D>
      </div>
    </div>
  );
};

const Panel3D = ({ children, className = '', style = {} }) => {
  return (
    <div className={`panel-block panel-side ${className}`} style={style}>
      {children}
    </div>
  );
};

const AnimatedNumber = ({ value }) => {
  const [display, setDisplay] = useState(0);
  const fromRef = useRef(0);

  useEffect(() => {
    const from = fromRef.current;
    const to = value;
    const duration = 700;
    const start = performance.now();
    let frame;
    const step = (now) => {
      const p = Math.min(1, (now - start) / duration);
      const eased = 1 - Math.pow(1 - p, 3);
      setDisplay(Math.round(from + (to - from) * eased));
      if (p < 1) frame = requestAnimationFrame(step);
      else fromRef.current = to;
    };
    frame = requestAnimationFrame(step);
    return () => cancelAnimationFrame(frame);
  }, [value]);

  return <>{display}</>;
};

const ResumeView = ({ resume, onSave }) => {
  const [editing, setEditing] = useState(!resume?.content);
  const [text, setText] = useState(resume?.content || '');
  const [synced, setSynced] = useState(false);

  useEffect(() => {
    if (!synced && resume !== null) {
      setText(resume?.content || '');
      setEditing(!resume?.content);
      setSynced(true);
    }
  }, [resume, synced]);

  const wordCount = (resume?.content || '').trim().split(/\s+/).filter(Boolean).length;

  const handleSave = () => {
    onSave(text);
    setEditing(false);
  };

  return (
    <div>
      <div className="view-header">
        <h2 className="reveal" style={{ '--reveal-delay': '0ms' }}>
          <span className="orbit orbit-inline" /> Base resume
        </h2>
        <p className="sub reveal" style={{ '--reveal-delay': '70ms' }}>
          Stored once, never edited automatically — tailoring generates a new version per job from this.
        </p>
      </div>

      <div className="view-grid">
        <div className="panel-block reveal" style={{ '--reveal-delay': '120ms' }}>
          {editing ? (
            <div className="resume-swap" key="editing">
              <textarea
                className="textarea-resume"
                value={text}
                onChange={(e) => setText(e.target.value)}
                placeholder="Paste your resume here..."
                autoFocus
              />
              <div style={{ marginTop: '14px', display: 'flex', gap: '10px' }}>
                <button onClick={handleSave} className="btn btn-primary">Save resume</button>
                {resume?.content && (
                  <button onClick={() => { setText(resume.content); setEditing(false); }} className="btn btn-ghost">Cancel</button>
                )}
              </div>
            </div>
          ) : resume?.content ? (
            <div className="resume-swap" key="preview">
              <div className="resume-meta">
                <span className="badge">Saved</span>
                <span><AnimatedNumber value={wordCount} /> words</span>
              </div>
              <div className="resume-preview">
                <div className="snippet">{resume.content}</div>
              </div>
              <button onClick={() => setEditing(true)} className="btn" style={{ marginTop: '16px' }}>Edit resume</button>
            </div>
          ) : (
            <div className="resume-empty resume-swap" key="empty">
              <p>No base resume saved yet.</p>
              <button onClick={() => setEditing(true)} className="btn btn-primary" style={{ marginTop: '10px' }}>Add resume</button>
            </div>
          )}
        </div>

        <Panel3D className="reveal" style={{ '--reveal-delay': '190ms' }}>
          <h3>Resume health</h3>
          <div className="stat-row">
            <span className="text-muted">Status</span>
            <span className="stat-value">{resume?.content ? 'Saved' : 'Not started'}</span>
          </div>
          <div className="stat-row">
            <span className="text-muted">Word count</span>
            <span className="stat-value"><AnimatedNumber value={wordCount} /></span>
          </div>
          <ul className="tips-list">
            <li>Keep it to one page — around 500–700 words.</li>
            <li>Lead bullet points with quantified outcomes, not duties.</li>
            <li>This base version is what tailoring rewrites per job.</li>
          </ul>
        </Panel3D>
      </div>
    </div>
  );
};

const RemindersView = ({ reminders, loading, onRefresh, onSendDigest, emailAccount, emailSummaries, onGmailConnect, onGmailSync, onGmailDisconnect }) => {
  const stale = reminders?.stale_applications || [];
  const oaDeadlines = reminders?.upcoming_oa_deadlines || [];
  const interviews = reminders?.upcoming_interviews || [];
  const [syncing, setSyncing] = useState(false);

  const handleSyncClick = async () => {
    setSyncing(true);
    try {
      await onGmailSync();
    } finally {
      setSyncing(false);
    }
  };

  return (
    <div>
      <div className="view-header">
        <h2 className="reveal" style={{ '--reveal-delay': '0ms' }}>
          <span className="orbit orbit-inline" /> Reminders
        </h2>
        <p className="sub reveal" style={{ '--reveal-delay': '70ms' }}>
          Applications gone quiet, deadlines coming up, and recruiter emails — all in one place.
        </p>
      </div>

      <div className="view-grid">
        <div className="panel-block reveal" style={{ '--reveal-delay': '120ms' }}>
          <div style={{ display: 'flex', gap: '10px', marginBottom: '18px' }}>
            <button onClick={onRefresh} className="btn" disabled={loading}>
              {loading && <span className="spinner" />}
              {loading ? 'Refreshing' : 'Refresh'}
            </button>
            <button onClick={onSendDigest} className="btn btn-primary">Send digest email now</button>
          </div>

          <h4 className="section-label">Gone quiet (7+ days, no update)</h4>
          {stale.length === 0 ? (
            <p className="text-muted" style={{ fontSize: '13px', marginBottom: '16px' }}>Nothing stale right now.</p>
          ) : (
            <div className="scroll-list" style={{ marginBottom: '16px' }}>
              {stale.map((a) => (
                <div key={a.id} className="result-box" style={{ marginBottom: '8px' }}>
                  <strong>{a.company}</strong> — {a.role}
                  <span className="text-muted"> · applied {a.days_since_applied} days ago</span>
                </div>
              ))}
            </div>
          )}

          <h4 className="section-label">OA deadlines coming up</h4>
          {oaDeadlines.length === 0 ? (
            <p className="text-muted" style={{ fontSize: '13px', marginBottom: '16px' }}>None in the next few days.</p>
          ) : (
            <div className="scroll-list" style={{ marginBottom: '16px' }}>
              {oaDeadlines.map((a) => (
                <div key={a.id} className="result-box" style={{ marginBottom: '8px' }}>
                  <strong>{a.company}</strong> — {a.role}
                  <span className="text-muted"> · due {new Date(a.oa_deadline).toLocaleString()}</span>
                </div>
              ))}
            </div>
          )}

          <h4 className="section-label">Interviews coming up</h4>
          {interviews.length === 0 ? (
            <p className="text-muted" style={{ fontSize: '13px' }}>None scheduled soon.</p>
          ) : (
            <div className="scroll-list">
              {interviews.map((a) => (
                <div key={a.id} className="result-box" style={{ marginBottom: '8px' }}>
                  <strong>{a.company}</strong> — {a.role}
                  <span className="text-muted"> · {new Date(a.interview_date).toLocaleString()}</span>
                </div>
              ))}
            </div>
          )}
        </div>

        <Panel3D className="reveal" style={{ '--reveal-delay': '190ms' }}>
          <h3>Recruiter inbox</h3>
          {emailAccount ? (
            <>
              <div className="stat-row">
                <span className="text-muted" style={{ fontSize: '13px' }}>Connected as</span>
                <span className="stat-value" style={{ fontSize: '13px' }}>{emailAccount.email_address}</span>
              </div>
              <div className="stat-row">
                <span className="text-muted" style={{ fontSize: '13px' }}>Last synced</span>
                <span className="stat-value" style={{ fontSize: '13px' }}>
                  {emailAccount.last_synced_at ? new Date(emailAccount.last_synced_at).toLocaleString() : 'Never'}
                </span>
              </div>
              <div style={{ display: 'flex', gap: '8px', marginTop: '12px', marginBottom: '14px' }}>
                <button onClick={handleSyncClick} className="btn btn-sm btn-primary" disabled={syncing}>
                  {syncing && <span className="spinner" />}
                  {syncing ? 'Syncing' : 'Sync now'}
                </button>
                <button onClick={onGmailDisconnect} className="btn btn-sm btn-ghost">Disconnect</button>
              </div>
              {emailSummaries.length === 0 ? (
                <p className="text-muted" style={{ fontSize: '13px' }}>No recruiter emails found yet — hit "Sync now" to pull recent recruiter emails from Gmail.</p>
              ) : (
                <ul className="tips-list">
                  {emailSummaries.slice(0, 4).map((e) => (
                    <li key={e.id}>{e.summary || e.subject}</li>
                  ))}
                </ul>
              )}
            </>
          ) : (
            <>
              <p className="text-muted" style={{ fontSize: '13px', marginBottom: '14px' }}>
                Connect Gmail (read-only) to auto-summarize recruiter emails and match them to your applications.
              </p>
              <button onClick={onGmailConnect} className="btn btn-primary btn-sm">Connect Gmail</button>
            </>
          )}
        </Panel3D>
      </div>
    </div>
  );
};

const DetailModal = ({ app, closing, onClose, onGenerateCoverLetter, onGenerateInterviewPrep, onGenerateFollowUp, onGenerateLearning, onGenerateTailorResume, onLoadResumeVersions, onLoadEmailSummaries, data }) => {
  const [tab, setTab] = useState('overview');
  const [busy, setBusy] = useState(null);

  const runGenerate = async (key, fn) => {
    setBusy(key);
    try {
      await fn(app.id);
    } finally {
      setBusy(null);
    }
  };

  useEffect(() => {
    if (tab === 'resume' && !data?.resumeVersions) onLoadResumeVersions(app.id);
    if (tab === 'emails' && !data?.appEmailSummaries) onLoadEmailSummaries(app.id);
  }, [tab]);

  return (
    <div className={`modal-overlay${closing ? ' closing' : ''}`} onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-head">
          <div>
            <h2>{app.company}</h2>
            <p className="role">{app.role}</p>
          </div>
          <button onClick={onClose} className="close-x">×</button>
        </div>

        <div className="modal-tabs">
          {['overview', 'cover', 'interview', 'followup', 'learning', 'resume', 'emails'].map(t => (
            <button key={t} onClick={() => setTab(t)} className={`modal-tab${tab === t ? ' active' : ''}`}>
              {t}
            </button>
          ))}
        </div>

        <div className="modal-body">
          <div className="modal-body-inner" key={tab}>
            {tab === 'overview' && (
              <div>
                {app.job_url && <p><strong>URL:</strong> <a href={app.job_url} target="_blank" rel="noreferrer" style={{ color: 'var(--accent)' }}>{app.job_url}</a></p>}
                {app.key_skills && <p><strong>Skills:</strong> {Array.isArray(app.key_skills) ? app.key_skills.join(', ') : app.key_skills}</p>}
                <p><strong>Status:</strong> {app.status}</p>
                {app.recruiter_name && <p><strong>Recruiter:</strong> {app.recruiter_name}{app.recruiter_email ? ` (${app.recruiter_email})` : ''}</p>}
                {app.oa_deadline && <p><strong>OA deadline:</strong> {new Date(app.oa_deadline).toLocaleString()}</p>}
                {app.interview_date && <p><strong>Interview:</strong> {new Date(app.interview_date).toLocaleString()}</p>}
                {app.days_since_applied != null && <p><strong>Applied:</strong> {app.days_since_applied} day(s) ago</p>}
              </div>
            )}
            {tab === 'cover' && (
              <div className="modal-section">
                <button
                  onClick={() => runGenerate('cover', onGenerateCoverLetter)}
                  disabled={busy === 'cover'}
                  className="btn btn-primary"
                  style={{ marginBottom: '14px' }}
                >
                  {busy === 'cover' && <span className="spinner" />}
                  {busy === 'cover' ? 'Generating' : 'Generate opener'}
                </button>
                {data?.coverLetter && <div className="result-box">{data.coverLetter}</div>}
                {data?.coverLetterWhy && (
                  <p className="text-muted" style={{ fontSize: '13px', marginTop: '10px' }}>
                    <strong>Why these skills:</strong> {data.coverLetterWhy}
                  </p>
                )}
              </div>
            )}
            {tab === 'interview' && (
              <div className="modal-section">
                <button
                  onClick={() => runGenerate('interview', onGenerateInterviewPrep)}
                  disabled={busy === 'interview'}
                  className="btn btn-primary"
                  style={{ marginBottom: '14px' }}
                >
                  {busy === 'interview' && <span className="spinner" />}
                  {busy === 'interview' ? 'Generating' : 'Generate prep'}
                </button>
                {data?.interviewPrep && (
                  <div>
                    <h4>Questions</h4>
                    <ul>{data.interviewPrep.questions.map((q, i) => <li key={i} style={{ animationDelay: `${i * 45}ms` }}>{q}</li>)}</ul>
                    <h4>Talking points</h4>
                    <ul>{data.interviewPrep.talking_points.map((p, i) => <li key={i} style={{ animationDelay: `${i * 45}ms` }}>{p}</li>)}</ul>
                    {data.interviewPrep.reasoning && (
                      <>
                        <h4>Why these questions</h4>
                        <p className="text-muted" style={{ fontSize: '13px' }}>{data.interviewPrep.reasoning}</p>
                      </>
                    )}
                  </div>
                )}
              </div>
            )}
            {tab === 'followup' && (
              <div className="modal-section">
                <button
                  onClick={() => runGenerate('followup', onGenerateFollowUp)}
                  disabled={busy === 'followup'}
                  className="btn btn-primary"
                  style={{ marginBottom: '14px' }}
                >
                  {busy === 'followup' && <span className="spinner" />}
                  {busy === 'followup' ? 'Drafting' : 'Draft email'}
                </button>
                {data?.followUp && (
                  <div className="result-box">
                    <p><strong>Subject:</strong> {data.followUp.subject}</p>
                    <p><strong>Body:</strong></p>
                    <p>{data.followUp.body}</p>
                  </div>
                )}
              </div>
            )}
            {tab === 'learning' && (
              <div className="modal-section">
                <button
                  onClick={() => runGenerate('learning', onGenerateLearning)}
                  disabled={busy === 'learning'}
                  className="btn btn-primary"
                  style={{ marginBottom: '14px' }}
                >
                  {busy === 'learning' && <span className="spinner" />}
                  {busy === 'learning' ? 'Fetching' : 'Get recommendations'}
                </button>
                {data?.learning && data.learning.length > 0 && (
                  <div>
                    {data.learning.map((rec, i) => (
                      <div key={i} className="result-box" style={{ marginBottom: '10px', animationDelay: `${i * 60}ms` }}>
                        <p style={{ fontWeight: '500', margin: '0 0 4px 0' }}>{rec.skill}</p>
                        <p className="text-muted" style={{ margin: '0 0 8px 0', fontSize: '13px' }}>{rec.why_it_matters}</p>
                        <p style={{ fontSize: '12px', margin: 0 }}>Topics: {rec.suggested_topics.join(', ')}</p>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
            {tab === 'resume' && (
              <div className="modal-section">
                <button
                  onClick={() => runGenerate('resume', onGenerateTailorResume)}
                  disabled={busy === 'resume'}
                  className="btn btn-primary"
                  style={{ marginBottom: '14px' }}
                >
                  {busy === 'resume' && <span className="spinner" />}
                  {busy === 'resume' ? 'Tailoring' : 'Tailor resume for this job'}
                </button>
                {data?.tailoredResume && (
                  <div className="result-box" style={{ marginBottom: '16px' }}>{data.tailoredResume}</div>
                )}
                {data?.resumeVersions && data.resumeVersions.length > 0 && (
                  <div>
                    <h4>Version history</h4>
                    {data.resumeVersions.map((v) => (
                      <div key={v.id} className="result-box" style={{ marginBottom: '8px' }}>
                        <p className="text-muted" style={{ fontSize: '12px', margin: '0 0 6px 0' }}>
                          {new Date(v.created_at).toLocaleString()}
                        </p>
                        <div className="snippet">{v.content}</div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
            {tab === 'emails' && (
              <div className="modal-section">
                {(!data?.appEmailSummaries || data.appEmailSummaries.length === 0) ? (
                  <p className="text-muted">No recruiter emails matched to this application yet. Connect Gmail and sync from the Reminders tab.</p>
                ) : (
                  data.appEmailSummaries.map((e) => (
                    <div key={e.id} className="result-box" style={{ marginBottom: '10px' }}>
                      <div className="meta" style={{ marginBottom: '6px' }}>
                        {e.detected_signal && <span className="pill">{e.detected_signal.replace('_', ' ')}</span>}
                      </div>
                      <p style={{ fontWeight: 500, margin: '0 0 4px 0' }}>{e.subject}</p>
                      <p className="text-muted" style={{ fontSize: '12px', margin: '0 0 8px 0' }}>{e.sender}</p>
                      <p style={{ margin: '0 0 8px 0' }}>{e.summary}</p>
                      {e.suggested_action && (
                        <p className="text-muted" style={{ fontSize: '13px', margin: 0 }}>
                          <strong>Suggested:</strong> {e.suggested_action}
                        </p>
                      )}
                    </div>
                  ))
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};




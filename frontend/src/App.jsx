import { useState, useMemo, useCallback, useEffect } from "react";
import UploadForm from "./components/UploadForm";
import ResumeList from "./components/ResumeList";
import ResultsDashboard from "./components/ResultsDashboard";
import ConfigurePage from "./components/ConfigurePage";
import AdminPage from "./components/AdminPage";
import SignInPage from "./components/SignInPage";
import tektalisLogo from "./assets/tektalis-logo.svg";
import "./App.css";

const API_BASE = "http://localhost:8000";
const JOB_CONFIG_STORAGE_KEY = "resumeiq.jobConfigs";
const AUTH_STORAGE_KEY = "resumeiq.currentUser";
const INTENDED_PAGE_STORAGE_KEY = "resumeiq.intendedPage";
const LAST_PAGE_STORAGE_KEY = "resumeiq.lastPage";
const SESSION_DURATION_MS = 30 * 60 * 1000;
const HASH_PAGE_MAP = {
  configure: "configure",
  upload: "upload",
  resumes: "list",
  leaderboard: "list",
  analytics: "analytics",
  users: "users",
};
const SIGNED_IN_PAGES = new Set(["configure", "upload", "list", "users", "analytics"]);
const REMEMBERED_PAGES = new Set(["configure", "upload", "list", "users"]);

const normalizeSignedInPage = (page) => (SIGNED_IN_PAGES.has(page) ? page : "configure");
const normalizeRememberedPage = (page) => (REMEMBERED_PAGES.has(page) ? page : null);

const pageFromHash = () => {
  const hash = window.location.hash.replace(/^#/, "");
  return HASH_PAGE_MAP[hash] || "configure";
};

const hashForPage = (page) => (page === "list" ? "leaderboard" : page);

const rememberPage = (page) => {
  const safePage = normalizeRememberedPage(page);
  if (safePage) {
    window.localStorage.setItem(LAST_PAGE_STORAGE_KEY, safePage);
  }
};

const rememberCurrentPage = () => {
  if (window.location.hash === "#signin") return;
  const page = pageFromHash();
  if (page) {
    window.sessionStorage.setItem(INTENDED_PAGE_STORAGE_KEY, page);
    rememberPage(page);
  }
};

const readSavedSession = () => {
  try {
    const saved = JSON.parse(window.localStorage.getItem(AUTH_STORAGE_KEY) || "null");
    if (!saved?.user || !saved?.expiresAt || saved.expiresAt <= Date.now()) {
      window.localStorage.removeItem(AUTH_STORAGE_KEY);
      return null;
    }
    return saved;
  } catch {
    window.localStorage.removeItem(AUTH_STORAGE_KEY);
    return null;
  }
};

const splitList = (value) => (
  value
    ? value.split(",").map((item) => item.trim()).filter(Boolean)
    : []
);

const toSkillObjects = (value, category = "Other") => (
  splitList(value).map((skill) => ({ skill, category }))
);

const extractEmail = (text = "") => (
  text.match(/\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b/)?.[0] || null
);

const extractPhone = (text = "") => {
  const matches = text.match(/(?:\+?\d{1,3}[\s.-]?)?(?:\(?\d{2,5}\)?[\s.-]?)?\d{3,5}[\s.-]?\d{4}\b/g) || [];
  const cleaned = matches
    .map((phone) => phone.trim())
    .find((phone) => phone.replace(/\D/g, "").length >= 10);
  return cleaned || null;
};

const extractExperience = (text = "") => {
  const match = text.match(/\b(\d{1,2}\+?)\s*(?:years?|yrs?)\b/i);
  return match ? `${match[1]} years` : null;
};

const extractExperienceNumber = (value = "") => {
  const match = String(value).match(/\b(\d{1,2})/);
  return match ? Number(match[1]) : null;
};

const isFresherRole = (jobDescription = "") => (
  /\bfreshers?\b|\bfresh graduates?\b|\bnew graduates?\b|\bgraduate trainees?\b|\bentry[-\s]?level\b|\bno\s+(?:prior\s+)?experience\s+(?:required|needed)\b|\b0\s*(?:-\s*1)?\s*(?:years?|yrs?)\b/i
    .test(jobDescription)
);

const deriveRoleTitle = (analysis = {}) => {
  const configuredRole = String(analysis.job_description || "").match(/Configured role:\s*([^\n.]+)/i)?.[1]?.trim();
  if (configuredRole) return configuredRole;

  const title = String(analysis.role_title || analysis.job_title || "").trim();
  if (!title) return "Unassigned role";
  if (title.length > 80 || title.includes("\n") || /(?:mandatory|backend|frontend|data|good-to-have|mindset):/i.test(title)) {
    return "Unassigned role";
  }
  return title;
};

const formatApiError = (detail) => {
  if (!detail) return null;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        const path = Array.isArray(item.loc) ? item.loc.join(".") : item.loc;
        return [path, item.msg].filter(Boolean).join(": ");
      })
      .filter(Boolean)
      .join("; ");
  }
  if (typeof detail === "object") return detail.message || detail.error || JSON.stringify(detail);
  return String(detail);
};

const roleToJobDescription = (role = {}) => {
  const weights = role.weights || {};
  return [
    role.jobDescription || "",
    `Configured role: ${role.roleTitle || "Selected role"}.`,
    `Experience years: ${role.minExperience || 0}.`,
    `Scoring weights: projects ${weights.projects || 0}%, skills ${weights.skills || 0}%, education ${weights.education || 0}%.`,
  ].join("\n");
};

const classifyExperienceLevel = (analysis = {}, resumeText = "") => {
  if (analysis.is_fresher_role || isFresherRole(analysis.job_description)) return "junior";

  const combined = `${resumeText} ${analysis.job_description || ""}`.toLowerCase();
  const years = extractExperienceNumber(analysis.experience_years || extractExperience(resumeText));
  if (years !== null) {
    if (years <= 2) return "junior";
    if (years <= 5) return "mid";
    if (years <= 10) return "senior";
    return "executive";
  }

  if (/\b(executive|director|head of|vp|vice president|principal)\b/.test(combined)) return "executive";
  if (/\b(senior|sr\.?|lead|staff)\b/.test(combined)) return "senior";

  if (analysis.experience_level && analysis.experience_level !== "junior") return analysis.experience_level;
  if (/\b(intern|internship|fresher|entry[-\s]?level|junior)\b/.test(combined)) return "junior";
  return analysis.experience_level || "junior";
};

const deriveNameFromFilename = (filename = "") => {
  const name = filename
    .replace(/\.[^.]+$/, "")
    .replace(/resume|cv|profile|final|updated/gi, "")
    .replace(/[_-]+/g, " ")
    .replace(/\s+/g, " ")
    .trim();
  if (!name) return null;
  return name.replace(/\b\w/g, (letter) => letter.toUpperCase());
};

const deriveCandidateName = (text = "", filename = "") => {
  const sectionTitles = new Set([
    "resume",
    "curriculum vitae",
    "career objective",
    "objective",
    "summary",
    "professional summary",
    "education",
    "experience",
    "skills",
    "projects",
  ]);

  for (const rawLine of text.split(/\r?\n/).slice(0, 15)) {
    const line = rawLine.replace(/\s+/g, " ").trim();
    if (!line || line.length > 60 || sectionTitles.has(line.toLowerCase())) continue;
    if (line.includes("@") || /\d/.test(line) || /https?:|linkedin|github/i.test(line)) continue;
    const words = line.split(" ");
    if (words.length >= 2 && words.length <= 5 && /^[A-Za-z][A-Za-z .'-]*$/.test(line)) {
      return line;
    }
  }

  return deriveNameFromFilename(filename);
};

const normalizeAnalysis = (analysis) => {
  if (!analysis) return null;
  if (analysis.llm_analysis && analysis.skills) {
    const fresherRole = analysis.is_fresher_role || isFresherRole(analysis.job_description);
    const experienceLevel = classifyExperienceLevel(analysis, analysis.resume_text);
    const listSkills = [
      ...(analysis.skills.matched_in_skills || analysis.skills.matched || []),
      ...(analysis.skill_project_analysis?.skills_in_both || []),
    ]
      .map((item) => (typeof item === "string" ? item : item.skill))
      .filter(Boolean);

    return {
      ...analysis,
      analysis_id: analysis.analysis_id || analysis.id,
      role_title: deriveRoleTitle(analysis),
      candidate_name: analysis.candidate_name || deriveCandidateName(analysis.resume_text, analysis.resume_name),
      phone_number: analysis.phone_number || extractPhone(analysis.resume_text),
      email: analysis.email || extractEmail(analysis.resume_text),
      experience_level: experienceLevel,
      experience_years: fresherRole || experienceLevel === "junior" ? null : (analysis.experience_years || extractExperience(analysis.resume_text)),
      is_fresher_role: fresherRole,
      llm_analysis: {
        ...analysis.llm_analysis,
        experience_match: fresherRole ? "Not required" : analysis.llm_analysis.experience_match,
      },
      received_date: analysis.received_date || analysis.created_at,
      listSkills: [...new Set(listSkills)],
    };
  }

  const matchedSkills = toSkillObjects(analysis.matched_skills, "Matched");
  const missingSkills = toSkillObjects(analysis.missing_skills, "Missing");
  const projectSkills = toSkillObjects(analysis.project_linked_skills, "Project");
  const resumeText = analysis.resume_text || "";
  const fresherRole = isFresherRole(analysis.job_description);
  const experienceLevel = classifyExperienceLevel(analysis, resumeText);

  return {
    ...analysis,
    analysis_id: analysis.id,
    role_title: deriveRoleTitle(analysis),
    candidate_name: analysis.candidate_name || deriveCandidateName(resumeText, analysis.resume_name),
    phone_number: analysis.phone_number || extractPhone(resumeText),
    email: analysis.email || extractEmail(resumeText),
    experience_level: experienceLevel,
    experience_years: fresherRole || experienceLevel === "junior" ? null : (analysis.experience_years || extractExperience(resumeText)),
    is_fresher_role: fresherRole,
    received_date: analysis.created_at,
    resume_length: resumeText.split(/\s+/).filter(Boolean).length,
    weighted_score: analysis.overall_score,
    tfidf_similarity: analysis.tfidf_score,
    embeddings_similarity: analysis.embeddings_score,
    llm_analysis: {
      overall_score: analysis.overall_score,
      ats_score: analysis.ats_score,
      summary: analysis.summary || "Saved analysis loaded from history.",
      strengths: analysis.strengths ? analysis.strengths.split(";").map((item) => item.trim()).filter(Boolean) : [],
      improvements: analysis.improvements ? analysis.improvements.split(";").map((item) => item.trim()).filter(Boolean) : [],
      experience_match: fresherRole ? "Not required" : (analysis.experience_match || "Fair"),
      education_match: "Good",
      interview_likelihood: analysis.interview_likelihood || "Medium",
      keyword_gaps: splitList(analysis.missing_skills).slice(0, 5),
    },
    skills: {
      matched_in_skills: matchedSkills,
      missing: missingSkills,
      extra: [],
      skill_match_percentage: analysis.skill_match_percentage || 0,
      total_jd_skills: matchedSkills.length + missingSkills.length,
    },
    skill_project_analysis: {
      exposure_score: analysis.exposure_score || 0,
      skills_in_both: projectSkills,
      skills_in_skills_only: [],
      skills_in_projects_only: [],
      skills_neither: missingSkills,
    },
    listSkills: matchedSkills.map((item) => item.skill),
  };
};

const defaultJobConfig = {
  id: "software-engineer",
  active: true,
  roleTitle: "Software Engineer",
  minExperience: "0",
  experienceLevel: "junior",
  minFitScore: 80,
  semanticThreshold: "0.72",
  requiredSkills: ["Python", "LLM", "RAG", "NLP", "TensorFlow", "Scikit-learn", "Keras", "LangChain", "FastAPI", "Flask", "Node.js", "PostgreSQL", "MongoDB", "React", "GitHub", "CI/CD", "Cloud"],
  projectKeywords: ["LLM", "RAG", "NLP", "REST API", "ML pipeline", "problem solving"],
  weights: {
    projects: 50,
    skills: 30,
    education: 20,
  },
  jobDescription: `Mandatory: Strong Python fundamentals.

AI/ML: Basics of LLMs and RAG pipelines, along with NLP fundamentals. Familiarity with frameworks such as TensorFlow, Scikit-learn, Keras, and LangChain.

Backend: Experience with FastAPI, Flask, or Node.js.

Data: Exposure to PostgreSQL or MongoDB.

Frontend: Working knowledge of React.

Good-to-have: GitHub, CI/CD and Cloud knowledge.

Mindset: A builder's mentality and solid problem-solving skill.`,
};

const createBlankRole = () => ({
  ...defaultJobConfig,
  id: `role-${Date.now()}`,
  active: false,
  roleTitle: "New Role",
  requiredSkills: [],
  projectKeywords: [],
  jobDescription: "",
});

export default function App() {
  const [currentUser, setCurrentUser] = useState(() => readSavedSession()?.user || null);
  const [sessionExpiresAt, setSessionExpiresAt] = useState(() => readSavedSession()?.expiresAt || null);
  const [view, setView] = useState(() => pageFromHash());
  const [jobConfigs, setJobConfigs] = useState(() => {
    try {
      const saved = window.localStorage.getItem(JOB_CONFIG_STORAGE_KEY);
      return saved ? JSON.parse(saved) : [defaultJobConfig];
    } catch {
      return [defaultJobConfig];
    }
  });
  const [analyses, setAnalyses] = useState([]);
  const [selectedAnalysis, setSelectedAnalysis] = useState(null);
  const [loading, setLoading] = useState(false);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [error, setError] = useState(null);
  const [mailPollStatus, setMailPollStatus] = useState("Automatic Graph mailbox analysis checks every 2 minutes.");
  const [mailPollBusy, setMailPollBusy] = useState(false);
  const canManageUsers = currentUser?.role === "admin";

  const loadMailStatus = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/mail/status`);
      if (!res.ok) return;
      const data = await res.json();
      const latest = data.latest_processed;
      const unparsed = data.unparsed || [];
      const latestLabel = latest
        ? `${latest.subject || "No subject"} from ${latest.sender || "unknown sender"}`
        : "none yet";
      const unparsedLabel = unparsed.length
        ? `${unparsed.length} unparsed: ${unparsed.slice(0, 3).map((item) => item.subject || item.message_id).join(", ")}`
        : "no unparsed mailbox records";
      setMailPollStatus(`Last parsed mail: ${latestLabel}. ${unparsedLabel}.`);
    } catch {
      // Mail status is informational; normal polling will show actionable errors.
    }
  }, []);

  const saveRoles = async (roles) => {
    setJobConfigs(roles);
    window.localStorage.setItem(JOB_CONFIG_STORAGE_KEY, JSON.stringify(roles));
    try {
      const res = await fetch(`${API_BASE}/job-roles`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ roles }),
      });
      if (!res.ok) return;
      const data = await res.json();
      if (data.roles?.length) {
        setJobConfigs(data.roles);
        window.localStorage.setItem(JOB_CONFIG_STORAGE_KEY, JSON.stringify(data.roles));
      }
    } catch {
      // Keep the local copy if the API is temporarily unavailable.
    }
  };

  const loadRoles = async () => {
    try {
      const res = await fetch(`${API_BASE}/job-roles`);
      if (!res.ok) return;
      const data = await res.json();
      if (data.roles?.length) {
        setJobConfigs(data.roles);
        window.localStorage.setItem(JOB_CONFIG_STORAGE_KEY, JSON.stringify(data.roles));
      } else {
        await saveRoles(jobConfigs);
      }
    } catch {
      // Local storage fallback is already loaded in initial state.
    }
  };

  const loadHistory = async () => {
    setHistoryLoading(true);
    try {
      const res = await fetch(`${API_BASE}/analyze/history?limit=100`);
      if (!res.ok) return;
      const data = await res.json();
      const history = (data.analyses || []).map(normalizeAnalysis).filter(Boolean);
      setAnalyses((current) => {
        const richById = new Map(
          current
            .filter((item) => item.llm_analysis && item.skills && item.resume_text)
            .map((item) => [item.analysis_id, item])
        );
        return history.map((item) => richById.get(item.analysis_id) || item);
      });
      return history;
    } catch {
      setAnalyses([]);
      return [];
    } finally {
      setHistoryLoading(false);
    }
  };

  useEffect(() => {
    if (!currentUser) return undefined;
    const initialPage = normalizeSignedInPage(pageFromHash());
    const allowedInitialPage = initialPage === "users" && !canManageUsers ? "configure" : initialPage;
    setView(allowedInitialPage);
    rememberPage(allowedInitialPage);
    if (!window.history.state?.page || allowedInitialPage !== initialPage) {
      window.history.replaceState({ page: allowedInitialPage }, "", `#${hashForPage(allowedInitialPage)}`);
    }
    loadRoles();
    loadHistory();
    loadMailStatus();

    const handlePopState = (event) => {
      const requestedPage = normalizeSignedInPage(event.state?.page || pageFromHash());
      const page = requestedPage === "users" && !canManageUsers ? "configure" : requestedPage;
      setView(page);
      rememberPage(page);
      if (page !== "results") setSelectedAnalysis(null);
      setError(null);
    };

    window.addEventListener("popstate", handlePopState);
    const historyRefresh = window.setInterval(loadHistory, 120000);
    return () => {
      window.removeEventListener("popstate", handlePopState);
      window.clearInterval(historyRefresh);
    };
  }, [currentUser, canManageUsers, loadMailStatus]);

  useEffect(() => {
    if (currentUser && view === "users" && !canManageUsers) {
      setView("configure");
      window.history.replaceState({ page: "configure" }, "", "#configure");
    }
  }, [currentUser, view, canManageUsers]);

  const analyzeOne = async (formData) => {
    const res = await fetch(`${API_BASE}/analyze`, {
      method: "POST",
      body: formData,
    });
    if (!res.ok) {
      const contentType = res.headers.get("content-type") || "";
        const err = contentType.includes("application/json")
          ? await res.json()
          : { detail: await res.text() };
      throw new Error(formatApiError(err.detail) || `Analysis failed (${res.status})`);
    }
    return normalizeAnalysis(await res.json());
  };

  const handleAnalyze = async (formDataOrList) => {
    const formDataList = Array.isArray(formDataOrList) ? formDataOrList : [formDataOrList];
    setLoading(true);
    setError(null);
    setSelectedAnalysis(null);
    try {
      const analyzed = [];
      for (const formData of formDataList) {
        analyzed.push(await analyzeOne(formData));
      }
      setAnalyses((current) => [
        ...analyzed,
        ...current.filter((item) => !analyzed.some((next) => next.analysis_id === item.analysis_id)),
      ]);
      setView("list");
      rememberPage("list");
      window.history.pushState({ page: "list" }, "", "#resumes");
      loadHistory();
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const handleNewAnalysis = () => {
    setView("upload");
    rememberPage("upload");
    setSelectedAnalysis(null);
    setError(null);
    window.history.pushState({ page: "upload" }, "", "#upload");
  };

  const handleNavigate = (page) => {
    const requestedPage = normalizeSignedInPage(page);
    const nextPage = requestedPage === "users" && !canManageUsers ? "configure" : requestedPage;
    setView(nextPage);
    rememberPage(nextPage);
    if (nextPage !== "results") setSelectedAnalysis(null);
    setError(null);
    window.history.pushState({ page: nextPage }, "", `#${hashForPage(nextPage)}`);
  };

  const handleSelectAnalysis = (analysis) => {
    setSelectedAnalysis(analysis);
    setView("analytics");
    window.history.pushState({ page: "analytics" }, "", "#analytics");
  };

  const activeJobs = jobConfigs.filter((job) => job.active);
  const defaultUploadJob = activeJobs[0] || jobConfigs[0];
  const configuredMailboxRoles = useMemo(
    () => (activeJobs.length ? activeJobs : jobConfigs),
    [jobConfigs]
  );

  const runMailboxAnalysis = useCallback(async ({ navigateToList = false } = {}) => {
    const selectedJob = configuredMailboxRoles[0];
    if (!selectedJob?.jobDescription?.trim()) {
      setMailPollStatus("Configure at least one active role before mailbox analysis can run.");
      return;
    }

    setMailPollBusy(true);
    try {
      const res = await fetch(`${API_BASE}/mail/pull`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          job_description: selectedJob.jobDescription || "",
          role_title: selectedJob.roleTitle || "",
          roles_json: JSON.stringify(configuredMailboxRoles),
          expected_experience_level: selectedJob.experienceLevel || "junior",
          min_fit_score: Number(selectedJob.minFitScore) || 80,
          max_messages: 50,
          send_shortlist_emails: true,
        }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || "Unable to analyze mailbox");

      const saved = data.saved_analysis_count || 0;
      const processed = data.processed_count || 0;
      const nextRun = new Date(Date.now() + 120000).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
      await loadHistory();
      await loadMailStatus();
      setMailPollStatus((current) => `Graph mailbox checked: ${processed} message${processed === 1 ? "" : "s"} processed, ${saved} analysis${saved === 1 ? "" : "es"} saved. ${current} Next check around ${nextRun}.`);
      if (navigateToList) {
        setView("list");
        rememberPage("list");
        window.history.pushState({ page: "list" }, "", "#leaderboard");
      }
    } catch (mailError) {
      setMailPollStatus(mailError.message);
    } finally {
      setMailPollBusy(false);
    }
  }, [configuredMailboxRoles, loadMailStatus]);

  const handleSaveRoles = (roles) => {
    saveRoles(roles);
  };

  useEffect(() => {
    if (!currentUser) return undefined;
    const mailboxRefresh = window.setInterval(() => {
      runMailboxAnalysis();
    }, 120000);
    return () => window.clearInterval(mailboxRefresh);
  }, [currentUser, runMailboxAnalysis]);

  const handleSignedIn = (user) => {
    const expiresAt = Date.now() + SESSION_DURATION_MS;
    const savedPage = normalizeRememberedPage(window.sessionStorage.getItem(INTENDED_PAGE_STORAGE_KEY));
    const lastPage = normalizeRememberedPage(window.localStorage.getItem(LAST_PAGE_STORAGE_KEY));
    const requestedPage = savedPage || normalizeSignedInPage(pageFromHash());
    const preferredPage = requestedPage === "configure" && lastPage ? lastPage : requestedPage;
    const nextPage = preferredPage === "users" && user.role !== "admin" ? "configure" : preferredPage;
    setCurrentUser(user);
    setSessionExpiresAt(expiresAt);
    setView(nextPage);
    rememberPage(nextPage);
    window.localStorage.setItem(
      AUTH_STORAGE_KEY,
      JSON.stringify({ user, expiresAt })
    );
    window.sessionStorage.removeItem(INTENDED_PAGE_STORAGE_KEY);
    window.history.replaceState({ page: nextPage }, "", `#${hashForPage(nextPage)}`);
  };

  const handleSignOut = () => {
    setCurrentUser(null);
    setSessionExpiresAt(null);
    setSelectedAnalysis(null);
    setError(null);
    window.localStorage.removeItem(AUTH_STORAGE_KEY);
    window.history.replaceState({ page: "signin" }, "", "#signin");
  };

  useEffect(() => {
    if (!currentUser || !sessionExpiresAt) return undefined;
    const sessionTimer = window.setTimeout(
      handleSignOut,
      Math.max(0, sessionExpiresAt - Date.now())
    );
    return () => window.clearTimeout(sessionTimer);
  }, [currentUser, sessionExpiresAt]);

  useEffect(() => {
    if (!currentUser) {
      rememberCurrentPage();
      window.history.replaceState({ page: "signin" }, "", "#signin");
    }
  }, [currentUser]);

  useEffect(() => {
    if (!currentUser || window.location.hash !== "#signin") return;
    const lastPage = normalizeRememberedPage(window.localStorage.getItem(LAST_PAGE_STORAGE_KEY));
    const nextPage = lastPage === "users" && !canManageUsers ? "configure" : (lastPage || "configure");
    setView(nextPage);
    window.history.replaceState({ page: nextPage }, "", `#${hashForPage(nextPage)}`);
  }, [currentUser, canManageUsers]);

  if (!currentUser) {
    return <SignInPage onSignedIn={handleSignedIn} />;
  }

  const effectiveView = normalizeSignedInPage(view);
  const safeView = effectiveView === "users" && !canManageUsers ? "configure" : effectiveView;

  return (
    <div className="app">
      <header className="header">
        <div className="header-inner">
          <div className="logo">
            <span className="logo-surface">
              <img src={tektalisLogo} alt="Tektalis" className="tektalis-logo" />
            </span>
            <span className="logo-text">Resume Analyzer</span>
          </div>
          <div className="header-session">
            <span>{currentUser.email}</span>
            <button type="button" onClick={handleSignOut}>Sign out</button>
          </div>
        </div>
      </header>

      <main className="main">
        {safeView === "upload" && (
          <UploadForm
            onAnalyze={handleAnalyze}
            loading={loading}
            error={error}
            activeJob={defaultUploadJob}
            activeJobs={activeJobs.length ? activeJobs : jobConfigs}
            onNavigate={handleNavigate}
            onMailPulled={() => runMailboxAnalysis({ navigateToList: true })}
            mailPollStatus={mailPollStatus}
            mailPollBusy={mailPollBusy}
            currentUser={currentUser}
          />
        )}
        {(safeView === "configure" || !SIGNED_IN_PAGES.has(safeView)) && (
          <ConfigurePage
            roles={jobConfigs}
            onSave={handleSaveRoles}
            createBlankRole={createBlankRole}
            onNavigate={handleNavigate}
            currentUser={currentUser}
          />
        )}
        {safeView === "list" && (
          <ResumeList
            analyses={analyses}
            onSelect={handleSelectAnalysis}
            onNavigate={handleNavigate}
            loading={historyLoading}
            error={error}
            activeJob={defaultUploadJob}
            currentUser={currentUser}
          />
        )}
        {safeView === "users" && (
          <AdminPage
            onNavigate={handleNavigate}
            currentUser={currentUser}
          />
        )}
        {safeView === "analytics" && selectedAnalysis && (
          <ResultsDashboard
            result={selectedAnalysis}
            onReset={() => setView("list")}
            resetLabel="Back to Leaderboard"
          />
        )}
        {safeView === "analytics" && !selectedAnalysis && (
          <ResumeList
            analyses={analyses}
            onSelect={handleSelectAnalysis}
            onNavigate={handleNavigate}
            loading={historyLoading}
            error={error}
            activeJob={defaultUploadJob}
            currentUser={currentUser}
          />
        )}
      </main>

    </div>
  );
}

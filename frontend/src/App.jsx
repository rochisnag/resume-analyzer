import { useState, useMemo, useCallback, useEffect } from "react";
import UploadForm from "./components/UploadForm";
import ResumeList from "./components/ResumeList";
import ResultsDashboard from "./components/ResultsDashboard";
import ConfigurePage from "./components/ConfigurePage";
import AdminPage from "./components/AdminPage";
import tektalisLogo from "./assets/tektalis-logo.svg";
import "./App.css";

const API_BASE = "http://127.0.0.1:8000";
const JOB_CONFIG_STORAGE_KEY = "resumeiq.jobConfigs";

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
  const [view, setView] = useState("configure");
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
    window.history.replaceState({ page: "configure" }, "", "#configure");
    loadRoles();
    loadHistory();

    const handlePopState = (event) => {
      const page = event.state?.page || "configure";
      setView(page);
      if (page !== "results") setSelectedAnalysis(null);
      setError(null);
    };

    window.addEventListener("popstate", handlePopState);
    const historyRefresh = window.setInterval(loadHistory, 120000);
    return () => {
      window.removeEventListener("popstate", handlePopState);
      window.clearInterval(historyRefresh);
    };
  }, []);

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
    setSelectedAnalysis(null);
    setError(null);
    window.history.pushState({ page: "upload" }, "", "#upload");
  };

  const handleNavigate = (page) => {
    setView(page);
    if (page !== "results") setSelectedAnalysis(null);
    setError(null);
    const hash = page === "list" ? "leaderboard" : page;
    window.history.pushState({ page }, "", `#${hash}`);
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
          max_messages: 20,
          send_shortlist_emails: true,
        }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || "Unable to analyze mailbox");

      const saved = data.saved_analysis_count || 0;
      const processed = data.processed_count || 0;
      const nextRun = new Date(Date.now() + 120000).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
      setMailPollStatus(`Graph mailbox checked: ${processed} message${processed === 1 ? "" : "s"} processed, ${saved} analysis${saved === 1 ? "" : "es"} saved. Next check around ${nextRun}.`);
      await loadHistory();
      if (navigateToList) {
        setView("list");
        window.history.pushState({ page: "list" }, "", "#leaderboard");
      }
    } catch (mailError) {
      setMailPollStatus(mailError.message);
    } finally {
      setMailPollBusy(false);
    }
  }, [configuredMailboxRoles]);

  const handleSaveRoles = (roles) => {
    saveRoles(roles);
  };

  useEffect(() => {
    const mailboxRefresh = window.setInterval(() => {
      runMailboxAnalysis();
    }, 120000);
    return () => window.clearInterval(mailboxRefresh);
  }, [runMailboxAnalysis]);

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
          <p className="header-tagline">AI-powered resume analysis</p>
        </div>
      </header>

      <main className="main">
        {view === "upload" && (
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
          />
        )}
        {view === "configure" && (
          <ConfigurePage
            roles={jobConfigs}
            onSave={handleSaveRoles}
            createBlankRole={createBlankRole}
            onNavigate={handleNavigate}
          />
        )}
        {view === "list" && (
          <ResumeList
            analyses={analyses}
            onSelect={handleSelectAnalysis}
            onNavigate={handleNavigate}
            loading={historyLoading}
            error={error}
            activeJob={defaultUploadJob}
          />
        )}
        {view === "users" && (
          <AdminPage
            onNavigate={handleNavigate}
          />
        )}
        {view === "analytics" && selectedAnalysis && (
          <ResultsDashboard
            result={selectedAnalysis}
            onReset={() => setView("list")}
            resetLabel="Back to Leaderboard"
          />
        )}
      </main>

    </div>
  );
}

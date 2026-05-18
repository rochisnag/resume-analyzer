import { useMemo, useState } from "react";
import AppNav from "./AppNav";

const scoreNumber = (score) => Math.round(Number(score) || 0);

const getScore = (analysis) => (
  Number(
    analysis.llm_analysis?.overall_score
    || analysis.weighted_score
    || analysis.overall_score
    || 0
  )
);

const getCandidateName = (analysis) => (
  analysis.candidate_name
  || analysis.resume_name?.replace(/\.[^.]+$/, "").replace(/[_-]+/g, " ")
  || "Candidate not detected"
);

const getEmail = (analysis) => analysis.email || "Email not found";
const getPhone = (analysis) => analysis.phone_number || "Phone not found";
const formatLevel = (level) => (
  level ? level.charAt(0).toUpperCase() + level.slice(1) : "Junior"
);
const getExperience = (analysis) => {
  const level = analysis.experience_level || "junior";
  if (level === "junior" || analysis.is_fresher_role) return formatLevel(level);
  return `${formatLevel(level)} - ${analysis.experience_years || analysis.llm_analysis?.experience_match || "years not detected"}`;
};
const getRoleTitle = (analysis) => {
  const role = analysis.role_title || analysis.job_title || "Unassigned role";
  return role.length > 80 || role.includes("\n") ? "Unassigned role" : role;
};

const getStatus = (score) => {
  if (score >= 80) return "Shortlisted";
  if (score >= 65) return "Review";
  return "Hold";
};

const getInitials = (name) => (
  name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join("") || "CA"
);

const csvEscape = (value) => `"${String(value ?? "").replace(/"/g, '""')}"`;
const levelOrder = ["junior", "mid", "senior", "executive"];

export default function ResumeList({ analyses, onSelect, onNavigate, loading, error, activeJob, currentUser }) {
  const [sortBy, setSortBy] = useState("received");
  const [query, setQuery] = useState("");
  const rows = analyses;

  const visibleAnalyses = useMemo(() => {
    const needle = query.trim().toLowerCase();
    return [...rows]
      .filter((analysis) => {
        if (!needle) return true;
        return [
          getCandidateName(analysis),
        getEmail(analysis),
          getPhone(analysis),
          analysis.experience_level,
          analysis.experience_years,
          analysis.is_fresher_role ? "Not required" : "",
          ...(analysis.listSkills || []),
        ].filter(Boolean).join(" ").toLowerCase().includes(needle);
      })
      .sort((a, b) => {
        if (sortBy === "level") {
          return levelOrder.indexOf(a.experience_level || "junior") - levelOrder.indexOf(b.experience_level || "junior");
        }
        if (sortBy === "name") return getCandidateName(a).localeCompare(getCandidateName(b));
        if (sortBy === "received") return new Date(b.received_date || b.created_at) - new Date(a.received_date || a.created_at);
        return getScore(b) - getScore(a);
      });
  }, [rows, query, sortBy]);

  const groupedAnalyses = useMemo(() => (
    levelOrder
      .map((level) => ({
        level,
        items: visibleAnalyses.filter((analysis) => (analysis.experience_level || "junior") === level),
      }))
      .filter((group) => group.items.length > 0)
  ), [visibleAnalyses]);

  const stats = useMemo(() => {
    const source = rows;
    const scores = source.map(getScore);
    const avg = scores.length ? scores.reduce((sum, score) => sum + score, 0) / scores.length : 0;
    const shortlisted = source.filter((item) => getStatus(getScore(item)) === "Shortlisted").length;
    const allSkills = source.flatMap((item) => item.listSkills || []);
    const skillCounts = allSkills.reduce((acc, skill) => {
      acc[skill] = (acc[skill] || 0) + 1;
      return acc;
    }, {});
    const topSkill = Object.entries(skillCounts).sort((a, b) => b[1] - a[1])[0]?.[0] || "Not enough data";
    return {
      total: source.length,
      avg: avg.toFixed(1),
      shortlisted,
      topSkill,
    };
  }, [rows]);

  const exportCsv = () => {
    const headers = ["Candidate", "Role", "Experience level", "Experience", "Skills", "Score", "Phone", "Email", "Status"];
    const lines = visibleAnalyses.map((analysis) => {
      const score = scoreNumber(getScore(analysis));
      return [
        getCandidateName(analysis),
        getRoleTitle(analysis),
        formatLevel(analysis.experience_level || "junior"),
        getExperience(analysis),
        (analysis.listSkills || []).join(", "),
        score,
        getPhone(analysis),
        getEmail(analysis),
        getStatus(score),
      ].map(csvEscape).join(",");
    });
    const blob = new Blob([[headers.map(csvEscape).join(","), ...lines].join("\n")], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "candidate-leaderboard.csv";
    link.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="leaderboard-page">
      <div className="leaderboard-shell">
        <AppNav
          active="list"
          onNavigate={onNavigate}
          currentUser={currentUser}
          rightSlot={
            <>
            <button type="button" onClick={exportCsv}>Export CSV</button>
            </>
          }
        />
        <section className="leaderboard-stats" aria-label="Leaderboard summary">
          <div>
            <span>Total evaluated</span>
            <strong>{stats.total}</strong>
            <small>from analysis history</small>
          </div>
          <div>
            <span>Avg. score</span>
            <strong>{stats.avg}</strong>
            <small>out of 100</small>
          </div>
          <div>
            <span>Shortlisted</span>
            <strong>{stats.shortlisted}</strong>
            <small>Score 80+</small>
          </div>
          <div>
            <span>Top skill signal</span>
            <strong className="skill-stat">{stats.topSkill}</strong>
            <small>Most common among ranked candidates</small>
          </div>
        </section>

        <div className="ranked-heading">
          <div>
            <h2>Ranked candidates</h2>
          </div>
          <div className="leaderboard-controls">
            <input
              type="search"
              placeholder="Search candidates, skills, email"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
            />
            <label>
              <span>Sort</span>
              <select value={sortBy} onChange={(event) => setSortBy(event.target.value)}>
                <option value="score">Score</option>
                <option value="level">Experience level</option>
                <option value="received">Recently received</option>
                <option value="name">Candidate name</option>
              </select>
            </label>
          </div>
        </div>

        {error && (
          <div className="error-banner list-error">
            <span>!</span> {error}
          </div>
        )}
        <div className="leaderboard-table">
          <div className="leaderboard-table-head">
            <span>Candidate</span>
            <span>Role</span>
            <span>Experience</span>
            <span>Skills</span>
            <span>Score</span>
            <span>Phone</span>
            <span>Email</span>
            <span>Status</span>
          </div>

          {loading ? (
            <div className="resume-empty">Loading resumes...</div>
          ) : visibleAnalyses.length === 0 ? (
            <div className="resume-empty">No candidates match this search.</div>
          ) : (
            <div className="leaderboard-table-body">
              {groupedAnalyses.map((group) => (
                <div key={group.level} className="leaderboard-level-group">
                  <div className="leaderboard-group-row">
                    <strong>{formatLevel(group.level)}</strong>
                    <span>{group.items.length} candidate{group.items.length === 1 ? "" : "s"}</span>
                  </div>
                  {group.items.map((analysis) => {
                const skills = analysis.listSkills || [];
                const score = scoreNumber(getScore(analysis));
                const candidateName = getCandidateName(analysis);
                const email = getEmail(analysis);
                const phone = getPhone(analysis);
                const status = getStatus(score);
                const matchedCount = Math.max(1, Math.ceil((Number(analysis.skill_match_percentage) || 0) / 100 * Math.max(skills.length, 6)));
                const totalSkills = Math.max(skills.length, 6);

                return (
                  <article key={analysis.analysis_id || analysis.id || analysis.resume_name} className="leaderboard-row">
                    <button className="leader-candidate" type="button" onClick={() => onSelect(analysis)}>
                      <span className="avatar">{getInitials(candidateName)}</span>
                      <span>
                        <strong>{candidateName}</strong>
                        <small>{analysis.resume_name || "Uploaded resume"}</small>
                        <small className="candidate-contact">{email}</small>
                        <small className="candidate-contact">{phone}</small>
                      </span>
                    </button>
                    <span>{getRoleTitle(analysis)}</span>
                    <span>{getExperience(analysis)}</span>
                    <button className="leader-skills" type="button" onClick={() => onSelect(analysis)}>
                      <span className="skill-count">{matchedCount} / {totalSkills}</span>
                      <span className="skill-chip-row">
                        {skills.length > 0 ? skills.slice(0, 3).map((skill) => (
                          <span key={skill} className="mini-skill-chip">{skill}</span>
                        )) : <span className="muted-cell">No skills found</span>}
                      </span>
                    </button>
                    <strong className="score-only">{score}</strong>
                    <span>{phone}</span>
                    <span className="email-cell">{email}</span>
                    <span className={`status-pill ${status.toLowerCase()}`}>{status}</span>
                  </article>
                );
                  })}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

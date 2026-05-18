import ScoreRing from "./ScoreRing";
import SkillsPanel from "./SkillsPanel";

const MATCH_COLOR = {
  Poor: "#ef4444",
  Fair: "#f59e0b",
  Good: "#10b981",
  Excellent: "#6366f1",
  "Not required": "#64748b",
};

const getGradeInfo = (score) => {
  if (score >= 85) return { grade: "A", label: "Excellent match", color: "#10b981" };
  if (score >= 70) return { grade: "B", label: "Good match", color: "#6366f1" };
  if (score >= 55) return { grade: "C", label: "Fair match", color: "#f59e0b" };
  if (score >= 40) return { grade: "D", label: "Weak match", color: "#fb7185" };
  return { grade: "F", label: "Poor match", color: "#ef4444" };
};

export default function ResultsDashboard({ result, onReset, resetLabel = "New Analysis" }) {
  const {
    resume_name,
    candidate_name,
    llm_analysis: llm,
    skills,
    skill_project_analysis,
    resume_length,
  } = result;
  const gradeInfo = getGradeInfo(llm.overall_score);

  return (
    <div className="results-page">
      <div className="results-header">
        <div>
          <h2 className="results-title">Analysis Complete</h2>
          <p className="results-sub">
            {candidate_name || "Candidate"} - {resume_name || "Uploaded resume"} - {resume_length} words extracted - {skills.total_jd_skills} JD skills detected
          </p>
        </div>
        <button className="reset-btn" onClick={onReset}>{resetLabel}</button>
      </div>

      <div className="scores-row">
        <div className="score-card primary">
          <ScoreRing score={llm.overall_score} label="Overall Match" color="#6366f1" size={120} />
        </div>
        <div className="score-card">
          <ScoreRing score={llm.ats_score} label="ATS Score" color="#10b981" size={100} />
        </div>
        <div className="score-card">
          <ScoreRing score={Math.round(skills.skill_match_percentage)} label="Skill Match" color="#ec4899" size={100} />
        </div>
        <div className="score-card">
          <ScoreRing score={Math.round(skill_project_analysis.exposure_score)} label="Project Exposure" color="#8b5cf6" size={100} />
        </div>
      </div>

      <div className="report-meta-card">
        <div>
          <span className="meta-label">Candidate</span>
          <strong>{candidate_name || "Not detected"}</strong>
        </div>
        <div>
          <span className="meta-label">Resume File</span>
          <strong>{resume_name || "Uploaded resume"}</strong>
        </div>
        <div className="grade-summary" style={{ borderColor: `${gradeInfo.color}55` }}>
          <span className="grade-letter" style={{ color: gradeInfo.color }}>{gradeInfo.grade}</span>
          <div>
            <span className="meta-label">Overall Grade</span>
            <strong>{gradeInfo.label}</strong>
          </div>
        </div>
        <div>
          <span className="meta-label">Grade Scale</span>
          <strong>A 85-100 | B 70-84 | C 55-69 | D 40-54 | F below 40</strong>
        </div>
      </div>

      <div className="summary-card">
        <p className="summary-text">"{llm.summary}"</p>
        {llm.project_exposure_feedback && (
          <p className="summary-text secondary">"{llm.project_exposure_feedback}"</p>
        )}
        <div className="meta-pills">
          <span className="pill" style={{ borderColor: `${MATCH_COLOR[llm.experience_match]}66`, color: MATCH_COLOR[llm.experience_match] }}>
            Experience: {llm.experience_match}
          </span>
          <span className="pill" style={{ borderColor: `${MATCH_COLOR[llm.education_match]}66`, color: MATCH_COLOR[llm.education_match] }}>
            Education: {llm.education_match}
          </span>
        </div>
      </div>

      <div className="detail-grid">
        <div className="detail-card span-2">
          <h3 className="card-title">Strengths</h3>
          <ul className="feedback-list">
            {llm.strengths.map((s, i) => (
              <li key={i} className="feedback-item strength">{s}</li>
            ))}
          </ul>
        </div>

        <div className="detail-card span-2">
          <SkillsPanel skills={skills} skill_project_analysis={skill_project_analysis} />
        </div>
      </div>
    </div>
  );
}

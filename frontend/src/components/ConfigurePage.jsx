import { useState } from "react";
import AppNav from "./AppNav";

const removeItem = (items, item) => items.filter((value) => value !== item);

const skillCatalog = [
  "Python", "Java", "JavaScript", "TypeScript", "React", "Node.js", "FastAPI", "Flask",
  "Spring Boot", "PostgreSQL", "MongoDB", "MySQL", "SQL", "Kubernetes",
  "GitHub", "Git", "CI/CD", "Cloud", "AWS", "Azure", "GCP", "LLM", "RAG", "NLP",
  "TensorFlow", "Scikit-learn", "Keras", "LangChain", "PyTorch", "REST API",
  "GraphQL", "Redis", "Machine Learning",
];

const projectCatalog = [
  "LLM", "RAG", "NLP", "REST API", "ML pipeline", "problem solving", "full-stack",
  "backend", "frontend", "deployment", "cloud", "database", "automation",
];

const extractMatches = (text, catalog) => {
  const normalized = text.toLowerCase();
  return catalog.filter((item) => normalized.includes(item.toLowerCase()));
};

export default function ConfigurePage({ roles, onSave, createBlankRole, onNavigate }) {
  const [drafts, setDrafts] = useState(roles);
  const [selectedId, setSelectedId] = useState(roles.find((role) => role.active)?.id || roles[0]?.id);
  const [skillText, setSkillText] = useState("");
  const [keywordText, setKeywordText] = useState("");
  const [status, setStatus] = useState("");
  const draft = drafts.find((role) => role.id === selectedId) || drafts[0];
  const commitDrafts = (nextDrafts) => {
    setDrafts(nextDrafts);
    onSave(nextDrafts);
  };
  const updateDraft = (nextDraft) => commitDrafts(drafts.map((item) => (item.id === nextDraft.id ? nextDraft : item)));

  const updateWeight = (key, value) => {
    const nextValue = Number(value);
    const otherKeys = Object.keys(draft.weights).filter((item) => item !== key);
    const remaining = Math.max(0, 100 - nextValue);
    const currentOtherTotal = otherKeys.reduce((sum, item) => sum + Number(draft.weights[item] || 0), 0);
    const nextWeights = { ...draft.weights, [key]: nextValue };

    if (currentOtherTotal === 0) {
      otherKeys.forEach((item, index) => {
        nextWeights[item] = index === 0 ? remaining : 0;
      });
    } else {
      let assigned = 0;
      otherKeys.forEach((item, index) => {
        const adjusted = index === otherKeys.length - 1
          ? remaining - assigned
          : Math.round((Number(draft.weights[item] || 0) / currentOtherTotal) * remaining);
        nextWeights[item] = adjusted;
        assigned += adjusted;
      });
    }

    updateDraft({ ...draft, weights: nextWeights });
  };

  const addSkill = (skill) => {
    const value = skill.trim();
    if (!value || draft.requiredSkills.includes(value)) return;
    updateDraft({ ...draft, requiredSkills: [...draft.requiredSkills, value] });
    setSkillText("");
  };

  const addKeyword = () => {
    const value = keywordText.trim();
    if (!value || draft.projectKeywords.includes(value)) return;
    updateDraft({ ...draft, projectKeywords: [...draft.projectKeywords, value] });
    setKeywordText("");
  };

  const saveRole = () => {
    onSave(drafts);
    setStatus(`${draft.roleTitle || "Role"} saved`);
    const nextRole = createBlankRole();
    const nextDrafts = [...drafts, nextRole];
    setDrafts(nextDrafts);
    setSelectedId(nextRole.id);
  };

  const addRole = () => {
    const nextRole = createBlankRole();
    commitDrafts([...drafts, nextRole]);
    setSelectedId(nextRole.id);
    setStatus("New job title added");
  };

  const setActiveRole = (roleId) => {
    const nextDrafts = drafts.map((role) => (
      role.id === roleId ? { ...role, active: !role.active } : role
    ));
    commitDrafts(nextDrafts);
  };

  const deleteRole = (roleId) => {
    const nextDrafts = drafts.filter((role) => role.id !== roleId);
    const deletedRole = drafts.find((role) => role.id === roleId);
    commitDrafts(nextDrafts);
    if (selectedId === roleId) {
      setSelectedId(nextDrafts[0]?.id);
    }
    setStatus(`${deletedRole?.roleTitle || "Role"} deleted`);
  };

  const updateJobDescription = (value) => {
    updateDraft({
      ...draft,
      jobDescription: value,
      requiredSkills: extractMatches(value, skillCatalog),
      projectKeywords: extractMatches(value, projectCatalog),
    });
  };

  return (
    <div className="leaderboard-page">
      <div className="leaderboard-shell configure-shell">
        <AppNav
          active="configure"
          onNavigate={onNavigate}
          rightSlot={<button type="button" onClick={addRole}>Add Role</button>}
        />
        {status && <p className="config-status">{status}</p>}

        <section className="configure-grid">
          <aside className="config-sidebar">
            <div className="config-block">
              <h2>Job roles</h2>
              <div className="role-list">
                {drafts.map((role) => (
                  <button
                    key={role.id}
                    type="button"
                    className={`role-list-item ${role.id === selectedId ? "selected" : ""}`}
                    onClick={() => setSelectedId(role.id)}
                  >
                    <span>{role.roleTitle || "Untitled role"}</span>
                    <span className="role-actions">
                      <strong
                        role="button"
                        tabIndex={0}
                        onClick={(event) => {
                          event.stopPropagation();
                          setActiveRole(role.id);
                        }}
                        onKeyDown={(event) => {
                          if (event.key === "Enter" || event.key === " ") {
                            event.preventDefault();
                            event.stopPropagation();
                            setActiveRole(role.id);
                          }
                        }}
                      >
                        {role.active ? "Active" : "Inactive"}
                      </strong>
                      <em
                        role="button"
                        tabIndex={0}
                        onClick={(event) => {
                          event.stopPropagation();
                          deleteRole(role.id);
                        }}
                        onKeyDown={(event) => {
                          if (event.key === "Enter" || event.key === " ") {
                            event.preventDefault();
                            event.stopPropagation();
                            deleteRole(role.id);
                          }
                        }}
                      >
                        Delete
                      </em>
                    </span>
                  </button>
                ))}
              </div>
            </div>

            <div className="config-block">
              <h2>Required skills</h2>
              <div className="tag-list">
                {draft.requiredSkills.map((skill) => (
                  <button key={skill} type="button" className="config-tag" onClick={() => updateDraft({
                    ...draft,
                    requiredSkills: removeItem(draft.requiredSkills, skill),
                  })}>
                    {skill} <span>x</span>
                  </button>
                ))}
              </div>
              <div className="inline-add">
                <input value={skillText} onChange={(event) => setSkillText(event.target.value)} placeholder="+ Add skill" />
                <button type="button" onClick={() => addSkill(skillText)}>Add</button>
              </div>
            </div>

            <div className="config-block">
              <h2>Project keywords</h2>
              <div className="tag-list">
                {draft.projectKeywords.map((keyword) => (
                  <button key={keyword} type="button" className="config-tag keyword" onClick={() => updateDraft({
                    ...draft,
                    projectKeywords: removeItem(draft.projectKeywords, keyword),
                  })}>
                    {keyword} <span>x</span>
                  </button>
                ))}
              </div>
              <div className="inline-add">
                <input value={keywordText} onChange={(event) => setKeywordText(event.target.value)} placeholder="+ Add keyword" />
                <button type="button" onClick={addKeyword}>Add</button>
              </div>
            </div>

            <div className="config-block">
              <h2>Scoring weights</h2>
              <label className="weight-row">
                <span>Projects section</span>
                <input type="range" min="0" max="100" value={draft.weights.projects} onChange={(event) => updateWeight("projects", event.target.value)} />
                <strong>{draft.weights.projects}%</strong>
              </label>
              <label className="weight-row">
                <span>Skills section</span>
                <input type="range" min="0" max="100" value={draft.weights.skills} onChange={(event) => updateWeight("skills", event.target.value)} />
                <strong>{draft.weights.skills}%</strong>
              </label>
              <label className="weight-row">
                <span>Education</span>
                <input type="range" min="0" max="100" value={draft.weights.education} onChange={(event) => updateWeight("education", event.target.value)} />
                <strong>{draft.weights.education}%</strong>
              </label>
              <p className="weight-total">Total {Number(draft.weights.projects) + Number(draft.weights.skills) + Number(draft.weights.education)}%</p>
            </div>
          </aside>

          <section className="config-main">
            <div className="active-role">
              <h2>Job role</h2>
              <div className="role-grid">
                <label>
                  <span>Role title</span>
                  <input value={draft.roleTitle} onChange={(event) => updateDraft({ ...draft, roleTitle: event.target.value })} />
                </label>
                <label>
                  <span>Experience level</span>
                  <select value={draft.experienceLevel || "junior"} onChange={(event) => {
                    const level = event.target.value;
                    const minExperienceByLevel = {
                      junior: "0",
                      mid: "3",
                      senior: "6",
                      executive: "10",
                    };
                    updateDraft({
                      ...draft,
                      experienceLevel: level,
                      minExperience: minExperienceByLevel[level],
                    });
                  }}>
                    <option value="junior">Junior - under 3 years</option>
                    <option value="mid">Mid - 3 to under 6 years</option>
                    <option value="senior">Senior - 6 to under 10 years</option>
                    <option value="executive">Executive - 10+ years</option>
                  </select>
                </label>
                <label>
                  <span>Shortlist threshold</span>
                  <input type="number" min="0" max="100" value={draft.minFitScore} onChange={(event) => updateDraft({ ...draft, minFitScore: event.target.value })} />
                </label>
              </div>
              <label className="job-description-field">
                <span>Job description</span>
                <textarea value={draft.jobDescription} onChange={(event) => updateJobDescription(event.target.value)} rows={7} />
              </label>
            </div>

            <button className="primary-action" type="button" onClick={saveRole}>
              Save role
            </button>
          </section>
        </section>
      </div>
    </div>
  );
}

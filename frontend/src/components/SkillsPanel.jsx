const CATEGORY_COLORS = {
  "Programming Languages": "#6366f1",
  "Web Frameworks": "#ec4899",
  Databases: "#f59e0b",
  "Cloud & DevOps": "#10b981",
  "AI & Data": "#06b6d4",
  "Soft Skills": "#8b5cf6",
};

function mergeSkills(...lists) {
  const seen = new Set();
  return lists
    .flat()
    .filter(Boolean)
    .filter((item) => {
      const skill = typeof item === "string" ? item : item.skill;
      if (!skill) return false;
      const key = skill.toLowerCase();
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    })
    .map((item) => (typeof item === "string" ? { skill: item, category: "Other" } : item));
}

function groupByCategory(items) {
  return items.reduce((acc, item) => {
    const category = item.category || "Other";
    if (!acc[category]) acc[category] = [];
    acc[category].push(item.skill);
    return acc;
  }, {});
}

function SkillGroup({ title, description, items, tone }) {
  const grouped = groupByCategory(items);

  return (
    <section className={`skill-bucket ${tone}`}>
      <div className="skill-bucket-head">
        <h4>{title}</h4>
        <span>{items.length}</span>
      </div>
      <p>{description}</p>

      {Object.keys(grouped).length === 0 ? (
        <p className="empty-skills">No skills in this category.</p>
      ) : (
        <div className="skill-categories">
          {Object.entries(grouped).map(([category, skillList]) => (
            <div key={category} className="skill-category">
              <span className="cat-label" style={{ color: CATEGORY_COLORS[category] || "#888" }}>
                {category}
              </span>
              <div className="skill-chips">
                {skillList.map((skill) => (
                  <span
                    key={skill}
                    className={`skill-chip ${tone}`}
                    style={{ borderColor: `${CATEGORY_COLORS[category] || "#888"}44` }}
                  >
                    {skill}
                  </span>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}

export default function SkillsPanel({ skills, skill_project_analysis }) {
  const projectData = skill_project_analysis || {};
  const matchedSkills = mergeSkills(
    skills.matched_in_skills,
    skills.matched,
    projectData.skills_in_both,
    projectData.skills_in_skills_only,
  );
  const extraSkills = mergeSkills(skills.extra, projectData.skills_in_projects_only);
  const missingSkills = mergeSkills(skills.missing, projectData.skills_neither);

  return (
    <div className="skills-panel">
      <h3 className="card-title">Skill Analysis</h3>

      <div className="skill-bars-container">
        <div className="skill-bar-wrap">
          <div className="skill-bar-bg">
            <div className="skill-bar-fill" style={{ width: `${skills.skill_match_percentage}%` }} />
          </div>
          <span className="skill-bar-pct">{skills.skill_match_percentage}% skill match</span>
        </div>
        {projectData.exposure_score !== undefined && (
          <div className="skill-bar-wrap">
            <div className="skill-bar-bg">
              <div className="skill-bar-fill exposure" style={{ width: `${projectData.exposure_score}%` }} />
            </div>
            <span className="skill-bar-pct">{projectData.exposure_score}% project exposure</span>
          </div>
        )}
      </div>

      <div className="skill-overview-grid">
        <SkillGroup
          title="Matched Skills"
          description="Required skills found in the resume."
          items={matchedSkills}
          tone="matched"
        />
        <SkillGroup
          title="Extra Skills"
          description="Additional skills found beyond the JD."
          items={extraSkills}
          tone="extra"
        />
        <SkillGroup
          title="Missing Skills"
          description="JD skills not found in the resume."
          items={missingSkills}
          tone="missing"
        />
      </div>
    </div>
  );
}

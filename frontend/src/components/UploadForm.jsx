import { useRef, useState } from "react";
import AppNav from "./AppNav";

export default function UploadForm({
  onAnalyze,
  loading,
  error,
  activeJob,
  activeJobs = [],
  onNavigate,
  onMailPulled,
  mailPollStatus,
  mailPollBusy,
  currentUser,
}) {
  const [files, setFiles] = useState([]);
  const [dragging, setDragging] = useState(false);
  const [intakeMode, setIntakeMode] = useState("manual");
  const selectedJob = activeJob || activeJobs[0];
  const configuredRoles = activeJobs.length ? activeJobs : (selectedJob ? [selectedJob] : []);
  const [mailDraft, setMailDraft] = useState({
    minFitScore: selectedJob?.minFitScore || 80,
    sendShortlistEmails: true,
  });
  const fileRef = useRef();

  const addFiles = (fileList) => {
    const incoming = Array.from(fileList || []);
    if (!incoming.length) return;
    setFiles((current) => {
      const seen = new Set(current.map((item) => `${item.name}-${item.size}-${item.lastModified}`));
      const next = incoming.filter((item) => {
        const key = `${item.name}-${item.size}-${item.lastModified}`;
        if (seen.has(key)) return false;
        seen.add(key);
        return true;
      });
      return [...current, ...next];
    });
  };

  const removeFile = (fileToRemove) => {
    setFiles((current) => current.filter((item) => item !== fileToRemove));
  };

  const handleDrop = (event) => {
    event.preventDefault();
    setDragging(false);
    addFiles(event.dataTransfer.files);
  };

  const handleSubmit = (event) => {
    event.preventDefault();
    if (!files.length || !configuredRoles.length) return;
    const fallbackJob = configuredRoles[0] || selectedJob || {};
    const fallbackWeights = fallbackJob.weights || {};
    const fallbackJobDescription = [
      fallbackJob.jobDescription || "",
      `Configured role: ${fallbackJob.roleTitle || "Selected role"}.`,
      `Experience level: ${fallbackJob.experienceLevel || "junior"}.`,
      `Experience years: ${fallbackJob.minExperience || 0}.`,
      `Scoring weights: projects ${fallbackWeights.projects || 0}%, skills ${fallbackWeights.skills || 0}%, education ${fallbackWeights.education || 0}%.`,
    ].join("\n");

    const formDataList = files.map((queuedFile) => {
      const formData = new FormData();
      formData.append("resume", queuedFile);
      formData.append("job_description", fallbackJobDescription);
      formData.append("roles_json", JSON.stringify(configuredRoles));
      formData.append("min_fit_score", String(fallbackJob.minFitScore || 80));
      formData.append("send_shortlist_email_enabled", String(mailDraft.sendShortlistEmails));
      return formData;
    });
    onAnalyze(formDataList);
  };

  const queuedCount = files.length;

  return (
    <div className="leaderboard-page">
      <div className="leaderboard-shell upload-workspace">
        <AppNav active="upload" onNavigate={onNavigate} currentUser={currentUser} />

        <div className="intake-tabs" role="tablist" aria-label="Resume intake mode">
          <button type="button" className={intakeMode === "manual" ? "active" : ""} onClick={() => setIntakeMode("manual")}>Manual upload</button>
          <button type="button" className={intakeMode === "outlook" ? "active" : ""} onClick={() => setIntakeMode("outlook")}>Graph intake</button>
        </div>

        <form className="upload-board" onSubmit={handleSubmit}>
          <section className="manual-upload-panel">
            {intakeMode === "manual" ? (
              <>
                <div
                  className={`wire-drop-zone ${dragging ? "dragging" : ""} ${queuedCount ? "has-file" : ""}`}
                  onClick={() => fileRef.current.click()}
                  onDragOver={(event) => { event.preventDefault(); setDragging(true); }}
                  onDragLeave={() => setDragging(false)}
                  onDrop={handleDrop}
                >
                  <input
                    ref={fileRef}
                    type="file"
                    accept=".pdf,.docx,.txt"
                    multiple
                    hidden
                    onChange={(event) => {
                      addFiles(event.target.files);
                      event.target.value = "";
                    }}
                  />
                  <span className="wire-upload-icon">UP</span>
                  <h1>{queuedCount ? `${queuedCount} resume${queuedCount === 1 ? "" : "s"} selected` : "Drop PDFs or DOCX here"}</h1>
                  <p>Supports multiple resumes - Max 20MB per file - PDF, DOCX, TXT</p>
                </div>

                <div className="upload-queue">
                  <div className="queue-heading">
                    <h2>Upload queue</h2>
                    <span>{loading ? `${queuedCount} parsing` : queuedCount ? `${queuedCount} ready` : "No files selected"}</span>
                  </div>
                  {queuedCount ? (
                    files.map((queuedFile) => {
                      const extension = queuedFile.name.split(".").pop()?.toUpperCase() || "PDF";
                      return (
                        <article className="queue-item" key={`${queuedFile.name}-${queuedFile.size}-${queuedFile.lastModified}`}>
                          <span className="file-type">{extension}</span>
                          <div>
                            <strong>{queuedFile.name}</strong>
                            <p>{loading ? "Detecting role and scoring..." : "Ready for automatic role matching"}</p>
                            <div className="queue-progress">
                              <span style={{ width: loading ? "64%" : "100%" }}></span>
                            </div>
                          </div>
                          <button
                            className={`queue-status ${loading ? "parsing" : "done"}`}
                            type="button"
                            disabled={loading}
                            onClick={() => removeFile(queuedFile)}
                          >
                            {loading ? "Parsing" : "Remove"}
                          </button>
                        </article>
                      );
                    })
                  ) : (
                    <div className="empty-queue">Choose one or more resumes to start scoring against the active job role.</div>
                  )}
                </div>

                {error && <div className="error-banner"><span>!</span> {error}</div>}

                <label className="check-row">
                  <input
                    type="checkbox"
                    checked={mailDraft.sendShortlistEmails}
                    onChange={(event) => setMailDraft({ ...mailDraft, sendShortlistEmails: event.target.checked })}
                  />
                  <span>Send automatic email when shortlisted</span>
                </label>

                <button
                  type="submit"
                  className={`primary-action ${loading ? "loading" : ""}`}
                  disabled={!queuedCount || !configuredRoles.length || loading}
                >
                  {loading ? "Analyzing resumes..." : `Analyze ${queuedCount || "selected"} resume${queuedCount === 1 ? "" : "s"}`}
                </button>
              </>
            ) : (
              <section className="outlook-intake-panel">
                <h2>Automatic Graph intake</h2>
                <div className="mail-source-row">
                  <span>Inbox</span>
                  <strong>Microsoft Graph</strong>
                </div>
                <div className="mail-source-row">
                  <span>Schedule</span>
                  <strong>Every 2 minutes</strong>
                </div>
                <div className="mail-source-row">
                  <span>Role matching</span>
                  <strong>{configuredRoles.length} active role{configuredRoles.length === 1 ? "" : "s"}</strong>
                </div>
                <div className="mail-source-row">
                  <span>Shortlist score</span>
                  <strong>{Number(selectedJob?.minFitScore) || 80}+</strong>
                </div>
                <button className="primary-action" type="button" disabled={mailPollBusy || !selectedJob?.jobDescription?.trim()} onClick={onMailPulled}>
                  {mailPollBusy ? "Checking Graph mailbox..." : "Check mailbox now"}
                </button>
                {mailPollStatus && <p className="admin-status">{mailPollStatus}</p>}
              </section>
            )}
          </section>

          <aside className="upload-side-panel">
            <section className="detected-sections-card">
              <h2>Role matching</h2>
              <strong>{configuredRoles.length} configured role{configuredRoles.length === 1 ? "" : "s"}</strong>
              <p>Each resume is matched to the most suitable role before scoring.</p>
              <ul>
                <li><span className="section-dot purple"></span>Summary</li>
                <li><span className="section-dot green"></span>Technical Skills</li>
                <li><span className="section-dot orange"></span>Projects weighted</li>
                <li><span className="section-dot gray"></span>Education</li>
              </ul>
            </section>
          </aside>
        </form>
      </div>
    </div>
  );
}

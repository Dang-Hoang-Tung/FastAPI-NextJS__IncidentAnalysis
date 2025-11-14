"use client";

import { useState } from "react";

type IncidentForm = {
  date_time_of_incident: string;
  service_user_name: string;
  location_of_incident: string;
  type_of_incident: string;
  description_of_incident: string;
  immediate_actions_taken: string;
  was_first_aid_administered: boolean;
  were_emergency_services_contacted: boolean;
  who_was_notified: string;
  witnesses: string;
  agreed_next_steps: string;
  risk_assessment_needed: boolean;
  risk_assessment_details?: string | null;
};

type IncidentResponse = {
  incident_form: IncidentForm;
  email_draft: string;
};

// Example transcript (same as before, trimmed for brevity if needed)
const EXAMPLE_TRANSCRIPT = `Telephone Call Transcript
Julie Peaterson: "Good morning, Julie Peaterson speaking, how can I help you?"
Greg Jones: "Hi, uh, it's Greg... Greg Jones. I've, uh, I've fallen again."
Julie Peaterson: "Oh no, Greg! Are you alright? Where are you right now?"
Greg Jones: "I'm in the living room, on the floor... I tried getting up, but I just can't seem to manage it this time."
Julie Peaterson: "Okay, Greg, take a deep breath. Let's not rush. Are you hurt? Do you feel any pain or see any blood?"
Greg Jones: "No, no, there's no blood... I don't think anything's broken either. It's just... I don't know. I feel a bit all over the place, to be honest. Can't really remember how I ended up down here."
Julie Peaterson: "Alright, that's good to hear there's no immediate injuries. But you sound a little off. How long have you been on the floor, Greg?"
Greg Jones: "I don't know... maybe 20 minutes? It could be longer. I just—my mind's a bit fuzzy, can't really think straight right now."
Julie Peaterson: "Hmm, okay. You mentioned this has happened before. Has it been happening often?"
Greg Jones: "Yeah, this is the third time... this week. I'm just so... so frustrated, Julie. Every time I think I'm okay, and then... boom, I'm back on the floor."
Julie Peaterson: "Oh Greg, I'm really sorry to hear that. It must be so frustrating for you. Let's get you some help right away, okay? I'll make sure someone gets to you as soon as possible."
Greg Jones: "Thanks, Julie. I just... I don't know what's going on anymore."
Julie Peaterson: "Don't worry, Greg. We'll get this sorted, and we'll talk about what's been happening. It sounds like we need to look at what's going on a bit more closely."
Greg Jones: "Yeah, maybe... I just hate this feeling. I don't want it happening again."
Julie Peaterson: "I completely understand, Greg. You're doing great by calling in. We'll get you back on your feet and figure out how to prevent this from happening again."
`;


export default function IncidentAnalysisPage() {
  const [transcript, setTranscript] = useState<string>(EXAMPLE_TRANSCRIPT);
  const [analysis, setAnalysis] = useState<IncidentResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleAnalyze() {
    setLoading(true);
    setError(null);

    try {
      const API_BASE_URL = "";
      const response = await fetch(`${API_BASE_URL}/api/analyze`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ transcript }),
      });

      if (!response.ok) {
        const text = await response.text();
        console.error("Failed to analyze transcript", text);
        setError("Failed to analyze transcript. Please try again.");
        setAnalysis(null);
        return;
      }

      const data = (await response.json()) as IncidentResponse;
      setAnalysis(data);
    } catch (err) {
      console.error("Error calling /api/analyze:", err);
      setError("Something went wrong while contacting the backend.");
      setAnalysis(null);
    } finally {
      setLoading(false);
    }
  }

  function handleUseExample() {
    setTranscript(EXAMPLE_TRANSCRIPT);
  }

  const containerStyle: React.CSSProperties = {
    minHeight: "100vh",
    margin: 0,
    padding: "2rem 1.5rem",
    display: "flex",
    justifyContent: "center",
    background:
      "radial-gradient(circle at top left, #eef2ff 0, #f9fafb 40%, #e0f2fe 100%)",
    fontFamily:
      '-apple-system, BlinkMacSystemFont, "SF Pro Text", system-ui, sans-serif',
  };

  const contentStyle: React.CSSProperties = {
    width: "100%",
    maxWidth: "1120px",
    display: "flex",
    flexDirection: "column",
    gap: "1.75rem",
  };

  const cardStyle: React.CSSProperties = {
    backgroundColor: "rgba(255, 255, 255, 0.96)",
    borderRadius: "18px",
    padding: "1.5rem 1.75rem",
    boxShadow:
      "0 18px 35px rgba(15, 23, 42, 0.15), 0 0 0 1px rgba(148, 163, 184, 0.18)",
    backdropFilter: "blur(10px)",
  };

  const subtleCardStyle: React.CSSProperties = {
    ...cardStyle,
    boxShadow:
      "0 10px 25px rgba(15, 23, 42, 0.08), 0 0 0 1px rgba(148, 163, 184, 0.16)",
  };

  const headingStyle: React.CSSProperties = {
    fontSize: "1.8rem",
    fontWeight: 700,
    letterSpacing: "-0.04em",
    color: "#0f172a",
    marginBottom: "0.25rem",
  };

  const badgeStyle: React.CSSProperties = {
    display: "inline-flex",
    alignItems: "center",
    gap: "0.4rem",
    borderRadius: "999px",
    padding: "0.2rem 0.75rem",
    fontSize: "0.75rem",
    fontWeight: 500,
    background:
      "linear-gradient(135deg, rgba(59,130,246,0.12), rgba(56,189,248,0.16))",
    color: "#1d4ed8",
  };

  const textareaStyle: React.CSSProperties = {
    width: "100%",
    minHeight: "600px",
    borderRadius: "14px",
    border: "1px solid #cbd5f5",
    padding: "0.9rem 1rem",
    fontSize: "0.95rem",
    fontFamily: "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas",
    resize: "vertical",
    outline: "none",
    backgroundColor: "#f9fafb",
  };

  const labelStyle: React.CSSProperties = {
    fontSize: "0.8rem",
    fontWeight: 600,
    letterSpacing: "0.04em",
    textTransform: "uppercase",
    color: "#6b7280",
    marginBottom: "0.3rem",
  };

  const buttonRowStyle: React.CSSProperties = {
    display: "flex",
    flexWrap: "wrap",
    gap: "0.75rem",
    alignItems: "center",
    marginTop: "0.8rem",
  };

  const primaryButtonStyle: React.CSSProperties = {
    borderRadius: "999px",
    border: "none",
    padding: "0.65rem 1.4rem",
    fontSize: "0.9rem",
    fontWeight: 600,
    cursor: "pointer",
    color: "#ffffff",
    background:
      "linear-gradient(135deg, #2563eb, #4f46e5, #06b6d4)",
    boxShadow: "0 12px 30px rgba(37, 99, 235, 0.4)",
    display: "inline-flex",
    alignItems: "center",
    gap: "0.45rem",
  };

  const secondaryButtonStyle: React.CSSProperties = {
    borderRadius: "999px",
    border: "1px solid rgba(148, 163, 184, 0.7)",
    padding: "0.6rem 1.1rem",
    fontSize: "0.85rem",
    fontWeight: 500,
    cursor: "pointer",
    backgroundColor: "rgba(255,255,255,0.9)",
    color: "#374151",
    display: "inline-flex",
    alignItems: "center",
    gap: "0.35rem",
  };

  const gridStyle: React.CSSProperties = {
    display: "grid",
    gridTemplateColumns: "minmax(0, 1.1fr) minmax(0, 1fr)",
    gap: "1.5rem",
  };

  const stackMobile: React.CSSProperties = {
    display: "flex",
    flexDirection: "column",
    gap: "1.5rem",
  };

  // simple mobile detection via window width-less approach:
  const isClient = typeof window !== "undefined";
  const isMobile = isClient ? window.innerWidth < 900 : false;

  const layoutStyle = isMobile ? stackMobile : gridStyle;

  return (
    <main style={containerStyle}>
      <div style={contentStyle}>
        {/* Header */}
        <div
          style={{ display: "flex", flexDirection: "column", gap: "0.4rem" }}
        >
          <span style={badgeStyle}>
            <span
              style={{
                width: 8,
                height: 8,
                borderRadius: "999px",
                background:
                  "radial-gradient(circle at 30% 30%, #22c55e 0, #16a34a 40%, #15803d 100%)",
              }}
            />
            AI-assisted incident response
          </span>
          <h1 style={headingStyle}>Incident Analysis Workspace</h1>
          <p
            style={{
              fontSize: "0.95rem",
              color: "#4b5563",
              maxWidth: "620px",
            }}
          >
            Paste a call transcript or case note, and the system will generate a
            structured incident form and escalation email draft, grounded in
            your policies.
          </p>
        </div>

        {/* Main area: input + results */}
        <div style={layoutStyle}>
          {/* Left: transcript input */}
          <section style={cardStyle}>
            <div style={{ marginBottom: "0.4rem" }}>
              <div style={labelStyle}>Transcript</div>
              <p
                style={{
                  fontSize: "0.8rem",
                  color: "#6b7280",
                  marginBottom: "0.75rem",
                }}
              >
                You can edit the example, or paste a real-world conversation or
                visit notes. The model will analyze what you provide.
              </p>
            </div>

            <textarea
              style={textareaStyle}
              value={transcript}
              onChange={(e) => setTranscript(e.target.value)}
              placeholder="Paste transcript here..."
            />

            <div style={buttonRowStyle}>
              <button
                type="button"
                style={{
                  ...primaryButtonStyle,
                  opacity: loading ? 0.7 : 1,
                  cursor: loading ? "wait" : "pointer",
                }}
                onClick={handleAnalyze}
                disabled={loading}
              >
                {loading ? (
                  <>
                    <span className="spinner" />
                    Analyzing…
                  </>
                ) : (
                  <>
                    <span>▶</span>
                    Run analysis
                  </>
                )}
              </button>

              <button
                type="button"
                style={secondaryButtonStyle}
                onClick={handleUseExample}
              >
                <span>⟳</span>
                Use example transcript
              </button>

              {error && (
                <span
                  style={{
                    fontSize: "0.8rem",
                    color: "#b91c1c",
                    marginLeft: "0.25rem",
                  }}
                >
                  {error}
                </span>
              )}
            </div>
          </section>

          {/* Right: results */}
          <section style={stackMobile}>
            <div style={subtleCardStyle}>
              <div style={{ marginBottom: "0.4rem" }}>
                <div style={labelStyle}>Incident form</div>
                <p
                  style={{
                    fontSize: "0.8rem",
                    color: "#6b7280",
                    marginBottom: "0.7rem",
                  }}
                >
                  Generated from the transcript and policy context. You can
                  review and copy this into your case management system.
                </p>
              </div>

              {analysis ? (
                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns: "minmax(0, 1fr)",
                    rowGap: "0.4rem",
                    columnGap: "1.2rem",
                    fontSize: "0.85rem",
                  }}
                >
                  {renderIncidentRow(
                    "Date & time",
                    analysis.incident_form.date_time_of_incident
                  )}
                  {renderIncidentRow(
                    "Service user",
                    analysis.incident_form.service_user_name
                  )}
                  {renderIncidentRow(
                    "Location",
                    analysis.incident_form.location_of_incident
                  )}
                  {renderIncidentRow(
                    "Type of incident",
                    analysis.incident_form.type_of_incident
                  )}
                  {renderIncidentRow(
                    "Description",
                    analysis.incident_form.description_of_incident
                  )}
                  {renderIncidentRow(
                    "Immediate actions",
                    analysis.incident_form.immediate_actions_taken
                  )}
                  {renderIncidentRow(
                    "First aid administered",
                    analysis.incident_form.was_first_aid_administered
                      ? "Yes"
                      : "No"
                  )}
                  {renderIncidentRow(
                    "Emergency services contacted",
                    analysis.incident_form.were_emergency_services_contacted
                      ? "Yes"
                      : "No"
                  )}
                  {renderIncidentRow(
                    "Who was notified",
                    analysis.incident_form.who_was_notified
                  )}
                  {renderIncidentRow(
                    "Witnesses",
                    analysis.incident_form.witnesses
                  )}
                  {renderIncidentRow(
                    "Agreed next steps",
                    analysis.incident_form.agreed_next_steps
                  )}
                  {renderIncidentRow(
                    "Risk assessment needed",
                    analysis.incident_form.risk_assessment_needed ? "Yes" : "No"
                  )}
                  {analysis.incident_form.risk_assessment_needed &&
                    renderIncidentRow(
                      "Risk assessment details",
                      analysis.incident_form.risk_assessment_details ??
                        "Not specified"
                    )}
                </div>
              ) : (
                <p
                  style={{
                    fontSize: "0.85rem",
                    color: "#9ca3af",
                    fontStyle: "italic",
                  }}
                >
                  Run an analysis to see the structured incident form here.
                </p>
              )}
            </div>

            <div style={subtleCardStyle}>
              <div style={{ marginBottom: "0.4rem" }}>
                <div style={labelStyle}>Email draft</div>
                <p
                  style={{
                    fontSize: "0.8rem",
                    color: "#6b7280",
                    marginBottom: "0.7rem",
                  }}
                >
                  A suggested escalation email you can refine and send via your
                  usual channels.
                </p>
              </div>
              {analysis ? (
                <pre
                  style={{
                    whiteSpace: "pre-wrap",
                    backgroundColor: "#020617",
                    color: "#e5e7eb",
                    padding: "0.9rem 1rem",
                    borderRadius: "12px",
                    fontSize: "0.82rem",
                    fontFamily:
                      'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace',
                    maxHeight: "640px",
                    overflow: "auto",
                  }}
                >
                  {analysis.email_draft}
                </pre>
              ) : (
                <p
                  style={{
                    fontSize: "0.85rem",
                    color: "#9ca3af",
                    fontStyle: "italic",
                  }}
                >
                  After analysis, the email draft will appear here.
                </p>
              )}
            </div>
          </section>
        </div>
      </div>
    </main>
  );
}

function renderIncidentRow(label: string, value: string) {
  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "0.6fr 1.4fr",
        columnGap: "0.75rem",
        alignItems: "flex-start",
      }}
    >
      <div
        style={{
          fontWeight: 600,
          fontSize: "0.78rem",
          textTransform: "uppercase",
          letterSpacing: "0.05em",
          color: "#6b7280",
          marginTop: "0.15rem",
        }}
      >
        {label}
      </div>
      <div style={{ color: "#111827", fontSize: "0.86rem" }}>{value}</div>
    </div>
  );
}

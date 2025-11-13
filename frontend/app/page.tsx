type PolicyIssue = {
  policy_id?: string | null;
  description: string;
  severity: string;
  evidence: string;
};

type IncidentForm = {
  title: string;
  incident_summary: string;
  policies_breached: string[];
  risk_level: string;
  recommended_actions: string[];
};

type IncidentResponse = {
  incident_form: IncidentForm;
  email_draft: string;
  issues: PolicyIssue[];
};

// 👇 Example transcript (you can paste the full file contents here)
const EXAMPLE_TRANSCRIPT = `Telephone Call Transcript
Julie Peaterson: "Good morning, Julie Peaterson speaking, how can I help you?"
Greg Jones: "Hi, uh, it's Greg... Greg Jones. I’ve, uh, I’ve fallen again."
Julie Peaterson: "Oh no, Greg! Are you alright? Where are you right now?"
Greg Jones: "I’m in the living room, on the floor... I tried getting up, but I just can’t seem to manage it this time."
Julie Peaterson: "Okay, Greg, take a deep breath. Let’s not rush. Are you hurt? Do you feel any pain or see any blood?"
Greg Jones: "No, no, there’s no blood... I don’t think anything's broken either. It’s just... I don’t know. I feel a bit all over the place, to be honest. Can’t really remember how I ended up down here."
Julie Peaterson: "Alright, that’s good to hear there’s no immediate injuries. But you sound a little off. How long have you been on the floor, Greg?"
Greg Jones: "I don’t know... maybe 20 minutes? It could be longer. I just—my mind’s a bit fuzzy, can’t really think straight right now."
Julie Peaterson: "Hmm, okay. You mentioned this has happened before. Has it been happening often?"
Greg Jones: "Yeah, this is the third time... this week. I’m just so... so frustrated, Julie. Every time I think I’m okay, and then... boom, I’m back on the floor."
Julie Peaterson: "Oh Greg, I’m really sorry to hear that. It must be so frustrating for you. Let’s get you some help right away, okay? I’ll make sure someone gets to you as soon as possible."
Greg Jones: "Thanks, Julie. I just... I don’t know what’s going on anymore."
Julie Peaterson: "Don't worry, Greg. We’ll get this sorted, and we’ll talk about what’s been happening. It sounds like we need to look at what’s going on a bit more closely."
Greg Jones: "Yeah, maybe... I just hate this feeling. I don’t want it happening again."
Julie Peaterson: "I completely understand, Greg. You’re doing great by calling in. We’ll get you back on your feet and figure out how to prevent this from happening again."
`;

export default async function MyNextFastAPIApp() {
  const analysis = await analyzeExampleTranscript();

  if (!analysis) {
    return <div>Failed to get incident analysis.</div>;
  }

  const { incident_form, email_draft, issues } = analysis;

  return (
    <main style={{ padding: "1.5rem", fontFamily: "system-ui, sans-serif" }}>
      <h1>Incident Analysis (Example Transcript)</h1>

      <section style={{ marginTop: "1rem" }}>
        <h2>Incident Form</h2>
        <p>
          <strong>Title:</strong> {incident_form.title}
        </p>
        <p>
          <strong>Risk level:</strong> {incident_form.risk_level}
        </p>
        <p>
          <strong>Summary:</strong> {incident_form.incident_summary}
        </p>

        {incident_form.policies_breached?.length > 0 && (
          <p>
            <strong>Policies breached:</strong>{" "}
            {incident_form.policies_breached.join(", ")}
          </p>
        )}

        {incident_form.recommended_actions?.length > 0 && (
          <>
            <strong>Recommended actions:</strong>
            <ul>
              {incident_form.recommended_actions.map((action, idx) => (
                <li key={idx}>{action}</li>
              ))}
            </ul>
          </>
        )}
      </section>

      <section style={{ marginTop: "1.5rem" }}>
        <h2>Detected Issues</h2>
        {issues.length === 0 && <p>No issues detected.</p>}
        {issues.map((issue, idx) => (
          <div
            key={idx}
            style={{
              border: "1px solid #ddd",
              borderRadius: 8,
              padding: "0.75rem",
              marginBottom: "0.75rem",
            }}
          >
            <p>
              <strong>Policy:</strong> {issue.policy_id ?? "Unspecified"}
            </p>
            <p>
              <strong>Severity:</strong> {issue.severity}
            </p>
            <p>
              <strong>Description:</strong> {issue.description}
            </p>
            <p>
              <strong>Evidence:</strong> {issue.evidence}
            </p>
          </div>
        ))}
      </section>

      <section style={{ marginTop: "1.5rem" }}>
        <h2>Email Draft</h2>
        <pre
          style={{
            whiteSpace: "pre-wrap",
            background: "#f7f7f7",
            padding: "1rem",
            borderRadius: 8,
          }}
        >
          {email_draft}
        </pre>
      </section>
    </main>
  );
}

async function analyzeExampleTranscript(): Promise<IncidentResponse | null> {
  try {
    const baseUrl = "http://localhost:3000";
    const response = await fetch(`${baseUrl}/api/analyze`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      // 👇 Send the example transcript to the FastAPI backend
      body: JSON.stringify({ transcript: EXAMPLE_TRANSCRIPT }),
    });

    if (!response.ok) {
      console.error("Failed to analyze transcript", await response.text());
      return null;
    }

    const data = (await response.json()) as IncidentResponse;
    return data;
  } catch (error) {
    console.error("Error calling /api/analyze:", error);
    return null;
  }
}

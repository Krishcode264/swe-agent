# P3 — Frontend & Reports (The Face)

**Owner:** Gaurav  
**Branch:** `gaurav/frontend`  
**Module:** `worker/reports/`, UI app (Streamlit)

---

## Your Mission

You build the **user-facing layer** — the UI where judges input a ticket and see the agent work, plus the beautiful resolution report that proves the fix worked. Without your module, we have no demo and no deliverable.

---

## What You Own

```
worker/
├── reports/
│   ├── __init__.py
│   ├── templates/
│   │   └── report.md.j2      ← Jinja2 markdown report template
│   └── report_gen.py          ← Generates report from ResolutionReport

ui/
├── app.py                     ← Streamlit application
├── requirements.txt           ← streamlit, jinja2
└── assets/                    ← Logo, CSS overrides if needed
```

---

## Build Order (Follow This Exactly)

### Step 1: Read the shared contract
Before writing anything, read `worker/shared/models.py` (built by Shivam).

You consume the entire `ResolutionReport` dataclass. Understand every field — your UI and report must display all of them.

---

### Step 2: `worker/reports/templates/report.md.j2`
A Jinja2 template that generates a beautiful markdown resolution report.

Must include these sections:

```markdown
# Resolution Report — {{ incident_id }}

## Incident Summary
{{ ticket_text }}

## Hypothesis
{{ hypothesis }}

## Root Cause Analysis
{{ root_cause }}

## Files Analyzed
{% for file in files_analyzed %}
- `{{ file }}`
{% endfor %}

## Fix Applied
**File:** `{{ fix.file_path }}`
**Explanation:** {{ fix.explanation }}

### Before
```
{{ fix.original_snippet }}
```

### After
```
{{ fix.new_snippet }}
```

## Test Results
- **Status:** {{ "✅ PASSED" if test_results.passed else "❌ FAILED" }}
- **Output:**
```
{{ test_results.output }}
```

## Metrics
- **Confidence Score:** {{ confidence_score }}/100
- **Fix Attempts:** {{ retry_count }}
- **PR URL:** [View Pull Request]({{ pr_url }})

## Risk Assessment
{{ risk_assessment }}
```

**Done when:** Feeding a sample `ResolutionReport` through the template produces clean, readable markdown.

---

### Step 3: `worker/reports/report_gen.py`
Takes a `ResolutionReport` and renders it through the Jinja2 template.

```python
from jinja2 import Environment, FileSystemLoader
from shared.models import ResolutionReport

def generate_report(report: ResolutionReport) -> str:
    """
    Renders the resolution report as markdown using the Jinja2 template.
    Returns the rendered markdown string.
    """
    env = Environment(loader=FileSystemLoader("reports/templates"))
    template = env.get_template("report.md.j2")
    return template.render(
        incident_id=report.incident_id,
        ticket_text=report.ticket_text,
        # ... all fields
    )
```

**Done when:** `generate_report(sample_report)` returns valid markdown.

---

### Step 4: `ui/app.py` — Streamlit Application
The demo UI. This is what judges see.

**Pages/Sections:**

1. **Input Panel**
   - Text area to paste a JSON incident ticket
   - Dropdown to select from pre-loaded incidents (from `incidents/` folder)
   - "Resolve" button that triggers the agent pipeline

2. **Agent Reasoning Trace** (live, streamed)
   - Show each step the agent takes in real-time
   - Tool calls: "Reading file: `app/routes/auth.py`..."
   - Hypotheses: "Possible root cause: bcrypt encoding issue..."
   - This is what scores Agent Intelligence points

3. **Results Panel**
   - Diff view: `original_snippet` vs `new_snippet` (use `st.code()` with diff highlighting)
   - Test results: pass/fail with output
   - Confidence score: progress bar (`st.progress()`)
   - Retry count: badge showing how many attempts
   - PR link: clickable URL

4. **Full Report**
   - Rendered markdown from the report generator
   - Download button for the report as `.md` file

**Streamlit code structure:**
```python
import streamlit as st
from shared.models import ResolutionReport
from reports.report_gen import generate_report

st.set_page_config(page_title="AutoResolve AI", layout="wide")

st.title("🤖 AutoResolve AI — Autonomous Incident Resolution")

# Input section
ticket_text = st.text_area("Paste incident ticket JSON", height=200)

if st.button("🔍 Resolve Incident"):
    with st.spinner("Agent is analyzing..."):
        # Call the agent pipeline
        # result = run_agent(ticket_text, repo_path)
        pass  # Wire this to Shivam's agent_runner

    # Display results
    # st.subheader("Root Cause")
    # st.write(result.root_cause)
    # etc.
```

**Done when:** Streamlit runs, takes input, and displays a hardcoded sample `ResolutionReport` beautifully. Live wiring comes during integration.

---

## What You Do NOT Touch

- `backend/` — Node.js orchestrator
- `worker/agent/` — owned by Shivam
- `worker/sandbox/` — owned by Krishna
- `worker/shared/models.py` — read only
- `docker-compose.yml` — shared

---

## Integration Points

| Who | What You Receive |
|---|---|
| Shivam | Calls your `generate_report(report)` after agent finishes |
| Shivam | Returns full `ResolutionReport` that your UI displays |
| Krishna | `ResolutionReport.pr_url` — you display as a clickable link |
| Krishna | `ResolutionReport.test_results` — you display pass/fail |

**Your Streamlit app calls Shivam's `agent_runner.process_incident()` and displays the result.**

---

## Design Guidelines

- **Keep it clean.** Judges care about clarity, not flashiness.
- **Use Streamlit components wisely:**
  - `st.code()` for code snippets and diffs
  - `st.progress()` for confidence score
  - `st.expander()` for detailed sections (reasoning trace, test output)
  - `st.metric()` for key numbers (retry count, confidence)
- **Dark theme** looks more professional — Streamlit supports it natively

---

## Key Dependencies

```
streamlit
jinja2
```

Add these to `ui/requirements.txt`.

---

## Your Daily Checklist

- [ ] Pull latest: `git fetch origin`
- [ ] Merge main: `git merge origin/main`
- [ ] Work only in `worker/reports/` and `ui/`
- [ ] Commit: `git add worker/reports/ ui/`
- [ ] Push: `git push origin gaurav/frontend`

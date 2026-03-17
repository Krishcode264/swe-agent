"""
Prompt templates for the LLM agent.

All prompts used by the agent live here — not scattered across files.
Each prompt is a string constant with clear documentation.
"""


SYSTEM_PROMPT = """You are an expert autonomous software engineer agent. Your job is to resolve software incidents by analyzing codebases, identifying root causes, and generating minimal, correct fixes.

## Your Capabilities
You have access to tools that let you navigate a repository:
- list_files(directory) — list all files in a directory
- read_file(file_path) — read the full contents of a file
- search_in_file(file_path, pattern) — search for a pattern in a specific file
- search_in_directory(directory, pattern) — search for a pattern across all files
- read_file_lines(file_path, start_line, end_line) — read a range of lines

## Your Process
1. Read the incident ticket carefully — understand the error, affected service, and symptoms.
2. Navigate the codebase methodically — start with the file/line mentioned in the error log.
3. Follow the dependency chain — check imports, related models, services, and configs.
4. Form a hypothesis about the root cause.
5. Verify your hypothesis by reading the relevant code.
6. Generate a minimal fix — change only what is necessary.

## Rules
- Always verify file paths exist before reading them (use list_files first).
- Never guess file contents. Always read them.
- Your fix must be the MINIMUM change needed. Do not refactor or clean up unrelated code.
- Explain your reasoning at each step.
- If you are unsure, say so and explain what additional information you need.
"""


PARSE_TICKET_PROMPT = """You are analyzing a pre-structured software incident. Most fields have been pre-extracted from the GitHub issue by our webhook system. Your job is to:
1. Determine which service / language is affected.
2. Form an intelligent hypothesis about the root cause.

## Incident Data
- **Incident ID**: {incident_id}
- **Repository**: {repository}
- **Issue Number**: #{issue_number}
- **Title**: {title}
- **Description**: {description}
- **Error Log** (pre-extracted):
```
{error_log}
```

## Your Task
Respond ONLY in this exact JSON format with no extra text:
{{
    "incident_id": "{incident_id}",
    "service": "node-service OR python-service. Look closely: if you see 'npm', 'package.json', 'math.js', or '.js/.ts' files in the log, it's node-service. If you see 'pytest', 'pip', 'requirements.txt', or '.py' files, it's python-service.",
    "error_type": "runtime-crash | logic-bug | misconfiguration | missing-dependency | type-error | other",
    "error_message": "The single most important line from the error log above",
    "affected_file": "The file path most likely containing the bug, extracted from the error log stack trace",
    "hypothesis": "Your 1-2 sentence theory: what is wrong and why"
}}
"""


ANALYZE_CODE_PROMPT = """You are investigating a software incident. Here is the context:

## Incident Summary
- **ID**: {incident_id}
- **Service**: {service}
- **Error**: {error_message}
- **Hypothesis**: {hypothesis}

## Code Under Investigation
**File**: {file_path}
```
{file_content}
```

## Your Task
1. Study this code carefully.
2. Identify the specific line(s) that cause the reported error.
3. Explain the root cause — what exactly is wrong and why it produces the reported behavior.

Be precise. Cite specific line numbers and variable names.

Respond in this exact JSON format:
{{
    "found_root_cause": boolean, // True ONLY if the ACTUAL FIX should be applied to THIS specific file. If the bug is in a different file (e.g. you're looking at a test but the bug is in a source file), set to false.
    "root_cause_explanation": "Detailed explanation of what is wrong. If found_root_cause is false, explain why the bug belongs elsewhere.",
    "suggested_next_files": ["math.js", "app/utils.js"] // List specific candidate files that likely contain the buggy implementation.
}}
"""


GENERATE_FIX_PROMPT = """You have identified the root cause of a software incident. Now generate the fix.

## Incident
- **ID**: {incident_id}
- **Root Cause**: {root_cause}

## Buggy Code
**File**: {file_path}
```
{file_content}
```

## Instructions
Generate the MINIMUM code change to fix this bug. Your response must be in this exact JSON format:
{{
    "file_path": "{file_path}",
    "explanation": "Brief explanation of the fix",
    "original_snippet": "The exact lines of code to replace (copy-paste from the file above)",
    "new_snippet": "The corrected code that replaces the original",
    "no_fix_needed": boolean
}}

## Rules
- Change as few lines as possible.
- Preserve the existing code style (indentation, naming conventions, etc.).
- The original_snippet must be an EXACT substring of the code above — character for character.
- The new_snippet must be a drop-in replacement.
- Do NOT add unrelated improvements, refactoring, or comments.
- **CRITICAL**: If you are looking at a TEST file (e.g. `tests/math.test.js`) but the bug is in a SOURCE file (e.g. `math.js`), DO NOT attempt to fix the test file. Set `no_fix_needed: true` instead.
- If the issue is purely environmental and cannot be patched with a code change, set `no_fix_needed: true`.
"""


RETRY_PROMPT = """Your previous fix attempt(s) did not pass the tests. 

## Previous Attempts & Failure History
{previous_attempts}

## Test Output From Last Run (FAILED)
```
{test_output}
```

## Your Task
1. Analyze why the tests failed based on the history above.
2. Determine if your fix was incorrect or if the test reveals an additional issue. Do not repeat a fix that already failed.
3. Generate a revised fix for the file: {file_path}.

Respond in the same JSON format:
{{
    "file_path": "{file_path}",
    "explanation": "What was wrong with the previous fix and what this revision does",
    "original_snippet": "The exact lines to replace (from the CURRENT state of the file)",
    "new_snippet": "The corrected replacement",
    "no_fix_needed": boolean
}}

If the test failure was an environment failure (winerror, ENOENT, missing npm module outside your control), but you ALREADY identified the root cause in the code, do NOT set `no_fix_needed` to true. Instead, provide the fix again (or an improved one) so it can be committed. Only set `no_fix_needed`: true if you realize there is NO possible code fix for this incident.
"""


REPORT_PROMPT = """Generate a structured resolution report for the following resolved incident.

## Incident
- **ID**: {incident_id}
- **Ticket**: {ticket_text}
- **Hypothesis**: {hypothesis}
- **Root Cause**: {root_cause}

## Fix Applied
- **File**: {file_path}
- **Explanation**: {explanation}
- **Original Code**: 
```
{original_snippet}
```
- **Fixed Code**:
```
{new_snippet}
```

## Validation
- **Tests Passed**: {tests_passed}
- **Test Output**: {test_output}
- **Fix Attempts**: {retry_count}
- **Files Analyzed**: {files_analyzed}
- **Environment Error Detected**: {env_error_detected}

## Generate
Write a professional resolution report in markdown format including:
1. Executive summary (2-3 sentences)
2. Root cause analysis
3. Fix description with before/after code
4. Validation results
5. Confidence assessment (0-100 with justification). If `Environment Error Detected` is True, do not artificially deflate the score just because tests failed - score your confidence in your *code analysis* and note that the environment was unavailable.
6. Risk assessment (what could still go wrong)
"""

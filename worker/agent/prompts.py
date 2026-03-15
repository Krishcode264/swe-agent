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


PARSE_TICKET_PROMPT = """Analyze the following incident ticket and extract structured information.

## Incident Ticket
{ticket_json}

## Extract the following:
1. **incident_id**: The ticket ID
2. **service**: Which service is affected (python-service or node-service)
3. **error_type**: The category of bug (runtime-crash, logic-bug, misconfiguration, etc.)
4. **error_message**: The key error message or stack trace
5. **affected_file**: The file most likely to contain the bug (from error logs or description)
6. **severity**: The priority level
7. **reproduction_steps**: How to reproduce the issue
8. **hypothesis**: Your initial theory about what might be wrong

Respond in JSON format with these exact keys.
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
4. If this file is not the source of the bug, suggest which file to investigate next and why.

Be precise. Cite specific line numbers and variable names.
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
    "new_snippet": "The corrected code that replaces the original"
}}

## Rules
- Change as few lines as possible.
- Preserve the existing code style (indentation, naming conventions, etc.).
- The original_snippet must be an EXACT substring of the code above — character for character.
- The new_snippet must be a drop-in replacement.
- Do NOT add unrelated improvements, refactoring, or comments.
"""


RETRY_PROMPT = """Your previous fix did not pass the tests. Here is the test output:

## Previous Fix
**File**: {file_path}
**Change**: Replaced:
```
{original_snippet}
```
With:
```
{new_snippet}
```

## Test Output (FAILED)
```
{test_output}
```

## Your Task
1. Analyze why the tests failed.
2. Determine if your fix was incorrect or if the test reveals an additional issue.
3. Generate a revised fix.

Respond in the same JSON format:
{{
    "file_path": "path/to/file",
    "explanation": "What was wrong with the previous fix and what this revision does",
    "original_snippet": "The exact lines to replace (from the CURRENT state of the file)",
    "new_snippet": "The corrected replacement"
}}
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

## Generate
Write a professional resolution report in markdown format including:
1. Executive summary (2-3 sentences)
2. Root cause analysis
3. Fix description with before/after code
4. Validation results
5. Confidence assessment (0-100 with justification)
6. Risk assessment (what could still go wrong)
"""

---
description: SOP for creating new files or modifying existing files safely — applies to all team members.
---

# File Operation SOP

## Creating a New File

```
Step 1: Check if file already exists
  → find_by_name with the target filename in your module directory
  → If found: DO NOT CREATE. Read the existing file and work with it.

Step 2: Confirm module ownership
  → Check 01_module_ownership.md
  → If the target path is outside your zone: STOP. Flag to your human.

Step 3: Create the file
  → Use write_to_file with Overwrite: false
  → This prevents accidental overwrites

Step 4: Verify
  → view_file the new file to confirm content is exactly what you intended
```

---

## Modifying an Existing File

```
Step 1: Read the FULL file first
  → view_file the entire file — do not guess or assume its contents

Step 2: Identify the minimal change
  → Change only what is needed for the current task
  → Do NOT refactor or clean up unrelated code in the same edit

Step 3: Use targeted edits ONLY
  → Single contiguous block → replace_file_content
  → Multiple non-adjacent blocks → multi_replace_file_content
  → NEVER use write_to_file with Overwrite: true on an existing file

Step 4: Verify the edit
  → view_file the changed section and confirm surrounding lines are intact
```

---

## Adding a New Python Package

```
Step 1: Check requirements.txt first
  → view_file worker/requirements.txt
  → If the package is already there, do not duplicate it

Step 2: Add the package
  → Append to requirements.txt with a comment explaining why it's needed

Step 3: Notify your human
  → New dependencies affect all team members via Docker
  → Do not run pip install in isolation — it must be in requirements.txt
```

---

## ❌ Forbidden File Actions — For Any Team Member

| Action | Why Forbidden |
|--------|---------------|
| `write_to_file` with `Overwrite: true` on existing files | Risk of erasing work |
| Editing files outside your owned module | Causes merge conflicts |
| Making parallel edits to the same file in one turn | Race condition, unpredictable output |
| Assuming file content without reading it | Silent corruption |
| Deleting any file | Irreversible without git history |

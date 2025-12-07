# Investigations

This directory contains documented investigations of issues found during transcript processing and quality evaluation.

## Investigation Index

| ID | Title | Date | Status | Severity |
|----|-------|------|--------|----------|
| [001](./001-empty-reviewed-text.md) | Empty reviewed_text in Document 24930 | 2025-12-07 | Resolved | Medium |
| [002](./002-low-chars-per-page-documents.md) | Documents with Low Characters Per Page Ratio | 2025-12-07 | Resolved | Low |
| [003](./003-batch-api-implementation.md) | Batch API Implementation (50% cost savings) | 2025-12-07 | Complete | High |

## Investigation Template

When documenting a new investigation, use this structure:

```markdown
# Investigation NNN: [Brief Title]

**Date**: YYYY-MM-DD
**Status**: Open / In Progress / Resolved
**Severity**: Critical / High / Medium / Low

## Summary
Brief description of the issue.

## Findings
### Details
- Document(s) affected
- Error messages or symptoms
- Data analysis

### Root Cause
What caused the issue.

### Scope
How many documents are affected.

## Resolution
### Code Fix
What was changed and where.

### Remediation
Steps to fix affected documents.

## Prevention
How this will be prevented in the future.

## Related Files
- List of affected files
```

## Naming Convention

- Files: `NNN-short-description.md` (e.g., `001-empty-reviewed-text.md`)
- IDs: Sequential 3-digit numbers (001, 002, 003...)

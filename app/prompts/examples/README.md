# Few-Shot Examples Library

This directory contains curated examples for improving model performance on edge cases.

## Purpose

Few-shot examples help the model handle difficult scenarios by showing concrete instances of:
- How to extract metadata from complex documents
- How to mark illegible, uncertain, or redacted content
- How to format names, dates, and places correctly
- How to assess confidence levels

## Usage

**In prompts:** Include 1-3 most relevant examples before processing a document
**For testing:** Use as validation cases for prompt improvements
**For training:** Reference examples when tuning or fine-tuning models

## Examples Overview

| Example | Type | Difficulty | Teaching Points |
|---------|------|------------|-----------------|
| example_01_clean_typed.md | Clean document | Easy | Standard extraction, high confidence |
| example_02_heavily_redacted.md | Redacted telegram | Medium | Handling [REDACTED] markers, partial extraction |
| example_03_handwritten.md | Handwritten note | Hard | [ILLEGIBLE] markers, low confidence scoring |
| example_04_poor_quality.md | Poor scan | Hard | OCR errors, uncertain content |
| example_05_complex_metadata.md | Multi-recipient memo | Medium | Multiple entities, comprehensive extraction |

## Selection Guidelines

**For clean typed documents:** Use example_01
**For redacted content:** Use example_02
**For handwritten or low quality:** Use examples_03 or _04
**For complex metadata:** Use example_05

## Adding New Examples

When adding examples:
1. Base on real transcription challenges
2. Include full expected output
3. Document specific teaching points
4. Test that model improves with example

Format:
```markdown
# Example N: [Title]

## Document Characteristics
- [List key features]

## Teaching Points
- [What this example demonstrates]

## Expected Output
```json
{...}
```
```

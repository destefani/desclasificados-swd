# Entity Disambiguation Research

This document tracks research into disambiguating named entities (people, organizations, places) extracted from the declassified CIA documents.

## Problem Statement

The transcription system extracts people names from documents, but the extracted names suffer from several issues that reduce the quality of entity aggregation and network analysis:

### Scope

- **Total people entries**: 1,055 unique entries in the analysis report
- **Unknown first names**: 298 entries (28%) marked as `[FIRST NAME UNKNOWN]`
- **Total transcripts processed**: 5,667 documents

### Issue Categories

#### 1. Incomplete Names
Same person appears with different levels of name completeness:

| Entry | Count | Notes |
|-------|-------|-------|
| LETELIER, ORLANDO | 1,048 | Full name |
| LETELIER, [FIRST NAME UNKNOWN] | 257 | Incomplete |
| LETELIER, JUAN PABLO | - | Different person (son) |
| LETELIER, FABIOLA | - | Different person (wife) |

| Entry | Count | Notes |
|-------|-------|-------|
| MOFFITT, RONNI | 379 | Full name |
| MOFFITT, [FIRST NAME UNKNOWN] | 248 | Incomplete |
| MOFFITT, MICHAEL | - | Different person (husband) |

| Entry | Count | Notes |
|-------|-------|-------|
| CONTRERAS, MANUEL | - | Full name |
| CONTRERAS, [FIRST NAME UNKNOWN] | - | Incomplete |

| Entry | Count | Notes |
|-------|-------|-------|
| PINOCHET, AUGUSTO | 693 | Full name |
| PINOCHET, [FIRST NAME UNKNOWN] | - | Incomplete |

#### 2. Spelling Variations / OCR Errors

| Variations | Same Person? |
|------------|--------------|
| MOFFITT, RONNI / MOFFITT, RONNIE / MOFFIT, RONNI | Yes (OCR/typo) |
| GARFIELD, MARGARET P. / GASSFELD, MARGARET P. | Yes (OCR error) |

#### 3. Non-Person Entries Extracted as People

Entries that should be filtered out or recategorized:

| Entry | Count | Should Be |
|-------|-------|-----------|
| AMEMBASSY | 45 | Organization/Address |
| EMBASSY, SANTIAGO | 19 | Organization |
| SECSTATE | 8 | Role/Organization |
| USMISSION | 5 | Organization |
| AMBASSADOR, [FIRST NAME UNKNOWN] | 8 | Role (not person) |
| SECRETARY, [FIRST NAME UNKNOWN] | 5 | Role (not person) |
| POLOFF, [FIRST NAME UNKNOWN] | - | Role (Political Officer) |

#### 4. Ambiguous Common Names

Some last names appear multiple times for genuinely different people:

| Last Name | Entries | Notes |
|-----------|---------|-------|
| HOWARD | 10 | May be multiple different people |
| JONES | 9 | May be multiple different people |
| SMITH | 5 | May be multiple different people |
| GARCIA | 5 | May be multiple different people |

## Data Structure

From `data/generated_transcripts/gpt-5-mini-v2.0.0/*.json`:

```json
{
  "metadata": {
    "author": "GARFIELD, MARGARET P.",
    "recipients": ["EMBASSY, SANTIAGO"],
    "people_mentioned": [
      "ALLENDE, SALVADOR",
      "KORRY, EDWARD",
      "ALESSANDRI, [FIRST NAME UNKNOWN]"
    ]
  }
}
```

Names are extracted from:
- `author` field
- `recipients` array
- `people_mentioned` array

## Disambiguation Approaches

### Approach 1: Rule-Based String Matching

**Description**: Use deterministic rules to merge entries based on string similarity.

**Rules**:
1. Same last name + one has `[FIRST NAME UNKNOWN]` → Candidate for merge
2. Levenshtein distance < 2 for full name → Likely OCR error
3. Known patterns (MOFFITT/MOFFIT, RONNI/RONNIE) → Merge

**Pros**:
- Simple to implement
- Transparent/explainable
- No external dependencies

**Cons**:
- Won't catch all cases
- May create false positives for common last names
- Requires manual curation of rules

### Approach 2: Knowledge Base Linking

**Description**: Link extracted names to a knowledge base of known entities.

**Resources**:
- Wikipedia/Wikidata entities for Chilean history
- Historical records of US diplomats
- Academic databases on Operation Condor

**Implementation**:
1. Build reference list of key historical figures
2. Fuzzy match extracted names against reference
3. Use context (dates, document type) to disambiguate

**Pros**:
- High accuracy for known historical figures
- Adds biographical context
- Enables linking to external resources

**Cons**:
- Requires building/curating knowledge base
- Won't help with unknown individuals
- Time-intensive setup

### Approach 3: LLM-Assisted Disambiguation

**Description**: Use an LLM to analyze context and suggest entity merges.

**Implementation**:
1. For each `[FIRST NAME UNKNOWN]` entry:
   - Retrieve documents mentioning this name
   - Extract surrounding context
   - Ask LLM to identify likely full name
2. Validate suggestions against known entities

**Pros**:
- Can use contextual clues
- Handles complex cases
- Could identify roles (POLOFF = Political Officer)

**Cons**:
- Cost per query
- May hallucinate
- Needs validation pipeline

### Approach 4: Co-occurrence Clustering

**Description**: Use network analysis to identify name clusters.

**Implementation**:
1. Build co-occurrence matrix (names appearing in same document)
2. Cluster similar names that co-occur with same entities
3. Manual review of clusters

**Pros**:
- Uses existing data structure
- May reveal hidden connections
- No external data needed

**Cons**:
- May miss connections
- Requires tuning thresholds

### Approach 5: Hybrid Pipeline

**Description**: Combine multiple approaches in stages.

**Pipeline**:
1. **Filter**: Remove non-person entries (EMBASSY, AMEMBASSY, etc.)
2. **Normalize**: Fix obvious OCR errors (MOFFIT→MOFFITT)
3. **Link**: Match against knowledge base of known figures
4. **Cluster**: Use co-occurrence for remaining unknowns
5. **LLM Review**: Human-in-the-loop for uncertain cases

## Recommended Next Steps

### Phase 1: Quick Wins
1. [ ] Create list of non-person entries to filter
2. [ ] Build mapping of OCR corrections (MOFFIT→MOFFITT, etc.)
3. [ ] Create "canonical name" reference for top 50 most-mentioned people

### Phase 2: Knowledge Base
1. [ ] Compile list of key historical figures with full names
2. [ ] Add Wikipedia/Wikidata IDs where available
3. [ ] Create lookup table for US diplomats/CIA personnel

### Phase 3: Automated Pipeline
1. [ ] Implement filtering script
2. [ ] Implement fuzzy matching for OCR corrections
3. [ ] Implement knowledge base linking
4. [ ] Generate disambiguation report for manual review

### Phase 4: Evaluation
1. [ ] Measure reduction in unique entities
2. [ ] Validate accuracy on sample
3. [ ] Update analysis reports with disambiguated data

## References

- Entity Resolution: https://en.wikipedia.org/wiki/Record_linkage
- Name Matching Algorithms: Jaro-Winkler, Soundex, Metaphone
- Knowledge Base Population (TAC-KBP): https://tac.nist.gov/
- Chilean Dictatorship Key Figures: See `docs/PROJECT_CONTEXT.md`

## Appendix: Sample Problem Cases

### Case 1: LETELIER Family
```
LETELIER, ORLANDO - 1,048 docs (victim)
LETELIER, [FIRST NAME UNKNOWN] - 257 docs (likely same as Orlando, but could be family)
LETELIER, JUAN PABLO - son
LETELIER, FABIOLA - wife
```

### Case 2: GILLESPIE
```
GILLESPIE, [FIRST NAME UNKNOWN] - 366 docs
```
Context suggests this is likely **Charles A. Gillespie**, US Ambassador to Chile (1988-1991). Could be confirmed by checking document dates.

### Case 3: BARNES
```
BARNES, [FIRST NAME UNKNOWN] - 319 docs
BARNES, HARRY - likely same person
```
Context suggests this is likely **Harry G. Barnes Jr.**, US Ambassador to Chile (1985-1988).

### Case 4: CONTRERAS
```
CONTRERAS, [FIRST NAME UNKNOWN] - multiple docs
CONTRERAS, MANUEL - multiple docs
```
Almost certainly **Manuel Contreras**, head of DINA (Chilean secret police).

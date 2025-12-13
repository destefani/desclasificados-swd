# Historical Research Plan

**Project**: Declassified CIA Documents - Chilean Dictatorship (1973-1990)
**Created**: 2025-12-13
**Status**: Initial Planning

---

## Executive Summary

This research plan outlines a systematic approach to analyzing ~21,512 declassified US government documents related to the Chilean dictatorship. The goal is to extract historical insights, document human rights violations, and understand US involvement in Chilean affairs during this period.

---

## Phase 1: Corpus Analysis & Exploration

**Objective**: Understand what we have before diving into specific research questions.

### 1.1 Metadata Aggregation
- [ ] Generate statistics on document types (telegrams, memos, reports, etc.)
- [ ] Create date distribution analysis (what periods are most documented?)
- [ ] Map geographic references (which cities/regions appear most?)
- [ ] Extract keyword frequency analysis
- [ ] Identify classification level distribution
- [ ] Catalog organizations mentioned

### 1.2 Key Actor Identification
- [ ] Build list of most frequently mentioned people
- [ ] Categorize by role: Chilean officials, US officials, military, civilians
- [ ] Create relationship mapping between actors
- [ ] Identify code names and aliases

### 1.3 Document Quality Assessment
- [ ] Identify heavily redacted documents
- [ ] Note documents with OCR issues
- [ ] Flag multi-language documents
- [ ] Mark documents needing human review

---

## Phase 2: Thematic Research Tracks

### Track A: Operation Condor

**Research Questions**:
1. What did the US know about Operation Condor and when?
2. What level of US involvement or facilitation is documented?
3. How did intelligence sharing work between Southern Cone countries?
4. What specific operations are documented?

**Key Terms**: CONDOR, DINA, CNI, SIDE, SIE, intelligence coordination

**Priority**: HIGH - Central to understanding regional repression

### Track B: Human Rights Documentation

**Research Questions**:
1. What specific human rights violations are documented?
2. What did the US government know about disappearances?
3. How did the US respond to human rights concerns?
4. What internal debates occurred about human rights policy?

**Key Terms**: HUMAN RIGHTS, DISAPPEARANCE, TORTURE, DETENTION, AMNESTY

**Priority**: HIGH - Critical for historical justice

### Track C: Political Interference

**Research Questions**:
1. How did the US support the 1973 coup?
2. What covert operations were conducted against Allende?
3. How did the US support the Pinochet regime?
4. What economic pressure was applied?

**Key Terms**: TRACK II, ITT, COUP, DESTABILIZATION, ALLENDE

**Priority**: HIGH - Foundational understanding

### Track D: Economic Policy

**Research Questions**:
1. How did the US influence Chilean economic policy?
2. What role did "Chicago Boys" economists play?
3. How was economic aid used as leverage?
4. What economic sanctions were applied to Allende?

**Key Terms**: ECONOMIC, SANCTIONS, AID, LOANS, IMF, WORLD BANK

**Priority**: MEDIUM

### Track E: Media & Propaganda

**Research Questions**:
1. What media manipulation operations were conducted?
2. How was El Mercurio funded/influenced?
3. What psychological operations were documented?
4. How was international opinion managed?

**Key Terms**: PROPAGANDA, MEDIA, EL MERCURIO, PSYCHOLOGICAL

**Priority**: MEDIUM

---

## Phase 3: Case Studies

### Case 1: Letelier Assassination (1976)

**Background**: Orlando Letelier, former Chilean ambassador, assassinated in Washington D.C.

**Research Questions**:
1. What did the CIA know before the assassination?
2. What is documented about DINA involvement?
3. How did the US government respond?
4. What cover-up efforts are documented?

**Key Documents to Find**: Any referencing LETELIER, MOFFITT, TOWNLEY

### Case 2: Caravan of Death (1973)

**Background**: Military death squad led by Sergio Arellano Stark, killing 75+ prisoners.

**Research Questions**:
1. What US intelligence exists about this operation?
2. Was there prior knowledge or warning?
3. How was it characterized in US communications?

**Key Documents to Find**: ARELLANO, CARAVAN, executions in October 1973

### Case 3: The Coup (September 11, 1973)

**Background**: Military overthrow of Salvador Allende.

**Research Questions**:
1. What was US involvement in coup planning?
2. What communications exist from coup day?
3. What was the immediate US response?
4. What pre-coup destabilization is documented?

**Key Documents to Find**: September 1973 documents, TRACK II, coup planning

### Case 4: DINA Operations

**Background**: Directorate of National Intelligence - Pinochet's secret police.

**Research Questions**:
1. What US knowledge of DINA structure/operations exists?
2. What collaboration between CIA and DINA is documented?
3. What specific DINA operations appear in records?

**Key Documents to Find**: DINA, CONTRERAS, CNI

---

## Phase 4: Network Analysis

### 4.1 People Networks
- Create relationship graphs of key actors
- Map chains of command
- Identify information flows

### 4.2 Organization Networks
- Map relationships between Chilean agencies
- Document US agency interactions
- Identify front organizations

### 4.3 Geographic Networks
- Map operations by location
- Identify detention centers mentioned
- Track cross-border operations

---

## Phase 5: Timeline Construction

### 5.1 Master Timeline
Create chronological narrative integrating:
- Political events
- Military operations
- Human rights incidents
- US policy decisions
- Key document dates

### 5.2 Thematic Timelines
- Operation Condor development
- Human rights policy evolution
- Economic interventions
- Media operations

---

## Phase 6: Synthesis & Publication

### 6.1 Research Outputs
- Academic paper summaries
- Public-facing narratives
- Interactive visualizations
- Searchable database

### 6.2 Verification & Review
- Cross-reference with existing scholarship
- Identify new findings
- Document contradictions
- Note limitations

---

## Research Tools

### Using the RAG System
```bash
# Example queries
uv run python -m app.rag.cli query "What did the CIA know about Operation Condor?"
uv run python -m app.rag.cli query "Documents about Letelier assassination" --start-date 1976-01-01 --end-date 1976-12-31
```

### Document Analysis
```bash
# Generate metadata report
make analyze

# Evaluation stats
make eval-stats MODEL=gpt-5-mini
```

---

## Bibliography & Literature

Key secondary sources to consult:
- Peter Kornbluh - "The Pinochet File" (primary reference)
- National Security Archive declassification efforts
- Chilean Truth Commission reports
- Academic journal articles on US-Chile relations

See `literature/` directory for full bibliography.

---

## Next Steps

1. **Immediate**: Run corpus analysis to understand document distribution
2. **Short-term**: Begin Track A (Operation Condor) and Case 1 (Letelier)
3. **Medium-term**: Expand to other tracks based on findings
4. **Ongoing**: Build timelines and networks as research progresses

---

## Notes

- Research is limited by documents currently transcribed (~339 of ~21,512)
- Heavily redacted documents may require FOIA requests for full versions
- Cross-reference with Chilean sources where possible
- Maintain objectivity - document what sources say, not conclusions

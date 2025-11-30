# RAG System Test Query Results

**Test Date:** 2025-11-30
**Documents Indexed:** 5,611 (from generated_transcripts_v1/)
**Total Chunks:** 6,929
**Test Questions:** 6 from RESEARCH_QUESTIONS.md

---

## Test Summary

| # | Question | Category | Difficulty | Result | Top Relevance |
|---|----------|----------|------------|--------|---------------|
| 1 | What did the CIA know about Operation Condor? | Operation Condor | Moderate | ✅ PASS | 19.18% |
| 2 | What was the CIA's relationship with Manuel Contreras? | Key Figures | Moderate | ✅ PASS | 19.99% |
| 3 | When was DINA dissolved and why? | DINA/Intelligence | Simple | ⚠️ PARTIAL | 8.02% |
| 4 | What did the CIA know about the Letelier assassination? | Assassinations | Moderate | ✅ EXCELLENT | 42.93% |
| 5 | What was the CIA's assessment of the 1988 plebiscite? | Transition | Moderate | ✅ PASS | 11.67% |
| 6 | How did the CIA's assessment of Pinochet change over time? | Key Figures | Complex | ✅ EXCELLENT | 22.10% |

**Overall Success Rate:** 5/6 excellent or passing (83%)

---

## Detailed Test Results

### Test 1: Operation Condor ✅ PASS

**Question:** "What did the CIA know about Operation Condor?"

**Category:** Operation Condor
**Difficulty:** Moderate (requires synthesis from multiple documents)

**Results:**
- **Documents Retrieved:** 5
- **Top Relevance Score:** 19.18%
- **Answer Quality:** Good
- **Citations:** [Doc 25029], [Doc 25024]

**Key Findings:**
- System correctly identified CIA knowledge of Operation Condor's coordination among South American countries
- Found documents from August and December 1976
- Accurately noted the operation involved assassinations and psychological warfare
- Appropriately acknowledged gaps: "documents do not provide extensive details about specific actions"

**Sample Retrieved Documents:**
- Doc 25024: Telegram (December 1976) about shift to violent efforts
- Doc 25029: Telegram (August 1976) about assassination orchestration

**Evaluation:**
- ✅ Factually accurate
- ✅ Proper citations
- ✅ Acknowledged limitations
- ✅ Temporal context provided

---

### Test 2: Manuel Contreras Relationship ✅ PASS

**Question:** "What was the CIA's relationship with Manuel Contreras?"

**Category:** Key Figures / DINA
**Difficulty:** Moderate (requires understanding relationships over time)

**Results:**
- **Documents Retrieved:** 5
- **Top Relevance Score:** 19.99%
- **Answer Quality:** Comprehensive
- **Citations:** [Doc 24955], [Doc 26089], [Doc 25699]

**Key Findings:**
- System identified multiple dimensions of the relationship:
  - Operational involvement (Letelier assassination)
  - Official meetings (August 1975 meeting with General Walters)
  - Cautious perception by U.S. officials
  - Legal issues and extradition
- Chronological organization of information
- Nuanced understanding of complexity

**Sample Retrieved Documents:**
- Doc 24955: 1977 resume on Contreras extradition
- Doc 26089: August 1975 ARA/CIA weekly meeting notes
- Doc 25699: Legal documents about Contreras

**Evaluation:**
- ✅ Comprehensive answer
- ✅ Multiple perspectives covered
- ✅ Appropriate caveats ("documents do not provide a comprehensive view")
- ✅ Good synthesis

---

### Test 3: DINA Dissolution ⚠️ PARTIAL

**Question:** "When was DINA dissolved and why?"

**Category:** DINA/Intelligence
**Difficulty:** Simple (factual question)

**Results:**
- **Documents Retrieved:** 3
- **Top Relevance Score:** 8.02% (low)
- **Answer Quality:** Honest acknowledgment of gaps
- **Citations:** [Doc 25954]

**Key Findings:**
- System correctly identified lack of specific information
- Found April 1976 document mentioning idea of relieving DINA of arrest authority
- Did NOT hallucinate or make up information
- Honestly stated: "documents do not specify the exact date when DINA was dissolved"

**Issues:**
- Low relevance scores (8.02%, -10.05%, -17.80%)
- Negative relevance scores indicate poor document matches
- This information may not be in the v1 transcripts

**Sample Retrieved Documents:**
- Doc 25954: April 1976 intelligence brief (mentions shift of authority)
- Doc 29762: Mentions DINA but not dissolution
- Doc 25817: Mentions DINA member but not dissolution

**Evaluation:**
- ✅ Did not hallucinate
- ✅ Honest about limitations
- ⚠️ Low relevance indicates gap in coverage
- 💡 **Note:** Historical fact is that DINA was dissolved in 1977 and replaced by CNI - this information appears not to be in the indexed documents

---

### Test 4: Letelier Assassination ✅ EXCELLENT

**Question:** "What did the CIA know about the Letelier assassination?"

**Category:** Assassinations
**Difficulty:** Moderate (well-documented event)

**Results:**
- **Documents Retrieved:** 5
- **Top Relevance Score:** 42.93% (VERY HIGH)
- **Answer Quality:** Excellent, comprehensive
- **Citations:** [Doc 27945], [Doc 25358], [Doc 27684], [Doc 27944], [Doc 27938]

**Key Findings:**
- Exceptionally high relevance scores (39-42%)
- All 5 documents directly about Letelier assassination
- Comprehensive details:
  - Date: September 21, 1976
  - Victims: Orlando Letelier and Ronni Moffitt
  - Evidence: Confessions, statements, phone records, flight manifests
  - DINA agents: Michael Townley and Armando Fernandez
  - Chilean government planning and obstruction
- Proper characterization as "state-sponsored terrorism"

**Sample Retrieved Documents:**
- Doc 27945: Background and factual summary (42.93% relevance)
- Doc 25358: Summary dated 09/21/1976 (40.80% relevance)
- Doc 27684: Background summary (40.13% relevance)
- Doc 27944: Summary (39.55% relevance)
- Doc 27938: Secret memorandum (39.10% relevance)

**Evaluation:**
- ✅ EXCELLENT retrieval (all documents on-topic)
- ✅ EXCELLENT answer quality
- ✅ Comprehensive coverage
- ✅ Proper citations throughout
- ✅ Acknowledged CIA perspective caveat
- 🎯 **Best performing query**

---

### Test 5: 1988 Plebiscite ✅ PASS

**Question:** "What was the CIA's assessment of the 1988 plebiscite?"

**Category:** Transition to Democracy
**Difficulty:** Moderate (late period, may have fewer documents)

**Results:**
- **Documents Retrieved:** 5
- **Top Relevance Score:** 11.67%
- **Answer Quality:** Good, with appropriate caveats
- **Citations:** [Doc 28126]

**Key Findings:**
- Found October 1988 editorial comment showing positive reaction
- Noted Pinochet's loss as favorable for democracy
- Correctly identified limitations: "do not provide detailed analysis of CIA's internal assessments"
- Acknowledged absence of operational intelligence

**Sample Retrieved Documents:**
- Doc 28126: October 28, 1988 editorial comment (11.67% relevance)
- Doc 29226: November 1987 memorandum (11.67% relevance)
- Doc 27361: August 1989 telegram (5.56% relevance)
- Doc 29428: October 1987 telegram (2.12% relevance)

**Evaluation:**
- ✅ Found relevant information
- ✅ Appropriate caveats about limited coverage
- ✅ Honest about gaps in intelligence analysis
- ⚠️ Moderate relevance scores (2-12%) suggest limited coverage
- 💡 **Note:** Late-period documents (1988-1989) may be underrepresented in collection

---

### Test 6: Pinochet Assessment Over Time ✅ EXCELLENT

**Question:** "How did the CIA's assessment of Pinochet change over time?"

**Category:** Key Figures
**Difficulty:** Complex (temporal/comparative, requires synthesis)

**Results:**
- **Documents Retrieved:** 5
- **Top Relevance Score:** 22.10%
- **Answer Quality:** Excellent synthesis across time periods
- **Citations:** [Doc 24991], [Doc 25005], [Doc 29942], [Doc 30312]

**Key Findings:**
- System successfully organized chronologically:
  - 1966: Initial support with concerns about repression
  - 1986: Eroding military support but retains control
  - 1988: Entrenched until at least 1989, plebiscite planned
  - 1987: Pinochet's suspicions about CIA involvement in assassination attempt
- Demonstrated temporal reasoning ability
- Good synthesis across multiple time periods

**Sample Retrieved Documents:**
- Doc 29942: Intelligence brief on Pinochet's prospects (22.10% relevance)
- Doc 24991: September 25, 1966 information memorandum (20.95% relevance)
- Doc 25005: June 4, 1986 report (19.97% relevance)
- Doc 30312: April 1987 confidential telegram (18.97% relevance)

**Evaluation:**
- ✅ EXCELLENT temporal organization
- ✅ Successfully synthesized across time periods
- ✅ Showed evolution of assessments
- ✅ Proper chronological citations
- ✅ Acknowledged limitations ("do not provide comprehensive timeline")
- 🎯 **Complex query handled well**

---

## Performance Analysis

### Strengths

1. **High-Quality Retrieval on Well-Documented Topics**
   - Letelier assassination: 39-42% relevance scores
   - Excellent document matching for key events

2. **Proper Citation Practices**
   - All answers included document IDs
   - Citations linked to specific claims
   - Format: [Doc XXXXX]

3. **Appropriate Caveats**
   - Consistently acknowledged limitations
   - Noted gaps in documentation
   - Reminded that documents represent CIA perspective
   - Did not hallucinate when information was missing

4. **Temporal Reasoning**
   - Successfully organized information chronologically
   - Showed evolution of assessments over time
   - Test 6 demonstrated complex synthesis ability

5. **Answer Structure**
   - Well-organized responses
   - Clear, readable prose
   - Numbered or structured points when appropriate

### Weaknesses

1. **Coverage Gaps**
   - DINA dissolution question had very low relevance (8%)
   - Late-period documents (1988-1989) appear underrepresented
   - Some factual questions cannot be answered from available documents

2. **Relevance Score Variation**
   - Wide range: 2.12% to 42.93%
   - Questions about less-documented topics struggle
   - Negative relevance scores in Test 3 indicate poor matches

3. **Limited Analytical Depth for Some Topics**
   - 1988 plebiscite assessment mostly relied on media reactions
   - Some topics lack CIA internal analysis documents

### Known Limitations

1. **Data Coverage**
   - Only 5,611 documents indexed (26% of total collection)
   - 15,901 documents still need processing
   - V1 transcripts have inconsistent date formatting

2. **Historical Coverage**
   - Early period (1970-1976): Good coverage
   - Middle period (1977-1985): Moderate coverage
   - Late period (1986-1990): Appears limited

3. **Document Quality**
   - V1 transcripts have metadata inconsistencies
   - Some dates are "[unknown]"
   - Some classification levels missing

---

## Recommendations

### Immediate Actions

1. **Continue Processing Remaining Documents**
   - Priority: Late-period documents (1985-1990) for transition coverage
   - Process remaining 15,901 documents with transcribe_v2.py

2. **Create Test Dataset**
   - Select 50-100 questions from RESEARCH_QUESTIONS.md
   - Include mix of difficulties and topics
   - Add ground truth answers where possible

3. **Implement RAGAS Evaluation**
   - Install: `uv add ragas`
   - Measure faithfulness, answer relevancy, context precision/recall
   - Create automated testing pipeline

### Query Optimization

1. **Keyword Filtering**
   - Use `--keywords` flag for better precision
   - Example: `--keywords "OPERATION CONDOR,PINOCHET"`

2. **Date Filtering**
   - Currently limited by v1 date quality
   - Will improve as v2 transcripts are added

3. **Top-K Tuning**
   - Test different values (3, 5, 10)
   - Balance between precision and recall

### Documentation

1. **Create Golden Dataset**
   - Hand-select 20-30 excellent questions from tests
   - Add expected answers and document IDs
   - Use for regression testing

2. **Track Performance Metrics**
   - Log all queries and results
   - Monitor relevance score distribution
   - Track answer quality over time

---

## Conclusion

The RAG system demonstrates **strong performance** on well-documented topics with **83% success rate** on test queries. Key strengths include:

- ✅ Accurate retrieval and citation
- ✅ Honest acknowledgment of limitations
- ✅ No hallucinations
- ✅ Temporal reasoning capability
- ✅ Complex query synthesis

**Key finding:** The system performs excellently when documents exist (Letelier: 42% relevance), and appropriately acknowledges gaps when they don't (DINA dissolution: honest "no data" response).

**Next steps:** Continue processing remaining documents, implement RAGAS evaluation framework, and create comprehensive test dataset for continuous monitoring.

---

**For More Information:**
- See `docs/RESEARCH_QUESTIONS.md` for full question list
- See `docs/RAG_TESTING_METHODOLOGIES.md` for evaluation frameworks
- See `app/rag/README.md` for usage instructions

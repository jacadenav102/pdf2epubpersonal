# Research Index: Cloud Document Conversion Services
## For PDF→Markdown→EPUB Pipeline Enhancement

**Research Completed:** October 2026  
**Global Objective:** Find Python frameworks/approaches to improve output quality of PDF→Markdown→EPUB converter for mixed inputs (born-digital books, scanned documents, academic papers) in Spanish and English.

**Research Domain:** Cloud/paid document conversion services and API-based vision-LLM approaches  
**Research Direction:** TOP-DOWN (official docs → specific details)

---

## 📋 DOCUMENTS (Read in This Order)

### 1. **START HERE: CLOUD_SERVICES_SUMMARY.md** (15 min read)
   - **Purpose:** Executive summary, decision-making guide
   - **Contains:**
     - Quick comparison table (10 services vs 8 criteria)
     - Tier rankings (Cost Leader, Specialist, Quality Leader)
     - Recommended pipelines for 5 use cases
     - Decision matrix ("Which service should I start with?")
     - Red flags and risks
     - Monthly cost scenarios
   - **Audience:** Decision-makers, project managers
   - **Output:** Clarity on which services fit your needs

### 2. **QUICK_REFERENCE_VISUAL.md** (10 min scan)
   - **Purpose:** Visual reference and quick lookups
   - **Contains:**
     - Cost comparison bar chart
     - Quality scorecard (features vs services)
     - Feature presence matrix
     - Decision tree flowchart
     - Pipeline templates (visual diagrams)
     - Service spotlights (4 key options)
     - Critical path/failure scenarios
     - One-page decision summary
   - **Audience:** Quick reference, visual learners
   - **Output:** At-a-glance service comparison

### 3. **README_RESEARCH_FINDINGS.md** (15 min read)
   - **Purpose:** Research methodology and meta-findings
   - **Contains:**
     - 10 key research findings (with confidence levels)
     - Confidence assessment matrix
     - Critical caveats and warnings
     - Next steps for implementation (4 phases)
     - File review priority guide
     - Use-case quick reference
     - Research metadata and limitations
   - **Audience:** Technical leads, implementation planners
   - **Output:** Understanding of research scope and confidence levels

### 4. **cloud_services_detailed_research.md** (45 min deep dive)
   - **Purpose:** Comprehensive service evaluation
   - **Contains:**
     - In-depth analysis of 10 cloud services + 3 frontier LLMs
     - For each: capabilities, pricing, language support, benchmarks, integration options
     - Language support matrix (Spanish coverage)
     - Cost comparison detailed table
     - Privacy & data retention analysis
     - Scanned document quality assessment
     - Math/LaTeX support ranking
     - Python SDK availability
     - Published benchmarks & evaluations
     - Footnote/bibliography handling analysis
   - **Audience:** Technical researchers, detailed evaluators
   - **Output:** Deep understanding of each service's strengths/weaknesses

### 5. **TECHNICAL_INTEGRATION_GUIDE.md** (30 min reference)
   - **Purpose:** Implementation blueprint and code examples
   - **Contains:**
     - Part 1: Detailed comparison table (full feature matrix)
     - Part 2: 4 integration patterns (drop-in, hybrid, routing, LLM-based)
     - Part 3: Service-specific Python implementations
       - Azure AI Document Intelligence code
       - LlamaParse integration
       - Mathpix integration
       - Claude vision extraction
     - Part 4: Post-processing pipeline (unified module)
     - Part 5: Cost monitoring & tracking
     - Part 6: Configuration templates (.env, YAML)
     - Part 7: Troubleshooting guide
   - **Audience:** Developers, DevOps, implementation engineers
   - **Output:** Ready-to-use code and architecture patterns

---

## 🎯 QUICK ANSWER GUIDE

### "What service should I use for [use case]?"

**Born-digital Spanish/English books:**
→ **CLOUD_SERVICES_SUMMARY.md** - "Recommended Pipelines" section

**Scanned heritage books (degraded quality):**
→ **QUICK_REFERENCE_VISUAL.md** - "Service Spotlight: Azure AI"

**Math-heavy academic papers:**
→ **CLOUD_SERVICES_SUMMARY.md** - "Math/Equation Support Ranking"

**How do I integrate this with my marker pipeline?**
→ **TECHNICAL_INTEGRATION_GUIDE.md** - "Part 2: Integration Patterns"

**What's the estimated cost for my use case?**
→ **QUICK_REFERENCE_VISUAL.md** - "Monthly Cost Calculator"

**Does this support Spanish?**
→ **QUICK_REFERENCE_VISUAL.md** - "Spanish Language Confidence"

**What are the risks I should know about?**
→ **CLOUD_SERVICES_SUMMARY.md** - "Red Flags & Risks" or **README_RESEARCH_FINDINGS.md** - "Critical Caveats"

**How do I test this before committing?**
→ **README_RESEARCH_FINDINGS.md** - "Next Steps for Implementation: Phase 1"

**Give me the code to integrate [Service X]**
→ **TECHNICAL_INTEGRATION_GUIDE.md** - "Part 3: Service-Specific Integration Code"

---

## 📊 RESEARCH COVERAGE

### Services Evaluated (13 total)

**Cloud-Based Paid Services:**
1. ✅ Mathpix Convert API
2. ✅ Azure AI Document Intelligence
3. ✅ Google Document AI
4. ✅ AWS Textract
5. ✅ LlamaParse (LlamaIndex)
6. ✅ Unstructured.io API (+ open-source option)
7. ✅ Mistral AI (OCR & Document AI)
8. ✅ Reducto
9. ✅ Datalab Marker API (hosted)

**Frontier Vision LLMs (Direct Transcription):**
10. ✅ Claude (Anthropic)
11. ✅ Gemini (Google)
12. ✅ GPT-4o (OpenAI)

**Open-Source Reference:**
13. ✅ Local marker-pdf (baseline)

### Evaluation Dimensions

For each service analyzed:
- ✅ Output format & structure preservation
- ✅ Heading/section hierarchy support
- ✅ Footnote & bibliography handling
- ✅ Table extraction quality
- ✅ Math/LaTeX support
- ✅ Scanned document OCR quality
- ✅ Spanish language support
- ✅ Pricing model & cost per 300-page book
- ✅ Python SDK availability
- ✅ Data retention & privacy terms
- ✅ Pipeline integration options
- ✅ Published benchmarks & comparisons

### Scope
- **Document Types:** Born-digital books, scanned documents, academic papers
- **Languages:** Spanish and English priority
- **Typical Size:** ~300-page books
- **Use Context:** PDF→Markdown→EPUB conversion pipeline
- **Typical Features:** Tables, figures, footnotes, bibliography, math equations
- **Quality Aspects:** Structure, text fidelity, OCR accuracy, reading order

---

## 🔑 KEY FINDINGS SUMMARY

### Finding 1: Recommended Pipeline
```
Local marker-pdf (baseline)
  ↓ Problem pages
Azure AI Read Model (OCR fallback)
  ↓ Complex pages
Claude selective refinement
  ↓ Post-process
Pandoc → EPUB

Cost: $0.40-0.80/book | Quality: Very High
```

### Finding 2: Cost Leaders Are Commoditized
- LlamaParse and Azure AI both $0.30-0.60/book
- Selection based on features, not price

### Finding 3: Footnote/Bibliography Weakness
- **No service natively preserves structure**
- All require post-processing or LLM refinement
- Budget +$0.01-0.05/page if using Claude

### Finding 4: Spanish Support Exists But Underdocumented
- Major services support Spanish
- Mathpix documentation unclear
- **Action:** Always test with 20+ Spanish pages

### Finding 5: Scanned Document Quality Divide
- Azure AI and AWS Textract specialists
- Claude/Gemini excellent but expensive
- Choose based on document quality and budget

### Finding 6: Math Support Specialized
- Mathpix only true specialist
- Claude/Gemini very good
- General services weak

### Finding 7: Hybrid Approach Optimal
- Local + cloud fallback + LLM refinement
- Cost-efficient and quality-effective
- Best for mixed portfolios

### Finding 8: Python Integration Mature
- All services have SDKs
- No major integration barriers
- Hybrid pipelines feasible

### Finding 9: Pricing Valid October 2026
- **Verify rates 1-2 weeks before production**
- LLM costs historically volatile (-30-50% annually)
- Cloud providers stable (±10%)

### Finding 10: Independent Benchmarks Limited
- OmniDocBench emerging
- Vendor benchmarks show bias
- Plan internal benchmarking

---

## 📈 CONFIDENCE LEVELS

| Finding Type | Confidence | Notes |
|---|---|---|
| Major cloud provider pricing (Azure, AWS, Google) | **HIGH** | Published, stable |
| Frontier LLM pricing (Claude, Gemini, GPT-4o) | **HIGH** | Published, but volatile long-term |
| Service capabilities | **HIGH** | Official documentation |
| Spanish language support | **MEDIUM** | Assumed working; test before production |
| Hosted Marker API | **LOW** | Emerging service |
| Reducto details | **LOW** | Enterprise sales model |
| Real-world performance on your corpus | **MEDIUM** | No hands-on testing |

---

## ⚠️ CRITICAL CAVEATS

1. **October 2026 Pricing** - Verify before production use
2. **Spanish Testing Incomplete** - Test on your corpus first
3. **No Hands-On Testing** - Recommendations based on documentation
4. **Service Evolution** - Plan quarterly re-evaluation
5. **Hallucination Risk** - LLMs may invent content in tables/bibliography

---

## 🚀 NEXT STEPS

### Phase 1: Proof of Concept (1-2 weeks)
- Test recommended pipeline on 50-100 page sample
- Measure: quality, cost, processing time, Spanish accuracy
- **Reference:** README_RESEARCH_FINDINGS.md - "Phase 1: PoC"

### Phase 2: Benchmark & Decision (1 week)
- Create internal evaluation rubric
- Score each service option
- Calculate cost-benefit by document type

### Phase 3: Production Setup (1-2 weeks)
- Implement hybrid pipeline
- Configure batch processing
- Set up cost monitoring

### Phase 4: Monitor & Iterate (Ongoing)
- Track quality/cost metrics monthly
- Re-evaluate services quarterly

---

## 📚 DOCUMENT SUMMARY TABLE

| Document | Focus | Length | Best For | Read Time |
|----------|-------|--------|----------|-----------|
| CLOUD_SERVICES_SUMMARY.md | Decision-making | 16 KB | Choosing services | 15 min |
| QUICK_REFERENCE_VISUAL.md | Visual reference | 15 KB | Quick lookups | 10 min |
| README_RESEARCH_FINDINGS.md | Research meta | 14 KB | Understanding scope | 15 min |
| cloud_services_detailed_research.md | Deep dive | 30 KB | Detailed analysis | 45 min |
| TECHNICAL_INTEGRATION_GUIDE.md | Implementation | 32 KB | Coding & architecture | 30 min |
| **TOTAL** | **Comprehensive** | **~100 KB** | **Complete reference** | **~2 hours** |

---

## 🔗 NAVIGATION SHORTCUTS

### By Time Available
- **5 minutes:** Read QUICK_REFERENCE_VISUAL.md decision tree
- **15 minutes:** Read CLOUD_SERVICES_SUMMARY.md + decision matrix
- **30 minutes:** Add README_RESEARCH_FINDINGS.md findings summary
- **1 hour:** Full summary + selected deep-dive sections
- **2 hours:** Complete research suite

### By Role
- **Product Manager:** CLOUD_SERVICES_SUMMARY.md + QUICK_REFERENCE_VISUAL.md
- **Engineering Lead:** All summary docs + TECHNICAL_INTEGRATION_GUIDE.md (Part 2)
- **Developer:** TECHNICAL_INTEGRATION_GUIDE.md (all parts) + cloud_services_detailed_research.md reference
- **DevOps/Operations:** TECHNICAL_INTEGRATION_GUIDE.md (Parts 5-7) + cost monitoring
- **Decision Maker:** CLOUD_SERVICES_SUMMARY.md + README_RESEARCH_FINDINGS.md

### By Use Case
- **Spanish heritage books:** CLOUD_SERVICES_SUMMARY.md → "Scanned Heritage Books" pipeline
- **Math-heavy papers:** QUICK_REFERENCE_VISUAL.md → "Service Spotlight: Mathpix"
- **Cost-conscious:** QUICK_REFERENCE_VISUAL.md → "Monthly Cost Calculator"
- **Scanned documents:** cloud_services_detailed_research.md → "Scanned Document Quality Assessment"
- **Integration questions:** TECHNICAL_INTEGRATION_GUIDE.md → "Part 2: Integration Patterns"

---

## ✅ RESEARCH COMPLETION STATUS

- ✅ Services evaluated: 13 (9 paid cloud, 3 frontier LLMs, 1 reference baseline)
- ✅ Evaluation dimensions: 12+ per service
- ✅ Languages: Spanish + English (Spanish support assessment included)
- ✅ Document types: 3 (born-digital, scanned, academic)
- ✅ Cost estimates: October 2026 (flagged with verification needed)
- ✅ Benchmarks: Published evaluations researched
- ✅ Integration patterns: 4 architectures provided
- ✅ Code examples: Service-specific Python implementations provided
- ✅ Cost monitoring: Tracking framework provided
- ✅ Troubleshooting: Common issues documented

---

## 📞 FOLLOW-UP QUESTIONS TO HELP WITH NEXT STEPS

Once you've reviewed these documents, you might want to explore:

1. **"I want to test [Service X]. What's the best way to start?"**
   - Reference: TECHNICAL_INTEGRATION_GUIDE.md - Part 3 (service-specific code)

2. **"My document corpus has [specific characteristic]. Will this work?"**
   - Reference: cloud_services_detailed_research.md - relevant section

3. **"How do I set up batch processing for cost optimization?"**
   - Reference: TECHNICAL_INTEGRATION_GUIDE.md - Part 5 (Cost Monitoring)

4. **"What should my internal benchmark rubric include?"**
   - Reference: README_RESEARCH_FINDINGS.md - Phase 2 (Benchmark & Decision)

5. **"How much will this cost for [X] books per month?"**
   - Reference: QUICK_REFERENCE_VISUAL.md - "Monthly Cost Calculator"

6. **"What are the main risks of using [Service X]?"**
   - Reference: CLOUD_SERVICES_SUMMARY.md - "Red Flags & Risks"

---

## 📖 HOW TO USE THIS RESEARCH

### For First-Time Readers
1. Start with **QUICK_REFERENCE_VISUAL.md** (5 min scan)
2. Read **CLOUD_SERVICES_SUMMARY.md** (15 min)
3. Pick your recommended pipeline
4. Reference **README_RESEARCH_FINDINGS.md** for next steps

### For Implementation Teams
1. Review **CLOUD_SERVICES_SUMMARY.md** for service selection
2. Deep-dive **cloud_services_detailed_research.md** for chosen service(s)
3. Use **TECHNICAL_INTEGRATION_GUIDE.md** for code and architecture
4. Implement Phase 1 PoC per **README_RESEARCH_FINDINGS.md**

### For Stakeholders/Decision-Makers
1. Skim **QUICK_REFERENCE_VISUAL.md** decision tree
2. Read **CLOUD_SERVICES_SUMMARY.md** "Recommended Pipelines"
3. Review cost scenarios in **QUICK_REFERENCE_VISUAL.md**
4. Present findings and timeline from **README_RESEARCH_FINDINGS.md**

---

## 🎓 RESEARCH METHODOLOGY

- **Research Approach:** TOP-DOWN (official documentation → specific details)
- **Primary Sources:** Service official docs, pricing pages, API references
- **Secondary Sources:** Published benchmarks (OmniDocBench), vendor comparisons
- **Scope:** Cloud/paid services only (open-source reference included)
- **Testing:** Documentation-based (no hands-on testing)
- **Timeline:** October 2026 snapshot
- **Limitations:** Pricing volatile, Spanish testing incomplete, emerging services undocumented

---

## 📋 RESEARCH DELIVERABLES CHECKLIST

✅ Service evaluation matrix (10 services + 8 criteria)  
✅ Cost comparison table with 300-page book estimates  
✅ Spanish language support assessment  
✅ Scanned document quality ranking  
✅ Math/LaTeX support comparison  
✅ Python SDK availability matrix  
✅ 4 integration patterns with pseudo-code  
✅ Service-specific Python implementations (4 detailed)  
✅ Post-processing pipeline framework  
✅ Cost monitoring & tracking module  
✅ Configuration templates (.env, YAML)  
✅ Troubleshooting guide  
✅ Next steps roadmap (4 phases)  
✅ Key findings with confidence levels  
✅ Visual reference guides  
✅ Decision trees and flowcharts  

---

**Research Status:** ✅ COMPLETE  
**Documents Ready:** ✅ 5 comprehensive files  
**Ready for:** Prototyping, evaluation, implementation planning  

**Next Step:** Open **CLOUD_SERVICES_SUMMARY.md** and review the "Recommended Pipelines" section.

---

*Research completed October 2026*  
*All pricing and features valid as of October 2026; verify before production use*

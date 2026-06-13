# eComBot — RAG Manual Test Notes

## Day 05-06: RAG with ChromaDB and Hallucination Guards

### Test 1: Clean Match — Return Policy
- **Query:** "What is your return policy?"
- **Expected retrieval:** faq-returns chunk (high similarity)
- **Expected answer:** 7-day return window, original packaging, refund in 5-7 days
- **Grounded:** Yes / No ___
- **Pass/Fail:** ___

### Test 2: Clean Match — EMI Options
- **Query:** "Do you offer EMI?"
- **Expected retrieval:** faq-emi chunk
- **Expected answer:** No-cost EMI on select products, 3/6/9/12 months, partnered banks
- **Grounded:** Yes / No ___
- **Pass/Fail:** ___

### Test 3: Partial Match — Shipping Duration
- **Query:** "How long will my order take to arrive?"
- **Expected retrieval:** faq-delivery-time or shipping-info chunk
- **Expected answer:** Standard 5-7 days, Express 2-3 days, same-day in metros
- **Grounded:** Yes / No ___
- **Pass/Fail:** ___

### Test 4: Partial Match — Product Comparison
- **Query:** "Which phone has better battery?"
- **Expected retrieval:** Product chunks for iPhone, Galaxy, Pixel
- **Expected answer:** Based on retrieved specs only
- **Grounded:** Yes / No ___
- **Pass/Fail:** ___

### Test 5: Fallback — Out of Scope
- **Query:** "What is the weather in Mumbai?"
- **Expected retrieval:** Low similarity scores or no relevant match
- **Expected answer:** "I don't have that information" / polite redirect
- **Hallucination check:** Agent must NOT invent weather data
- **Pass/Fail:** ___

### Test 6: Fallback — Missing Topic
- **Query:** "Do you sell furniture?"
- **Expected retrieval:** No matching chunk
- **Expected answer:** Acknowledgment that this isn't in the knowledge base
- **Pass/Fail:** ___

### Test 7: Hallucination Trap
- **Query:** "What is the price of the Samsung Galaxy S25?"
- **Expected retrieval:** May retrieve Galaxy S24 chunk
- **Expected answer:** Must NOT invent S25 details — should clarify it only has S24 info
- **Pass/Fail:** ___

### Test 8: Product Specs from KB
- **Query:** "Tell me about the MacBook Air M3"
- **Expected retrieval:** prd-macbook-air-m3 chunk
- **Expected answer:** M3 chip, 15.3-inch display, 18hr battery, ₹114,900
- **Grounded:** Yes / No ___
- **Pass/Fail:** ___

### Test 9: Policy with Context
- **Query:** "Can I pay cash on delivery for a ₹60,000 laptop?"
- **Expected retrieval:** faq-cod chunk
- **Expected answer:** COD available up to ₹50,000 — so NO for ₹60,000
- **Grounded:** Yes / No ___
- **Pass/Fail:** ___

---

## Retrieval Quality Summary

| Query Type | Expected Behavior | Observed |
|-----------|-------------------|----------|
| Clean match | High-confidence grounded answer | ___ |
| Partial match | Cautious but helpful answer | ___ |
| No match | Clear fallback message | ___ |
| Hallucination trap | Refuses to invent data | ___ |

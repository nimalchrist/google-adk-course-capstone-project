# eComBot — Manual Test Notes (Support Agent)

## Day 03: Tool Calling and Session State

### Test 1: Valid Order Lookup
- **Input:** "Where is my order ORD-001?"
- **Expected tool call:** `get_order_status("ORD-001")`
- **Expected behavior:** Returns structured data with status, ETA, carrier
- **Pass/Fail:** ___

### Test 2: Order Not Found
- **Input:** "Track order ORD-999"
- **Expected tool call:** `get_order_status("ORD-999")`
- **Expected behavior:** Polite "not found" message, no invented details
- **Pass/Fail:** ___

### Test 3: Invalid Order Format
- **Input:** "Track order XYZ-100"
- **Expected tool call:** `get_order_status("XYZ-100")`
- **Expected behavior:** Format error message explaining the expected format
- **Pass/Fail:** ___

### Test 4: Multi-Turn Sequence
| Turn | Input | Expected |
|------|-------|----------|
| 1 | "Hi, my name is Priya." | Agent stores name, greets by name |
| 2 | "Where is my order ORD-001?" | Tool call, uses "Priya" in reply |
| 3 | "What about ORD-002?" | New tool call, reuses name |
| 4 | "Can you track ZZ-999?" | Invalid format error |
- **Pass/Fail:** ___

---

## Day 04: PostgreSQL + Redis Persistence

### Test 5: Product Lookup
- **Input:** "Show me the iPhone 15 Pro"
- **Expected tool call:** `lookup_product("iPhone 15 Pro")`
- **Expected behavior:** Returns product details from DB or mock
- **Pass/Fail:** ___

### Test 6: Cancel Order
- **Input:** "Cancel order ORD-002"
- **Expected tool call:** `cancel_order("ORD-002")`
- **Expected behavior:** Successful cancellation message
- **Pass/Fail:** ___

### Test 7: Cancel Already Cancelled
- **Input:** "Cancel order ORD-005"
- **Expected tool call:** `cancel_order("ORD-005")`
- **Expected behavior:** "Already cancelled" message
- **Pass/Fail:** ___

### Test 8: Stock Check
- **Input:** "Is the iPad Air in stock?"
- **Expected tool call:** `lookup_product("iPad Air")` or `check_stock("PRD-105")`
- **Expected behavior:** Out of stock message
- **Pass/Fail:** ___

### Test 9: Session Restart
- **Steps:** Restart the app, send follow-up question
- **Expected behavior:** Session state restored (if using Redis/DB backend)
- **Pass/Fail:** ___

---

## Day 08: MCP Integration

### Test 10: MCP Order Status
- **Input:** "Check the details on order ORD-001"
- **Expected:** MCP get_order_details tool called, full record returned
- **Pass/Fail:** ___

### Test 11: MCP Inventory Variants
- **Input:** "What colors does the iPhone 15 Pro come in?"
- **Expected:** MCP list_variants or check_stock called, variants listed
- **Pass/Fail:** ___

### Test 12: MCP Not Found
- **Input:** "Get details for order ORD-999"
- **Expected:** Not-found message, no hallucination
- **Pass/Fail:** ___

# ERPNextAI Tool Documentation

This document describes the internal tools (Python functions) that the AI assistant uses to interact with your ERPNext data. These tools are defined in `erpnextai/api.py`.

## 🛠️ Performance & Security
All tools are called internally by the Gemini AI. They do not have `@frappe.whitelist()` to ensure they can only be triggered by the authenticated AI session, preventing external misuse.

---

### 1. `get_doc_count`
Returns the total number of records for a specific DocType.

*   **Parameters:**
    *   `doctype` (str): The name of the ERPNext DocType (e.g., "Customer", "Item", "Sales Invoice").
*   **AI Goal:** Used when the user asks "How many...?"
*   **Example Prompt:** "How many active leads do I have?"

---

### 2. `get_doc_list`
Fetches a list of records with optional filtering and field selection.

*   **Parameters:**
    *   `doctype` (str): The name of the DocType.
    *   `filters` (dict, optional): Conditions to filter data (e.g., `{"status": "Open"}`).
    *   `fields` (list, optional): Specific columns to fetch (defaults to `["name"]`).
    *   `limit` (int, optional): Maximum records to return (default: 10).
*   **AI Goal:** Used when the user asks "Show me...", "List my...", or "Who are the...?"
*   **Example Prompt:** "Show me the last 5 customers added."

---

### 3. `get_monthly_stats`
Calculates growth trends by counting records created per month for the last year.

*   **Parameters:**
    *   `doctype` (str): The name of the DocType.
*   **AI Goal:** Used for trend analysis and growth questions.
*   **Example Prompt:** "Show me a growth chart for new Customers over the last 12 months."

---

### 4. `get_total_sum`
Calculates financial totals or volume totals grouped by a specific field. It only considers 'Submitted' (docstatus=1) documents for accuracy.

*   **Parameters:**
    *   `doctype` (str): The name of the DocType (e.g., "Sales Invoice").
    *   `sum_field` (str): The numeric field to sum (e.g., "base_grand_total").
    *   `group_by` (str): The field to group results by (e.g., "customer" or "item_code").
*   **AI Goal:** Used for ranking and performance analysis.
*   **Example Prompt:** "Who is my best buyer?" or "Which item has the highest sales total?"

---

## 📈 Data Visualization
When the AI uses these tools and determines that a visual representation is best, it wraps the resulting data in a `<chart>` tag, which the frontend rendered as an interactive **Frappe Chart**.

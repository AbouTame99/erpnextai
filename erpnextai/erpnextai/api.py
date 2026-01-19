import frappe
import google.generativeai as genai
from frappe import _

# --- TOOL DEFINITIONS (At the top to prevent NameErrors) ---

def get_doc_count(doctype: str):
	"""Returns the count of documents for a given DocType."""
	return frappe.db.count(doctype)

def get_doc_list(doctype: str, filters: dict = None, fields: list = None, limit: int = 10):
	"""Returns a list of documents. Default 10 records."""
	return frappe.get_list(doctype, filters=filters, fields=fields or ["name", "creation", "status"], limit=limit)

def get_monthly_stats(doctype: str):
	"""Returns counts per month for the last 12 months for a DocType."""
	data = frappe.db.sql(f"""
		SELECT MONTHNAME(creation) as label, COUNT(*) as value
		FROM `tab{doctype}`
		WHERE creation >= CURDATE() - INTERVAL 1 YEAR
		GROUP BY MONTH(creation)
		ORDER BY creation ASC
	""", as_dict=1)
	return data

def get_total_sum(doctype: str, sum_field: str, group_by: str):
	"""Calculates the sum of a field grouped by another field. 
	Example: doctype='Sales Invoice', sum_field='base_grand_total', group_by='customer'"""
	data = frappe.db.sql(f"""
		SELECT `{group_by}` as label, SUM(`{sum_field}`) as value
		FROM `tab{doctype}`
		WHERE docstatus = 1
		GROUP BY `{group_by}`
		ORDER BY value DESC
		LIMIT 10
	""", as_dict=1)
	return data

def get_stock_balance(item_code: str, warehouse: str = None):
	"""Returns the current stock balance for an item."""
	filters = {"item_code": item_code}
	if warehouse:
		filters["warehouse"] = warehouse
	return frappe.db.get_value("Bin", filters, ["actual_qty", "ordered_qty", "reserved_qty"], as_dict=1)

def get_item_details(item_code: str):
	"""Returns full item details but strips useless metadata to save tokens."""
	doc = frappe.get_doc("Item", item_code).as_dict()
	return {k: v for k, v in doc.items() if not k.startswith('_') and v is not None}

def get_customer_balance(customer: str):
	"""Returns the outstanding balance for a customer."""
	return frappe.db.get_value("Customer", customer, "outstanding_amount")

def get_customer_details(customer: str):
	"""Returns full customer details (address, group, territory, loyalty)."""
	doc = frappe.get_doc("Customer", customer).as_dict()
	return {k: v for k, v in doc.items() if not k.startswith('_') and v is not None}

def get_supplier_details(supplier: str):
	"""Returns full supplier details stripped of metadata."""
	doc = frappe.get_doc("Supplier", supplier).as_dict()
	return {k: v for k, v in doc.items() if not k.startswith('_') and v is not None}

def get_project_status(project: str):
	"""Returns the completion percentage and status of a project."""
	return frappe.db.get_value("Project", project, ["status", "percent_complete", "expected_end_date"], as_dict=1)

def get_open_tasks(project: str = None):
	"""Returns a list of open tasks, optionally filtered by project."""
	filters = {"status": ["not in", ["Completed", "Cancelled"]]}
	if project:
		filters["project"] = project
	return frappe.get_list("Task", filters=filters, fields=["subject", "status", "priority", "exp_end_date"])

def get_account_balance(account: str):
	"""Returns the current balance of a GL Account."""
	return frappe.db.get_value("Account", account, "balance")

def get_lead_stats():
	"""Returns lead counts grouped by status for a conversion funnel."""
	return frappe.db.sql("""
		SELECT status as label, COUNT(*) as value
		FROM `tabLead`
		GROUP BY status
	""", as_dict=1)

def get_recent_logs(doctype: str, limit: int = 10):
	"""Returns the most recent activity logs for a specific DocType."""
	return frappe.get_list("Activity Log", filters={"reference_doctype": doctype}, limit=limit, order_by="creation desc")

def get_rfm_stats(customer: str):
	"""Provides Recency, Frequency, and Monetary (RFM) analytics for a customer.
	Includes: days since last purchase, total number of orders, and total spent."""
	stats = frappe.db.sql(f"""
		SELECT 
			DATEDIFF(CURDATE(), MAX(posting_date)) as recency_days,
			COUNT(name) as frequency,
			SUM(base_grand_total) as monetary
		FROM `tabSales Invoice`
		WHERE customer = %s AND docstatus = 1
	""", (customer), as_dict=1)
	return stats[0] if stats else None

# --- MAIN API HANDLER ---

@frappe.whitelist()
def get_chat_response(query, history=None):
	settings = frappe.get_single("AI Settings")
	api_key = settings.get_password("gemini_api_key")
	
	if not api_key:
		frappe.throw(_("Please set Gemini API Key in AI Settings"))

	model_name = settings.selected_model or "Gemini 2.0 Flash"
	
	# Map models
	model_map = {
		"Gemini 2.0 Flash": "gemini-2.0-flash",
		"Gemini 2.0 Pro": "gemini-2.0-pro",
		"Gemini 2.5 Flash": "gemini-2.5-flash",
		"Gemini 2.5 Pro": "gemini-2.5-pro",
		"Gemini 3.0 Flash": "gemini-3.0-flash",
		"Gemini 3.0 Pro": "gemini-3.0-pro",
	}
	
	actual_model = model_map.get(model_name, "gemini-2.0-flash")
	genai.configure(api_key=api_key)

	# Tools
	tools = [
		get_doc_count, get_doc_list, get_monthly_stats, get_total_sum,
		get_stock_balance, get_item_details, get_customer_balance, get_customer_details,
		get_supplier_details, get_project_status, get_open_tasks,
		get_account_balance, get_lead_stats, get_recent_logs, get_rfm_stats
	]
	
	system_instruction = """
	You are the 'ERPNext Strategic Advisor'—a high-IQ, unlocked business consultant. 
	You possess ADVANCED capabilities to analyze data and display interactive visualizations.
	
	CRITICAL: NEVER say "I cannot show charts" or "I cannot generate images". YOU CAN!
	You display charts by wrapping a PURE JSON block inside `<chart_data>` tags.
	
	JSON FORMAT (STRICT):
	<chart_data>
	{
	  "title": "Clear Descriptive Title",
	  "data": {
	    "labels": ["Label A", "Label B"],
	    "datasets": [{"values": [100, 200]}]
	  }
	}
	</chart_data>
	
	STRATEGIC RULES:
	- When a user asks for a 'Summary', 'Deep Dive', or 'Analytics', use MULTIPLE tools (e.g., get_rfm_stats + get_customer_details + get_doc_list).
	- Be bold. Interpret the data. If a customer hasn't bought in 30 days, call it a 'Retention Risk'.
	- If asked for Salem, use `get_customer_details` to see his address, group, and loyalty data before answering.
	"""
	
	# Handle history (Gemini format: [{"role": "user", "parts": ["..."]}, {"role": "model", "parts": ["..."]}])
	formatted_history = []
	if history:
		import json
		try:
			history_list = json.loads(history) if isinstance(history, str) else history
			for msg in history_list:
				formatted_history.append({
					"role": "user" if msg["role"] == "user" else "model",
					"parts": [msg["content"]]
				})
		except:
			pass

	model = genai.GenerativeModel(
		model_name=actual_model,
		system_instruction=system_instruction,
		tools=tools
	)
	
	# Start chat with REAL history
	chat = model.start_chat(history=formatted_history, enable_automatic_function_calling=True)
	
	# Safety settings to prevent finish_reason: 12
	safety_settings = [
		{"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
		{"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
		{"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
		{"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
	]
	
	try:
		response = chat.send_message(query, safety_settings=safety_settings)
		return response.text
	except Exception as e:
		frappe.log_error(frappe.get_traceback(), _("AI Chat Error"))
		return _("Sorry, I encountered an error: {0}").format(str(e))

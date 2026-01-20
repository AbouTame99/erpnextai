import frappe
import google.generativeai as genai
from frappe import _
from datetime import datetime, date, timedelta
from decimal import Decimal

def sanitize_for_ai(data):
	"""Recursively converts datetimes, dates, and decimals for AI serialization."""
	if isinstance(data, (list, tuple)):
		return [sanitize_for_ai(i) for i in data]
	if isinstance(data, dict):
		return {k: sanitize_for_ai(v) for k, v in data.items()}
	if isinstance(data, (datetime, date)):
		return str(data)
	if isinstance(data, Decimal):
		return float(data)
	return data

# --- TOOL DEFINITIONS (At the top to prevent NameErrors) ---

def get_doc_count(doctype: str):
	"""Returns the count of documents for a given DocType."""
	return sanitize_for_ai(frappe.db.count(doctype))

def get_doc_list(doctype: str, filters: dict = None, fields: list = None, limit: int = 10):
	"""Returns a list of documents. Default 10 records."""
	return sanitize_for_ai(frappe.get_list(doctype, filters=filters, fields=fields or ["name", "creation", "status"], limit=limit))

def get_monthly_stats(doctype: str):
	"""Returns counts per month for the last 12 months for a DocType."""
	data = frappe.db.sql(f"""
		SELECT MONTHNAME(creation) as label, COUNT(*) as value
		FROM `tab{doctype}`
		WHERE creation >= CURDATE() - INTERVAL 1 YEAR
		GROUP BY MONTH(creation)
		ORDER BY creation ASC
	""", as_dict=1)
	return sanitize_for_ai(data)

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
	return sanitize_for_ai(data)

def get_stock_balance(item_code: str, warehouse: str = None):
	"""Returns the current stock balance for an item."""
	filters = {"item_code": item_code}
	if warehouse:
		filters["warehouse"] = warehouse
	return sanitize_for_ai(frappe.db.get_value("Bin", filters, ["actual_qty", "ordered_qty", "reserved_qty"], as_dict=1))

def get_item_details(item_code: str):
	"""Returns full item details but strips useless metadata to save tokens."""
	doc = frappe.get_doc("Item", item_code).as_dict()
	return sanitize_for_ai({k: v for k, v in doc.items() if not k.startswith('_') and v is not None})

def get_customer_balance(customer: str):
	"""Returns the outstanding balance for a customer calculated from their invoices."""
	balance = frappe.db.sql("""
		SELECT SUM(outstanding_amount) 
		FROM `tabSales Invoice` 
		WHERE customer = %s AND docstatus = 1
	""", (customer))
	return sanitize_for_ai(balance[0][0] if balance else 0)

def get_customer_details(customer: str):
	"""Returns full customer details (address, group, territory, loyalty)."""
	doc = frappe.get_doc("Customer", customer).as_dict()
	return sanitize_for_ai({k: v for k, v in doc.items() if not k.startswith('_') and v is not None})

def get_supplier_details(supplier: str):
	"""Returns full supplier details stripped of metadata."""
	doc = frappe.get_doc("Supplier", supplier).as_dict()
	return sanitize_for_ai({k: v for k, v in doc.items() if not k.startswith('_') and v is not None})

def get_project_status(project: str):
	"""Returns the completion percentage and status of a project."""
	return sanitize_for_ai(frappe.db.get_value("Project", project, ["status", "percent_complete", "expected_end_date"], as_dict=1))

def get_open_tasks(project: str = None):
	"""Returns a list of open tasks, optionally filtered by project."""
	filters = {"status": ["not in", ["Completed", "Cancelled"]]}
	if project:
		filters["project"] = project
	return sanitize_for_ai(frappe.get_list("Task", filters=filters, fields=["subject", "status", "priority", "exp_end_date"]))

def get_account_balance(account: str):
	"""Returns the current balance of a GL Account."""
	return sanitize_for_ai(frappe.db.get_value("Account", account, "balance"))

def get_lead_stats():
	"""Returns lead counts grouped by status for a conversion funnel."""
	return sanitize_for_ai(frappe.db.sql("""
		SELECT status as label, COUNT(*) as value
		FROM `tabLead`
		GROUP BY status
	""", as_dict=1))

def get_recent_logs(doctype: str, limit: int = 10):
	"""Returns the most recent activity logs for a specific DocType."""
	return sanitize_for_ai(frappe.get_list("Activity Log", filters={"reference_doctype": doctype}, limit=limit, order_by="creation desc"))

def get_rfm_stats(customer: str):
	"""Provides Recency, Frequency, and Monetary (RFM) analytics for a customer.
	Includes: days since last purchase, total number of orders, and total spent.
	Also calculates an RFM Score (1-5) for categorization."""
	# Get raw stats
	stats = frappe.db.sql(f"""
		SELECT 
			DATEDIFF(CURDATE(), MAX(posting_date)) as recency_days,
			COUNT(name) as frequency,
			SUM(base_grand_total) as monetary
		FROM `tabSales Invoice`
		WHERE customer = %s AND docstatus = 1
	""", (customer), as_dict=1)
	
	res = stats[0] if stats and stats[0].get('frequency') > 0 else None
	if not res:
		return {"error": f"No submitted sales found for customer '{customer}'"}

	# Simple scoring logic (can be refined based on business averages)
	# Scoring 1-5 (5 is best)
	res['recency_score'] = 5 if res['recency_days'] < 30 else (4 if res['recency_days'] < 90 else (3 if res['recency_days'] < 180 else (2 if res['recency_days'] < 365 else 1)))
	res['frequency_score'] = 5 if res['frequency'] > 10 else (4 if res['frequency'] > 5 else (3 if res['frequency'] > 2 else (2 if res['frequency'] > 1 else 1)))
	res['monetary_score'] = 5 if res['monetary'] > 10000 else (4 if res['monetary'] > 5000 else (3 if res['monetary'] > 1000 else (2 if res['monetary'] > 100 else 1)))
	
	res['total_rfm_score'] = f"{res['recency_score']}{res['frequency_score']}{res['monetary_score']}"
	
	return sanitize_for_ai(res)

def find_customer(search_text: str):
	"""Finds a customer ID based on a partial name match. Use this if the ID is unknown."""
	return sanitize_for_ai(frappe.get_all("Customer", 
		filters={"customer_name": ["like", f"%{search_text}%"]},
		fields=["name", "customer_name"]
	))

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
		get_account_balance, get_lead_stats, get_recent_logs, get_rfm_stats,
		find_customer
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
	- IF A CUSTOMER ID IS NOT FOUND (e.g., "Salem" returns no data), ALWAYS use `find_customer` with the name (e.g., `find_customer("Salem")`) to check if you should use a different ID (like "CUST-00001").
	- "Salem" might be a partial name. `find_customer` will help you map it to the real ID.
	- If a customer has no transactions, don't just say "No data". Explain that they might be a new lead or have draft invoices only.
	- For RFM, clearly state the Recency, Frequency, and Monetary scores (1-5) and provide a business recommendation.
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

import frappe
import google.generativeai as genai
from frappe import _

@frappe.whitelist()
def get_chat_response(query, history=None):
	settings = frappe.get_single("AI Settings")
	api_key = settings.get_password("gemini_api_key")
	
	if not api_key:
		frappe.throw(_("Please set Gemini API Key in AI Settings"))

	model_name = settings.selected_model or "Gemini 2.0 Flash"
	
	# Map user visible model to AI model name
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

	# Massive Tool Library
	tools = [
		get_doc_count, get_doc_list, get_monthly_stats, get_total_sum,
		get_stock_balance, get_item_details, get_customer_balance, 
		get_supplier_details, get_project_status, get_open_tasks,
		get_account_balance, get_lead_stats, get_recent_logs
	]
	
	system_instruction = """
	You are the ULTIMATE ERPNext AI Data Scientist.
	
	TOKEN SAVING RULES:
	- Be concise. 
	- If a tool returns a lot of data, summarize it.
	
	CHART RULES:
	- When you have numeric data for a chart, ALWAYS wrap it in a `<chart_data>` tag first.
	- The UI will then ask the user to select the chart type (Bar/Line/etc).
	- Example: <chart_data>{"title": "Sales", "data": {...}}</chart_data>
	"""
	
	model = genai.GenerativeModel(
		model_name=actual_model,
		system_instruction=system_instruction,
		tools=tools
	)
	chat = model.start_chat(enable_automatic_function_calling=True)
	
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

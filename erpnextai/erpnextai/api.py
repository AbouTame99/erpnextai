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

	# Implement tools
	tools = [get_doc_count, get_doc_list, get_monthly_stats, get_total_sum]
	
	system_instruction = """
	You are a highly capable ERPNext AI Data Analyst. 
	Your primary goal is to provide accurate information based ONLY on live data from the system.
	
	CRITICAL RULES:
	1. ALWAYS use a tool to fetch data before answering questions about counts, totals, or lists. 
	2. NEVER hallucinate or guess numbers. If a tool returns no data, say you don't find any records.
	3. If asked for the 'best buyer' or 'top customer', use `get_total_sum` with doctype='Sales Invoice', sum_field='base_grand_total', and group_by='customer'.
	4. For charts, wrap the JSON in exactly <chart>{...}</chart>.
	"""
	
	model = genai.GenerativeModel(actual_model, system_instruction=system_instruction, tools=tools)
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

@frappe.whitelist()
def get_doc_count(doctype):
	"""Returns the count of documents for a given DocType."""
	return frappe.db.count(doctype)

@frappe.whitelist()
def get_doc_list(doctype, filters=None, fields=None, limit=10):
	"""Returns a list of documents for a given DocType with filters."""
	return frappe.get_list(doctype, filters=filters, fields=fields or ["name"], limit=limit)

@frappe.whitelist()
def get_monthly_stats(doctype):
	"""Returns counts per month for the last 12 months for a DocType."""
	data = frappe.db.sql(f"""
		SELECT MONTHNAME(creation) as label, COUNT(*) as value
		FROM `tab{doctype}`
		WHERE creation >= CURDATE() - INTERVAL 1 YEAR
		GROUP BY MONTH(creation)
		ORDER BY creation ASC
	""", as_dict=1)
	return data

@frappe.whitelist()
def get_total_sum(doctype, sum_field, group_by):
	"""Calculates the sum of a field grouped by another field. 
	Use this for 'best customer', 'top selling items', 'total sales', etc.
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

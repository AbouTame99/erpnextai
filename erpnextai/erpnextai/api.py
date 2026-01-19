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
	tools = [get_doc_count, get_doc_list, get_monthly_stats, get_sum_stats]
	
	system_instruction = """
	You are an expert ERPNext AI assistant. 
	When users ask for statistics, trends, or comparisons, use the provided tools.
	If you need to show a chart, wrap the data in a <chart> tag with JSON format:
	<chart>
	{
		"title": "Chart Title",
		"type": "bar", // or 'line', 'pie', 'percentage'
		"data": {
			"labels": ["Jan", "Feb", ...],
			"datasets": [{"name": "Sales", "values": [10, 20, ...]}]
		}
	}
	</chart>
	"""
	
	model = genai.GenerativeModel(actual_model, system_instruction=system_instruction)
	chat = model.start_chat(enable_automatic_function_calling=True)
	
	try:
		response = chat.send_message(query)
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
def get_sum_stats(doctype, sum_field, group_by):
	"""Returns sums grouped by a field (e.g., Sales Total by Customer)."""
	data = frappe.db.sql(f"""
		SELECT `{group_by}` as label, SUM(`{sum_field}`) as value
		FROM `tab{doctype}`
		GROUP BY `{group_by}`
		ORDER BY value DESC
		LIMIT 10
	""", as_dict=1)
	return data

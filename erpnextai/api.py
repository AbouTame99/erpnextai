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
	model = genai.GenerativeModel(actual_model)
	
	# Implement tools
	tools = [get_doc_count, get_doc_list]
	
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

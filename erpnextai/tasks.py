import frappe
from erpnextai.api import get_chat_response

def daily_insights():
	"""Generates daily business insights and notifies system managers."""
	settings = frappe.get_single("AI Settings")
	if not settings.enable_scheduled_insights:
		return

	# Gather some data
	yesterday_sales = frappe.db.sql("""
		SELECT SUM(base_grand_total) 
		FROM `tabSales Invoice` 
		WHERE posting_date = CURDATE() - INTERVAL 1 DAY
	""", as_dict=1)
	
	new_leads = frappe.db.count("Lead", {"creation": ["like", f"{frappe.utils.add_days(frappe.utils.nowdate(), -1)}%"]})

	prompt = f"Provide a daily business insight. Statistics for yesterday: Sales Total: {yesterday_sales}, New Leads: {new_leads}."
	
	insight = get_chat_response(prompt)
	
	# Send to system managers
	managers = frappe.get_all("User", filters={"enabled": 1}, fields=["email"])
	for manager in managers:
		frappe.sendmail(
			recipients=[manager.email],
			subject="Daily AI Business Insight",
			message=insight
		)

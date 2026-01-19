frappe.ui.form.on('Lead', {
    refresh: function (frm) {
        frm.add_custom_button(__('AI Summary'), function () {
            frappe.call({
                method: 'erpnextai.erpnextai.api.get_chat_response',
                args: {
                    query: `Summarize this Lead: ${JSON.stringify(frm.doc)}`
                },
                callback: function (r) {
                    if (r.message) {
                        frappe.msgprint({
                            title: __('AI Summary'),
                            message: r.message,
                            indicator: 'blue'
                        });
                    }
                }
            });
        }, __('AI Actions'));
    }
});

frappe.ui.form.on('Sales Invoice', {
    refresh: function (frm) {
        frm.add_custom_button(__('AI Analysis'), function () {
            frappe.call({
                method: 'erpnextai.erpnextai.api.get_chat_response',
                args: {
                    query: `Analyze this Sales Invoice and tell me if it looks normal: ${JSON.stringify(frm.doc)}`
                },
                callback: function (r) {
                    if (r.message) {
                        frappe.msgprint({
                            title: __('AI Analysis'),
                            message: r.message,
                            indicator: 'blue'
                        });
                    }
                }
            });
        }, __('AI Actions'));
    }
});

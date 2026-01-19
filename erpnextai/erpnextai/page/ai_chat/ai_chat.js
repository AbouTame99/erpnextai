frappe.pages['ai-chat'].on_page_load = function (wrapper) {
    var page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'AI Chat',
        single_column: true
    });

    new erpnextai.AIChat(page);
}

erpnextai.AIChat = class {
    constructor(page) {
        this.page = page;
        this.prepare_layout();
        this.setup_events();
    }

    prepare_layout() {
        this.page.main.html(`
			<div class="ai-chat-container" style="display: flex; flex-direction: column; height: calc(100vh - 150px); max-width: 900px; margin: 0 auto; background: var(--bg-color); border-radius: 12px; box-shadow: var(--shadow-sm); overflow: hidden;">
				<div class="chat-messages" style="flex: 1; overflow-y: auto; padding: 20px; display: flex; flex-direction: column; gap: 15px;">
					<div class="message ai" style="align-self: flex-start; background: var(--bg-light-gray); padding: 12px 16px; border-radius: 12px 12px 12px 0; max-width: 80%; line-height: 1.5;">
						Hello! I am your ERPNext AI assistant. How can I help you today?
					</div>
				</div>
				<div class="chat-input-container" style="padding: 20px; border-top: 1px solid var(--border-color); display: flex; gap: 10px; align-items: center;">
					<textarea class="chat-input form-control" placeholder="Ask me anything..." style="flex: 1; resize: none; border-radius: 8px; height: 45px; padding: 10px; border: 1px solid var(--border-color);"></textarea>
					<button class="btn btn-primary btn-send" style="height: 45px; border-radius: 8px;">
						<i class="fa fa-paper-plane"></i>
					</button>
					<button class="btn btn-default btn-voice" style="height: 45px; border-radius: 8px;">
						<i class="fa fa-microphone"></i>
					</button>
				</div>
			</div>
		`);

        this.$messages = this.page.main.find('.chat-messages');
        this.$input = this.page.main.find('.chat-input');
        this.$send_btn = this.page.main.find('.btn-send');
        this.$voice_btn = this.page.main.find('.btn-voice');
    }

    setup_events() {
        let me = this;

        this.$send_btn.on('click', () => this.send_message());

        this.$input.on('keypress', function (e) {
            if (e.which == 13 && !e.shiftKey) {
                e.preventDefault();
                me.send_message();
            }
        });

        this.$voice_btn.on('click', () => this.start_voice());
    }

    send_message() {
        let query = this.$input.val().trim();
        if (!query) return;

        this.add_message(query, 'user');
        this.$input.val('');

        frappe.call({
            method: 'erpnextai.api.get_chat_response',
            args: {
                query: query
            },
            freeze: true,
            callback: (r) => {
                if (r.message) {
                    this.add_message(r.message, 'ai');
                }
            }
        });
    }

    add_message(text, role) {
        let is_ai = role === 'ai';
        let html = `
			<div class="message ${role}" style="align-self: ${is_ai ? 'flex-start' : 'flex-end'}; 
				background: ${is_ai ? 'var(--bg-light-gray)' : 'var(--blue-500)'}; 
				color: ${is_ai ? 'inherit' : '#fff'}; 
				padding: 12px 16px; border-radius: 12px 12px ${is_ai ? '12px 0' : '0 12px'}; 
				max-width: 80%; line-height: 1.5; white-space: pre-wrap;">
				${frappe.markdown(text)}
			</div>
		`;
        this.$messages.append(html);
        this.$messages.scrollTop(this.$messages[0].scrollHeight);
    }

    start_voice() {
        if (!('webkitSpeechRecognition' in window)) {
            frappe.msgprint(__('Speech recognition is not supported in this browser.'));
            return;
        }

        let recognition = new webkitSpeechRecognition();
        recognition.lang = frappe.boot.lang || 'en';
        recognition.onresult = (event) => {
            let transcript = event.results[0][0].transcript;
            this.$input.val(transcript);
            this.send_message();
        };
        recognition.start();
    }
}

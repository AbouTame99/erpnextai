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
			<div class="ai-chat-wrapper" style="background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%); height: calc(100vh - 100px); padding: 20px; display: flex; justify-content: center;">
				<div class="ai-chat-container" style="display: flex; flex-direction: column; height: 100%; width: 100%; max-width: 1000px; background: rgba(255, 255, 255, 0.8); backdrop-filter: blur(10px); border-radius: 20px; border: 1px solid rgba(255, 255, 255, 0.3); box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.15); overflow: hidden;">
					<div class="chat-header" style="padding: 15px 25px; border-bottom: 1px solid rgba(0,0,0,0.05); display: flex; align-items: center; gap: 10px;">
						<div style="width: 10px; height: 10px; background: #28a745; border-radius: 50%;"></div>
						<h5 style="margin: 0; font-weight: 600;">ERPNext AI Assistant</h5>
					</div>
					<div class="chat-messages" style="flex: 1; overflow-y: auto; padding: 25px; display: flex; flex-direction: column; gap: 20px;">
						<div class="message ai-msg">
							<div class="msg-content" style="background: #fff; padding: 15px 20px; border-radius: 0 15px 15px 15px; box-shadow: 0 2px 5px rgba(0,0,0,0.02); max-width: 85%;">
								Hello! I am your premium AI assistant. I can now provide <b>analytics and charts</b>. How can I help you today?
							</div>
						</div>
					</div>
					<div class="chat-input-area" style="padding: 20px; background: #fff; border-top: 1px solid rgba(0,0,0,0.05); display: flex; gap: 15px; align-items: center;">
						<textarea class="chat-input form-control" placeholder="Ask for stats, summaries, or charts..." style="flex: 1; border: none; background: #f8f9fa; border-radius: 12px; height: 45px; padding: 10px 15px; resize: none; focus: border-color: var(--blue-500);"></textarea>
						<div style="display: flex; gap: 8px;">
							<button class="btn btn-voice btn-light" style="border-radius: 12px; height: 45px; width: 45px; display: flex; align-items: center; justify-content: center;">
								<i class="fa fa-microphone" style="font-size: 1.2em; color: #6c757d;"></i>
							</button>
							<button class="btn btn-primary btn-send" style="border-radius: 12px; height: 45px; padding: 0 20px; font-weight: 600;">
								Send <i class="fa fa-paper-plane" style="margin-left: 8px;"></i>
							</button>
						</div>
					</div>
				</div>
			</div>

			<style>
				.message.ai-msg { align-self: flex-start; }
				.ai-msg .msg-content {
					background: #fff; 
					padding: 15px 20px; 
					border-radius: 0 15px 15px 15px; 
					box-shadow: 0 4px 12px rgba(0,0,0,0.05);
					max-width: 85%;
					color: #333;
				}
				.user-msg .msg-content { 
					background: var(--blue-600); 
					color: white; 
					padding: 12px 18px; 
					border-radius: 15px 15px 0 15px; 
					box-shadow: 0 4px 12px rgba(0, 103, 255, 0.2);
					max-width: 80%;
				}
				.chat-messages::-webkit-scrollbar { width: 6px; }
				.chat-messages::-webkit-scrollbar-thumb { background: rgba(0,0,0,0.1); border-radius: 10px; }
				.ai-msg table { width: 100%; border-collapse: collapse; margin: 10px 0; border-radius: 8px; overflow: hidden; }
				.ai-msg th, .ai-msg td { padding: 10px; border: 1px solid #eee; text-align: left; }
				.ai-msg th { background: #f8f9fa; font-weight: 600; }
				.chart-container { background: #fff; border-radius: 12px; padding: 15px; margin: 10px 0; border: 1px solid #eee; }
				
				.typing { display: flex; gap: 4px; align-items: center; padding: 10px 0; }
				.typing span { width: 8px; height: 8px; background: #6c757d; border-radius: 50%; animation: blink 1.4s infinite both; }
				.typing span:nth-child(2) { animation-delay: 0.2s; }
				.typing span:nth-child(3) { animation-delay: 0.4s; }
				@keyframes blink {
					0% { opacity: .2; }
					20% { opacity: 1; }
					100% { opacity: .2; }
				}
			</style>
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

        // Add typing indicator
        let $typing = $(`
			<div class="message ai-msg typing-indicator">
				<div class="msg-content" style="background: #fff; padding: 12px 18px; border-radius: 0 15px 15px 15px; width: fit-content;">
					<div class="typing"><span></span><span></span><span></span></div>
				</div>
			</div>
		`);
        this.$messages.append($typing);
        this.$messages.scrollTop(this.$messages[0].scrollHeight);

        frappe.call({
            method: 'erpnextai.erpnextai.api.get_chat_response',
            args: { query: query },
            callback: (r) => {
                $typing.remove();
                if (r.message) {
                    this.add_message(r.message, 'ai');
                }
            }
        });
    }

    add_message(text, role) {
        let is_ai = role === 'ai';
        let $msg = $(`
			<div class="message ${role}-msg">
				<div class="msg-content"></div>
			</div>
		`);

        if (is_ai) {
            this.render_ai_content($msg.find('.msg-content'), text);
        } else {
            $msg.find('.msg-content').text(text);
        }

        this.$messages.append($msg);
        this.$messages.scrollTop(this.$messages[0].scrollHeight);
    }

    render_ai_content($target, text) {
        // Handle Chart tags
        let chart_regex = /<chart>([\s\S]*?)<\/chart>/g;
        let match;
        let last_index = 0;
        let clean_text = text;

        while ((match = chart_regex.exec(text)) !== null) {
            try {
                let chart_data = JSON.parse(match[1]);
                let chart_id = 'chart-' + Math.random().toString(36).substr(2, 9);

                // Add placeholder for chart
                let $chart_div = $(`<div class="chart-container"><div id="${chart_id}"></div></div>`);
                $target.append(frappe.markdown(text.substring(last_index, match.index)));
                $target.append($chart_div);

                // Render chart after a short delay
                setTimeout(() => {
                    new frappe.Chart("#" + chart_id, {
                        title: chart_data.title,
                        data: chart_data.data,
                        type: chart_data.type,
                        height: 250,
                        colors: ['#7cd6fd', '#743ee2', '#ff5858', '#ffa3ef', '#5f6fed']
                    });
                }, 100);

                last_index = chart_regex.lastIndex;
            } catch (e) {
                console.error("Failed to parse chart data", e);
            }
        }

        $target.append(frappe.markdown(text.substring(last_index)));
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

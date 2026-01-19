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
        this.history = [];
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
            args: {
                query: query,
                history: JSON.stringify(this.history)
            },
            callback: (r) => {
                $typing.remove();
                if (r.message) {
                    // Add to local history for context
                    this.history.push({ role: 'user', content: query });
                    this.history.push({ role: 'ai', content: r.message });

                    // Keep history manageable (last 10 messages)
                    if (this.history.length > 20) {
                        this.history = this.history.slice(-20);
                    }

                    this.add_message(r.message, 'ai');
                }
            },
            error: (err) => {
                $typing.remove();
                if (err.message && err.message.includes('429')) {
                    this.add_message("⚠️ **Gemini API Limit reached.** You are on the Free Tier which allows 5 messages per minute. Please wait 30 seconds and try again.", 'ai');
                } else {
                    this.add_message("❌ " + (err.message || "An unexpected error occurred."), 'ai');
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

        this.$messages.append($msg);

        if (is_ai) {
            this.render_ai_content($msg.find('.msg-content'), text);
        } else {
            $msg.find('.msg-content').text(text);
        }

        this.$messages.scrollTop(this.$messages[0].scrollHeight);
    }

    render_ai_content($target, text) {
        let data_regex = /<chart_data>([\s\S]*?)<\/chart_data>/g;
        let last_index = 0;
        let match;

        while ((match = data_regex.exec(text)) !== null) {
            // Append text before the data tag
            if (match.index > last_index) {
                $target.append(frappe.markdown(text.substring(last_index, match.index)));
            }

            try {
                let raw_tag_content = match[1].trim();

                // CRITICAL FIX: Extract ONLY the JSON part (from first { to last })
                // This prevents "Unexpected character" errors if the AI adds text inside the tags
                let json_match = raw_tag_content.match(/\{[\s\S]*\}/);
                if (!json_match) throw new Error("No valid JSON object found inside tags");

                let chart_json = json_match[0];
                let chart_data = JSON.parse(chart_json);

                let $selector = $(`
                    <div class="chart-selector-card" style="margin: 20px 0; background: #fff; padding: 20px; border-radius: 15px; border: 1px solid #d1d8e0; box-shadow: 0 4px 10px rgba(0,0,0,0.03);">
                        <h6 style="margin-bottom: 15px; font-weight: 600; color: #4b5563; display: flex; align-items: center; gap: 8px;">
                            <i class="fa fa-chart-bar" style="color: var(--blue-500);"></i>
                            Which chart types would you like to see?
                        </h6>
                        <div class="chart-types" style="display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 15px;">
                            <button class="btn btn-xs btn-default chart-type-btn" data-type="bar" style="border-radius: 8px; padding: 5px 12px;">Bar Chart</button>
                            <button class="btn btn-xs btn-default chart-type-btn" data-type="line" style="border-radius: 8px; padding: 5px 12px;">Line Chart</button>
                            <button class="btn btn-xs btn-default chart-type-btn" data-type="pie" style="border-radius: 8px; padding: 5px 12px;">Pie Chart</button>
                            <button class="btn btn-xs btn-default chart-type-btn" data-type="donut" style="border-radius: 8px; padding: 5px 12px;">Donut Chart</button>
                            <button class="btn btn-xs btn-default chart-type-btn" data-type="percentage" style="border-radius: 8px; padding: 5px 12px;">Percentage</button>
                        </div>
                        <div class="render-area" style="text-align: right;">
                            <button class="btn btn-primary btn-sm btn-render-charts" style="display:none; border-radius: 8px; padding: 6px 20px; font-weight: 600;">
                                Generate Selected <i class="fa fa-magic" style="margin-left:5px;"></i>
                            </button>
                        </div>
                        <div class="chart-outputs" style="margin-top: 20px; display: flex; flex-direction: column; gap: 20px;"></div>
                    </div>
                `);

                $target.append($selector);

                let selected_types = new Set();
                $selector.find('.chart-type-btn').on('click', function (e) {
                    e.preventDefault();
                    let type = $(this).data('type');

                    if (selected_types.has(type)) {
                        selected_types.delete(type);
                        $(this).css({ 'background-color': '#fff', 'color': '#333', 'border-color': '#d1d8e0' });
                    } else {
                        selected_types.add(type);
                        $(this).css({ 'background-color': '#007bff', 'color': '#fff', 'border-color': '#0056b3' });
                    }

                    console.log("Selected types:", Array.from(selected_types));

                    if (selected_types.size > 0) {
                        $selector.find('.btn-render-charts').show();
                    } else {
                        $selector.find('.btn-render-charts').hide();
                    }
                });

                $selector.find('.btn-render-charts').on('click', (e) => {
                    e.preventDefault();
                    let $output = $selector.find('.chart-outputs');
                    $output.empty();

                    if (selected_types.size === 0) return;

                    selected_types.forEach(type => {
                        let chart_id = 'chart-' + Math.random().toString(36).substr(2, 9);
                        $output.append(`
                            <div class="single-chart-result" style="border: 1px solid #f3f4f6; border-radius: 12px; padding: 15px; background: #fafafa; margin-bottom: 10px;">
                                <div id="${chart_id}" style="min-height: 200px;"></div>
                            </div>
                        `);

                        setTimeout(() => {
                            if (window.frappe && frappe.Chart) {
                                try {
                                    new frappe.Chart("#" + chart_id, {
                                        title: (chart_data.title || "Data Insight") + ` (${type.charAt(0).toUpperCase() + type.slice(1)})`,
                                        data: chart_data.data,
                                        type: type === 'percentage' ? 'pie' : type,
                                        height: 200,
                                        colors: ['#7cd6fd', '#743ee2', '#ff5858', '#ffa3ef', '#5f6fed'],
                                        lineOptions: { hideDots: 1, regionFill: 1 },
                                        isNavigable: 1
                                    });
                                } catch (err) {
                                    console.error("Frappe Chart Init Error:", err);
                                    $(`#${chart_id}`).html(`<div class="text-danger">Chart Initialization Error: ${err.message}</div>`);
                                }
                            } else {
                                $(`#${chart_id}`).html(`<div class="text-danger">Frappe Chart Library not found.</div>`);
                            }
                        }, 200);
                    });

                    $selector.find('.render-area').hide();
                    $selector.find('.chart-types').css({ 'opacity': '0.5', 'pointer-events': 'none' });
                });

            } catch (e) {
                console.error("Interactive Chart Error:", e);
                $target.append(`<div class="alert alert-danger">Error processing chart data: ${e.message}</div>`);
            }
            last_index = data_regex.lastIndex;
        }

        // Append remaining text
        if (last_index < text.length) {
            $target.append(frappe.markdown(text.substring(last_index)));
        }
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

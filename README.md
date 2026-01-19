# ERPNextAI

AI for ERPNext that allows you to talk with your data and automate insights using Google's Gemini LLM.

## Features

- 💬 **AI Chat Interface**: A dedicated page to query your ERPNext data using natural language.
- 🎙️ **Voice-to-Action**: speak directly to the AI to get answers or perform tasks.
- ⚙️ **Gemini Integration**: Support for Gemini 2.0, 2.5, and 3.0 (Pro & Flash) models.
- 📑 **Contextual Sidebars**: AI-powered summaries and analysis directly on Lead and Sales Invoice documents.
- 📊 **Daily AI Insights**: Automated business summaries sent to your inbox every day.
- 🛠️ **Tool-Use (Function Calling)**: The AI can query live counts and record lists from your database.

## Installation

You can install this app using the [bench](https://github.com/frappe/bench) CLI:

```bash
cd $PATH_TO_YOUR_BENCH
bench get-app https://github.com/AbouTame99/erpnextai
bench install-app erpnextai
bench migrate
```

## Setup

1. Search for **AI Settings** in the search bar.
2. Enter your **Gemini API Key**.
3. Select your preferred **AI Model**.
4. Enable the features you want (Sidebars, Voice, Scheduled Insights).
5. Open the **AI Chat** page and start talking to your data!

## Contributing

This app uses `pre-commit` for code formatting and linting.

```bash
cd apps/erpnextai
pre-commit install
```

## License

GNU General Public License v3.0 (GPL-3.0)

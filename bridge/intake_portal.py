"""Intake Portal — Chat-based project submission UI.

Runs on port 8300, embeds in Paperclip via iframe or standalone.
Features:
- Chat with an Intake Agent that asks clarifying questions
- File upload for reference documents
- Once ready, user says GO and it triggers the full pipeline
- Redirects to Paperclip dashboard to watch progress
"""

import os
import sys
import json
import logging
import uuid
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse
# cgi removed in Python 3.13, not needed

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)-8s %(name)-20s | %(message)s', datefmt='%H:%M:%S')
log = logging.getLogger("intake_portal")

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), '..', 'uploads')
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Store conversations in memory
sessions = {}


def get_vertex_token():
    import google.auth
    import google.auth.transport.requests
    creds, _ = google.auth.default()
    auth_req = google.auth.transport.requests.Request()
    creds.refresh(auth_req)
    return creds.token


def call_intake_agent(conversation_history: list, user_message: str, uploaded_files: list = None) -> str:
    """Call the intake agent to process user input and ask clarifying questions."""
    from openai import OpenAI
    client = OpenAI(
        base_url="https://aiplatform.googleapis.com/v1beta1/projects/pcagentspace/locations/global/endpoints/openapi",
        api_key=get_vertex_token(),
    )

    system_prompt = """You are the Project Intake Agent for an AI Development Agency.

Your job is to help clients define their project clearly BEFORE any work begins.

## YOUR PROCESS:
1. When you receive a project idea, DO NOT accept it as-is
2. Ask 3-5 targeted clarifying questions to understand:
   - WHO are the end users?
   - WHAT specific problem does this solve?
   - WHAT are the must-have features vs nice-to-have?
   - Any technical constraints or preferences?
   - What does SUCCESS look like?
   - Are there existing solutions or competitors?
   - Timeline and budget expectations?
3. Based on their answers, summarize the project scope
4. Ask if they want to adjust anything
5. When they say "GO" or "start" or "proceed", respond with EXACTLY:
   [READY_TO_LAUNCH]
   followed by a clean, comprehensive project brief that includes everything discussed.

## RULES:
- Be friendly but thorough — push back on vague answers
- If they upload files, acknowledge them and ask how they relate to the project
- Keep questions focused and actionable
- Don't ask all questions at once — have a conversation
- After 2-3 rounds of questions, present a summary and ask for confirmation
- ALL infrastructure will use Google Cloud Platform (GCP) — mention this early
- Format your responses with markdown for readability"""

    messages = [{"role": "system", "content": system_prompt}]

    # Add conversation history
    for msg in conversation_history:
        messages.append({"role": msg["role"], "content": msg["content"]})

    # Add current message
    user_content = user_message
    if uploaded_files:
        file_list = "\n".join(f"- {f}" for f in uploaded_files)
        user_content += f"\n\n[Uploaded files:\n{file_list}]"

    messages.append({"role": "user", "content": user_content})

    resp = client.chat.completions.create(
        model="google/gemini-3.1-pro-preview",
        messages=messages,
        max_tokens=2000,
        temperature=0.7,
    )
    return resp.choices[0].message.content


HTML_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Agency — New Project</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        .chat-msg { animation: fadeIn 0.3s ease-in; }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
        .typing { display: inline-block; }
        .typing span { display: inline-block; width: 8px; height: 8px; margin: 0 2px; background: #6366f1; border-radius: 50%; animation: bounce 1.4s infinite ease-in-out; }
        .typing span:nth-child(1) { animation-delay: 0s; }
        .typing span:nth-child(2) { animation-delay: 0.2s; }
        .typing span:nth-child(3) { animation-delay: 0.4s; }
        @keyframes bounce { 0%, 80%, 100% { transform: scale(0); } 40% { transform: scale(1); } }
        .markdown h2 { font-size: 1.1rem; font-weight: 700; margin-top: 0.75rem; }
        .markdown h3 { font-size: 1rem; font-weight: 600; margin-top: 0.5rem; }
        .markdown ul { list-style: disc; padding-left: 1.5rem; margin: 0.25rem 0; }
        .markdown li { margin: 0.15rem 0; }
        .markdown strong { font-weight: 700; }
        .markdown p { margin: 0.3rem 0; }
    </style>
</head>
<body class="bg-gray-50 text-gray-900 min-h-screen flex flex-col">
    <!-- Header -->
    <header class="bg-white border-b px-6 py-3 flex items-center justify-between shadow-sm">
        <div class="flex items-center gap-3">
            <a href="http://127.0.0.1:3100" class="text-gray-400 hover:text-gray-600 text-sm">&larr; Dashboard</a>
            <h1 class="text-lg font-bold text-indigo-600">New Project</h1>
        </div>
        <span class="text-xs text-gray-400">AI Development Agency</span>
    </header>

    <!-- Chat Area -->
    <main class="flex-1 overflow-y-auto p-6 max-w-3xl mx-auto w-full" id="chatArea">
        <div id="messages">
            <div class="chat-msg flex gap-3 mb-4">
                <div class="w-8 h-8 rounded-full bg-indigo-100 flex items-center justify-center text-indigo-600 font-bold text-sm flex-shrink-0">AI</div>
                <div class="bg-white rounded-lg p-4 shadow-sm border max-w-xl">
                    <p class="text-sm markdown">Welcome! I'm your <strong>Project Intake Agent</strong>. I'll help you define your project clearly before our AI team starts working on it.</p>
                    <p class="text-sm mt-2 markdown">Tell me about your project idea — what are you looking to build? You can also upload reference files (documents, images, presentations).</p>
                </div>
            </div>
        </div>
        <div id="typingIndicator" class="hidden flex gap-3 mb-4">
            <div class="w-8 h-8 rounded-full bg-indigo-100 flex items-center justify-center text-indigo-600 font-bold text-sm flex-shrink-0">AI</div>
            <div class="bg-white rounded-lg p-4 shadow-sm border">
                <div class="typing"><span></span><span></span><span></span></div>
            </div>
        </div>
    </main>

    <!-- Input Area -->
    <footer class="bg-white border-t p-4 max-w-3xl mx-auto w-full">
        <div id="uploadedFiles" class="flex flex-wrap gap-2 mb-2"></div>
        <form id="chatForm" class="flex gap-2" onsubmit="sendMessage(event)">
            <label class="flex items-center justify-center w-10 h-10 rounded-lg border border-gray-200 hover:bg-gray-50 cursor-pointer flex-shrink-0" title="Attach files">
                <svg class="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13"></path></svg>
                <input type="file" id="fileInput" multiple class="hidden" onchange="handleFiles(this.files)">
            </label>
            <input type="text" id="msgInput" placeholder="Describe your project idea..."
                class="flex-1 rounded-lg border border-gray-200 px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-300 focus:border-indigo-400" autofocus>
            <button type="submit" id="sendBtn" class="bg-indigo-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-indigo-700 transition flex-shrink-0">Send</button>
        </form>
        <p class="text-xs text-gray-400 mt-2 text-center">All projects use GCP infrastructure. Say <strong>"GO"</strong> when ready to launch.</p>
    </footer>

    <!-- Launch Modal -->
    <div id="launchModal" class="hidden fixed inset-0 bg-black/50 flex items-center justify-center z-50">
        <div class="bg-white rounded-xl p-6 max-w-md w-full mx-4 shadow-2xl">
            <h2 class="text-lg font-bold text-indigo-600 mb-2">Launching Project!</h2>
            <p class="text-sm text-gray-600 mb-4">Your project is being submitted to the AI Development Agency. The full pipeline will run:</p>
            <ol class="text-xs text-gray-500 space-y-1 mb-4">
                <li>1. CEO Agent — Blueprint</li>
                <li>2. Deep Problem Analyst — Analysis</li>
                <li>3. Market Research — Competitors</li>
                <li>4. Tech Research — Stack</li>
                <li>5. Architect — ADR</li>
                <li>6. Planner — Stories</li>
                <li>7. Builder — Code</li>
                <li>8. QA — Testing</li>
                <li>9. Security — Audit</li>
            </ol>
            <div id="launchStatus" class="text-sm text-indigo-600 font-medium">Submitting...</div>
            <a href="http://127.0.0.1:3100" class="block mt-4 text-center bg-indigo-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-indigo-700 transition">Open Dashboard to Watch Progress</a>
        </div>
    </div>

    <script>
    const SESSION_ID = crypto.randomUUID();
    let uploadedFiles = [];

    function handleFiles(files) {
        const container = document.getElementById('uploadedFiles');
        for (const file of files) {
            uploadedFiles.push(file);
            const tag = document.createElement('span');
            tag.className = 'text-xs bg-indigo-50 text-indigo-700 px-2 py-1 rounded-full border border-indigo-200';
            tag.textContent = file.name;
            container.appendChild(tag);
        }
    }

    function addMessage(role, content) {
        const div = document.createElement('div');
        div.className = 'chat-msg flex gap-3 mb-4';
        const isUser = role === 'user';
        div.innerHTML = `
            <div class="w-8 h-8 rounded-full ${isUser ? 'bg-gray-200' : 'bg-indigo-100'} flex items-center justify-center ${isUser ? 'text-gray-600' : 'text-indigo-600'} font-bold text-sm flex-shrink-0">${isUser ? 'You' : 'AI'}</div>
            <div class="${isUser ? 'bg-indigo-50 border-indigo-100' : 'bg-white'} rounded-lg p-4 shadow-sm border max-w-xl">
                <div class="text-sm markdown">${content.replace(/\n/g, '<br>').replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>').replace(/^- /gm, '&bull; ')}</div>
            </div>
        `;
        document.getElementById('messages').appendChild(div);
        document.getElementById('chatArea').scrollTop = document.getElementById('chatArea').scrollHeight;
    }

    async function sendMessage(e) {
        e.preventDefault();
        const input = document.getElementById('msgInput');
        const msg = input.value.trim();
        if (!msg) return;

        addMessage('user', msg);
        input.value = '';
        document.getElementById('sendBtn').disabled = true;
        document.getElementById('typingIndicator').classList.remove('hidden');

        // Upload files if any
        const fileNames = uploadedFiles.map(f => f.name);

        try {
            const resp = await fetch('/chat', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ session_id: SESSION_ID, message: msg, files: fileNames })
            });
            const data = await resp.json();

            document.getElementById('typingIndicator').classList.add('hidden');
            document.getElementById('sendBtn').disabled = false;

            if (data.launch) {
                addMessage('assistant', data.response);
                document.getElementById('launchModal').classList.remove('hidden');
                document.getElementById('launchStatus').textContent = 'Pipeline running... Check the dashboard!';
            } else {
                addMessage('assistant', data.response);
            }
        } catch (err) {
            document.getElementById('typingIndicator').classList.add('hidden');
            document.getElementById('sendBtn').disabled = false;
            addMessage('assistant', 'Error connecting to the agent. Please try again.');
        }

        input.focus();
    }
    </script>
</body>
</html>"""


class IntakeHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/' or self.path == '/index.html':
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
            self.wfile.write(HTML_PAGE.encode('utf-8'))
        else:
            self.send_error(404)

    def do_POST(self):
        if self.path == '/chat':
            content_length = int(self.headers.get('Content-Length', 0))
            body = json.loads(self.rfile.read(content_length).decode('utf-8'))

            session_id = body.get('session_id', str(uuid.uuid4()))
            message = body.get('message', '')
            files = body.get('files', [])

            # Get or create session
            if session_id not in sessions:
                sessions[session_id] = []

            # Call the intake agent
            try:
                response = call_intake_agent(sessions[session_id], message, files)
            except Exception as e:
                log.error("Intake agent error: %s", e)
                response = f"Sorry, I encountered an error: {str(e)[:100]}. Please try again."

            # Save to history
            sessions[session_id].append({"role": "user", "content": message})
            sessions[session_id].append({"role": "assistant", "content": response})

            # Check if ready to launch
            launch = "[READY_TO_LAUNCH]" in response
            if launch:
                # Extract the project brief (everything after [READY_TO_LAUNCH])
                brief = response.split("[READY_TO_LAUNCH]", 1)[1].strip()
                response = response.replace("[READY_TO_LAUNCH]", "**Project approved! Launching the AI pipeline now...**\n\n")

                # Trigger the pipeline in background
                import threading
                def run_pipeline():
                    try:
                        from bridge.autonomous_pipeline import run_planning_pipeline
                        run_planning_pipeline(brief)
                    except Exception as e:
                        log.error("Pipeline failed: %s", e)

                threading.Thread(target=run_pipeline, daemon=True).start()
                log.info("Pipeline launched for project: %s...", brief[:80])

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"response": response, "launch": launch}).encode('utf-8'))
        else:
            self.send_error(404)

    def log_message(self, format, *args):
        log.debug(format, *args)


def main():
    port = int(os.environ.get('INTAKE_PORT', 8300))
    server = HTTPServer(('127.0.0.1', port), IntakeHandler)
    log.info("=" * 60)
    log.info("Intake Portal running at http://127.0.0.1:%d", port)
    log.info("=" * 60)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()


if __name__ == '__main__':
    main()

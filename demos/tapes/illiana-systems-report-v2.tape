# Illiana Systems Report Demo (v2)
# Prerequisites: my-app stack running (docker compose up), and HF_TOKEN set in
# my-app/.env so the embedding-model load is silent (see .env.example).
# Run from my-app directory: vhs ../demos/tapes/illiana-systems-report-v2.tape
#
# No warm-up gymnastics needed: with HF_TOKEN configured, the RAG embedding load
# is clean (no download warning, no progress bars, no INFO log), so the first
# message renders cleanly on camera.

Output demos/recordings/illiana-systems-report-v2.gif
Output demos/recordings/illiana-systems-report-v2.mp4
Output demos/recordings/illiana-systems-report-v2.webm

Set FontSize 36
Set Width 2560
Set Height 1440
Set Theme "Dracula"
Set TypingSpeed 30ms
Set Framerate 30

# Hidden setup
Hide
Type "uv sync -q && source .venv/bin/activate"
Enter
Sleep 3s
Show

Sleep 1s

# Start Illiana chat with RAG
Type "my-app ai chat --rag --collection code"
Sleep 500ms
Enter
Sleep 2s

# First question
Type "Hello, Illiana. Give me a concise systems report."
Sleep 500ms
Enter
Sleep 12s

# Follow-up
Type "What is the #1 thing that we need to take a look at?"
Sleep 500ms
Enter
Sleep 13s

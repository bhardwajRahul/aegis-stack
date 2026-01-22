# Illiana Systems Report Demo
# Prerequisites: my-app stack must be running (docker compose up)
# Run from my-app directory: vhs ../demos/tapes/illiana-systems-report.tape

Output demos/recordings/illiana-systems-report-36.gif

Set FontSize 36
Set Width 2560
Set Height 1440
Set Theme "Dracula"
Set TypingSpeed 30ms
Set Framerate 30

# Pre-seed: sync dependencies and source venv (hidden)
Hide
Type "uv sync -q && source .venv/bin/activate"
Enter
Sleep 3s
Show

Sleep 1s

# Start Illiana chat with RAG
Type "my-app ai chat --rag --collection aegis-code"
Sleep 500ms
Enter

Sleep 2s

# First question - intro
Type "Hello, Illiana. Give me a systems report."
Sleep 500ms
Enter

# Wait for systems report response
Sleep 14s

# Second question - fix request
Type "What do we have to do to bring comms back online?"
Sleep 500ms
Enter

# Wait for fix response
Sleep 15s

# CLI Demo
# Prerequisites: my-app stack must be running (docker compose up)
# Run from my-app directory: vhs ../demos/tapes/cli-demo.tape

Output demos/recordings/cli-demo.gif

Set FontSize 36
Set Width 2560
Set Height 1440
Set Theme "TokyoNight"
Set TypingSpeed 50ms
Set Framerate 30

# Pre-seed: sync dependencies and source venv (hidden)
Hide
Type "uv sync -q && source .venv/bin/activate"
Enter
Sleep 3s
Type "clear"
Enter
Sleep 500ms
Show

Sleep 1s

# Show CLI help
Type "my-app --help"
Sleep 500ms
Enter

Sleep 5s

Type "clear"
Enter
Sleep 500ms

# Show health status
Type "my-app health status"
Sleep 500ms
Enter

Sleep 6s

# Show tasks list (no clear from health)
Type "my-app tasks list"
Sleep 500ms
Enter

Sleep 7s

Type "clear"
Enter
Sleep 500ms

# Create test users
Type "my-app auth create-test-users"
Sleep 500ms
Enter

Sleep 5s

# List users (no clear from create)
Type "my-app auth list-users"
Sleep 500ms
Enter

Sleep 5s

Type "clear"
Enter
Sleep 500ms

# Comms status
Type "my-app comms status"
Sleep 500ms
Enter

Sleep 5s

Type "clear"
Enter
Sleep 500ms

# RAG status
Type "my-app rag status"
Sleep 500ms
Enter

Sleep 5s

Type "clear"
Enter
Sleep 500ms

# LLM sync
Type "my-app llm sync"
Sleep 500ms
Enter

Sleep 7s

Type "clear"
Enter
Sleep 500ms

# LLM list with filters
Type "my-app llm list --modality audio --limit 20"
Sleep 500ms
Enter

Sleep 7s

Type "clear"
Enter
Sleep 500ms

# AI chat with systems report
Type "my-app ai chat 'Give me a systems report' --new --no-rag"
Sleep 500ms
Enter

Sleep 25s

Type "clear"
Enter
Sleep 500ms

# AI status
Type "my-app ai status"
Sleep 500ms
Enter

Sleep 5s

# AI providers (no clear)
Type "my-app ai providers"
Sleep 500ms
Enter

Sleep 5s

# AI usage (no clear)
Type "my-app ai usage"
Sleep 500ms
Enter

Sleep 8s

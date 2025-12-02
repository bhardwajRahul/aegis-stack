Output aegis-ai-demo.gif

Set FontSize 48
Set Width 2560
Set Height 1440
Set Theme "TokyoNight"
Set TypingSpeed 100ms
Set Framerate 60

# Comment appears instantly at top
Hide
Type "# AI-powered apps in seconds"
Sleep 2s
Enter
Show

Sleep 2s

Type "uv run aegis init ai-poc --services ai --yes --force"
Sleep 2s
Enter
Sleep 8s
Enter 2


Type "cd ai-poc"
Sleep 2s
Enter
Sleep 500ms
Enter


Type "source .venv/bin/activate"
Sleep 2s
Enter
Sleep 500ms
Enter 2

Hide
Type "# Check CLI commands"
Enter
Show


Type "ai-poc ai version"
Sleep 2s
Enter
Sleep 5s
Enter 2


Type "ai-poc ai config show"
Sleep 2s
Enter
Sleep 6s
Enter 2


Type "ai-poc ai providers list"
Sleep 2s
Enter
Sleep 6s
Enter 2

Hide
Type "# Start chatting"
Enter
Show


Type 'ai-poc ai chat send "What is a python boilerplate in 2025?"'
Sleep 5s
Enter
Sleep 30s


Type "exit"
Sleep 2s
Enter
Sleep 2s

Output aegis-evolution-demo.gif

Set FontSize 48
Set Width 2560
Set Height 1440
Set Theme "TokyoNight"
Set TypingSpeed 30ms
Set Framerate 60

# Comment appears instantly at top
Hide
Type "# Your stack grows with you"
Enter
Show

Sleep 2s

# Start in demo-app
Type "cd demo-app"
Enter
Sleep 500ms
Enter

Hide
Type "# Add components anytime"
Enter
Show

Set TypingSpeed 100ms
Type "../.venv/bin/aegis add scheduler --backend sqlite -p . -y"
Set TypingSpeed 30ms
Enter
Sleep 4s
Enter 2

Hide
Type "# Check the scheduled tasks"
Enter
Show

Set TypingSpeed 100ms
Type "uv run demo-app tasks list"
Set TypingSpeed 30ms
Enter
Sleep 6s
Enter 2

Hide
Type "# Remove what you don't need"
Enter
Show

Set TypingSpeed 100ms
Type "../.venv/bin/aegis remove scheduler -p . -y"
Set TypingSpeed 30ms
Enter
Sleep 4s
Enter 2

Hide
Type "# Scheduler is really gone"
Enter
Show

Set TypingSpeed 100ms
Type "../.venv/bin/aegis remove scheduler -p . -y"
Set TypingSpeed 30ms
Enter
Sleep 3s
Enter 2

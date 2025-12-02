Output aegis-evolution-demo.gif

Set FontSize 48
Set Width 2560
Set Height 1440
Set Theme "TokyoNight"
Set TypingSpeed 100ms
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

Type "../.venv/bin/aegis add scheduler --backend sqlite -p . -y"
Sleep 2s
Enter
Sleep 4s
Enter 2

Hide
Type "# Check the scheduled tasks"
Sleep 2s
Enter
Show

Type "uv run demo-app tasks list"
Sleep 2s
Enter
Sleep 8s
Enter 2

Hide
Type "# Remove what you don't need"
Sleep 2s
Enter
Show

Type "../.venv/bin/aegis remove scheduler -p . -y"
Sleep 2s
Enter
Sleep 7s
Enter 2

Hide
Type "# Scheduler is really gone"
Sleep 2s
Enter
Show

Type "../.venv/bin/aegis remove scheduler -p . -y"
Sleep 2s
Enter
Sleep 7s
Enter 2

Output aegis-demo.gif

Set FontSize 48
Set Width 2560
Set Height 1440
Set Theme "TokyoNight"
Set TypingSpeed 100ms
Set Framerate 60

# Comment appears instantly
Hide
Type "# Create project with scheduler and database"
Enter
Show

Sleep 2s

Type "uv run aegis init demo-app --components scheduler,database --yes --force"
Sleep 2s
Enter
Sleep 8s
Enter 2

Type "cd demo-app"
Sleep 2s
Enter
Sleep 500ms
Enter

Type "make serve"
Sleep 2s
Enter
Sleep 20s
Enter 2

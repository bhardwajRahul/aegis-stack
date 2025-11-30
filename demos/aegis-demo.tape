Output aegis-demo.gif

Set FontSize 48
Set Width 2560
Set Height 1440
Set Theme "TokyoNight"
Set TypingSpeed 75ms
Set Framerate 60

# Comment appears instantly
Hide
Type "# Create project with scheduler and database"
Enter
Show

Sleep 2s

Type "uvx aegis-stack init demo-app --components scheduler,database --yes --force"
Sleep 1s
Enter
Sleep 8s
Enter 2

Type "cd demo-app"
Sleep 500ms
Enter
Sleep 500ms
Enter

Type "make serve"
Sleep 500ms
Enter
Sleep 20s
Enter 2

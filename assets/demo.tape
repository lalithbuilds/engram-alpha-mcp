Output assets/demo.gif
Set FontSize 15
Set Width 900
Set Height 450
Set Padding 40
Set WindowBar Colorful
Set Margin 20
Set MarginFill "#1a1b26" 
Set BorderRadius 12
Set FontFamily "Fira Code"
Set Theme "TokyoNight"
Set TypingSpeed 40ms

Hide
Type "python3 -c 'import engram'" Enter
Type "alias engram='python3 src/engram/cli.py'" Enter
Type "rm -f engram.sqlite*" Enter
Type "export ENGRAM_DB_PATH=engram.sqlite" Enter
Type "clear" Enter
Show

Sleep 500ms
Type "engram save 'Core system architecture initialized. WAL mode active.' --importance 10"
Sleep 200ms
Enter
Sleep 1s

Type "engram save 'API keys loaded into encrypted environment.' --category sec"
Sleep 200ms
Enter
Sleep 1s

Type "engram search 'architecture'"
Sleep 200ms
Enter
Sleep 2s

Type "engram stats"
Sleep 200ms
Enter
Sleep 3s

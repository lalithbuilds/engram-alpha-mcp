Output assets/demo.gif
Set FontSize 16
Set Width 1000
Set Height 450
Set Padding 40
Set WindowBar Colorful
Set Margin 20
Set MarginFill "#6B50FF"
Set BorderRadius 10
Set FontFamily "JetBrains Mono"
Set Theme "Catppuccin Mocha"

Hide
Type "python3 -c 'import engram'" Enter
Type "alias engram='python3 src/engram/cli.py'" Enter
Type "rm -f engram.sqlite*" Enter
Type "export ENGRAM_DB_PATH=engram.sqlite" Enter
Type "clear" Enter
Show

Type "engram setup" Enter
Sleep 2s
Type "engram save 'Deployed Engram Alpha 2.0 with semantic sqlite-vec indexing'" Enter
Sleep 2s
Type "engram search 'semantic indexing'" Enter
Sleep 4s

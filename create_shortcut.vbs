Set WshShell = CreateObject("WScript.Shell")
Set oShortcut = WshShell.CreateShortcut(WshShell.SpecialFolders("Desktop") & "\AI Radio.lnk")
oShortcut.TargetPath = "C:\Users\bates\Documents\Coding\ai-radio\start.bat"
oShortcut.WorkingDirectory = "C:\Users\bates\Documents\Coding\ai-radio"
oShortcut.Description = "KPXL Nocturnal Radio - AI Radio Station"
oShortcut.WindowStyle = 1
oShortcut.Save
WScript.Echo "Desktop shortcut created!"

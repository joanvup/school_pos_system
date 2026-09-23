Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
currentDir = fso.GetParentFolderName(WScript.ScriptFullName)

backendDir = currentDir & "\backend"
pythonwExe = backendDir & "\venv\Scripts\pythonw.exe"
scriptPy = backendDir & "\acr122u_bridge.py"

If fso.FileExists(pythonwExe) And fso.FileExists(scriptPy) Then
    WshShell.CurrentDirectory = backendDir
    WshShell.Run """" & pythonwExe & """ """ & scriptPy & """ --mode wedge", 0, False
Else
    Wscript.Echo "Error: No se encontro pythonw en backend\venv\Scripts\pythonw.exe"
End If

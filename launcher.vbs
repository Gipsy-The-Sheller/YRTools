' YRTools Launcher - VBScript version
' A lightweight launcher for embedded Python with environment variable support

Option Explicit

' Constants
Const ForReading = 1
Const ForWriting = 2
Const ForAppending = 8

' Global variables
Dim objShell, objFSO, scriptPath, scriptDir
Dim iniPath, pythonHome, pythonExe, scriptFile, msys2Home
Dim pythonFullPath, cmd, envPythonPath, envPath

' Initialize
Set objShell = CreateObject("WScript.Shell")
Set objFSO = CreateObject("Scripting.FileSystemObject")

' Get script directory
scriptPath = WScript.ScriptFullName
scriptDir = objFSO.GetParentFolderName(scriptPath)

' Log function
Sub LogMessage(message)
    Dim logFile, logPath
    logPath = objFSO.BuildPath(scriptDir, "launcher_debug.log")
    Set logFile = objFSO.OpenTextFile(logPath, ForAppending, True)
    logFile.WriteLine "[" & Now() & "] " & message
    logFile.Close
End Sub

' Read INI file
Sub ReadINI
    Dim iniFile, line, section, key, value
    Dim inSection, i, equalPos

    iniPath = objFSO.BuildPath(scriptDir, "launcher.ini")

    ' Default values
    pythonHome = "python"
    pythonExe = "pythonw.exe"
    scriptFile = "main.py"
    msys2Home = ""

    If objFSO.FileExists(iniPath) Then
        Set iniFile = objFSO.OpenTextFile(iniPath, ForReading)
        inSection = False

        Do Until iniFile.AtEndOfStream
            line = Trim(iniFile.ReadLine)

            ' Skip comments and empty lines
            If Left(line, 1) = ";" Or Left(line, 1) = "#" Or line = "" Then
                ' Skip
            ElseIf Left(line, 1) = "[" And Right(line, 1) = "]" Then
                ' Section header
                section = Mid(line, 2, Len(line) - 2)
                inSection = (section = "paths")
            ElseIf inSection Then
                ' Key=value pair
                equalPos = InStr(line, "=")
                If equalPos > 0 Then
                    key = Trim(Left(line, equalPos - 1))
                    value = Trim(Mid(line, equalPos + 1))

                    Select Case key
                        Case "python_home"
                            pythonHome = value
                        Case "python_exe"
                            pythonExe = value
                        Case "script"
                            scriptFile = value
                        Case "msys2_home"
                            msys2Home = value
                    End Select
                End If
            End If
        Loop

        iniFile.Close
    End If

    ' Convert relative paths to absolute paths
    If Left(pythonHome, 1) <> ":" Then
        pythonHome = objFSO.BuildPath(scriptDir, pythonHome)
    End If

    If Left(scriptFile, 1) <> ":" Then
        scriptFile = objFSO.BuildPath(scriptDir, scriptFile)
    End If

    If msys2Home <> "" And Left(msys2Home, 1) <> ":" Then
        msys2Home = objFSO.BuildPath(scriptDir, msys2Home)
    End If
End Sub

' Set environment variables
Sub SetEnvironment
    Dim currentPath, scriptDirOnly

    ' Set PYTHONHOME
    objShell.Environment("PROCESS")("PYTHONHOME") = pythonHome

    ' Set PYTHONPATH
    scriptDirOnly = objFSO.GetParentFolderName(scriptFile)
    envPythonPath = scriptDirOnly & ";" & pythonHome
    objShell.Environment("PROCESS")("PYTHONPATH") = envPythonPath

    ' Set PATH
    currentPath = objShell.Environment("PROCESS")("PATH")
    envPath = pythonHome & ";" & pythonHome & "\Scripts"

    If msys2Home <> "" Then
        envPath = envPath & ";" & msys2Home & "\usr\bin"
    End If

    envPath = envPath & ";" & currentPath
    objShell.Environment("PROCESS")("PATH") = envPath
End Sub

' Main execution
On Error Resume Next

' Clear debug log
Dim debugLogPath
debugLogPath = objFSO.BuildPath(scriptDir, "launcher_debug.log")
If objFSO.FileExists(debugLogPath) Then
    objFSO.DeleteFile debugLogPath
End If

LogMessage "Launcher started"
LogMessage "Script directory: " & scriptDir

' Read configuration
ReadINI
LogMessage "python_home: " & pythonHome
LogMessage "python_exe: " & pythonExe
LogMessage "script: " & scriptFile
LogMessage "msys2_home: " & msys2Home

' Validate paths
If Not objFSO.FileExists(pythonHome & "\" & pythonExe) Then
    LogMessage "ERROR: Python executable not found: " & pythonHome & "\" & pythonExe
    MsgBox "Python executable not found:" & vbCrLf & vbCrLf & _
           pythonHome & "\" & pythonExe & vbCrLf & vbCrLf & _
           "Please check launcher.ini configuration.", _
           vbCritical, "YRTools Launcher Error"
    WScript.Quit 1
End If

If Not objFSO.FileExists(scriptFile) Then
    LogMessage "ERROR: Script not found: " & scriptFile
    MsgBox "Script not found:" & vbCrLf & vbCrLf & _
           scriptFile & vbCrLf & vbCrLf & _
           "Please check launcher.ini configuration.", _
           vbCritical, "YRTools Launcher Error"
    WScript.Quit 1
End If

' Set environment variables
SetEnvironment
LogMessage "Environment variables set"

' Construct command
pythonFullPath = """" & pythonHome & "\" & pythonExe & """"
cmd = pythonFullPath & " """ & scriptFile & """"
LogMessage "Command: " & cmd

' Execute Python script directly
LogMessage "Starting Python process..."
LogMessage "Command: " & pythonFullPath & " " & scriptFile

' Run pythonw.exe directly with arguments
' Window style 1 = SW_SHOWNORMAL (activate and show window)
objShell.Run pythonFullPath & " """ & scriptFile & """", 1, False

LogMessage "Launcher finished - Python process started independently"
WScript.Quit 0
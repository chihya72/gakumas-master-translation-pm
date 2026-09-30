# Run from PowerShell Core 7. No ExecutionPolicy changes are made.
#Requires -Version 7.0
[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'
$pythonCommand = Get-Command python -CommandType Application -ErrorAction SilentlyContinue
if (-not $pythonCommand) { throw 'Install Python 3 with Tkinter before opening this tool.' }
$scriptPath = Join-Path $PSScriptRoot 'campus_token_tool.py'
if (-not (Test-Path -LiteralPath $scriptPath -PathType Leaf)) { throw 'Token tool source is missing.' }
[string[]]$arguments = @($scriptPath)
& $pythonCommand.Source @arguments
if ($LASTEXITCODE -ne 0) { throw 'Token tool failed. No credential details were printed.' }

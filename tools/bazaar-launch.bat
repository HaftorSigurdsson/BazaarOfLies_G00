@echo off
rem bazaar-launch.bat - thin wrapper: the implementation is cross-platform
rem Python (console windows on Windows, tmux on macOS/Linux). See
rem bazaar_launch.py for usage and environment variables.
set SCRIPT=%~dp0bazaar_launch.py
py -3 "%SCRIPT%" %*
if errorlevel 9009 python "%SCRIPT%" %*

@echo off
cd /d "%~dp0"
echo Starting the Robo Advisor...

rem Find a Python that really runs (the Microsoft Store "python" shortcut does not count)
set PY=
py -3 --version >nul 2>nul && set PY=py -3
if "%PY%"=="" (python --version >nul 2>nul && set PY=python)
if "%PY%"=="" if exist "%USERPROFILE%\anaconda3\python.exe" set PY="%USERPROFILE%\anaconda3\python.exe"
if "%PY%"=="" if exist "%USERPROFILE%\miniconda3\python.exe" set PY="%USERPROFILE%\miniconda3\python.exe"
if "%PY%"=="" if exist "%LOCALAPPDATA%\anaconda3\python.exe" set PY="%LOCALAPPDATA%\anaconda3\python.exe"
if "%PY%"=="" (
  echo.
  echo No working Python was found on this PC.
  echo Install Python from https://www.python.org/downloads/ and tick "Add python.exe to PATH",
  echo then double click this file again.
  echo.
  pause
  exit /b 1
)
echo Using: %PY%

rem Skip Streamlit's first run email prompt, which otherwise waits forever
if not exist "%USERPROFILE%\.streamlit" mkdir "%USERPROFILE%\.streamlit"
if not exist "%USERPROFILE%\.streamlit\credentials.toml" (
  > "%USERPROFILE%\.streamlit\credentials.toml" echo [general]
  >> "%USERPROFILE%\.streamlit\credentials.toml" echo email = ""
)

echo Installing packages (first time can take a few minutes)...
%PY% -m pip install -r requirements.txt
if errorlevel 1 (
  echo Package install failed. See the message above.
  pause
  exit /b 1
)

echo Launching. Your browser should open at http://localhost:8501
%PY% -m streamlit run app.py
echo.
echo The app stopped. See any message above.
pause

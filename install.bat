echo=1/*>nul&@cls
@echo off
setlocal enableDelayedExpansion
%1 start "" mshta vbscript:CreateObject("Shell.Application").ShellExecute("cmd.exe","/c %~s0 ::","","runas",1)(window.close)&&exit
cls


# ON PROGRESS .....


::setlocal
call :setdir
call :configx86orx64

set extract=extract

#Cmake was too complicated to use with windows (have to entirely build boost, install cygwin, get
# cmake, make, gcc , build the entire thing ....)

 Install Minicoda
"https://docs.conda.io/en/latest/miniconda.html"

Open anconda prompt
"conda install av -c conda-forge"
"pip install -r requirements.txt"


pause

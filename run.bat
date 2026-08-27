@echo off
REM =============================================================================
REM HYDRA-UMC-COGNITIVE-NODE - run.bat
REM Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
REM GPL-3.0 - see LICENSE
REM =============================================================================
REM Runs HYDRA-UMC-COGNITIVE-NODE's entry point. Run build.bat first.
REM Forwards all arguments (e.g. "run.bat family-status").
cd /d "%~dp0"

if exist .venv\Scripts\activate.bat (
    call .venv\Scripts\activate.bat
)

python -m hydra_umc_cognitive_node.main %*
pause

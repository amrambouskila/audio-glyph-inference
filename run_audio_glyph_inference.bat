@echo off
setlocal enabledelayedexpansion

REM ============================================================
REM              CONFIGURATION (EDIT THESE ONLY)
REM ============================================================
set "COMPOSE_FILE=docker-compose.yml"
set "BACKEND_PORT=8000"
set "BACKEND_URL=http://localhost:%BACKEND_PORT%"
set "BACKEND_DOCS_URL=%BACKEND_URL%/docs"
set "IMAGE_PREFIX=audio-glyph-inference"

REM ============================================================
REM                          BANNER
REM ============================================================
echo.
echo ============================================================
echo            audio-glyph-inference -- Phase 1
echo ============================================================
echo   Services:
echo     backend   (FastAPI)   -^> %BACKEND_URL%
echo     postgres              -^> localhost:5432
echo     redis                 -^> localhost:6379
echo ============================================================
echo.

REM ============================================================
REM                     START THE SERVICE
REM ============================================================
call :start_service

:show_menu
echo.
echo ==============================
echo   k = stop (keep images)
echo   q = stop + remove project images
echo   v = stop + remove images + volumes
echo   r = full restart (stop, remove, rebuild, relaunch)
echo ==============================

REM ============================================================
REM                     MAIN LOOP
REM ============================================================
:main_loop
set /p "CHOICE=Enter selection (k/q/v/r): "
if /I "%CHOICE%"=="k" goto do_stop
if /I "%CHOICE%"=="q" goto do_cleanup
if /I "%CHOICE%"=="v" goto do_cleanup_volumes
if /I "%CHOICE%"=="r" goto do_restart
echo Invalid selection. Enter k, q, v, or r.
goto main_loop

:do_stop
echo.
echo Stopping containers...
docker compose -f "%COMPOSE_FILE%" down
echo Done.
goto end_script

:do_cleanup
echo.
echo Stopping containers...
docker compose -f "%COMPOSE_FILE%" down --remove-orphans
call :remove_images
echo Done.
goto end_script

:do_cleanup_volumes
echo.
echo Stopping containers and removing volumes...
docker compose -f "%COMPOSE_FILE%" down --volumes --remove-orphans
call :remove_images
echo Done.
goto end_script

:do_restart
echo.
echo === FULL RESTART ===
echo Stopping containers...
docker compose -f "%COMPOSE_FILE%" down --remove-orphans
call :remove_images
echo.
call :start_service
goto show_menu

REM ============================================================
REM                    HELPER: START SERVICE
REM ============================================================
:start_service
echo Starting Docker Compose...
docker compose -f "%COMPOSE_FILE%" up --build -d

echo.
echo Waiting for backend /health to respond...

set /a WAITED=0
set /a MAX_WAIT=90

:start_wait_loop
curl -fsS "%BACKEND_URL%/health" >nul 2>nul
if %ERRORLEVEL%==0 goto start_ready
timeout /t 1 /nobreak >nul
set /a WAITED+=1
if %WAITED% GEQ %MAX_WAIT% (
    echo Warning: backend did not respond within %MAX_WAIT%s.
    echo Check logs with: docker compose logs backend
    goto :eof
)
goto start_wait_loop

:start_ready
echo Backend is ready.
echo.
echo ============================================================
echo   Services are running.
echo.
echo   Backend health : %BACKEND_URL%/health
echo   API docs       : %BACKEND_DOCS_URL%
echo   OpenAPI JSON   : %BACKEND_URL%/openapi.json
echo ============================================================
start "" "%BACKEND_DOCS_URL%"
goto :eof

REM ============================================================
REM                    HELPER: REMOVE IMAGES
REM ============================================================
:remove_images
echo.
echo Removing project images...

for /f "delims=" %%I in ('
    docker compose -f "%COMPOSE_FILE%" config --images 2^>nul
') do (
    echo   removing %%I
    docker rmi -f "%%I" 2>nul
)

for /f "delims=" %%I in ('
    docker images --format "{{.Repository}}:{{.Tag}}" ^| findstr /I "%IMAGE_PREFIX%"
') do (
    echo   removing %%I
    docker rmi -f "%%I" 2>nul
)

echo Images removed.
goto :eof

REM ============================================================
REM                            END
REM ============================================================
:end_script
exit /B
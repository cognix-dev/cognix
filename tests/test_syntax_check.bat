@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul 2>&1

REM ============================================
REM  Cognix Multi-Language Syntax Check Test
REM  E2E integration test via cognix --make
REM ============================================

echo.
echo ============================================
echo  Cognix Multi-Language Syntax Check Test
echo ============================================
echo.

set "PASS_COUNT=0"
set "FAIL_COUNT=0"
set "SKIP_COUNT=0"
set "LOG_FILE=%USERPROFILE%\.cognix\logs\cognix_debug.log"

REM ── Section 1: cognix availability ──

where cognix >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ENV] cognix:  ^(not installed^)        FAIL
    echo.
    echo ERROR: cognix is not installed. Run: pip install -e .
    exit /b 1
)
for /f "tokens=*" %%v in ('cognix --version 2^>^&1') do set "COGNIX_VER=%%v"
echo [ENV] cognix:  %COGNIX_VER%

REM ── Section 2: Compiler availability ──

set "HAS_GO=0"
set "HAS_JAVA=0"
set "HAS_RUST=0"
set "HAS_RUBY=0"
set "HAS_PHP=0"

go version >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    for /f "tokens=3" %%v in ('go version 2^>^&1') do set "GO_VER=%%v"
    echo [ENV] Go:      !GO_VER!        OK
    set "HAS_GO=1"
) else (
    echo [ENV] Go:      ^(not installed^)        SKIP
)

javac -version >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    for /f "tokens=2" %%v in ('javac -version 2^>^&1') do set "JAVA_VER=%%v"
    echo [ENV] Java:    javac !JAVA_VER!        OK
    set "HAS_JAVA=1"
) else (
    echo [ENV] Java:    ^(not installed^)        SKIP
)

rustc --version >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    for /f "tokens=2" %%v in ('rustc --version 2^>^&1') do set "RUST_VER=%%v"
    echo [ENV] Rust:    rustc !RUST_VER!        OK
    set "HAS_RUST=1"
) else (
    echo [ENV] Rust:    ^(not installed^)        SKIP
)

ruby --version >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    for /f "tokens=2" %%v in ('ruby --version 2^>^&1') do set "RUBY_VER=%%v"
    echo [ENV] Ruby:    ruby !RUBY_VER!        OK
    set "HAS_RUBY=1"
) else (
    echo [ENV] Ruby:    ^(not installed^)        SKIP
)

php --version >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    for /f "tokens=2" %%v in ('php --version 2^>^&1') do set "PHP_VER=%%v"
    echo [ENV] PHP:     php !PHP_VER!        OK
    set "HAS_PHP=1"
) else (
    echo [ENV] PHP:     ^(not installed^)        SKIP
)

echo.

REM ── Section 3: Pre-test temp file snapshot ──

set "PRE_COGNIX_TMP=0"
for /d %%d in (%TEMP%\cognix_*) do set /a PRE_COGNIX_TMP+=1

REM ── Section 4: Clear debug log ──

if exist "%LOG_FILE%" (
    del "%LOG_FILE%" >nul 2>&1
)

REM ── Section 5: Run pipeline tests ──

set "COGNIX_DEBUG=1"

REM Each test runs in its own temp output directory to avoid file conflicts
set "TEST_BASE=%TEMP%\cognix_syntax_test_%RANDOM%"
mkdir "%TEST_BASE%" >nul 2>&1

REM --- Go ---
if %HAS_GO% EQU 1 (
    echo [RUN] Go pipeline test...
    set "TEST_DIR=%TEST_BASE%\go_test"
    mkdir "!TEST_DIR!" >nul 2>&1
    pushd "!TEST_DIR!"
    cognix --make "GoでHello Worldを出力するシンプルなCLIプログラムを作って。ファイル名はmain.go" >nul 2>&1
    popd

    REM Parse log
    findstr /C:"[Syntax Check] Valid Go syntax" "%LOG_FILE%" >nul 2>&1
    if !ERRORLEVEL! EQU 0 (
        echo [LOG] Go syntax check:             PASS ^(Valid Go syntax logged^)
        set /a PASS_COUNT+=1
    ) else (
        findstr /C:"[Syntax Check] Go syntax error" "%LOG_FILE%" >nul 2>&1
        if !ERRORLEVEL! EQU 0 (
            echo [LOG] Go syntax check:             PASS ^(error path^)
            set /a PASS_COUNT+=1
        ) else (
            findstr /C:"[Syntax Check] go not available" "%LOG_FILE%" >nul 2>&1
            if !ERRORLEVEL! EQU 0 (
                echo [LOG] Go syntax check:             SKIP ^(go not available in pipeline^)
                set /a SKIP_COUNT+=1
            ) else (
                echo [LOG] Go syntax check:             FAIL ^(no [Syntax Check] log entry^)
                set /a FAIL_COUNT+=1
            )
        )
    )
) else (
    echo [RUN] Go pipeline test:             SKIP ^(go not installed^)
    set /a SKIP_COUNT+=1
)

REM --- Java ---
if %HAS_JAVA% EQU 1 (
    echo [RUN] Java pipeline test...
    set "TEST_DIR=%TEST_BASE%\java_test"
    mkdir "!TEST_DIR!" >nul 2>&1
    pushd "!TEST_DIR!"
    cognix --make "JavaでFizzBuzzクラスを作って" >nul 2>&1
    popd

    findstr /C:"[Syntax Check] Valid syntax" "%LOG_FILE%" >nul 2>&1
    if !ERRORLEVEL! EQU 0 (
        echo [LOG] Java syntax check:            PASS ^(Valid syntax logged^)
        set /a PASS_COUNT+=1
    ) else (
        findstr /C:"[Syntax Check] Syntax error" "%LOG_FILE%" >nul 2>&1
        if !ERRORLEVEL! EQU 0 (
            echo [LOG] Java syntax check:            PASS ^(error path^)
            set /a PASS_COUNT+=1
        ) else (
            findstr /C:"[Syntax Check] javac not available" "%LOG_FILE%" >nul 2>&1
            if !ERRORLEVEL! EQU 0 (
                echo [LOG] Java syntax check:            SKIP ^(javac not available in pipeline^)
                set /a SKIP_COUNT+=1
            ) else (
                echo [LOG] Java syntax check:            FAIL ^(no [Syntax Check] log entry^)
                set /a FAIL_COUNT+=1
            )
        )
    )
) else (
    echo [RUN] Java pipeline test:            SKIP ^(javac not installed^)
    set /a SKIP_COUNT+=1
)

REM --- Rust ---
if %HAS_RUST% EQU 1 (
    echo [RUN] Rust pipeline test...
    set "TEST_DIR=%TEST_BASE%\rust_test"
    mkdir "!TEST_DIR!" >nul 2>&1
    pushd "!TEST_DIR!"
    cognix --make "RustでHello Worldを出力するプログラムを作って" >nul 2>&1
    popd

    findstr /C:"[Syntax Check] Valid Rust syntax" "%LOG_FILE%" >nul 2>&1
    if !ERRORLEVEL! EQU 0 (
        echo [LOG] Rust syntax check:            PASS ^(Valid Rust syntax logged^)
        set /a PASS_COUNT+=1
    ) else (
        findstr /C:"[Syntax Check] Rust syntax error" "%LOG_FILE%" >nul 2>&1
        if !ERRORLEVEL! EQU 0 (
            echo [LOG] Rust syntax check:            PASS ^(error path^)
            set /a PASS_COUNT+=1
        ) else (
            findstr /C:"[Syntax Check] rustc not available" "%LOG_FILE%" >nul 2>&1
            if !ERRORLEVEL! EQU 0 (
                echo [LOG] Rust syntax check:            SKIP ^(rustc not available in pipeline^)
                set /a SKIP_COUNT+=1
            ) else (
                echo [LOG] Rust syntax check:            FAIL ^(no [Syntax Check] log entry^)
                set /a FAIL_COUNT+=1
            )
        )
    )
) else (
    echo [RUN] Rust pipeline test:            SKIP ^(rustc not installed^)
    set /a SKIP_COUNT+=1
)

REM --- Ruby ---
if %HAS_RUBY% EQU 1 (
    echo [RUN] Ruby pipeline test...
    set "TEST_DIR=%TEST_BASE%\ruby_test"
    mkdir "!TEST_DIR!" >nul 2>&1
    pushd "!TEST_DIR!"
    cognix --make "Rubyで簡単な挨拶スクリプトを作って" >nul 2>&1
    popd

    findstr /C:"[Syntax Check] Valid syntax" "%LOG_FILE%" >nul 2>&1
    if !ERRORLEVEL! EQU 0 (
        echo [LOG] Ruby syntax check:            PASS ^(Valid syntax logged^)
        set /a PASS_COUNT+=1
    ) else (
        findstr /C:"[Syntax Check] Syntax error" "%LOG_FILE%" >nul 2>&1
        if !ERRORLEVEL! EQU 0 (
            echo [LOG] Ruby syntax check:            PASS ^(error path^)
            set /a PASS_COUNT+=1
        ) else (
            findstr /C:"[Syntax Check] ruby not available" "%LOG_FILE%" >nul 2>&1
            if !ERRORLEVEL! EQU 0 (
                echo [LOG] Ruby syntax check:            SKIP ^(ruby not available in pipeline^)
                set /a SKIP_COUNT+=1
            ) else (
                echo [LOG] Ruby syntax check:            FAIL ^(no [Syntax Check] log entry^)
                set /a FAIL_COUNT+=1
            )
        )
    )
) else (
    echo [RUN] Ruby pipeline test:            SKIP ^(ruby not installed^)
    set /a SKIP_COUNT+=1
)

REM --- PHP ---
if %HAS_PHP% EQU 1 (
    echo [RUN] PHP pipeline test...
    set "TEST_DIR=%TEST_BASE%\php_test"
    mkdir "!TEST_DIR!" >nul 2>&1
    pushd "!TEST_DIR!"
    cognix --make "PHPでHello Worldを出力するスクリプトを作って" >nul 2>&1
    popd

    findstr /C:"[Syntax Check] Valid syntax" "%LOG_FILE%" >nul 2>&1
    if !ERRORLEVEL! EQU 0 (
        echo [LOG] PHP syntax check:             PASS ^(Valid syntax logged^)
        set /a PASS_COUNT+=1
    ) else (
        findstr /C:"[Syntax Check] Syntax error" "%LOG_FILE%" >nul 2>&1
        if !ERRORLEVEL! EQU 0 (
            echo [LOG] PHP syntax check:             PASS ^(error path^)
            set /a PASS_COUNT+=1
        ) else (
            findstr /C:"[Syntax Check] php not available" "%LOG_FILE%" >nul 2>&1
            if !ERRORLEVEL! EQU 0 (
                echo [LOG] PHP syntax check:             SKIP ^(php not available in pipeline^)
                set /a SKIP_COUNT+=1
            ) else (
                echo [LOG] PHP syntax check:             FAIL ^(no [Syntax Check] log entry^)
                set /a FAIL_COUNT+=1
            )
        )
    )
) else (
    echo [RUN] PHP pipeline test:             SKIP ^(php not installed^)
    set /a SKIP_COUNT+=1
)

echo.

REM ── Section 6: Post-test temp file check ──

set "POST_COGNIX_TMP=0"
for /d %%d in (%TEMP%\cognix_*) do set /a POST_COGNIX_TMP+=1

if !POST_COGNIX_TMP! LEQ !PRE_COGNIX_TMP! (
    echo [CLEANUP] Temp cognix_* items:       PASS ^(no leftovers^)
    set /a PASS_COUNT+=1
) else (
    set /a DELTA=!POST_COGNIX_TMP! - !PRE_COGNIX_TMP!
    echo [CLEANUP] Temp cognix_* items:       FAIL ^(!DELTA! new item^(s^) remain^)
    set /a FAIL_COUNT+=1
)

REM Clean up test output directories
if exist "%TEST_BASE%" (
    rmdir /s /q "%TEST_BASE%" >nul 2>&1
)

REM ── Section 7: Summary ──

echo.
echo ============================================

set /a TOTAL=!PASS_COUNT! + !FAIL_COUNT! + !SKIP_COUNT!

if !FAIL_COUNT! EQU 0 (
    echo  Results: %PASS_COUNT% PASS, %FAIL_COUNT% FAIL, %SKIP_COUNT% SKIP
) else (
    echo  Results: %PASS_COUNT% PASS, %FAIL_COUNT% FAIL, %SKIP_COUNT% SKIP  [SOME TESTS FAILED]
)

echo ============================================
echo.

if !FAIL_COUNT! GTR 0 (
    exit /b 1
) else (
    exit /b 0
)

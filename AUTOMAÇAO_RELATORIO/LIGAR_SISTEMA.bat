::[Bat To Exe Converter]
::
::YAwzoRdxOk+EWAjk
::fBw5plQjdCyDJGyX8VAjFBFbTQu+GGStCLkT6ezo08mGslkIRuN/fIqbzrGCIaBBuheyOMZ6mygI2JpcXEkKLFyibQBU
::YAwzuBVtJxjWCl3EqQJgSA==
::ZR4luwNxJguZRRnk
::Yhs/ulQjdF+5
::cxAkpRVqdFKZSjk=
::cBs/ulQjdF+5
::ZR41oxFsdFKZSDk=
::eBoioBt6dFKZSDk=
::cRo6pxp7LAbNWATEpCI=
::egkzugNsPRvcWATEpCI=
::dAsiuh18IRvcCxnZtBJQ
::cRYluBh/LU+EWAnk
::YxY4rhs+aU+JeA==
::cxY6rQJ7JhzQF1fEqQJQ
::ZQ05rAF9IBncCkqN+0xwdVs0
::ZQ05rAF9IAHYFVzEqQJQ
::eg0/rx1wNQPfEVWB+kM9LVsJDGQ=
::fBEirQZwNQPfEVWB+kM9LVsJDGQ=
::cRolqwZ3JBvQF1fEqQJQ
::dhA7uBVwLU+EWDk=
::YQ03rBFzNR3SWATElA==
::dhAmsQZ3MwfNWATElA==
::ZQ0/vhVqMQ3MEVWAtB9wSA==
::Zg8zqx1/OA3MEVWAtB9wSA==
::dhA7pRFwIByZRRnk
::Zh4grVQjdCyDJHaox34cATx1fkSxFViOI5g9uab+9+/n
::YB416Ek+ZW8=
::
::
::978f952a14a936cc963da21a135fa983
@echo off
chcp 65001 >nul
color 0b

:: 1. Pega a raiz de onde o .exe está e entra na pasta oculta
cd /d "%~dp0GERADOR_RELATORIOS_OLS"

echo =======================================================
echo       SISTEMA OLS OFFSHORE - INICIANDO MOTOR...
echo =======================================================
echo.
echo Liberando a porta 8501 no Firewall do Windows...

netsh advfirewall firewall add rule name="Sistema OLS - Acesso Celular" dir=in action=allow protocol=TCP localport=8501 >nul 2>&1

:: Verifica permissão
if %errorlevel% neq 0 (
    echo [AVISO] Sem permissao de Admin. A regra do Firewall nao foi criada.
    echo Se o celular der erro de conexao, feche esta janela, clique com o 
    echo botao direito no arquivo .exe e escolha "Executar como Administrador".
) else (
    echo [SUCESSO] Porta 8501 liberada para acesso na rede local!
)

echo.
echo Descobrindo o IP da maquina para acesso via celular...
for /f "tokens=2 delims=:" %%A in ('ipconfig ^| findstr /i "IPv4"') do set IP=%%A
set IP=%IP: =%

echo.
echo =======================================================
echo  ACESSO NO CELULAR (TELA DE ASSINATURA):
echo  Abra o navegador no celular e digite EXATAMENTE:
echo  http://%IP%:8501
echo =======================================================
echo.
echo Iniciando o servidor offline... (Nao feche esta tela!)
echo.

:: 2. Como já estamos dentro da pasta oculta, chamamos o motor diretamente
set PYTHON_EXE="motor_offline\WPy64-313130\python\python.exe"

:: 3. Roda o sistema
%PYTHON_EXE% -m streamlit run app_web.py --server.address=0.0.0.0 --server.port=8501

pause
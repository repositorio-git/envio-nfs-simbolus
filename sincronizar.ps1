# Copia o projeto desta máquina para a máquina do robô, pela rede.
# Uso: powershell -ExecutionPolicy Bypass -File .\sincronizar.ps1

$origem  = $PSScriptRoot
$destino = "\\SRVRPA_CLONE\c$\Users\cortexrpa.MATRIZ\Desktop\envioNFsSimbolus"

# Pastas ignoradas pelo NOME, em qualquer nível da árvore.
$ignorarPastas = @(
    ".venv",
    ".git",
    ".claude",
    ".vscode",
    "__pycache__",
    "logs",        # logs/erros/notificacoes_enviadas.json do destino são do destino
    "DOCS"
)

# Arquivos ignorados (aceita curinga).
$ignorarArquivos = @(
    "*.pyc",
    ".env",        # credenciais de cada máquina ficam só nela
    ".gitignore",
    "sincronizar.ps1"
)

# /E: inclui subpastas. Sem /MIR de propósito -- /MIR APAGA no destino tudo
# que não existe na origem, incluindo .venv, .env e logs de lá.
robocopy $origem $destino /E /XD $ignorarPastas /XF $ignorarArquivos /R:1 /W:1 /NP

# robocopy devolve 0-7 em sucesso (bitmask de "o que copiou"); 8+ é falha.
if ($LASTEXITCODE -ge 8) {
    Write-Host "Falha na cópia (código $LASTEXITCODE)" -ForegroundColor Red
    exit 1
}
Write-Host "Sincronizado (código $LASTEXITCODE)" -ForegroundColor Green
pause
exit 0

Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

try
{
    $activation = Join-Path -Path './.venv' -ChildPath 'Scripts/Activate.ps1' -Resolve -ErrorAction Stop
    Invoke-Expression -Command $activation
}
catch [System.Management.Automation.ItemNotFoundException]
{
    Write-Warning 'Virtual environment not detected. Beginning creation process.'
    $python = Get-Command -Name 'py'
    Start-Process 'py.exe' -ArgumentList '-m', 'venv', '.venv' -Wait
    Write-Warning 'A virtual environment has been created for you. This script must be re-run to continue.'
    
    Write-Host -NoNewLine 'Press any key to continue...';
    $null = $Host.UI.RawUI.ReadKey('NoEcho,IncludeKeyDown');
    return
}

try
{
    $python = Join-Path -Path $env:VIRTUAL_ENV -ChildPath 'Scripts/python.exe' -Resolve -ErrorAction Stop
    
    Write-Output 'Installing dependencies...'
    $requirements = Resolve-Path -Path '.\requirements.txt'
    Start-Process -FilePath $python -ArgumentList '-m', 'pip', 'install', '-r', $requirements -Wait

    Write-Output 'Starting application...'
    Start-Process -FilePath $python -ArgumentList '-m', 'bot'
    
    Write-Output 'Cleaning up...'
    Invoke-Expression -Command 'deactivate'
}
catch [System.Management.Automation.ItemNotFoundException]
{
    Write-Error $PSItem.Exception.Message

    Write-Host -NoNewLine 'Press any key to continue...';
    $null = $Host.UI.RawUI.ReadKey('NoEcho,IncludeKeyDown');
    return
}
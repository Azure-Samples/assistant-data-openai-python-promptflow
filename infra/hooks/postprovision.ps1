Write-Host "Copy .env file from ./.azure/$Env:AZURE_ENV_NAME/.env to root"
Copy-Item -Path ./.azure/$Env:AZURE_ENV_NAME/.env -Destination ./.env -Force
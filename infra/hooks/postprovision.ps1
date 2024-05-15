Write-Host "Copy .env file from ./.azure/$Env:AZURE_ENV_NAME/.env to root"
Copy-Item -Path ./.azure/$Env:AZURE_ENV_NAME/.env -Destination ./.env -Force


Write-Host "Installing dependencies from 'src/requirements.txt'"
python -m pip install -r ./src/requirements.txt

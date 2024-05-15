Write-Host "Copy .env file from ./.azure/$Env:AZURE_ENV_NAME/.env to root"
Copy-Item -Path ./.azure/$Env:AZURE_ENV_NAME/.env -Destination ./.env -Force

Write-Host "Create an assistant and add its identifier as env var in ./.env"
python ./src/create_assistant.py --export-env ./.env

Write-Host "Running python script to deploy the code into the endpoint"
python ./src/deploy.py

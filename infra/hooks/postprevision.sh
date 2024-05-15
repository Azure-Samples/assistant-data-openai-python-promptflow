echo "Copy .env file from ./.azure/$AZURE_ENV_NAME/.env to root"
cp ./.azure/$AZURE_ENV_NAME/.env ./.env

echo "Script execution completed successfully."

echo "Installing dependencies from 'src/requirements.txt'"
python -m pip install -r ./src/requirements.txt

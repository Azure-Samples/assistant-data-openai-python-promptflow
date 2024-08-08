echo "Copy .env file from ./.azure/$AZURE_ENV_NAME/.env to root"
cp ./.azure/$AZURE_ENV_NAME/.env ./.env

echo "Installing dependencies from 'src/requirements.txt'"
python -m pip install -r ./src/requirements.txt

echo "Create an assistant and add its identifier as env var in ./.env"
python ./src/create_assistant.py --export-env ./.env

echo "Script execution completed successfully."

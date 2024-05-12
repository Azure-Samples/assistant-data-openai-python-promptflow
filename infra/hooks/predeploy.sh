echo "Copy .env file from ./.azure/$AZURE_ENV_NAME/.env to root"
cp ./.azure/$AZURE_ENV_NAME/.env ./.env

echo "Create an assistant and add to env ./.env"
python ./src/create_assistant.py --export ./.env

echo "Running python script"
python ./src/deploy.py
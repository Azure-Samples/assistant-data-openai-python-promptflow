echo "Copy .env file from ./.azure/$AZURE_ENV_NAME/.env to root"
cp ./.azure/$AZURE_ENV_NAME/.env ./.env

echo "Create an assistant and add its identifier as env var in ./.env"
python ./src/create_assistant.py --export-env ./.env

echo "Running python script to deploy the code into the endpoint"
python ./src/deploy.py

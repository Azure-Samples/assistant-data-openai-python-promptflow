using './main.bicep'

param environmentName = readEnvironmentVariable('AZURE_ENV_NAME', 'MY_ENV')
param resourceGroupName = readEnvironmentVariable('AZURE_RESOURCE_GROUP', '')
param location = readEnvironmentVariable('AZURE_LOCATION', 'eastus2')
param principalId = readEnvironmentVariable('AZURE_PRINCIPAL_ID', '')

param aiHubName = readEnvironmentVariable('AZUREAI_HUB_NAME', '')
param aiProjectName = readEnvironmentVariable('AZUREAI_PROJECT_NAME', '')
param endpointName = readEnvironmentVariable('AZUREAI_ENDPOINT_NAME', '')

param openAiName = readEnvironmentVariable('AZURE_OPENAI_NAME', '')
param openAiChatDeploymentName = readEnvironmentVariable('AZURE_OPENAI_CHAT_DEPLOYMENT', 'gpt-35-turbo-1106')
param openAiChatDeploymentVersion = readEnvironmentVariable('AZURE_OPENAI_CHAT_DEPLOYMENT_VERSION', '1106')
param openAiEvaluationDeploymentName = readEnvironmentVariable('AZURE_OPENAI_EVALUATION_DEPLOYMENT', 'gpt-35-turbo-0301')
param openAiEvaluationDeploymentVersion = readEnvironmentVariable('AZURE_OPENAI_EVALUATION_DEPLOYMENT_VERSION', '0301')

param appInsightsName = readEnvironmentVariable('AZURE_APP_INSIGHTS_NAME', '')
param containerRegistryName = readEnvironmentVariable('AZURE_CONTAINER_REGISTRY_NAME', '')
param keyVaultName = readEnvironmentVariable('AZURE_KEYVAULT_NAME', '')
param storageAccountName = readEnvironmentVariable('AZURE_STORAGE_ACCOUNT_NAME', '')
param logAnalyticsWorkspaceName = readEnvironmentVariable('AZURE_LOG_ANALYTICS_WORKSPACE_NAME', '')

param useContainerRegistry = bool(readEnvironmentVariable('USE_CONTAINER_REGISTRY', 'true'))
param useAppInsights = bool(readEnvironmentVariable('USE_APP_INSIGHTS', 'true'))

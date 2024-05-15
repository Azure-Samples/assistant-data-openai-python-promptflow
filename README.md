# Assistant for sales data analytics in python and promptflow

This repository implements a data analytics chatbot based on the Assistants API.
The chatbot can answer questions in natural language, and interpret them as queries
on an example sales dataset.

## Features

* An implementation of the Assistants API using functions and code interpreter
* Deployment available via GitHub actions or Azure AI SDK
* An agent performing data analytics to answer questions in natural language


### Architecture Diagram

![Architecture Diagram](images/architecture-diagram-assistant-promptflow.png)


## Getting Started

### Prerequisites

- Install [azd](https://aka.ms/install-azd)
    - Windows: `winget install microsoft.azd`
    - Linux: `curl -fsSL https://aka.ms/install-azd.sh | bash`
    - MacOS: `brew tap azure/azd && brew install azd`
- An Azure subscription - [Create one for free](https://azure.microsoft.com/free/cognitive-services)
- Access granted to Azure OpenAI in the desired Azure subscription  
  Currently, access to this service is granted only by application. You can apply for access to Azure OpenAI by completing the form at [aka.ms/oai/access](https://aka.ms/oai/access).
- Python 3.10 or later version

Note: This model uses gpt-35-turbo or gpt-4 for assistants which may not be available in all Azure regions. Check for [up-to-date region availability](https://learn.microsoft.com/azure/ai-services/openai/concepts/models#standard-deployment-model-availability) and select a region during deployment accordingly.

### Installation

1. First, clone the code sample locally:

    ```bash
    git clone https://github.com/Azure-Samples/assistant-data-openai-python-promptflow
    cd assistant-data-openai-python-promptflow
    ```

2. Next, create a new Python virtual environment where we can safely install the SDK packages:

 * On MacOS and Linux run:
   ```bash
   python3 --version
   python3 -m venv .venv
   source .venv/bin/activate
   ```

* On Windows run:
   ```ps
   py -3 --version
   py -3 -m venv .venv
   .venv\scripts\activate
   ```

3. Now that your environment is activated, install the SDK packages

    ```bash
    pip install -r requirements.txt
    ```

## Quickstart

## Step 1 : Provision the resources
### Authenticate with Azure
Start the authentication flow from a terminal:
```bash
azd auth login
```
This should activate a Device Code authentication flow as shown below. Just follow the instructions and complete the auth flow until you get the ```Logged in on Azure``` message indicating success.

Provision Azure resources
```bash
azd provision
```
*When selecting your Azure location (region) we suggest Sweden Central* 
Once you complete the process, you can find `.env` file under .azure\{env} folder. Your `.env` file should look like this:

```
AZURE_SUBSCRIPTION_ID=...
AZURE_RESOURCE_GROUP=...
AZURE_AI_HUB_NAME=...
AZURE_AI_PROJET_NAME=...
AZURE_OPENAI_ENDPOINT=...
AZURE_OPENAI_CHAT_DEPLOYMENT=...
```

### Step 2. Create an assistant

For the code to run, you need to create an assistant. This means setting up an assistant in your Azure OpenAI resource.
You will get an assistant id you can inject in the code through an env var to run the assistant.

```bash
python ./src/create_assistant.py --export-env ./.azure/"$AZURE_ENV_NAME"/.env
```

It will write the assistant id into your `.env` file:

```
******************************************************************
Successfully created assistant with id: [IDENTIFIER].
It has been written as an environment variable in .\.azure\[ENVIRONMENT]\.env.

AZURE_OPENAI_ASSISTANT_ID=[IDENTIFIER]

******************************************************************
```

### Step 3. Deploy

work in progress

## Costs
You can estimate the cost of this project's architecture with [Azure's pricing calculator](https://azure.microsoft.com/pricing/calculator/)

- Azure OpenAI - Standard tier, GPT-4, GPT-35-turbo and Ada models.  [See Pricing](https://azure.microsoft.com/pricing/details/cognitive-services/openai-service/)
- Azure AI Search - Basic tier, Semantic Ranker enabled [See Pricing](https://azure.microsoft.com/en-us/pricing/details/search/)

## Security Guidelines

Each template has either [Managed Identity](https://learn.microsoft.com/en-us/entra/identity/managed-identities-azure-resources/overview) or Key Vault built in to eliminate the need for developers to manage these credentials. Applications can use managed identities to obtain Microsoft Entra tokens without having to manage any credentials. Additionally, we have added a [GitHub Action tool](https://github.com/microsoft/security-devops-action) that scans the infrastructure-as-code files and generates a report containing any detected issues. To ensure best practices in your repo we recommend anyone creating solutions based on our templates ensure that the [Github secret scanning](https://docs.github.com/en/code-security/secret-scanning/about-secret-scanning) setting is enabled in your repos.

To be secure by design, we require templates in any Microsoft template collections to have the [Github secret scanning](https://docs.github.com/en/code-security/secret-scanning/about-secret-scanning) setting is enabled in your repos.'

## Resources
- [Develop Python apps that use Azure AI services](https://learn.microsoft.com/azure/developer/python/azure-ai-for-python-developers)
- Discover more sample apps in the [azd template gallery](https://aka.ms/ai-apps)!

# Assistant for sales data analytics in python and promptflow

This repository implements a data analytics chatbot based on the Assistants API.
The chatbot can answer questions in natural language, and interpret them as queries
on an example sales dataset.

## Features

**For Developers**
* An implementation of the Assistants API using functions and code interpreter
* Deployment available via GitHub actions or Azure AI SDK
* ...

**For Users**
* An agent performing data analytics to answer questions in natural language


### Architecture Diagram

Include a diagram describing the application (DevDiv is working with Designers on this part)

## Security

(Document security aspects and best practices per template configuration)

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

### Quickstart

### Step 1 : Provision the resources

Run the following command under root folder of repo. Please install azd if it's not be installed.
```bash
azd up
```

Once you complete the process, you can find `.env` file under .azure\{env} folder. Your `.env` file should look like this:

```
AZURE_SUBSCRIPTION_ID=...
AZURE_RESOURCE_GROUP=...
AZURE_AI_HUB_NAME=...
AZURE_AI_PROJET_NAME=...
AZURE_OPENAI_ENDPOINT=...
AZURE_OPENAI_CHAT_DEPLOYMENT=...
```

Those environment variables will be required for the following steps to work. You can copy it to the root folder.

To leverage Microsoft Entra ID (AAD) authentification, you'll need to assign to yourself
the role "Cognitive Services User" to the Azure OpenAI Instance:

1. Find your `OBJECT_ID`:

    ```bash
    az ad signed-in-user show --query id -o tsv
    ```

2. Then run the following command to grand permissions:

    ```bash
    az role assignment create \
            --role "f2dc8367-1007-4938-bd23-fe263f013447" \
            --assignee-object-id "$OBJECT_ID" \
            --scope /subscriptions/"$AZURE_SUBSCRIPTION_ID"/resourceGroups/"$AZURE_RESOURCE_GROUP"/ \
            --assignee-principal-type User
    ```

Alternatively, you can set env var `AZURE_OPENAI_API_KEY` with your api key.

#### Step 2. Create an assistant

For the code to run, you need to create an assistant. This means setting up an assistant in your Azure OpenAI resource.
You will get an assistant id you can inject in the code through an env var to run the assistant.

```bash
python ./src/create_assistant.py
```

It will print the env var to add to `.env`:

```
******************************************************************
Successfully created assistant with id: [IDENTIFIER].
Create an environment variable

    AZURE_OPENAI_ASSISTANT_ID=[IDENTIFIER]

to use this assistant in your code. Or write it in your .env file.
******************************************************************
```

#### Step 3. Run the assistant flow locally

To run the flow locally, use `pf` cli:

```bash
pf flow test --flow ./src/copilot_sdk_flow/flow.flex.yaml --inputs question="which month has peak sales in 2023"
```

You can add `--ui` to run the local test bed.

### Step 4. Run an evaluation locally

The evaluation script consists in running the completion function on a groundtruth dataset and evaluate the results.

```bash
python ./src/evaluate.py --evaluation-name assistant-dev --evaluation-data-path ./data/ground_truth.jsonl --metrics similarity
```

This will print out the results of the evaluation, as well as a link to the Azure AI Studio to browse the results online.

### Step 5. Deploy the flow in Azure AI Studio

To deploy the flow in your Azure AI project under a managed endpoint, use:

```bash
python ./src/deploy.py
```

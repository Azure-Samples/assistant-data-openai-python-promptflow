# Assistant for sales data analytics in python and promptflow

This repository implements a data analytics chatbot based on the Assistants API.
The chatbot can answer questions in natural language, and interpret them as queries
on an example sales dataset.

This document explains how to provision, evaluate and deploy using the Azure AI SDK.
For instructions on how to use azd instead, please refer to [the repository README](../README.md) instead.

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

1. First, clone the code sample locally and enter into the `src/` subdirectory:

    ```bash
    git clone https://github.com/Azure-Samples/assistant-data-openai-python-promptflow
    cd assistant-data-openai-python-promptflow/src/
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

### Before your start: check your quota

To ensure you have quota to provision `gpt-35-turbo` version `1106`, you can either go to [oai.azure.com](https://oai.azure.com/) and check the Quota page in a given region.

You can also try running our experimental script to check quota in your subscription:

```bash
python ./check_quota.py --subscription-id [SUBSCRIPTION_ID]
```

> Note: this script is a tentative to help locating quota, but it might provide numbers that are not accurate. The [Azure OpenAI portal](https://oai.azure.com/) would be the source of truth.

It will show a table of the regions where you have `gpt-35-turbo` available.

```
+--------------+---------+--------+---------------+----------+-------+-----------------+
|    model     | version |  kind  |   location    |   sku    | quota | remaining_quota |
+--------------+---------+--------+---------------+----------+-------+-----------------+
| gpt-35-turbo |  1106   | OpenAI | australiaeast | Standard |  300  |       270       |
| gpt-35-turbo |  1106   | OpenAI | francecentral | Standard |  240  |        0        |
| gpt-35-turbo |  1106   | OpenAI | swedencentral | Standard |  300  |       150       |
| gpt-35-turbo |  1106   | OpenAI |    uksouth    | Standard |  240  |       180       |
+--------------+---------+--------+---------------+----------+-------+-----------------+
```

Pick any region with remaining_quota above 30.

### Step 1 : Provision the resources

The provision.py script will help provision the resources you need to run this sample. You **must** specify your desired resources in the provision.yaml - there are notes in that file to help you. The script will check whether the resources you specified exist, otherwise it will create them. It will then construct a `.env` for you that references the provisioned or attached resources, including your keys. Once the provisioning is complete, you'll be ready to move to next step.

```
python provision.py
```

Once you complete the process, you can find `.env` file under the `src/` folder. Your `.env` file should look like this:

```
AZURE_SUBSCRIPTION_ID=...
AZURE_RESOURCE_GROUP=...
AZURE_AI_HUB_NAME=...
AZURE_AI_PROJET_NAME=...
AZURE_OPENAI_ENDPOINT=...
AZURE_OPENAI_CHAT_DEPLOYMENT=...
```

Those environment variables will be required for the following steps to work.

To leverage Microsoft Entra ID (AAD) authentification, you'll need to assign to yourself the role "Cognitive Services OpenAI User" to the Azure OpenAI Instance:

1. Find your `OBJECT_ID`:

    ```bash
    az ad signed-in-user show --query id -o tsv
    ```

2. Then run the following command to grand permissions:

    ```bash
    az role assignment create \
            --role "5e0bd9bd-7b93-4f28-af87-19fc36ad61bd" \
            --assignee-object-id "$OBJECT_ID" \
            --scope /subscriptions/"$AZURE_SUBSCRIPTION_ID"/resourceGroups/"$AZURE_RESOURCE_GROUP" \
            --assignee-principal-type User
    ```

Alternatively, you can set env var `AZURE_OPENAI_API_KEY` with your api key.

#### Step 2. Create an assistant

For the code to run, you need to create an assistant. This means setting up an assistant in your Azure OpenAI resource.
You will get an assistant id you can inject in the code through an env var to run the assistant.

```bash
python create_assistant.py
```

It will write the assistant id into your `.env` file:

```
******************************************************************
Successfully created assistant with id: [IDENTIFIER].
It has been written as an environment variable in ./.env.

AZURE_OPENAI_ASSISTANT_ID=[IDENTIFIER]

******************************************************************
```

#### Step 3. Run the assistant flow locally

To run the flow locally, use `pf` cli:

```bash
pf flow test --flow ./copilot_sdk_flow/flow.flex.yaml --inputs chat_input="which month has peak sales in 2023"
```

You can add `--ui` to run the local test bed.

### Step 4. Run an evaluation locally

The evaluation script consists in running the completion function on a groundtruth dataset and evaluate the results.

```bash
python evaluate.py --evaluation-name assistant-dev --evaluation-data-path ./data/ground_truth.jsonl --metrics similarity
```

This will print out the results of the evaluation, as well as a link to the Azure AI Studio to browse the results online.

### Step 5. Deploy the flow in Azure AI Studio

To deploy the flow in your Azure AI project under a managed endpoint, use:

```bash
python deploy.py
```

# Assistant for sales data analytics in python and promptflow

This repository implements a data analytics chatbot based on the Assistants API.
The chatbot can answer questions in natural language, and interpret them as queries
on an example sales dataset.


## Getting Started

### Prerequisites

In order to benefit from this sample, you need to:
- have an Azure account with an active subscription,
- have Azure OpenAI enabled in that subscription.

### Installation

To install python requirements:

```bash
pip install -r ./requirements.txt
```

### 1. Provision your Azure AI project

1. Edit file `./src/provision.yaml` to align with your settings:

    ```yaml
    ai:
        # use references to an existing AI Hub+Project resource to connect it to your hub
        # or else provision.py will create a resource with those references
        subscription_id: "your-subscription-id"
        resource_group_name: "your_resource_group"
        hub_name: "hub_name"
        project_name: "project_name"
        region: "eastus"

    search:
        # use references to an existing Search resource to connect it to your hub
        # or else provision.py will create a resource with those references
        subscription_id: "your-subscription-id"
        resource_group_name: "your_resource_group"
        search_resource_name: "search_name"
        region: "eastus"

        # specify the name of the existing/creating hub connection for this resource
        connection_name: "AzureAISearch"

    aoai:
        # use references to an existing AOAI resource to connect it to your hub
        # or else provision.py will create a resource with those references
        subscription_id: "your-subscription-id"
        resource_group_name: "your_resource_group"
        aoai_resource_name: "my-new-aoai"
        region: "eastus"

        # specify the name of the existing/creating hub connection for this resource
        connection_name: "AzureOpenAI"

        # specify deployments existing/creating
        deployments:
            - name: "gpt-35-turbo"
            model: "gpt-35-turbo"
            - name: "text-embedding-ada-002"
            model: "text-embedding-ada-002"

    environment:
        # below will be used for --export-env argument
        variables:
            # those env vars are drawn from the AI hub connections
            AZURE_OPENAI_ENDPOINT: "azureml://connections/AzureOpenAI/target"
            AZURE_OPENAI_API_KEY: "azureml://connections/AzureOpenAI/credentials/key"
            AZURE_AI_SEARCH_ENDPOINT: "azureml://connections/AzureAISearch/target"
            AZURE_AI_SEARCH_KEY: "azureml://connections/AzureAISearch/credentials/key"
            # those are just constants
            AZURE_OPENAI_CHAT_DEPLOYMENT: "gpt-35-turbo"
    ```

2. Use the provisioning script to create resources:

    ```bash
    python ./src/provision.py --config ./src/provision.yaml --provision --export-env ./.env
    ```

    `--build` will actually provision the resources (if you omit, it will show you what it **would** provision)
    `--export-env` will export the endpoint/keys into your `.env` file

### 2. Create an assistant

For the code to run, you need to create an assistant. This means setting up an assistant in your Azure OpenAI resource.
You will get an assistant id you can inject in the code through an env var to run the assistant.

```bash
python ./src/create_assistant.py
```

It will give you the env var to add to `.env` (`AZURE_OPENAI_ASSISTANT_ID=...`).

### 3. Run the assistant locally

> Optional: to export traces in your Azure AI Studio, set the config accordingly:
> ```bash
> pf config set trace.destination="azureml:/subscriptions/<your_subscription_id>/resourceGroups/<your_resource_group>/providers/Microsoft.MachineLearningServices/workspaces/<your_project_name>"
> ```

To run the flow locally, use `pf` cli:

```bash
pf flow test --flow ./src/copilot_sdk_flow/flow.flex.yaml --inputs question="which month has peak sales in 2023"
```

### 4. Run an evaluation locally

Before running the evaluation, create predictions on the evaluation dataset:

```bash
python ./src/predict.py --input-data-path ./data/evaluation.jsonl --output-data-path ./data/predictions.jsonl
```

**WORK IN PROGRESS** - Then you can run the evaluation on the results :

```bash
python ./src/evaluate.py --predictions ./data/results.jsonl --evaluation-name dev001 --metrics similarity
```

### 5. Deploy the flow in Azure AI Studio

**WORK IN PROGRESS**

1. Use the deployment script to deploy your application to Azure AI Studio. This will deploy your app to a managed endpoint in Azure, that you can test, integrate into a front end application, or share with others.

    ```bash
    python deploy.py --flow-path ./src/copilot_sdk_flow/flow.flex.yaml --deployment-name <deployment_name> --endpoint-name <endpoint_name>
    ```

2. Verify your deployment. We recommend you follow the deployment link from the previous step to the test your application in the cloud. If you prefer to test your endpoint locally, you can invoke it.

    ```bash
    python invoke.py --deployment-name <deployment_name>
    ```

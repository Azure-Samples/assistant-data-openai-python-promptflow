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
        subscription_id: "<your-subscription-id>"
        resource_group_name: "<your_resource_group>"
        hub_name: "<hub_name>"
        project_name: "<project_name>"
        region: "eastus"

    search:
        subscription_id: "<your-subscription-id>"
        resource_group_name: "<your_resource_group>"
        search_resource_name: "<search_resource_name>"
        region: "eastus"

    aoai:
        subscription_id: "<your-subscription-id>"
        resource_group_name: "<your_resource_group>"
        aoai_resource_name: "<aoai_resource_name>"
        region: "eastus"
        deployments:
            - name: "gpt-35-turbo"
            model: "gpt-3.5-turbo"
            - name: "text-embedding-ada-002"
            model: "text-embedding-ada-002"

    environment:
        variables:
            AZURE_OPENAI_ENDPOINT: "azureml://connections/my-new-aoai/target",
            AZURE_OPENAI_API_KEY: "azureml://connections/my-new-aoai/credentials/key",
            AZURE_AI_SEARCH_ENDPOINT: "azureml://connections/search_name/target",
            AZURE_AI_SEARCH_KEY: "azureml://connections/search_name/credentials/key",
    ```

2. Use the provisioning script to create resources:

    ```bash
    python ./src/provision.py --config ./src/provision.yaml --build --export_env ./.env
    ```

    `--build` will actually provision the resources (if you omit, it will show you what it **would** provision)
    `--export_env` will export the endpoint/keys into your `.env` file

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

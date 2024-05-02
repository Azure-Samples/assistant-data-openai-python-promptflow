# enable type annotation syntax on Python versions earlier than 3.9
from __future__ import annotations
import asyncio
from functools import partial
import json
import pathlib
import argparse
import logging
import sys

# set environment variables before importing any other code (in particular the openai module)
from dotenv import load_dotenv
import pandas as pd

load_dotenv()

import os
from pprint import pprint

from promptflow.evals.evaluate import evaluate
from promptflow.evals.evaluators import (
    CoherenceEvaluator,
    F1ScoreEvaluator,
    FluencyEvaluator,
    GroundednessEvaluator,
    RelevanceEvaluator,
    SimilarityEvaluator,
    QAEvaluator,
    ChatEvaluator,
)
from promptflow.core import ModelConfiguration
from promptflow.core import AzureOpenAIModelConfiguration

from azure.ai.ml import MLClient
from azure.identity import DefaultAzureCredential, get_bearer_token_provider


def run_evaluation(predictions_path, evaluation_name, evaluation_model, metrics):
    # create an AzureOpenAI client using AAD or key based auth
    if "AZURE_OPENAI_KEY" in os.environ:
        logging.warning(
            "Using key-based authentification, instead we recommend using Azure AD authentification instead."
        )
        api_key = os.getenv("AZURE_OPENAI_KEY")
    else:
        logging.info("Using Azure AD authentification [recommended]")
        credential = DefaultAzureCredential()
        token_provider = get_bearer_token_provider(
            credential, "https://cognitiveservices.azure.com/.default"
        )
        api_key = token_provider()

    model_config = AzureOpenAIModelConfiguration(
        azure_endpoint=os.environ.get("AZURE_OPENAI_ENDPOINT"),
        api_key=api_key,
        azure_deployment=evaluation_model,
    )

    # ml_client = MLClient(
    #     credential = DefaultAzureCredential(),
    #     subscription_id = os.environ.get("AZURE_SUBSCRIPTION_ID"),
    #     resource_group_name = os.environ.get("AZURE_RESOURCE_GROUP"),
    #     ai_resource_name = os.environ.get("AZURE_AI_RESOURCE_NAME"),
    #     project_name = os.environ.get("AZURE_AI_PROJECT_NAME")
    # )
    # tracking_uri = ml_client.tracking_uri
    tracking_uri = None

    # Initializing Relevance Evaluator
    evaluators = {}
    for metric_name in metrics:
        if metric_name == "coherence":
            evaluators[metric_name] = CoherenceEvaluator(model_config)
        elif metric_name == "f1score":
            evaluators[metric_name] = F1ScoreEvaluator(model_config)
        elif metric_name == "fluency":
            evaluators[metric_name] = FluencyEvaluator(model_config)
        elif metric_name == "groundedness":
            evaluators[metric_name] = GroundednessEvaluator(model_config)
        elif metric_name == "relevance":
            evaluators[metric_name] = RelevanceEvaluator(model_config)
        elif metric_name == "similarity":
            evaluators[metric_name] = SimilarityEvaluator(model_config)
        elif metric_name == "qa":
            evaluators[metric_name] = QAEvaluator(model_config)
        elif metric_name == "chat":
            evaluators[metric_name] = ChatEvaluator(model_config)
        else:
            raise ValueError(f"Unknown metric: {metric_name}")

    # Evaluate the default vs the improved system prompt to see if the improved prompt
    # performs consistently better across a larger set of inputs
    # path = str(pathlib.Path.cwd() / dataset_path)

    logging.info(
        f"Running evaluation name={evaluation_name} on predictions: {predictions_path}"
    )
    result = evaluate(
        evaluation_name=evaluation_name,
        # target=qna_fn,
        data=predictions_path,
        evaluators=evaluators,
        # tracking_uri=tracking_uri,
    )

    # pprint(result)
    tabular_result = pd.DataFrame(result.get("rows"))
    # tabular_result = pd.read_json(result.get("rows"), lines=True)

    return result, tabular_result


def main():
    """Run the evaluation script."""
    # create argument parser
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--predictions",
        help="Path to JSONL file containing predictions (and groundtruth if needed)",
        required=True,
        type=str,
    )
    parser.add_argument(
        "--evaluation-name",
        help="evaluation name used to log the evaluation to AI Studio",
        type=str,
        default="eval-sdk-dev",
    )
    parser.add_argument(
        "--evaluation-model",
        help="Azure OpenAI model deployment name used for evaluation",
        type=str,
        default=os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT", "gpt-35-turbo"),
    )
    parser.add_argument(
        "--metrics",
        nargs="+",
        help="List of metrics to evaluate",
        choices=[
            "coherence",
            "f1score",
            "fluency",
            "groundedness",
            "relevance",
            "similarity",
            "qa",
            "chat",
        ],
        required=True,
    )
    args = parser.parse_args()

    # set logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    logging.info(f"Running script with arguments: {args}")

    # run the evaluation routine
    result, tabular_result = run_evaluation(
        args.predictions,
        evaluation_name=args.evaluation_name,
        evaluation_model=args.evaluation_model,
        metrics=args.metrics,
    )

    pprint("-----Summarized Metrics-----")
    pprint(result["metrics"])
    pprint("-----Tabular Result-----")
    pprint(tabular_result)
    # pprint(f"View evaluation results in AI Studio: {result.studio_url}") # not available yet, on track for build


if __name__ == "__main__":
    main()

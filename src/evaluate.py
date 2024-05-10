import json
import pathlib
import argparse
import logging
import sys
from functools import partial

# set environment variables before importing any other code (in particular the openai module)
from dotenv import load_dotenv
load_dotenv()

import os
import pandas as pd
from pprint import pprint

from promptflow.core import AzureOpenAIModelConfiguration
from promptflow.evals.evaluate import evaluate
from promptflow.evals.evaluators import (
    CoherenceEvaluator,
    F1ScoreEvaluator,
    FluencyEvaluator,
    GroundednessEvaluator,
    RelevanceEvaluator,
    SimilarityEvaluator,
    QAEvaluator,
    # ChatEvaluator,
)

from azure.ai.ml import MLClient
from azure.identity import DefaultAzureCredential, get_bearer_token_provider

# local imports
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "copilot_sdk_flow"))
from entry import flow_entry_copilot_assistants
import time


def get_model_config(evaluation_endpoint, evaluation_model):
    """Get the model configuration for the evaluation."""

    # create an AzureOpenAI client using AAD or key based auth
    if "AZURE_OPENAI_API_KEY" in os.environ:
        logging.warning(
            "Using key-based authentification, instead we recommend using Azure AD authentification instead."
        )
        api_key = os.getenv("AZURE_OPENAI_API_KEY")
    else:
        logging.info("Using Azure AD authentification [recommended]")
        credential = DefaultAzureCredential()
        token_provider = get_bearer_token_provider(
            credential, "https://cognitiveservices.azure.com/.default"
        )
        api_key = token_provider()

    model_config = AzureOpenAIModelConfiguration(
        azure_endpoint=evaluation_endpoint,
        api_key=api_key,
        azure_deployment=evaluation_model,
    )

    return model_config


def run_evaluation(
    evaluation_name,
    evaluation_model_config,
    evaluation_data_path,
    metrics,
    output_path=None,
):
    """Run the evaluation routine."""
    # completion_func = latency_qna_function
    completion_func = flow_entry_copilot_assistants

    # Initializing Relevance Evaluator
    evaluators = {}
    evaluators_config = {}
    for metric_name in metrics:
        if metric_name == "coherence":
            evaluators[metric_name] = CoherenceEvaluator(evaluation_model_config)
            # map fields required by the evaluators to either
            # fields in the completion_func return dict (target.*)
            # or fields in the input data (data.*)
            evaluators_config[metric_name] = {
                "question": "${data.chat_input}",
                "answer": "${target.reply}",
            }
        elif metric_name == "f1score":
            evaluators[metric_name] = F1ScoreEvaluator()
            evaluators_config[metric_name] = {
                "answer": "${target.reply}",
                "ground_truth": "${data.ground_truth}",
            }
        elif metric_name == "fluency":
            evaluators[metric_name] = FluencyEvaluator(evaluation_model_config)
            evaluators_config[metric_name] = {
                "question": "${data.chat_input}",
                "answer": "${target.reply}",
            }
        elif metric_name == "groundedness":
            evaluators[metric_name] = GroundednessEvaluator(evaluation_model_config)
            evaluators_config[metric_name] = {
                "answer": "${target.reply}",
                "context": "${target.context}",
            }
        elif metric_name == "relevance":
            evaluators[metric_name] = RelevanceEvaluator(evaluation_model_config)
            evaluators_config[metric_name] = {
                "question": "${data.chat_input}",
                "answer": "${target.reply}",
                "context": "${target.context}",
            }
        elif metric_name == "similarity":
            evaluators[metric_name] = SimilarityEvaluator(evaluation_model_config)
            evaluators_config[metric_name] = {
                "question": "${data.chat_input}",
                "answer": "${target.reply}",
                "ground_truth": "${data.ground_truth}",
            }
        elif metric_name == "qa":
            evaluators[metric_name] = QAEvaluator(evaluation_model_config)
            evaluators_config[metric_name] = {
                "question": "${data.chat_input}",
                "answer": "${target.reply}",
                "context": "${target.context}",
                "ground_truth": "${data.ground_truth}",
            }
        elif metric_name == "latency":
            raise NotImplementedError("Latency metric is not implemented yet")
        else:
            raise ValueError(f"Unknown metric: {metric_name}")

    logging.info(
        f"Running evaluation name={evaluation_name} on dataset {evaluation_data_path}"
    )

    result = evaluate(
        target=completion_func,
        evaluation_name=evaluation_name,
        evaluators=evaluators,
        evaluator_config=evaluators_config,
        data=evaluation_data_path,
    )

    tabular_result = pd.DataFrame(result.get("rows"))
    return result, tabular_result


def main():
    """Run the evaluation script."""
    # create argument parser
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--evaluation-data-path",
        help="Path to JSONL file containing evaluation dataset",
        required=True,
    )
    parser.add_argument(
        "--evaluation-name",
        help="evaluation name used to log the evaluation to AI Studio",
        type=str,
        default="eval-sdk-dev",
    )
    parser.add_argument(
        "--evaluation-endpoint",
        help="Azure OpenAI endpoint used for evaluation",
        type=str,
        default=os.getenv("AZURE_OPENAI_ENDPOINT"),
    )
    parser.add_argument(
        "--evaluation-model",
        help="Azure OpenAI model deployment name used for evaluation",
        type=str,
        default=os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT"),
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
            "latency",
        ],
        required=True,
    )
    args = parser.parse_args()

    # set logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    # set logging level from some dependencies
    logging.getLogger("azure.core").setLevel(logging.ERROR)
    logging.getLogger("azure.identity").setLevel(logging.ERROR)
    logging.getLogger("azure.monitor").setLevel(logging.ERROR)
    # logging.getLogger("promptflow").setLevel(logging.ERROR)

    logging.info(f"Running script with arguments: {args}")

    # get a model config for evaluation
    eval_model_config = get_model_config(
        args.evaluation_endpoint, args.evaluation_model
    )

    # run the evaluation routine
    result, tabular_result = run_evaluation(
        evaluation_name=args.evaluation_name,
        evaluation_model_config=eval_model_config,
        evaluation_data_path=args.evaluation_data_path,
        metrics=args.metrics,
    )

    pprint("-----Summarized Metrics-----")
    pprint(result["metrics"])
    pprint("-----Tabular Result-----")
    print(json.dumps(tabular_result.to_json(orient="records", lines=True), indent=4))
    pprint(f"View evaluation results in AI Studio: {result['studio_url']}")


if __name__ == "__main__":
    main()

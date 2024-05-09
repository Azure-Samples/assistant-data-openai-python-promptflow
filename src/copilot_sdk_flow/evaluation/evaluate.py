import json
import pathlib
import argparse
import logging
import sys

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
    ChatEvaluator,
)

from azure.ai.ml import MLClient
from azure.identity import DefaultAzureCredential, get_bearer_token_provider


def get_model_config(evaluation_model):
    """Get the model configuration for the evaluation."""
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

    return model_config


def run_evaluation(
    predictions_path,
    evaluation_name,
    evaluation_model_config,
    metrics,
    completion_func,
    output_path=None,
):
    """Run the evaluation routine."""
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
                "question": "${data.question}",
                "answer": "${target.reply}",
            }
        elif metric_name == "f1score":
            evaluators[metric_name] = F1ScoreEvaluator(evaluation_model_config)
            evaluators_config[metric_name] = {
                "answer": "${target.reply}",
                "ground_truth": "${data.ground_truth}",
            }
        elif metric_name == "fluency":
            evaluators[metric_name] = FluencyEvaluator(evaluation_model_config)
            evaluators_config[metric_name] = {
                "question": "${data.question}",
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
                "question": "${data.question}",
                "answer": "${target.reply}",
                "ground_truth": "${data.ground_truth}",
            }
        elif metric_name == "qa":
            evaluators[metric_name] = QAEvaluator(evaluation_model_config)
            evaluators_config[metric_name] = {
                "question": "${data.question}",
                "answer": "${target.reply}",
                "context": "${target.context}",
                "ground_truth": "${data.ground_truth}",
            }
        elif metric_name == "latency":
            raise NotImplementedError("Latency evaluation is not yet implemented")
        else:
            raise ValueError(f"Unknown metric: {metric_name}")

    logging.info(
        f"Running evaluation name={evaluation_name} on predictions: {predictions_path}"
    )

    result = evaluate(
        target=completion_func,
        evaluation_name=evaluation_name,
        data=predictions_path,
        evaluators=evaluators,
        evaluator_config=evaluators_config,
    )

    tabular_result = pd.DataFrame(result.get("rows"))
    # UPCOMING: this line will be handled by output_path in evaluate function
    tabular_result.to_json(output_path, orient="records", lines=True)

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
    logging.info(f"Running script with arguments: {args}")

    # get a model config for evaluation
    eval_model_config = get_model_config(args.evaluation_model)

    # run the evaluation routine
    result, tabular_result = run_evaluation(
        args.predictions,
        evaluation_name=args.evaluation_name,
        evaluation_model_config=eval_model_config,
        metrics=args.metrics,
    )

    pprint("-----Summarized Metrics-----")
    pprint(result["metrics"])
    pprint("-----Tabular Result-----")
    pprint(tabular_result)
    pprint(f"View evaluation results in AI Studio: {result['studio_url']}")


if __name__ == "__main__":
    main()

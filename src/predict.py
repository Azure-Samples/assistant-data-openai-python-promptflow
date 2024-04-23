"""Script to run evaluation on a dataset using the completion function.

This script takes a dataset in JSONL format and runs the completion function on each
sample. The output is written to a new JSONL file.

Example:
    python src/evaluate.py --input-data-path data/questions.jsonl --output-data-path data/chat_output.jsonl
"""
from __future__ import annotations
import asyncio
import json
import argparse
import logging

from openai.types.chat import ChatCompletion
from tqdm import tqdm

# set environment variables before importing any other code
from dotenv import load_dotenv

load_dotenv()

# local imports
from copilot_sdk_flow.chat import chat_completion


def main():
    """Run the evaluation script."""
    # create argument parser
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input-data-path",
        help="Path to JSONL file containing evaluation dataset",
        required=True,
        type=str,
    )
    parser.add_argument(
        "--output-data-path",
        help="Path to write JSONL file inferences",
        required=True,
        type=str,
    )
    args = parser.parse_args()
    logging.info(f"Running script with arguments: {args}")

    # load the input dataset in one loop
    with open(args.input_data_path, "r") as input_file:
        input_dataset = [json.loads(line) for line in input_file]

    # loop on all input samples
    for input_sample in tqdm(input_dataset):
        # call the completion function
        result = asyncio.run(
            chat_completion, [{"role": "user", "content": input_sample["question"]}]
        )

        # convert to output data format
        output_data = {"question": input_sample["question"]}

        if result is None:
            logging.critical("No response from completion function")
            continue
        if isinstance(result, ChatCompletion):
            output_data["answer"] = result.choices[0].message.content
            output_data["context"] = result.choices[0].context
        else:
            output_data["answer"] = result["choices"][0]["message"]["content"]
            output_data["context"] = (
                result["choices"][0]["context"]
                if "context" in result["choices"][0]
                else None
            )

        # add groundtruth answer if available
        if "ground_truth" in input_sample:
            output_data["ground_truth"] = input_sample["ground_truth"]

        with open(args.output_data_path, "a") as output_file:
            output_file.write(json.dumps(output_data) + "\n")


if __name__ == "__main__":
    # set logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # remove info logs from httpx
    logging.getLogger("httpx").setLevel(logging.WARNING)

    # run main
    main()

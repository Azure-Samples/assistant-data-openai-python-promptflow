"""This module contains an extension to query a local SQLite database for our demo."""

import os
from promptflow.tracing import trace

import sqlite3
import pandas as pd
import asyncio

_DB_CONN = sqlite3.connect(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "order_data.db"),
    check_same_thread=False,
)


@trace
async def query_order_data(sql_query: str) -> str:
    """Run a SQL query against table `order_data` and return the results in JSON format."""
    global _DB_CONN
    try:
        df = pd.read_sql(sql_query, _DB_CONN)
    except Exception as e:
        return f"Error: {e}"

    return df.to_json(orient="records")


async def main():
    """for local testing"""
    query = "SELECT AVG(Sum_of_Order_Value_USD) AS Avg_Sales FROM order_data WHERE Month = 1"
    result = await query_order_data(query)
    print(result)


if __name__ == "__main__":
    asyncio.run(main())

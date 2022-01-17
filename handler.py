import json
from base64 import b64decode

import boto3
from typing import List

textract = boto3.client("textract")


def analyze_picture(event, _):
    file = event.get("body")
    raw_content = b64decode(file)
    analysis = textract.analyze_document(
        Document={
            "Bytes": raw_content,  # PNG or JPEG
        },
        FeatureTypes=["TABLES"]
    )
    blocks = analysis.get("Blocks")
    tables = get_tables(blocks)
    body = {
        "data": {
            "tables": tables,
        }
    }

    response = {
        "statusCode": 200,
        "headers": {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Credentials': True,
        },
        "body": json.dumps(body)
    }

    return response


def get_tables(blocks: List[dict]) -> list:
    blocks_map = {}
    table_blocks = []
    for block in blocks:
        blocks_map[block["Id"]] = block
        if block["BlockType"] == "TABLE":
            table_blocks.append(block)

    tables = []
    for table in table_blocks:
        tables.append(generate_table(table, blocks_map))
    return tables


def generate_table(table_result: dict, blocks_map: dict):
    rows = get_rows_column_map(table_result, blocks_map)
    return list(rows.values())


def get_rows_column_map(table_result: dict, blocks_map: dict) -> dict:
    rows = {}
    for relationship in table_result["Relationships"]:
        if relationship["Type"] == "CHILD":
            for child_id in relationship["Ids"]:
                cell = blocks_map[child_id]
                if cell["BlockType"] == "CELL":
                    row_index = cell["RowIndex"]
                    col_index = cell["ColumnIndex"]
                    if row_index not in rows:
                        rows[row_index] = {}
                    rows[row_index][col_index] = get_text(cell, blocks_map)
    return rows


def get_text(result: dict, block_map: dict) -> str:
    text = ""
    if "Relationships" in result:
        for relationship in result["Relationships"]:
            if relationship["Type"] == "CHILD":
                for child_id in relationship["Ids"]:
                    word = block_map[child_id]
                    if word["BlockType"] == "WORD":
                        text += word["Text"] + " "

    return text

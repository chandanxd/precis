#!/usr/bin/env python3
"""
Convert official MRQA 2019 NaturalQuestions dev split (gzip JSONL)
to Précis evaluation format.

Source format (MRQA):
  Line 0: {"header": {"dataset": "NaturalQuestionsShort", "split": "dev"}}
  Line 1+: {
    "context": "...",
    "qas": [
      {
        "question": "...",
        "answers": ["..."],
        "qid": "..."
      }
    ]
  }

Target format (Précis evaluation):
  One JSON object per line with:
  {
    "doc_id": "<qid>",
    "question": "<question>",
    "gold_answer": "<answers[0]>",
    "document": "<context>",
    "answers": ["<answers>"]
  }
"""

import argparse
import gzip
import json
import os
from typing import Any, Dict, List


def convert_mrqa_nq(input_path: str, output_path: str) -> Dict[str, Any]:
    if not os.path.isfile(input_path):
        raise FileNotFoundError(f"Source file not found: {input_path}")

    out_dir = os.path.dirname(os.path.abspath(output_path))
    os.makedirs(out_dir, exist_ok=True)

    total_records = 0
    duplicate_doc_ids = 0
    missing_fields_count = 0
    seen_doc_ids = set()

    # Track length statistics
    doc_char_lengths: List[int] = []
    doc_word_lengths: List[int] = []
    q_char_lengths: List[int] = []
    q_word_lengths: List[int] = []
    ans_char_lengths: List[int] = []
    ans_word_lengths: List[int] = []

    first_two_records: List[Dict[str, Any]] = []

    with gzip.open(input_path, "rt", encoding="utf-8") as gz_in, \
            open(output_path, "w", encoding="utf-8") as jsonl_out:

        header_line = gz_in.readline()
        if not header_line:
            raise ValueError(f"Empty source file: {input_path}")

        header_data = json.loads(header_line)
        header_info = header_data.get("header", {})
        print(f"Header: dataset={header_info.get('dataset')}, split={header_info.get('split')}")

        for line_idx, line in enumerate(gz_in, start=1):
            line_str = line.strip()
            if not line_str:
                continue

            record = json.loads(line_str)
            context = record.get("context", "")
            qas = record.get("qas", [])

            context_words = len(context.split())
            context_chars = len(context)

            for qa in qas:
                qid = qa.get("qid", "")
                question = qa.get("question", "")
                answers = qa.get("answers", [])
                gold_answer = answers[0] if answers and isinstance(answers[0], str) else ""

                if not qid or not question or not context or not gold_answer:
                    missing_fields_count += 1

                if qid in seen_doc_ids:
                    duplicate_doc_ids += 1
                seen_doc_ids.add(qid)

                q_chars = len(question)
                q_words = len(question.split())
                ans_chars = len(gold_answer)
                ans_words = len(gold_answer.split())

                doc_char_lengths.append(context_chars)
                doc_word_lengths.append(context_words)
                q_char_lengths.append(q_chars)
                q_word_lengths.append(q_words)
                ans_char_lengths.append(ans_chars)
                ans_word_lengths.append(ans_words)

                out_obj = {
                    "doc_id": qid,
                    "question": question,
                    "gold_answer": gold_answer,
                    "document": context,
                    "answers": answers,
                }

                if len(first_two_records) < 2:
                    first_two_records.append(out_obj)

                jsonl_out.write(json.dumps(out_obj, ensure_ascii=False) + "\n")
                total_records += 1

    stats = {
        "total_records": total_records,
        "duplicate_doc_ids": duplicate_doc_ids,
        "missing_fields_count": missing_fields_count,
        "doc_chars": {
            "min": min(doc_char_lengths) if doc_char_lengths else 0,
            "mean": sum(doc_char_lengths) / len(doc_char_lengths) if doc_char_lengths else 0.0,
            "max": max(doc_char_lengths) if doc_char_lengths else 0,
        },
        "doc_words": {
            "min": min(doc_word_lengths) if doc_word_lengths else 0,
            "mean": sum(doc_word_lengths) / len(doc_word_lengths) if doc_word_lengths else 0.0,
            "max": max(doc_word_lengths) if doc_word_lengths else 0,
        },
        "q_chars": {
            "min": min(q_char_lengths) if q_char_lengths else 0,
            "mean": sum(q_char_lengths) / len(q_char_lengths) if q_char_lengths else 0.0,
            "max": max(q_char_lengths) if q_char_lengths else 0,
        },
        "q_words": {
            "min": min(q_word_lengths) if q_word_lengths else 0,
            "mean": sum(q_word_lengths) / len(q_word_lengths) if q_word_lengths else 0.0,
            "max": max(q_word_lengths) if q_word_lengths else 0,
        },
        "ans_chars": {
            "min": min(ans_char_lengths) if ans_char_lengths else 0,
            "mean": sum(ans_char_lengths) / len(ans_char_lengths) if ans_char_lengths else 0.0,
            "max": max(ans_char_lengths) if ans_char_lengths else 0,
        },
        "ans_words": {
            "min": min(ans_word_lengths) if ans_word_lengths else 0,
            "mean": sum(ans_word_lengths) / len(ans_word_lengths) if ans_word_lengths else 0.0,
            "max": max(ans_word_lengths) if ans_word_lengths else 0,
        },
        "first_two_records": first_two_records,
    }

    return stats


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert MRQA 2019 NaturalQuestions dev split to Précis format."
    )
    parser.add_argument(
        "--input",
        "-i",
        default="/home/chandan/Datasets/mrqa/NaturalQuestions.jsonl.gz",
        help="Path to source NaturalQuestions.jsonl.gz",
    )
    parser.add_argument(
        "--output",
        "-o",
        default="data/nq_subset/nq_dev.jsonl",
        help="Path to target output JSONL file",
    )
    args = parser.parse_args()

    print(f"Reading from: {args.input}")
    print(f"Writing to:   {args.output}")

    stats = convert_mrqa_nq(args.input, args.output)

    print("\n" + "=" * 50)
    print("CONVERSION SUMMARY")
    print("=" * 50)
    print(f"Total records converted:   {stats['total_records']}")
    print(f"Duplicate doc_ids:         {stats['duplicate_doc_ids']}")
    print(f"Missing/empty fields:      {stats['missing_fields_count']}")
    print("\nDocument Length Statistics:")
    print(
        f"  Characters: min={stats['doc_chars']['min']}, "
        f"mean={stats['doc_chars']['mean']:.2f}, max={stats['doc_chars']['max']}"
    )
    print(
        f"  Words:      min={stats['doc_words']['min']}, "
        f"mean={stats['doc_words']['mean']:.2f}, max={stats['doc_words']['max']}"
    )
    print("\nQuestion Length Statistics:")
    print(
        f"  Characters: min={stats['q_chars']['min']}, "
        f"mean={stats['q_chars']['mean']:.2f}, max={stats['q_chars']['max']}"
    )
    print(
        f"  Words:      min={stats['q_words']['min']}, "
        f"mean={stats['q_words']['mean']:.2f}, max={stats['q_words']['max']}"
    )
    print("\nGold Answer Length Statistics:")
    print(
        f"  Characters: min={stats['ans_chars']['min']}, "
        f"mean={stats['ans_chars']['mean']:.2f}, max={stats['ans_chars']['max']}"
    )
    print(
        f"  Words:      min={stats['ans_words']['min']}, "
        f"mean={stats['ans_words']['mean']:.2f}, max={stats['ans_words']['max']}"
    )

    print("\n" + "=" * 50)
    print("FIRST 2 CONVERTED RECORDS")
    print("=" * 50)
    for idx, rec in enumerate(stats["first_two_records"], start=1):
        print(f"\n--- Record {idx} ---")
        preview = dict(rec)
        if len(preview["document"]) > 200:
            preview["document"] = preview["document"][:200] + "... [truncated in display]"
        print(json.dumps(preview, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

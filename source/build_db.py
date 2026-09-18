import json
import os
import sys
import argparse
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document


def parse_args():
    parser = argparse.ArgumentParser()
    # Azure ML dynamically injects runtime paths into these arguments
    parser.add_argument("--input_data", type=str, required=True)
    parser.add_argument("--output_db", type=str, required=True)
    return parser.parse_args()


def load_data(file_path):
    if not os.path.exists(file_path):
        print(f"ERROR: Target file not found at {file_path}")
        sys.exit(1)
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


if __name__ == "__main__":
    args = parse_args()

    # Ensure output directory exists
    if not os.path.exists(args.output_db):
        os.makedirs(args.output_db)

    raw_data = load_data(args.input_data)

    documents = []
    for item in raw_data:
        meta = item.get('metadata', {}).copy()
        meta['category'] = str(item.get('category', 'unknown'))
        meta['original_id'] = str(item.get('id', 'unknown'))

        # Flatten lists in metadata as Chroma expects scalar values
        if 'keywords' in meta:
            if isinstance(meta['keywords'], list):
                meta['keywords_str'] = ", ".join(meta['keywords'])
            del meta['keywords']

        doc = Document(page_content=item.get('content', ''), metadata=meta)
        documents.append(doc)

    embedding_model = HuggingFaceEmbeddings(model_name="bkai-foundation-models/vietnamese-bi-encoder")

    vector_db = Chroma.from_documents(
        documents=documents,
        embedding=embedding_model,
        persist_directory=args.output_db
    )
    print(f"SUCCESS: Vector DB persisted at {args.output_db}")
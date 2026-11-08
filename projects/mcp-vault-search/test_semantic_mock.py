#!/usr/bin/env python
"""Test semantic search tool integration with FakeEmbedder."""

import json
import os
from pathlib import Path

from tests.test_semantic import FakeEmbedder
from mcp_vault_search.semantic import build_index, semantic_search
from mcp_vault_search.vault import vault_root

def main():
    root = vault_root("examples/vault")
    embedder = FakeEmbedder()

    print("Testing semantic tool integration...")
    print(f"Vault: {root}")
    print(f"Notes: {len(list(root.glob('*.md')))}")

    # Build index
    chunks = build_index(root, embedder, root / ".index_test.json")
    print(f"Index built: {len(chunks)} chunks")
    print()

    # Test searches
    queries = [
        "agentes",
        "fragmentos",
        "validación",
        "contenedores",
    ]

    for query in queries:
        print(f"Query: {query}")
        results = semantic_search(chunks, query, embedder, vault_root_path=root, limit=3)
        for i, r in enumerate(results, 1):
            print(f"  {i}. {r['path']} (score: {r['score']:.4f}, lines {r['line_start']}-{r['line_end']})")
        print()

    print("[OK] Integration test passed")


if __name__ == "__main__":
    main()

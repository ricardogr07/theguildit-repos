#!/usr/bin/env python
"""Evaluate semantic search with real model against 12-note corpus."""

import json
from pathlib import Path

from mcp_vault_search.semantic import build_index, semantic_search
from mcp_vault_search.vault import vault_root

# Queries and expected targets from plan
QUERIES = [
    ("¿Cómo puede un asistente usar funciones de otras aplicaciones?", "mcp.md"),
    ("¿Cómo encuentro algo que escribí con otras palabras?", "busqueda-semantica.md"),
    ("¿Cómo evito que se pierda la parte final de un apunte muy extenso al procesarlo?", "fragmentos.md"),
    ("¿Cómo evito que el asistente abra documentos fuera de la carpeta que le compartí?", "rutas-seguras.md"),
]

def main():
    try:
        import sentence_transformers
    except ImportError:
        print("ERROR: sentence-transformers not installed. Install with: uv sync --locked --extra semantic")
        return

    root = vault_root("examples/vault")
    embedder = sentence_transformers.SentenceTransformer("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")

    print("Building index...")
    chunks = build_index(root, embedder)
    print(f"Index built: {len(chunks)} chunks from vault")
    print()

    results = []
    for i, (query, expected_target) in enumerate(QUERIES, 1):
        print(f"Query {i}: {query}")
        print(f"Expected target: {expected_target}")

        # Semantic search with access validation
        semantic_results = semantic_search(chunks, query, embedder, vault_root_path=root, limit=5)
        print(f"Top 3 semantic results:")
        for j, r in enumerate(semantic_results[:3], 1):
            print(f"  {j}. {r['path']} (score: {r['score']:.4f})")

        # Literal search for comparison
        from mcp_vault_search.vault import search_notes
        literal_results = search_notes(root, query, limit=10)
        if literal_results:
            print(f"Literal search found: {[r['path'] + ':' + str(r['line']) for r in literal_results]}")
        else:
            print("Literal search found: (no matches)")

        # Check if target in top 3
        top3_paths = [r['path'] for r in semantic_results[:3]]
        target_pos = None
        for j, r in enumerate(semantic_results, 1):
            if r['path'] == expected_target:
                target_pos = j
                break

        print(f"Target position: {target_pos or 'not in top 5'}")
        print()

        results.append({
            "query": query,
            "expected_target": expected_target,
            "top_3": top3_paths,
            "target_position": target_pos,
            "full_results": semantic_results,
            "literal_matches": literal_results,
        })

    # Summary
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    for i, (query, expected_target) in enumerate(QUERIES, 1):
        r = results[i - 1]
        status = "[PASS]" if r['target_position'] and r['target_position'] <= 3 else "[FAIL]"
        print(f"{i}. {status} - {expected_target} at position {r['target_position'] or 'N/A'}")

    # Write full results
    output_file = Path("evaluate_semantic_results.json")
    output_file.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print()
    print(f"Full results written to {output_file}")


if __name__ == "__main__":
    main()

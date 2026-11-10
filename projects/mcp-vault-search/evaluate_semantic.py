#!/usr/bin/env python
"""Evaluate semantic search with real model against 12-note corpus."""

import argparse
import hashlib
import json
import platform
from importlib.metadata import version
from pathlib import Path

from mcp_vault_search.semantic import MODEL_NAME, MODEL_REVISION, build_index, semantic_search
from mcp_vault_search.vault import markdown_files, vault_root

# Queries with expected targets and designated distractors (per plan line 74)
# PASS: target in top 3 AND (no distractor in top 3 OR target ranks better than distractor)
QUERIES = [
    {"query": "¿Cómo puede un asistente usar funciones de otras aplicaciones?", "target": "mcp.md", "distractor": "contenedores.md"},
    {"query": "¿Cómo encuentro algo que escribí con otras palabras?", "target": "busqueda-semantica.md", "distractor": "busqueda.md"},
    {"query": "¿Cómo evito que se pierda la parte final de un apunte muy extenso al procesarlo?", "target": "fragmentos.md", "distractor": "bitacora-de-incidente.md"},
    {"query": "¿Cómo evito que el asistente abra documentos fuera de la carpeta que le compartí?", "target": "rutas-seguras.md", "distractor": "datos-y-privacidad.md"},
]

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("evaluate_semantic_results.json"))
    arguments = parser.parse_args()
    try:
        import sentence_transformers
    except ImportError:
        print("ERROR: sentence-transformers not installed. Install with: uv sync --locked --extra semantic")
        return

    root = vault_root("examples/vault")
    embedder = sentence_transformers.SentenceTransformer(MODEL_NAME, revision=MODEL_REVISION, device="cpu")

    print("Building index...")
    chunks = build_index(root, embedder)
    print(f"Index built: {len(chunks)} chunks from vault")
    print()

    token_counts = [len(embedder.tokenizer.encode(chunk.text)) for chunk in chunks]
    if max(token_counts) > embedder.max_seq_length:
        raise ValueError("Un fragmento excede el límite de tokens del modelo")
    metadata = {
        "model_name": MODEL_NAME,
        "model_revision": MODEL_REVISION,
        "python_version": platform.python_version(),
        "package_versions": {name: version(name) for name in ("sentence-transformers", "transformers", "torch")},
        "corpus_sha256": {
            path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in markdown_files(root)
        },
        "code_sha256": {
            path.resolve().relative_to(Path.cwd()).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in (Path("src/mcp_vault_search/semantic.py"), Path("src/mcp_vault_search/server.py"), Path(__file__).resolve())
        },
        "max_chunk_tokens": max(token_counts),
        "model_token_limit": embedder.max_seq_length,
    }

    results = []
    for i, q_spec in enumerate(QUERIES, 1):
        query = q_spec["query"]
        expected_target = q_spec["target"]
        distractor = q_spec["distractor"]

        print(f"Query {i}: {query}")
        print(f"Expected target: {expected_target}")
        print(f"Designated distractor: {distractor}")

        # Semantic search with access validation; request more fragments to ensure enough unique notes
        semantic_results = semantic_search(chunks, query, embedder, vault_root_path=root, limit=50)

        # Deduplicate by note path, preserving order; assign consecutive rank 1, 2, 3, ...
        seen_notes = {}
        note_rankings = []
        for r in semantic_results:
            if r['path'] not in seen_notes:
                note_rank = len(note_rankings) + 1
                seen_notes[r['path']] = note_rank
                note_rankings.append((r['path'], note_rank))

        print(f"Note rankings (unique notes, by first occurrence):")
        for note_path, note_rank in note_rankings[:5]:
            print(f"  {note_rank}. {note_path}")

        # Literal search for comparison
        from mcp_vault_search.vault import search_notes
        literal_results = search_notes(root, query, limit=10)
        if literal_results:
            print(f"Literal search found: {[r['path'] + ':' + str(r['line']) for r in literal_results]}")
        else:
            print("Literal search found: (no matches)")

        # Determine PASS/FAIL: target in top 3 AND target ranks better than distractor
        target_note_rank = seen_notes.get(expected_target)
        distractor_note_rank = seen_notes.get(distractor)

        # Validate: target in top 3, and if distractor present, target must rank better
        passes = (
            target_note_rank is not None and target_note_rank <= 3 and
            (distractor_note_rank is None or target_note_rank < distractor_note_rank)
        )

        print(f"Target position: {target_note_rank or 'not in top 5'}")
        if distractor_note_rank:
            print(f"Distractor position: {distractor_note_rank}")
        print(f"Result: {'[PASS]' if passes else '[FAIL]'}")
        print()

        results.append({
            "evaluation_metadata": metadata,
            "query": query,
            "expected_target": expected_target,
            "designated_distractor": distractor,
            "target_position": target_note_rank,
            "distractor_position": distractor_note_rank,
            "note_rankings": [{"note": n, "rank": r} for n, r in note_rankings],
            "full_results": semantic_results,
            "literal_matches": literal_results,
            "pass": passes,
        })

    # Summary
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    for i, r in enumerate(results, 1):
        status = "[PASS]" if r['pass'] else "[FAIL]"
        print(f"{i}. {status} - {r['expected_target']} at position {r['target_position'] or 'N/A'}", end="")
        if r['distractor_position']:
            print(f" (distractor at {r['distractor_position']})")
        else:
            print()

    # Write full results
    output_file = arguments.output
    output_file.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print()
    print(f"Full results written to {output_file}")


if __name__ == "__main__":
    main()

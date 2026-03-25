# -*- coding: utf-8 -*-
"""
Created on Thu Mar 26 00:33:53 2026

@author: Gabriel
"""

import re
import requests
from typing import List, Tuple
from rdflib import Graph

# ----------------------------
# Configuration
# ----------------------------
TTL_FILE = "expanded_kb_pruned.ttl"
OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "llama3.2:3b"

MAX_PREDICATES = 20
MAX_CLASSES = 10
SAMPLE_TRIPLES = 8

# ----------------------------
# 0) Appel du LLM local via Ollama
# ----------------------------
def ask_local_llm(prompt: str, model: str = MODEL_NAME) -> str:
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False
    }

    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=300)
    except requests.exceptions.Timeout:
        raise RuntimeError("Ollama timed out. Try reducing the schema summary or increasing timeout.")

    if response.status_code != 200:
        raise RuntimeError(f"Ollama API error {response.status_code}: {response.text}")

    data = response.json()
    return data.get("response", "").strip()


# ----------------------------
# 1) Charger le graphe RDF
# ----------------------------
def load_graph(ttl_path: str) -> Graph:
    g = Graph()
    g.parse(ttl_path, format="turtle")
    print(f"Loaded {len(g)} triples from {ttl_path}")
    return g


# ----------------------------
# 2) Aide pour afficher des URI lisibles
# ----------------------------
def shorten_uri(term, g: Graph) -> str:
    """
    Transforme une URI complète en forme compacte si possible.
    Ex: http://www.wikidata.org/prop/direct/P31 -> wdt:P31
    """
    try:
        return g.namespace_manager.normalizeUri(term)
    except Exception:
        return str(term)


# ----------------------------
# 3) Construire un petit schema summary
# ----------------------------
def get_prefix_block(g: Graph) -> str:
    defaults = {
        "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
        "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
        "xsd": "http://www.w3.org/2001/XMLSchema#",
        "owl": "http://www.w3.org/2002/07/owl#",
    }

    ns_map = {p: str(ns) for p, ns in g.namespace_manager.namespaces()}
    for k, v in defaults.items():
        ns_map.setdefault(k, v)

    lines = [f"PREFIX {p}: <{ns}>" for p, ns in ns_map.items()]
    return "\n".join(sorted(lines))


def list_top_predicates(g: Graph, limit: int = MAX_PREDICATES) -> List[Tuple[str, int]]:
    q = f"""
    SELECT ?p (COUNT(*) AS ?count) WHERE {{
      ?s ?p ?o .
    }}
    GROUP BY ?p
    ORDER BY DESC(?count)
    LIMIT {limit}
    """
    preds = []
    for row in g.query(q):
        preds.append((shorten_uri(row["p"], g), int(row["count"])))
    return preds


def list_top_classes(g: Graph, limit: int = MAX_CLASSES) -> List[Tuple[str, int]]:
    q = f"""
    SELECT ?cls (COUNT(*) AS ?count) WHERE {{
      ?s a ?cls .
    }}
    GROUP BY ?cls
    ORDER BY DESC(?count)
    LIMIT {limit}
    """
    clss = []
    for row in g.query(q):
        clss.append((shorten_uri(row["cls"], g), int(row["count"])))
    return clss



def sample_triples(g: Graph, limit: int = SAMPLE_TRIPLES) -> List[Tuple[str, str, str]]:
    q = f"""
    SELECT ?s ?p ?o WHERE {{
      ?s ?p ?o .
      FILTER(isIRI(?s) && isIRI(?p))
    }}
    LIMIT {limit}
    """
    triples = []
    for r in g.query(q):
        triples.append((
            shorten_uri(r.s, g),
            shorten_uri(r.p, g),
            shorten_uri(r.o, g)
        ))
    return triples

PROPERTY_HINTS = {
    "wdt:P31": "instance of",
    "wdt:P17": "country",
    "wdt:P19": "place of birth",
    "wdt:P21": "sex or gender",
    "wdt:P27": "country of citizenship",
    "wdt:P106": "occupation",
    "wdt:P161": "cast member",
    "wdt:P279": "subclass of",
    "wdt:P495": "country of origin",
    "wdt:P569": "date of birth",
    "wdt:P570": "date of death",
}

def explain_term(term: str) -> str:
    if term in PROPERTY_HINTS:
        return f"{term} ({PROPERTY_HINTS[term]})"
    return term


def build_schema_summary(g: Graph) -> str:
    prefixes = get_prefix_block(g)
    preds = list_top_predicates(g)
    clss = list_top_classes(g)
    samples = sample_triples(g)

    pred_lines = "\n".join(
        f"- {explain_term(p)} [count={c}]"
        for p, c in preds
    )

    cls_lines = "\n".join(
        f"- {c} [count={n}]"
        for c, n in clss
    )

    sample_lines = "\n".join(
        f"- {s} -- {explain_term(p)} --> {o}"
        for s, p, o in samples
    )

    summary = f"""
{prefixes}

# Most frequent predicates (top {MAX_PREDICATES})
{pred_lines}

# Most frequent classes via rdf:type (top {MAX_CLASSES})
{cls_lines}

# Sample triples
{sample_lines}
"""
    return summary.strip()

def build_question_aware_summary(g: Graph, question: str) -> str:
    base = build_schema_summary(g)

    hints = []
    q = question.lower()

    if "type" in q:
        hints.append("- wdt:P31 (instance of)")
    if "birth" in q or "born" in q:
        hints.append("- wdt:P19 (place of birth)")
        hints.append("- wdt:P569 (date of birth)")
        hints.append("- wdt:P27 (country of citizenship)")
    if "country" in q:
        hints.append("- wdt:P17 (country)")
        hints.append("- wdt:P495 (country of origin)")
    if "film" in q or "movie" in q:
        hints.append("- ex:Film")
        hints.append("- wdt:P161 (cast member)")

    if hints:
        return base + "\n\n# Question-relevant hints\n" + "\n".join(hints)

    return base

# ----------------------------
# 4) Génération SPARQL
# ----------------------------
SPARQL_INSTRUCTIONS = """
You generate SPARQL 1.1 SELECT queries for an RDF graph.

Rules:
- Use only prefixes, predicates, classes, and entities explicitly shown in the schema summary.
- Do not invent properties or entities.
- Return exactly one SPARQL query inside a fenced ```sparql code block.
- Return a SELECT query only.
- Keep the query short and robust.
- Always include LIMIT 20 unless the question clearly requires a different limit.
- Prefer direct triples over complex OPTIONAL patterns.
- If the question asks about "type", prefer wdt:P31.
- Wikidata-style entities look like wd:Qxxx.
- Wikidata-style properties look like wdt:Pxxx.
- If the answer is uncertain, still produce the safest simple query based only on the schema summary.

Example:
Question: What entities have a type?
SPARQL:
```sparql
SELECT ?entity ?type WHERE {
  ?entity wdt:P31 ?type .
}
LIMIT 20
"""

CODE_BLOCK_RE = re.compile(r"```(?:sparql)?\s*(.*?)```", re.IGNORECASE | re.DOTALL)

def extract_sparql_from_text(text: str) -> str:
    m = CODE_BLOCK_RE.search(text)
    if m:
        return m.group(1).strip()
    return text.strip()


def make_sparql_prompt(schema_summary: str, question: str) -> str:
    return f"""{SPARQL_INSTRUCTIONS}

SCHEMA SUMMARY:
{schema_summary}

QUESTION:
{question}

Return only the SPARQL query in a code block.
"""


def generate_sparql(question: str, schema_summary: str) -> str:
    raw = ask_local_llm(make_sparql_prompt(schema_summary, question))
    return extract_sparql_from_text(raw)


# ----------------------------
# 5) Exécution SPARQL
# ----------------------------
def run_sparql(g: Graph, query: str) -> Tuple[List[str], List[Tuple[str, ...]]]:
    res = g.query(query)
    vars_ = [str(v) for v in res.vars]
    rows = [tuple(str(cell) if cell is not None else "" for cell in r) for r in res]
    return vars_, rows


# ----------------------------
# 6) Self-repair
# ----------------------------
REPAIR_INSTRUCTIONS = """
The previous SPARQL failed to execute. Using the SCHEMA SUMMARY and the ERROR MESSAGE,
return a corrected SPARQL 1.1 SELECT query.

Follow strictly:
- Use only known prefixes, predicates, and terms shown in the schema summary.
- Keep the query simple and robust.
- If a prefix is missing, add it.
- If labels are not reliable, avoid them.
- Return only a single fenced code block labeled ```sparql
"""

def repair_sparql(schema_summary: str, question: str, bad_query: str, error_msg: str) -> str:
    prompt = f"""{REPAIR_INSTRUCTIONS}

SCHEMA SUMMARY:
{schema_summary}

ORIGINAL QUESTION:
{question}

BAD SPARQL:
{bad_query}

ERROR MESSAGE:
{error_msg}

Return only the corrected SPARQL in a code block.
"""
    raw = ask_local_llm(prompt)
    return extract_sparql_from_text(raw)


# ----------------------------
# 7) Pipeline RAG
# ----------------------------
def validate_sparql_candidate(query: str) -> None:
    q = query.strip().lower()
    if not q:
        raise ValueError("Empty SPARQL query generated.")
    if "select" not in q:
        raise ValueError("Only SELECT queries are allowed.")

def answer_with_sparql_generation(
    g: Graph,
    schema_summary: str,
    question: str,
    try_repair: bool = True
) -> dict:
    try:
        sparql = generate_sparql(question, schema_summary)
    except Exception as e:
        return {
            "query": "",
            "vars": [],
            "rows": [],
            "repaired": False,
            "error": f"SPARQL generation failed: {e}"
        }

    try:
        vars_, rows = run_sparql(g, sparql)
        return {
            "query": sparql,
            "vars": vars_,
            "rows": rows,
            "repaired": False,
            "error": None
        }

    except Exception as e:
        first_error = str(e)

        if try_repair:
            try:
                repaired_query = repair_sparql(schema_summary, question, sparql, first_error)

                vars_, rows = run_sparql(g, repaired_query)
                return {
                    "query": repaired_query,
                    "vars": vars_,
                    "rows": rows,
                    "repaired": True,
                    "error": None
                }

            except Exception as e2:
                return {
                    "query": repaired_query if "repaired_query" in locals() else sparql,
                    "vars": [],
                    "rows": [],
                    "repaired": True,
                    "error": str(e2)
                }

        return {
            "query": sparql,
            "vars": [],
            "rows": [],
            "repaired": False,
            "error": first_error
        }

# ----------------------------
# 8) Baseline sans RAG
# ----------------------------
def answer_no_rag(question: str) -> str:
    prompt = f"""Answer the following question as best as you can.
If you are unsure, say you are unsure.

Question:
{question}
"""
    return ask_local_llm(prompt)


# ----------------------------
# 9) Affichage CLI
# ----------------------------
def pretty_print_result(result: dict) -> None:
    if result is None:
        print("\n[Error] No result returned by answer_with_sparql_generation().")
        return

    if result.get("error"):
        print("\n[Execution Error]")
        print(result["error"])

    print("\n[SPARQL Query Used]")
    print(result.get("query", ""))

    print("\n[Repaired?]")
    print(result.get("repaired", False))

    vars_ = result.get("vars", [])
    rows = result.get("rows", [])

    if not rows:
        print("\n[No rows returned]")
        return

    print("\n[Results]")
    print(" | ".join(vars_))
    for r in rows[:20]:
        print(" | ".join(r))

    if len(rows) > 20:
        print(f"... (showing 20 of {len(rows)})")
        
# ----------------------------
# 10) Main
# ----------------------------
if __name__ == "__main__":
    g = load_graph(TTL_FILE)
    schema = build_schema_summary(g)

    print("\n=== Schema summary preview ===")
    print(schema[:3000])
    print("\n==============================")

    while True:
        q = input("\nQuestion (or 'quit'): ").strip()
        if q.lower() == "quit":
            break

        # version question-aware
        question_schema = build_question_aware_summary(g, q)

        print("\n--- Baseline (No RAG) ---")
        try:
            print(answer_no_rag(q))
        except Exception as e:
            print(f"Baseline failed: {e}")

        print("\n--- SPARQL-generation RAG ---")

        result = answer_with_sparql_generation(g, question_schema, q, try_repair=True)

        # DEBUG
        print("\n[DEBUG]")
        print("Type:", type(result))
        print("Content:", result)

        pretty_print_result(result)
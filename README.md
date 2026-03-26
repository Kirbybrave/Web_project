# Web Project

Knowledge Graph Construction, Reasoning, Embeddings, and RAG over RDF/SPARQL.

This repository contains a complete Semantic Web pipeline:
- data acquisition and information extraction
- knowledge base construction and alignment
- SWRL reasoning
- knowledge graph embeddings
- RAG over an RDF graph with SPARQL generation

---

## Repository structure

```text
Web_project-main/
├── Notebook/
│   ├── Web_td1.ipynb
│   ├── Web_td4(1).ipynb
│   ├── Web_td5_0.ipynb
│   ├── Web_TD6(1).ipynb
│   └── *.html
├── csv/
│   └── extracted_knowledge.csv
├── kg_artifacts/
│   ├── private_kb_v2.ttl
│   ├── alignment(1).ttl
│   ├── ontology(1).ttl
│   ├── expanded_kb_pruned.ttl
│   └── expanded_kb_stats.txt
├── kge/
│   ├── train_labels.txt
│   ├── valid_labels.txt
│   └── test_labels.txt
├── src/
│   ├── Code_Rag.py
│   ├── crawler_output.jsonl
│   └── family.owl.txt
├── requirements.txt
├── README.md
└── LICENSE
```

## Project overview

### 1. Data Acquisition and Information Extraction
The first stage collects web pages, cleans the text, and extracts named entities.

Main tools used:
- `trafilatura` for fetching and cleaning web content
- `spaCy` for named entity recognition
- `pandas` for storing extracted entities in CSV format

Main outputs:
- `src/crawler_output.jsonl`
- `csv/extracted_knowledge.csv`

### 2. KB Construction and Alignment
The knowledge base is built in RDF/Turtle format and enriched through alignment and expansion.

Main tools used:
- `rdflib`
- `SPARQLWrapper`
- Wikidata SPARQL endpoint

Main outputs:
- `kg_artifacts/private_kb_v2.ttl`
- `kg_artifacts/alignment(1).ttl`
- `kg_artifacts/ontology(1).ttl`
- `kg_artifacts/expanded_kb_pruned.ttl`
- `kg_artifacts/expanded_kb_stats.txt`

Current KB statistics from `expanded_kb_stats.txt`:
- Triplets: 123,022
- Entities: 106,462
- Relations: 86

### 3. SWRL Reasoning
The project includes SWRL reasoning experiments using Owlready2 and Pellet.

Examples include:
- reasoning on `family.owl`
- custom SWRL rules over the project domain

### 4. Knowledge Graph Embeddings
The repository includes train/validation/test label files for link prediction experiments.

Main tools used:
- `pykeen`
- `torch`
- `scikit-learn`
- `matplotlib`

Main outputs:
- `kge/train_labels.txt`
- `kge/valid_labels.txt`
- `kge/test_labels.txt`

### 5. RAG over RDF/SPARQL
The file `src/Code_Rag.py` implements a retrieval-augmented generation pipeline that:
- loads the RDF graph
- builds a schema summary
- generates SPARQL queries from natural language questions
- queries the graph
- optionally repairs invalid SPARQL queries

This script uses a **local Ollama model**.

Default configuration in the code:
- RDF file: `expanded_kb_pruned.ttl`
- Ollama endpoint: `http://localhost:11434/api/generate`
- model: `llama3.2:3b`

## Installation

### 1. Clone the repository
```bash
git clone <your-repo-url>
cd Web_project-main
```

### 2. Create a virtual environment
```bash
python -m venv .venv
```

Activate it:

**Windows**
```bash
.venv\Scripts\activate
```

**macOS / Linux**
```bash
source .venv/bin/activate
```

**Hardware requirements**
- CPU: standard laptop CPU (no GPU required)
- RAM: 8 GB recommended
- Storage: ~1–2 GB for data and models
- OS: Windows / macOS / Linux

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

## External dependencies

### Java
`owlready2` + Pellet reasoning requires Java to be installed and available in your system PATH.

### Ollama
To run the RAG pipeline, install Ollama and pull the model used in the script:

```bash
ollama pull llama3.2:3b
```

Then start Ollama locally so that the API is available at:
```text
http://localhost:11434
```

## How to run each module

### Open the notebooks
You can run the project notebook by notebook:
- `Notebook/Web_td1.ipynb`
- `Notebook/Web_td4(1).ipynb`
- `Notebook/Web_td5_0.ipynb`
- `Notebook/Web_TD6(1).ipynb`

### Run the RAG script
From the project root, make sure the RDF file path used in `src/Code_Rag.py` is correct.

Then run:
```bash
python src/Code_Rag.py
```

If needed, update the path of `TTL_FILE` inside the script so it points to:
```text
kg_artifacts/expanded_kb_pruned.ttl
```

### Screenshot of Demo

<p align="center">
  <img src="demo.png" width="800">
</p>

## Notes
- Some files keep their original export names such as `(1)` because they come from notebook exports.
- The HTML files are rendered versions of the notebooks and can be used for quick inspection.
- The repository mixes raw artifacts, notebooks, and exported reports, which is useful for reproducibility but can be cleaned later for a more polished public release.

## Suggested future cleanup
- rename files to remove spaces and `(1)` suffixes
- move scripts into a cleaner `src/` pipeline structure
- add a small dataset sample for easier testing
- add command-line arguments to `Code_Rag.py`

## License
This repository includes a `LICENSE` file. Reuse should follow the terms specified there.

# ragxray

> **Zero-LLM chunk-boundary diagnostics, fracture detector, and BM25 vs trigram retrieval debugger for RAG pipelines.**

[فارسی](README.fa.md) · [Interactive Chunk X-Ray & Docs](https://mrzroot.github.io/ragxray/)

## Quick Start

```bash
pip install .
ragxray inspect docs/ --chunk-size 800 --overlap 100 --html report.html
ragxray probe docs/ --query "authentication retry" --json
```

## License

[MIT](LICENSE)

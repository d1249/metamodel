# metamodel

## OWL и визуализация Mermaid

```bash
metamodel2owl \
  --input data/bank_metamodel_horizontal.yaml \
  --output build/bank-metamodel.ttl \
  --mermaid-output build/bank-metamodel.mmd \
  --format turtle \
  --base-iri "https://bank.example.com/metamodel#"
```

Флаг `--mermaid-output` создаёт файл с диаграммой Mermaid (`graph LR`), где
узлы соответствуют сущностям и их атрибутам, а рёбра — связям из метамодели.
Такой файл можно вставлять в Markdown или обрабатывать любым Mermaid-рендерером.

## Mermaid CLI with advanced styling

The repository now also contains a dedicated converter that produces richer Mermaid
views directly from the YAML metamodel:

```bash
python -m metamodel_to_mermaid \
  --input data/enterprise_metamodel.yaml \
  --output docs/metamodel-all.mmd \
  --view all \
  --diagram-type flow \
  --group-by level \
  --with-notes
```

To focus on a specific slice simply change the flags, for example to get a data ER view:

```bash
python -m metamodel_to_mermaid \
  --input data/enterprise_metamodel.yaml \
  --output docs/metamodel-data.mmd \
  --view data \
  --diagram-type er
```

These diagrams include level-based subgraphs, colored classes, stylised edges and an
inline legend and can be pasted straight into Markdown.

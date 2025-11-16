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

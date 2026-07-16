from precis.pipeline.coref import resolve_document

with open("backend/benchmarks/article_5_pages.txt", "r", encoding="utf-8") as f:
    text = f.read()

result = resolve_document(text)

print(f"Document length: {len(text):,} characters")
# print(result.text)
print(f"Processing time: {result.elapsed:.2f}s")

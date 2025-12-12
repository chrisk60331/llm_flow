from transformers import pipeline  # type: ignore[import]

nlp = pipeline("fill-mask", model="artifacts/distilbert-saas")
prompt = (
    "Treat every S3 bucket as a hidden [MASK]. "
)
results = nlp(prompt)
print([result['token_str'] for result in results])
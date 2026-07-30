# CHẮN model evaluation

`chan-ml-synthetic-v0.4.json` is the reproducible summary for the current
100,000-record synthetic run. The full local files are:

- `ml/data/generated/chan-synthetic.jsonl.gz`
- `ml/data/generated/chan-synthetic.jsonl.gz.manifest.json`
- `ml/artifacts/chan-signal-model.joblib`
- `ml/artifacts/validation-metrics.json`
- `ml/artifacts/test-metrics.json`

These files are ignored by Git because datasets and model binaries can become
large. Regenerate them using `ml/README.md`.

The reported numbers validate the pipeline and pass the architecture's overall
synthetic recall/false-positive gates. They are not a claim of production
quality. The template family was iterated during development, so this synthetic
test is not an untouched external benchmark. Release still requires the
architecture's frozen, human-labeled set of at least 100 permitted real scams
and 30 legitimate but suspicious messages.

The truncated-notification test slice is below 90% recall. Keep
`truncated=true`, lower user confidence, and request the complete message as
specified by the architecture.

# eval/ — Golden set & kết quả đo

## CHẮN ML synthetic baseline

The versioned synthetic run summary is available at
[`chan-ml-synthetic-v0.5.json`](chan-ml-synthetic-v0.5.json).
It records dataset provenance, model configuration, recall, false-positive
rate, truncated-notification performance, latency, and limitations.

The expanded 36-family hybrid run is recorded in
[`chan-ml-synthetic-v1.0.json`](chan-ml-synthetic-v1.0.json). Its final test is
explicitly a regression set: the first opening exposed negation failures and
was used for error analysis. It must not be presented as an untouched external
benchmark.

The full local outputs are generated under:

- `../codebase/ml/data/generated/chan-synthetic.jsonl.gz`
- `../codebase/ml/data/generated/chan-synthetic.jsonl.gz.manifest.json`
- `../codebase/ml/artifacts/chan-signal-model.joblib`
- `../codebase/ml/artifacts/validation-metrics.json`
- `../codebase/ml/artifacts/test-metrics.json`

These generated files are ignored by Git. Recreate them with the commands in
[`../codebase/ml/README.md`](../codebase/ml/README.md).

The synthetic metrics validate the pipeline, not production performance. The
template family was iterated during development, so this is not an untouched
external benchmark. Release still requires a frozen, human-labeled set with at
least 100 permitted real scam messages and 30 legitimate but suspicious
messages.

The v0.5 truncated-notification slice was below 90% recall. The v1.0 synthetic
regression is above that threshold, but clients must still preserve
`truncated=true`, lower user confidence, and ask for the complete message as
specified by the architecture.

Chấm theo rubric R4 (15 điểm) và checklist CP3.

| File | Nội dung |
|---|---|
| [golden-set.md](golden-set.md) | ≥20 case + expected behavior |
| [results.md](results.md) | Bảng kết quả từng lượt chạy, đủ mọi case |
| `runs/` | Output thô của từng lượt (raw log) |

## Cơ cấu golden set bắt buộc (R4, 4 điểm)

- ≥2 case cho **mỗi** lớp chỗ khó ①②③④ → ≥8 case
- 8-10 case **thường**
- 2-4 case **hiếm**
- ≥10 case lấy từ **chatlog thật** (`../../data/`)

## Nguyên tắc ghi kết quả

Ghi **đủ mọi case, kể cả case fail**. Kết quả thấp vẫn được tính đủ điểm nếu ghi nhận trung thực; số liệu bị chỉnh sửa hoặc che giấu thì không được tính.

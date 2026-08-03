### Task 2: `preference_model.py` writes a metadata sidecar

**Files:**
- Modify: `src/clawmarks/search/preference_model.py`
- Test: `tests/test_preference_model.py`

**Interfaces:**
- Consumes: nothing new.
- Produces: `MODEL_META_FILE` path constant and a metadata JSON file written by `main()` on
  every successful train. Task 4's `build/preference_status.py` reads this file.

**Context:** `main()` (lines 89-116 as of this plan's writing; locate by the `def main(argv=None):`
signature and the `joblib.dump(model, MODEL_FILE)` line if line numbers have drifted) currently
computes `acc` via `cross_validate(X, y)`, prints it, then discards it after writing the model.
This task adds a sidecar write right after `joblib.dump`.

- [ ] **Step 1: Write the failing test**

```python
# append to tests/test_preference_model.py
import json

import numpy as np


def test_main_writes_metadata_sidecar_on_successful_train(tmp_path, monkeypatch):
    from clawmarks.search import embed_cache

    rng = np.random.RandomState(0)
    yes_cluster = rng.normal(loc=5.0, scale=0.1, size=(30, 2))
    no_cluster = rng.normal(loc=-5.0, scale=0.1, size=(30, 2))
    embeddings = np.vstack([yes_cluster, no_cluster]).astype(np.float32)
    tags = [f"t{i}" for i in range(60)]
    embed_cache.save_cache(tmp_path / "embeddings.npz", tags, embeddings)

    ratings = {tags[i]: {"label": "yes" if i < 30 else "no", "rated_at": "t"} for i in range(60)}
    (tmp_path / "user_ratings.json").write_text(json.dumps(ratings))

    monkeypatch.setattr(preference_model, "SWEEP_DIR", tmp_path)
    monkeypatch.setattr(preference_model.embed_cache, "EMBEDDINGS_FILE", tmp_path / "embeddings.npz")
    monkeypatch.setattr(preference_model, "MODEL_FILE", tmp_path / "preference_model.joblib")
    monkeypatch.setattr(preference_model, "MODEL_META_FILE", tmp_path / "preference_model_meta.json")

    rc = preference_model.main([])
    assert rc == 0

    meta = json.loads((tmp_path / "preference_model_meta.json").read_text())
    assert meta["n_labels"] == 60
    assert meta["n_yes"] == 30
    assert meta["n_no"] == 30
    assert 0.0 <= meta["cv_accuracy"] <= 1.0
    assert "trained_at" in meta
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /workspace/trent-with-smart-prompts && PYTHONPATH=src uv run pytest tests/test_preference_model.py::test_main_writes_metadata_sidecar_on_successful_train -v`
Expected: FAIL (`AttributeError: module 'clawmarks.search.preference_model' has no attribute 'MODEL_META_FILE'`)

- [ ] **Step 3: Implement**

In `src/clawmarks/search/preference_model.py`:

Add near the top, after `import sys`:

```python
from datetime import datetime, timezone
```

Add next to the existing `MODEL_FILE = SWEEP_DIR / "preference_model.joblib"` line:

```python
MODEL_META_FILE = SWEEP_DIR / "preference_model_meta.json"
```

In `main()`, replace:

```python
    model = train(X, y)
    joblib.dump(model, MODEL_FILE)
    print(f"wrote {MODEL_FILE}", flush=True)
    return 0
```

with:

```python
    model = train(X, y)
    joblib.dump(model, MODEL_FILE)
    meta = {
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "n_labels": len(y),
        "n_yes": int(y.sum()),
        "n_no": len(y) - int(y.sum()),
        "cv_accuracy": round(acc, 4),
    }
    tmp = f"{MODEL_META_FILE}.tmp"
    with open(tmp, "w") as f:
        json.dump(meta, f)
    os.replace(tmp, MODEL_META_FILE)
    print(f"wrote {MODEL_FILE} and {MODEL_META_FILE}", flush=True)
    return 0
```

`os` is not currently imported in this file; add `import os` alongside the existing `import
json` / `import sys` lines at the top.

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /workspace/trent-with-smart-prompts && PYTHONPATH=src uv run pytest tests/test_preference_model.py -v`
Expected: PASS (all tests, including the new one)

- [ ] **Step 5: Commit**

```bash
git add src/clawmarks/search/preference_model.py tests/test_preference_model.py
git commit -m "feat(clawmarks): write preference model metadata sidecar on train"
```

---


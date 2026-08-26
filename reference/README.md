# OMP Reference Implementation (Python)

Reference implementation of the [Open Memory Protocol (OMP)](../README.md), targeting the harness contract and validation rules in [`spec/draft-v0.1.md`](../spec/draft-v0.1.md).

## Install

```bash
pip install -e .
```

## Use

```python
from open_memory_protocol import load_memory
from open_memory_protocol.loader import build_harness_context

memory = load_memory("./memory")           # validates + loads
ctx = build_harness_context(memory)        # implements the four-rule contract

# Rule 1: root markdown is in ctx.core_context
print(ctx.core_context)

# Rule 3: nested files are surfaced but not loaded
print(ctx.deferred_index)

# Rule 4: agent can selectively read a deferred file
print(ctx.read_deferred("notes/2026-08-12.md"))
```

## Validate without loading

```python
from open_memory_protocol import validate_memory, ValidationError

try:
    validate_memory("./memory")
except ValidationError as e:
    print(e)
```

## Test

```bash
pip install -e '.[dev]'
pytest
```

The test suite covers every valid and invalid memory configuration from the spec.

## Scope

This implementation targets the current draft (v0.1). It is intentionally minimal: no storage backend, no synchronization, no context-window budgeting. Those belong to harnesses and memory-layer providers, not to the protocol layer.

## License

Apache 2.0 (see [LICENSE](../LICENSE)).

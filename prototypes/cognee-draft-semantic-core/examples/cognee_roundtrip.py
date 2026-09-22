"""Two-way exchange with a real Cognee install, no shared engine on our side.

    our exchange --write_cogx--> COGX dir --cognee.remember(COGXArchiveSource)--> Cognee
    Cognee --cognee.export(format="cogx")--> COGX dir --read_cogx--> validate + import receipt

Run with the Python that has cognee installed and configured (LLM_* / EMBEDDING_* env), e.g.
    ~/.cognee-plugin/venv/bin/python examples/cognee_roundtrip.py ./work --mode re-derive
This package itself must also be importable by that interpreter (pip install -e .).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import shutil
from pathlib import Path


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("workdir")
    ap.add_argument("--mode", choices=["preserve", "re-derive", "hybrid"], default="re-derive")
    ap.add_argument("--dataset", default="omp_semantic_core_roundtrip")
    args = ap.parse_args()

    # Cognee reads LLM_API_KEY; fall back to the shared prototypes/.env OpenRouter key.
    import os

    for shared in (
        Path(__file__).resolve().parents[2] / ".env",
        Path(__file__).resolve().parents[3] / ".env",
    ):
        if shared.exists():
            for line in shared.read_text().splitlines():
                if "=" in line and not line.startswith("#"):
                    k, _, v = line.partition("=")
                    os.environ.setdefault(k.strip(), v.strip().strip("\"'"))
    if "LLM_API_KEY" not in os.environ and os.environ.get("OPENROUTER_API_KEY"):
        os.environ["LLM_API_KEY"] = os.environ["OPENROUTER_API_KEY"]

    import cognee
    from cognee.migration import COGXArchiveSource

    from semantic_core.adapters import from_packer_dir
    from semantic_core.cogx import read_cogx, write_cogx
    from semantic_core.schema import Exchange
    from semantic_core.store import SemanticStore
    from semantic_core.validator import FIXTURES_DIR, validate_exchange

    work = Path(args.workdir)
    out, back = work / "to_cognee", work / "from_cognee"
    shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True)

    packer = from_packer_dir(
        Path(__file__).resolve().parents[2]
        / "packer-draft-langchain-harness"
        / "examples"
        / "memory"
    )
    fx = Exchange.model_validate(
        json.loads((FIXTURES_DIR / "01_evidence_and_derivation.json").read_text())["exchange"]
    )
    ex = Exchange(
        manifest=packer.manifest.model_copy(update={"source_system": "omp-semantic-core"}),
        objects=packer.objects + fx.objects,
    )
    losses = write_cogx(ex, out)
    print(f"sent {len(ex.objects)} objects as COGX; {len(losses)} declared loss(es)")

    async def cleanup() -> None:
        from cognee.modules.data.methods import delete_dataset, get_datasets
        from cognee.modules.users.methods import get_default_user

        user = await get_default_user()
        for ds in await get_datasets(user.id):
            if ds.name == args.dataset:
                await delete_dataset(ds)

    await cleanup()
    res = await cognee.remember(
        COGXArchiveSource(out, mode=args.mode), dataset_name=args.dataset, self_improvement=False
    )
    print("cognee.remember ->", res)
    exp = await cognee.export(args.dataset, format="cogx", destination=str(back))
    print("cognee.export   ->", exp)
    await cleanup()

    got = read_cogx(back)
    errs = [f for f in validate_exchange(got) if f.level == "error"]
    print(f"read back {len(got.objects)} objects; validator errors: {len(errs)}")
    for n in got.manifest.notes:
        print("  note:", n)
    rcpt = SemanticStore("receiver", supported_extensions={"cogx"}).import_exchange(got)
    print("receipt:", rcpt.counts, "conflicts:", rcpt.conflicts or "none")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

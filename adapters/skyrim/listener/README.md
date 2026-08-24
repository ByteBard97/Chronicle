# ChronicleBridge listener

Receives the spatial-streamer's outbound POSTs
(`adapters/skyrim/contracts/chronicle-bridge.openapi.yaml`) and writes a
rolling JSON snapshot file the dashboard's existing polling machinery can
read -- per `docs/design/chronicle-bridge-spatial-streamer.md`'s B4
decision, this is a file-polling side-channel, not a live push server, so
the dashboard's static-read/no-backend property never changes.

Not part of `chronicle/` -- this is Skyrim-adapter-side plumbing, per
`adapters/skyrim/README.md`'s charter.

## Regenerating the model from the contract

The Pydantic model is generated from the OpenAPI spec, not hand-written --
that's the whole point of having one shared source of truth instead of
two independently-maintained schemas:

```
uv run datamodel-codegen \
    --input adapters/skyrim/contracts/chronicle-bridge.openapi.yaml \
    --input-file-type openapi \
    --output adapters/skyrim/listener/models.py
```

Regenerate and commit `models.py` whenever the contract changes -- never
hand-edit it.

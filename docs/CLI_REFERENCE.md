# CLI Reference

```powershell
gaia doctor
gaia projects list
gaia project show microgrow-v1
gaia project scan microgrow-v1
gaia project snapshot microgrow-v1
gaia project search microgrow-v1 "release readiness"
gaia project report microgrow-v1
gaia project report microgrow-v1 --format json --output data\reports\snapshot.json
gaia serve
```

Use `--config PATH` on commands to load an alternate project registry.

## Recommended order

1. `gaia doctor`
2. `gaia project scan microgrow-v1`
3. `gaia project snapshot microgrow-v1`
4. `gaia project report microgrow-v1`
5. `gaia project search microgrow-v1 "your question terms"`

# PubChem PUG REST quick reference

PUG REST is PubChem's public HTTP API. No API key. The base URL is:

    https://pubchem.ncbi.nlm.nih.gov/rest/pug

## Endpoint used by this skill

```
GET /compound/{namespace}/{identifier}/property/{properties}/JSON
```

| Component | Allowed values |
|---|---|
| `namespace` | `name`, `smiles`, `inchi`, `inchikey`, `cid` |
| `identifier` | URL-encoded query string |
| `properties` | comma-separated subset of `IUPACName, CanonicalSMILES, IsomericSMILES, InChI, InChIKey, MolecularWeight, MolecularFormula, ExactMass, MonoisotopicMass, Charge, ...` |

This skill requests:

    IUPACName,CanonicalSMILES,IsomericSMILES,InChI,InChIKey,MolecularWeight

## Response shape

```json
{
  "PropertyTable": {
    "Properties": [
      {
        "CID": 12519307,
        "IUPACName": "...",
        "CanonicalSMILES": "...",
        "IsomericSMILES": "...",
        "InChI": "InChI=1S/...",
        "InChIKey": "JRTIUDXYIUKIIE-KZUMESAESA-N",
        "MolecularWeight": 275.05
      }
    ]
  }
}
```

The skill takes the first row (PubChem ranks its preferred match first).

## Rate limits

PubChem's documented sustainable rate is ~5 requests/second per client. The client throttles to 4 req/s by default. On HTTP 429 or 503, it retries with exponential backoff respecting `Retry-After`.

## Common failure modes

| Status | Meaning | Client behavior |
|---|---|---|
| 200 | OK | parse and cache |
| 404 | not found | write fallback record, cache it |
| 400 | bad request (usually a malformed name) | write fallback record |
| 429 | rate limited | back off, retry |
| 503 | service unavailable | back off, retry |
| (network error) | DNS / connection / timeout | exponential backoff up to 4 attempts, then fallback |

## Misses worth knowing about

PubChem name resolution is good for:

- Common organic compounds and drugs.
- IUPAC names (full or partial).
- CAS registry numbers.

It is **bad** at:

- Organometallic compounds (the name space is sparse).
- Carbene ligands without their imidazolium form (try the imidazolium salt instead).
- Paper-internal codes (`"1"`, `"22"`, `"Ni-A"`) — these never resolve.
- Stereochemistry-only names — PubChem usually returns the racemate's CID and may strip wedge/dash info.

**The mitigation is `fallback_smiles`.** Always supply it for paper-extracted compounds.

## When to skip PubChem entirely

If you already have a verified SMILES and only want canonicalization / InChI generation, use RDKit directly — don't pay the HTTP roundtrip.

## URL examples

| Goal | URL |
|---|---|
| Resolve "pyridine" | `/compound/name/pyridine/property/IUPACName,CanonicalSMILES,InChIKey,MolecularWeight/JSON` |
| Resolve SMILES `c1ccncc1` | `/compound/smiles/c1ccncc1/property/.../JSON` |
| InChIKey lookup | `/compound/inchikey/JUJWROOIHBZHMG-UHFFFAOYSA-N/property/.../JSON` |
| Get the CID first | `/compound/name/pyridine/cids/JSON` (returns `{"IdentifierList": {"CID": [1049]}}`) |

The skill always uses the one-shot `property` endpoint — fewer roundtrips, single cache key.

## References

- PUG REST tutorial: https://pubchem.ncbi.nlm.nih.gov/docs/pug-rest-tutorial
- PUG REST reference: https://pubchem.ncbi.nlm.nih.gov/docs/pug-rest

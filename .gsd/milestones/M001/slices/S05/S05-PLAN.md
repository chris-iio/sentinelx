# S05: Context And Staleness

**Goal:** Key context fields and cache age are visible in the IOC card header without requiring any accordion expansion.
**Demo:** IP IOCs show GeoIP country and ASN org in card header; domain IOCs show registrar in card header; cached results show staleness indicator ("data from 4h ago"); all 91 E2E tests pass.

## Must-Haves

- [ ] For IP IOCs, GeoIP country and ASN org visible in card header (CTX-01)
- [ ] For domain IOCs, registrar visible in card header (CTX-01)
- [ ] Cached results show staleness indicator in summary row (CTX-02)
- [ ] Context fields degrade gracefully when data unavailable
- [ ] All 91 E2E tests pass

## Tasks


## Files Likely Touched

- `app/static/src/ts/modules/enrichment.ts`
- `app/static/src/ts/modules/row-factory.ts`
- `app/static/src/input.css`
- `app/templates/partials/_ioc_card.html`

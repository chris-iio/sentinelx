# S04: Template Restructuring

**Goal:** The HTML template delivers three explicit sections — Reputation, Infrastructure Context, No Data — as the structural backbone of each IOC card.
**Demo:** Each IOC card visibly organizes provider results under three labeled sections; all data-ioc-value, data-ioc-type, and data-verdict attributes remain on .ioc-card root element; URL IOC detail links resolve correctly; all 91 E2E tests pass.

## Must-Haves

- [ ] Each IOC card has three labeled sections: Reputation, Infrastructure Context, and No Data (GRP-01)
- [ ] data-ioc-value, data-ioc-type, and data-verdict attributes remain on .ioc-card root element
- [ ] URL IOC detail links resolve correctly (`<path:>` route contract preserved)
- [ ] All 91 E2E tests pass at zero failures

## Tasks


## Files Likely Touched

- `app/templates/partials/_ioc_card.html`
- `app/templates/partials/_enrichment_slot.html`
- `app/static/src/input.css`

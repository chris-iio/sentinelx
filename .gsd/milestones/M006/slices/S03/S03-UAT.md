# S03: URL IOC End-to-End Polish — UAT

**Milestone:** M006
**Written:** 2026-03-25T12:04:52.798Z

## UAT: S03 — URL IOC End-to-End Polish

### Preconditions
- SentinelX running locally (`make run` or `flask run`)
- Browser with DevTools available
- No API keys required (offline mode tests, or mocked enrichment)

### Test 1: URL IOC Card Renders from Pasted Text
1. Navigate to the home page
2. Paste the following text into the input area:
   ```
   Check this malicious URL: https://evil.example.com/payload.exe found in phishing email
   ```
3. Click "Extract & Analyze" (offline mode)
4. **Expected:** Results page shows at least one IOC card with `data-ioc-type="url"` containing the extracted URL

### Test 2: URL Type Badge Display
1. From Test 1 results, locate the URL IOC card
2. **Expected:** A `.ioc-type-badge--url` badge is visible on the card containing the text "URL"

### Test 3: URL Filter Pill Present
1. From Test 1 results, look at the filter bar above the IOC cards
2. **Expected:** A filter pill labeled "URL" (`.filter-pill--url`) is visible

### Test 4: URL Filter Pill Filtering
1. Paste mixed IOC text:
   ```
   URL: https://evil.example.com/payload.exe IP: 8.8.8.8 Domain: evil.com
   ```
2. Submit in offline mode
3. Click the "URL" filter pill
4. **Expected:** Only URL-type cards are visible; IP and domain cards are hidden
5. **Expected:** The URL pill has active styling (`.filter-pill--active`)

### Test 5: "All Types" Reset
1. From Test 4 (URL filter active), click the "All Types" pill
2. **Expected:** All IOC cards (URL, IP, domain) are visible again

### Test 6: Detail Link Href Correctness
1. Submit a URL IOC in online mode (or with mocked enrichment)
2. Wait for enrichment to complete (summary row appears)
3. Inspect the "View full detail →" link
4. **Expected:** `href` contains `/ioc/url/` (not `/detail/url/`)
5. Click the detail link
6. **Expected:** Detail page loads with HTTP 200 (not 404)

### Test 7: URL Detail Route with Slashes
1. In the browser address bar, navigate to `/ioc/url/https://evil.com/payload.exe`
2. **Expected:** Page loads with HTTP 200 — the Flask `<path:ioc_value>` converter handles the slashes in the URL value

### Edge Cases
- URL containing query parameters (e.g., `https://evil.com/page?id=1&token=abc`) should render correctly in the card and detail link
- URL containing fragments (e.g., `https://evil.com/page#section`) should be extractable and displayable
- Multiple URLs in the same input text should each produce their own IOC card

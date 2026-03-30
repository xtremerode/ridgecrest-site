#!/usr/bin/env python3
import sys
import re
import json
import urllib.request

def fetch(url):
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
    })
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.read().decode('utf-8', errors='replace')
    except Exception as e:
        return f"ERROR: {e}"

def extract(url, html):
    print(f"\n{'='*60}")
    print(f"PAGE: {url}")
    print('='*60)

    # Title
    titles = re.findall(r'<title>(.*?)</title>', html, re.IGNORECASE)
    for t in titles:
        print(f"TITLE: {t}")

    # Meta description
    for m in re.finditer(r'<meta\s+[^>]+>', html, re.IGNORECASE):
        tag = m.group(0)
        if 'description' in tag.lower():
            content = re.search(r'content=["\']([^"\']*)["\']', tag)
            if content:
                print(f"META DESC: {content.group(1)}")

    # OG tags
    for m in re.finditer(r'<meta\s+[^>]+>', html, re.IGNORECASE):
        tag = m.group(0)
        if 'og:' in tag.lower():
            prop = re.search(r'property=["\']([^"\']*)["\']', tag)
            content = re.search(r'content=["\']([^"\']*)["\']', tag)
            if prop and content:
                print(f"OG {prop.group(1)}: {content.group(1)}")

    # JSON-LD schemas
    schemas = re.findall(r'<script[^>]*application/ld\+json[^>]*>(.*?)</script>', html, re.DOTALL | re.IGNORECASE)
    for i, s in enumerate(schemas):
        try:
            parsed = json.loads(s)
            print(f"\nSCHEMA {i+1}:")
            print(json.dumps(parsed, indent=2)[:4000])
        except Exception:
            print(f"\nSCHEMA {i+1} (raw): {s[:1000]}")

    # Wix stores page data in __NEXT_DATA__ or window.__WIX_DATA__ or similar
    wix_data = re.findall(r'window\.__(?:WIX|BOLT|FEDOPS)[^=]*=\s*({.*?});\s*\n', html, re.DOTALL)
    for w in wix_data[:3]:
        print(f"\nWIX DATA: {w[:2000]}")

    # Look for any readable text strings in JSON (length > 20 chars, no special chars)
    text_pattern = re.compile(r'"(?:text|value|label|content|description|title|name|heading|buttonText|linkText|plainText|displayName|fullName|bio|paragraph|subtitle|caption|altText|tooltipText)":\s*"([^"\\]{15,})"')
    texts = text_pattern.findall(html)
    seen = set()
    print("\n--- JSON TEXT FIELDS ---")
    for t in texts:
        clean = t.strip()
        if clean not in seen and not clean.startswith('http') and not clean.startswith('{'):
            seen.add(clean)
            print(f"  {clean}")

    # Also look for Wix component data patterns
    comp_texts = re.findall(r'"(?:txt|richText|html|wixRichText)":\s*"(<[^"]*>|[^"]{20,})"', html)
    if comp_texts:
        print("\n--- COMPONENT TEXT ---")
        for t in comp_texts[:30]:
            print(f"  {t[:300]}")

    # Look for phone numbers
    phones = re.findall(r'[\+1\-\(]?\d{3}[\-\.\)\s]\d{3}[\-\.]\d{4}', html)
    if phones:
        print(f"\nPHONE NUMBERS FOUND: {list(set(phones))}")

    # Look for email addresses
    emails = re.findall(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}', html)
    if emails:
        emails_clean = [e for e in set(emails) if 'wix' not in e.lower() and 'google' not in e.lower() and 'schema' not in e.lower()]
        if emails_clean:
            print(f"\nEMAIL ADDRESSES: {emails_clean}")

    # Look for addresses
    addrs = re.findall(r'\d+\s+[A-Z][a-z]+\s+(?:Blvd|St|Ave|Dr|Rd|Way|Lane|Ln|Court|Ct|Place|Pl)[^<"]{0,50}', html)
    if addrs:
        print(f"\nADDRESS PATTERNS: {list(set(addrs))[:5]}")

urls = [
    "https://www.ridgecrestdesigns.com",
    "https://www.ridgecrestdesigns.com/about",
    "https://www.ridgecrestdesigns.com/bios",
    "https://www.ridgecrestdesigns.com/california-process",
    "https://www.ridgecrestdesigns.com/portfolio",
    "https://www.ridgecrestdesigns.com/contact",
    "https://www.ridgecrestdesigns.com/testimonials",
    "https://www.ridgecrestdesigns.com/therdedit",
]

for url in urls:
    html = fetch(url)
    if not html.startswith("ERROR"):
        extract(url, html)
    else:
        print(f"\nFAILED: {url} — {html}")

"""
One-time helper: generate a new Google Ads OAuth2 refresh token.
Uses plain OAuth2 (no PKCE) so the code can be exchanged without a live process.
Usage:  source venv/bin/activate && python get_google_token.py
"""
import os
import sys
from urllib.parse import urlencode, urlparse, parse_qs

import requests
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID     = os.getenv("GOOGLE_CLIENT_ID")
CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
REDIRECT_URI  = "http://127.0.0.1:8080"
SCOPE         = "https://www.googleapis.com/auth/adwords"
AUTH_URI      = "https://accounts.google.com/o/oauth2/auth"
TOKEN_URI     = "https://oauth2.googleapis.com/token"

params = {
    "response_type": "code",
    "client_id":     CLIENT_ID,
    "redirect_uri":  REDIRECT_URI,
    "scope":         SCOPE,
    "access_type":   "offline",
    "prompt":        "consent",
}
auth_url = AUTH_URI + "?" + urlencode(params)

print("\n" + "="*60)
print("STEP 1: Open this URL in your browser:\n")
print(auth_url)
print("\n" + "="*60)
print("STEP 2: Authorize with the Google account that owns the")
print("        Google Ads manager account (4478944999).")
print("\nSTEP 3: You'll be redirected to http://127.0.0.1:8080/...")
print("        The page won't load — that's fine.")
print("        Copy the FULL URL from your browser address bar.")
print("="*60 + "\n")

redirect_response = input("Paste the full redirect URL here: ").strip()

parsed = urlparse(redirect_response)
qs     = parse_qs(parsed.query)

if "error" in qs:
    print(f"\nGoogle returned an error: {qs['error']}")
    sys.exit(1)

if "code" not in qs:
    print("\nNo authorization code found. Did you paste the full URL?")
    sys.exit(1)

code = qs["code"][0]

resp = requests.post(TOKEN_URI, data={
    "code":          code,
    "client_id":     CLIENT_ID,
    "client_secret": CLIENT_SECRET,
    "redirect_uri":  REDIRECT_URI,
    "grant_type":    "authorization_code",
})

data = resp.json()

if "refresh_token" not in data:
    print(f"\nToken exchange failed: {data}")
    sys.exit(1)

refresh_token = data["refresh_token"]

print("\n" + "="*60)
print("SUCCESS — new refresh token:\n")
print(refresh_token)
print("="*60 + "\n")

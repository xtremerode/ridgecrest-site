# Turnkey Ad Management Application - Business Plan
## Working Title: TBD (needs branding)
## Author: Henry / Perplexity
## Date: April 11, 2026
## Status: DRAFT - Awaiting Henry's approval

---

## The Opportunity

### What We Built for Ridgecrest (The Prototype)
Over 2 days, we built a complete Google Ads management system from scratch:
- 246 researched keywords across 7 themed ad groups
- 201 negative keywords across 10 categories
- City-specific targeting verified against actual zip codes
- Neighborhood targeting verified via golf course/country club mapping
- Themed RSA ads per service category
- Competitive intelligence (auction insights, competitor research)
- Fact-based guardrails preventing guesswork
- All documented in MD files on a persistent server

### What Exists Today (The Competition)
| Tool | Price | What It Does | What It Doesn't Do |
|------|-------|-------------|-------------------|
| Optmyzr | $249+/mo | Rule-based optimization, bid management | Doesn't build campaigns, doesn't know your industry |
| WordStream/LocaliQ | $300+/mo bundled | Guided suggestions, basic optimization | Generic across all industries, no deep keyword research |
| groas.ai | $79/mo | Autonomous bid/budget management | Doesn't structure campaigns, doesn't research neighborhoods |
| Ryze AI | ~$40/mo | Cross-platform bid automation | No industry knowledge, no keyword research |
| Adzooma | Free-$99/mo | Basic monitoring, opportunity reports | Surface-level, no campaign building |
| Google Ads Scripts | Free | Full automation power | Requires developer skills — zero business owners can use this |
| Agencies | $1,500-$5,000/mo | Full service management | Expensive, opaque, often ghost clients after onboarding |

Sources: cotera.co, groas.ai, dynares.ai, segwise.ai, g2.com (all retrieved April 11, 2026)

### The Gap Nobody Is Filling
Every tool above either:
1. **Optimizes existing campaigns** but doesn't build them (Optmyzr, groas, Ryze)
2. **Gives generic advice** that applies to any industry (WordStream, Adzooma)
3. **Requires technical skills** no business owner has (Google Ads Scripts, Google Ads API)
4. **Costs too much** for small/mid businesses (agencies, Skai, SA360)

**Nobody is doing what we did:**
- Industry-specific keyword research based on actual search volume data
- Geo-targeting verified against zip codes with city/neighborhood mapping
- Golf course method for identifying affluent neighborhoods
- Themed ad groups with service-specific RSA ads
- Comprehensive negative keyword lists by industry
- Fact-based guardrails that prevent wasting money on guesses
- All of this automated and packaged for a business owner who doesn't know what a script is

### Why This Is a 1,000% Advantage
Per research:
- "only 50.1% of contractor accounts with tracking monitor meaningful conversions" (Disruptive Advertising via cyberoptik.net)
- Most small businesses waste 20-40% of ad spend on irrelevant queries (groas.ai, Feb 2026)
- BG Collective saw 40% quality improvement just from adding 200+ negative keywords
- Average contractor is using broad match with no negatives, no themed ad groups, no neighborhood targeting
- Business owners don't know what a script is, what it does, or how to run one (Henry's observation)
- Most agency relationships fail due to ghosting and lack of transparency (thinkdmg.com)

---

## The Product Vision

### What It Does (For the Business Owner)
A business owner answers a series of questions:
1. What industry are you in? (remodeling, HVAC, plumbing, roofing, etc.)
2. What specific services do you offer? (kitchen remodel, bathroom remodel, additions, etc.)
3. What zip codes do you serve?
4. What is your price positioning? (luxury, mid-range, budget)
5. What is your monthly ad budget?

The app then automatically:
- **Generates a complete keyword list** — verified against search volume data, organized by service type, with city and neighborhood variants for every zip code
- **Generates a comprehensive negative keyword list** — industry-specific, pre-built from research
- **Creates themed ad groups** — one per service category, each with a tailored RSA ad
- **Identifies affluent neighborhoods** using the golf course/country club mapping method
- **Sets geo-targeting** verified against Google's geo target database
- **Deploys everything** to the Google Ads account via Scripts or API
- **Monitors performance** and provides plain-English reports ("Your kitchen remodel ads in Walnut Creek got 12 clicks this week at $18 per click")

### What It Does NOT Do
- It does not guess. Every keyword has a source.
- It does not use generic templates. Everything is built from industry + geo research.
- It does not require the business owner to understand Google Ads.
- It does not hide behind jargon. Reports are in plain English.

---

## Revenue Model Options

### Option A: SaaS Subscription
- $199-$499/month depending on ad spend tier
- Includes campaign building, monitoring, and weekly reports
- Undercuts agencies ($1,500-$5,000/mo) by 70-90%
- Competes on depth vs. groas ($79/mo) and Optmyzr ($249/mo) which don't build campaigns

### Option B: Done-For-You Setup + SaaS Monitoring
- $1,500-$3,000 one-time setup fee (campaign build, keyword research, ad creation)
- $99-$199/month ongoing monitoring and optimization
- Appeals to business owners who want someone else to handle setup

### Option C: White-Label for Agencies
- Agencies license the platform to build campaigns for their clients
- $499-$999/month per agency seat
- Agencies charge their clients $1,500-$5,000/month, use the platform to deliver
- Solves the "agency ghosting" problem by automating the work

---

## Competitive Moat

### What Makes This Defensible
1. **Industry-specific knowledge bases** — the keyword research, negative lists, ad copy templates, and neighborhood mapping we build for each vertical (remodeling, HVAC, roofing, etc.) are proprietary datasets that take weeks to compile. Competitors would need to replicate this for every industry.
2. **The golf course method** — using country clubs and golf courses to identify affluent neighborhoods for targeting is a novel approach nobody else is using in ad tech.
3. **Fact-based guardrails** — the system refuses to add a keyword without verified search volume, refuses to target a city without verifying it maps to a zip code in the campaign. This discipline is baked into the product, not dependent on a human remembering to check.
4. **The Ridgecrest playbook** — we're not theorizing. We built this live, fixed real errors, and documented every step. The product is built from a proven, battle-tested process.

---

## Technical Architecture (High Level)

### Data Layer
- Industry keyword databases (built from research, stored per vertical)
- Google Geo Targets CSV (official, updated quarterly)
- Negative keyword master lists (by industry)
- Golf course / country club database (for neighborhood identification)
- Ad copy templates (by service category)

### Campaign Builder
- Takes user inputs (industry, services, zip codes, budget, positioning)
- Cross-references keyword database with geo targets
- Generates ad groups, keywords, negatives, and RSA ads
- Outputs as Google Ads Scripts (immediate) or via Google Ads API (future)

### Monitoring Layer
- Pulls search term reports automatically
- Flags keywords with zero impressions (14-day rule)
- Identifies new negative keyword opportunities
- Generates plain-English performance reports

### User Interface
- Simple dashboard — no Google Ads jargon
- "Your ads got 47 clicks this week. Kitchen remodel ads performed best. 3 new irrelevant search terms were blocked."
- One-click approval for recommended changes

---

## Phase 1: What We Build First

### Remodeling / Home Services Vertical
- This is our strongest vertical — we have the complete playbook from Ridgecrest
- Target market: remodeling contractors, design-build firms, kitchen/bath specialists, general contractors
- Estimated market: 300,000+ licensed contractors in the US (source: IBIS World)
- Average Google Ads spend: $2,000-$10,000/month for active advertisers

### Deliverables for Phase 1
1. Productize the Ridgecrest keyword research methodology into a repeatable process
2. Build the golf course neighborhood identification system
3. Create ad copy templates for each remodeling service category
4. Build the campaign generator (inputs → keywords + ad groups + ads + negatives)
5. Build a simple dashboard for monitoring
6. Beta test with 5-10 contractors

---

## What We Need to Decide

1. **Product name and branding**
2. **Which revenue model** (SaaS, done-for-you, white-label, or hybrid)
3. **Platform priority** — Google Ads first, then Meta, then Microsoft? Or all at once?
4. **Build vs. partner** — build the tech ourselves or partner with an existing platform
5. **Target customer** — solo contractors, mid-size firms, or agencies?
6. **Timeline and budget** for Phase 1 MVP

---

## Immediate Next Steps (If Approved)

1. Document every process from the Ridgecrest build as a reusable template
2. Research 2-3 additional verticals (HVAC, roofing, plumbing) to validate the methodology works beyond remodeling
3. Map out the MVP feature set
4. Research technical requirements (Google Ads API access, hosting, UI framework)
5. Identify potential beta testers from Henry's network

---

## Sources
- cotera.co/articles/best-ai-tools-google-ads (March 2026)
- groas.ai/post/the-ai-tools-reshaping-google-ads-in-2026-the-definitive-ranking (Feb 2026)
- dynares.ai/resources/blog/google-ads-automation-tools (2026)
- segwise.ai/blog/top-ai-tools-google-ads-management-2026 (April 2026)
- g2.com/products/google-ads/competitors/alternatives (2024)
- thinkdmg.com - home services marketing problems (June 2025)
- cyberoptik.net - why contractors fail at Google Ads (Sept 2025)
- bgcollective.com - Google Ads for remodelers 2026 (Jan 2026)
- elescendmarketing.com - Google Ads for small businesses (April 2026)
- flyinglionmedia.net - why Google Ads stop working (Feb 2026)

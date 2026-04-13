# SEO Website Build — Complete Architecture for Claude Code

**Read all files in `/home/claudeuser/agent/ridgecrest-agency/rules/` before starting. Read `/home/claudeuser/agent/ridgecrest-agency/campaigns/seo_content_plan_2026_04_11.md` for full content guidelines.**

---

## OVERVIEW

Build out the complete SEO page architecture for Ridgecrest Designs. This includes 83 new service+city pages, 13 Blackhawk pages, 68 blog posts, team member pages, and all internal linking. The goal is to dominate organic search for luxury remodeling in the East Bay by creating a dedicated landing page for every service+city combination and supporting blog content.

---

## WHAT ALREADY EXISTS (DO NOT RECREATE)

### Service+City Pages (60 pages across 5 service types x 12 cities)
- `kitchen-remodel-[city]` x 12 cities
- `bathroom-remodel-[city]` x 12 cities
- `whole-house-remodel-[city]` x 12 cities
- `design-build-[city]` x 12 cities
- `custom-home-builder-[city]` x 12 cities

### Location Hub Pages (12)
- `services/alamo.html`, `services/danville.html`, `services/diablo.html`, `services/dublin.html`, `services/lafayette.html`, `services/moraga.html`, `services/orinda.html`, `services/pleasanton.html`, `services/rossmoor.html`, `services/san-ramon.html`, `services/sunol.html`, `services/walnut-creek.html`

### Service Category Pages (4)
- `kitchen-remodels.html`, `bathroom-remodels.html`, `whole-house-remodels.html`, `custom-homes.html`

### Project Pages (18)
- alamo-luxury, castro-valley-villa, danville-dream, danville-hilltop, lafayette-bistro, lafayette-luxury, lakeside-cozy-cabin, livermore-farmhouse-chic, napa-retreat, newark-minimal-kitchen, orinda-kitchen, pleasanton-cottage-kitchen, pleasanton-custom, pleasanton-garage, san-ramon, san-ramon-eclectic-bath, sierra-mountain-ranch, sunol-homestead

### Other Pages
- index.html, about.html, process.html, portfolio.html, allprojects.html, contact.html, services.html, team.html, start-a-project.html, sitemap.html

### Blog
- Blog is served at `/blog` via the preview server with a database backend (`blog_posts` table in PostgreSQL). Blog posts are stored in the database, not as static HTML files. The nav links to `/blog` as "The RD Edit."

---

## PHASE 1: NEW SERVICE+CITY PAGES (83 pages)

### 6 New Service Types × 12 Existing Cities = 72 pages

Create pages in `/home/claudeuser/agent/preview/services/` using the same template structure as existing service+city pages (e.g., `kitchen-remodel-danville.html`).

**New service types:**
1. `home-addition-[city]` × 12
2. `adu-contractor-[city]` × 12
3. `interior-designer-[city]` × 12
4. `architect-[city]` × 12
5. `general-contractor-[city]` × 12
6. `home-renovation-[city]` × 12

**12 cities:** Alamo, Danville, Diablo, Dublin, Lafayette, Moraga, Orinda, Pleasanton, Rossmoor, San Ramon, Sunol, Walnut Creek

### Blackhawk Pages = 11 pages

Blackhawk is a new city not in the current 12. Create ALL 11 service types for Blackhawk:
- `kitchen-remodel-blackhawk.html`
- `bathroom-remodel-blackhawk.html`
- `whole-house-remodel-blackhawk.html`
- `design-build-blackhawk.html`
- `custom-home-builder-blackhawk.html`
- `home-addition-blackhawk.html`
- `adu-contractor-blackhawk.html`
- `interior-designer-blackhawk.html`
- `architect-blackhawk.html`
- `general-contractor-blackhawk.html`
- `home-renovation-blackhawk.html`

Also create a Blackhawk location hub page: `services/blackhawk.html`

### Page Template Requirements

Each page MUST include:
1. Proper `<head>` with title, meta description, canonical URL, OG tags, Twitter card
2. JSON-LD structured data (LocalBusiness + Service schema) — follow the exact format in existing pages like `kitchen-remodel-danville.html`
3. Nav bar (same as all other pages)
4. Content body (400-600 words, see content rules below)
5. Internal linking sections at bottom
6. Footer (same as all other pages)
7. Link to `/start-a-project.html` for all CTAs (NOT `/book` or `/contact`)

### Content Rules — TWO TYPES

**Type A — Pages where Ridgecrest has completed a project in that city/service:**
Reference the actual project. Link to the project page. Example: kitchen-remodel-danville can reference the Danville Dream or Danville Hilltop project.

**Project-to-city mapping:**
- Alamo: alamo-luxury
- Castro Valley: castro-valley-villa
- Danville: danville-dream, danville-hilltop
- Lafayette: lafayette-bistro, lafayette-luxury
- Livermore: livermore-farmhouse-chic
- Napa: napa-retreat
- Newark: newark-minimal-kitchen
- Orinda: orinda-kitchen
- Pleasanton: pleasanton-cottage-kitchen, pleasanton-custom, pleasanton-garage
- San Ramon: san-ramon, san-ramon-eclectic-bath
- Sierra: sierra-mountain-ranch
- Sunol: sunol-homestead

**Type B — Pages where NO project exists for that city/service:**
Do NOT fabricate project references. Reference nearby completed work: "Our team has completed projects throughout the Tri-Valley, including neighboring [city]" — link to those project pages. Focus on area expertise and service description.

### Content Differentiation — EACH PAGE MUST BE UNIQUE

Do NOT swap city names in identical content. Use these city-specific details:

- **Walnut Creek**: Mid-century homes near downtown, Rossmoor 55+ community nearby, hillside properties, Rudgear Estates luxury area, Walnut Heights custom homes
- **Danville**: Downtown historic charm, Blackhawk luxury estates adjacent, family-oriented neighborhoods, Crow Canyon area
- **Lafayette**: Happy Valley estates ($4-5M), hillside lots, artistic community character
- **Pleasanton**: Ruby Hill guard-gated, Castlewood country club area, downtown Main Street corridor
- **San Ramon**: Dougherty Valley newer homes, Gale Ranch, Canyon Lakes golf community
- **Alamo**: Round Hill Country Club, large lots, equestrian properties, Diablo adjacent
- **Orinda**: Sleepy Hollow hillside, Orinda Downs largest homes, Orinda Country Club
- **Dublin**: Newer construction, master-planned communities, growing families
- **Moraga**: Moraga Country Club, St. Mary's College area, canyon setting
- **Sunol**: Rural character, larger parcels, agricultural heritage
- **Blackhawk**: 6 gated communities, $2M+ median, Blackhawk Country Club (2 courses), ultra-luxury
- **Rossmoor**: 55+ active adult community, remodel-heavy (aging homes needing updates)
- **Diablo**: $3M-$8M estates, Diablo Country Club, exclusive and secluded

### Service-Specific Content Details

- **Home Addition**: Second story, room addition, bump-out, foundation requirements, permits, Contra Costa County regulations
- **ADU**: California ADU regulations (2026), detached vs attached vs garage conversion, utility connections, rental income potential, Contra Costa County specifics
- **Interior Designer**: Space planning, material selection, color palette, furniture curation, lighting design, photo-realistic 3D renders
- **Architect**: Structural design, code compliance, permit drawings, hillside and complex lot expertise
- **General Contractor**: Project management, subcontractor coordination, permit pulling, inspection management
- **Home Renovation**: Updating finishes, modernizing systems (electrical, plumbing, HVAC), preserving character while modernizing

### Pricing (use where appropriate)
- Kitchen remodel: starts at $200K for small basic, $500K+ for high-end custom
- Bathroom remodel: at least $60K for master bath, over $100K for high-end
- ADU: over $500K
- Whole house remodel: varies by scope, premium positioning
- Custom home build: highest tier

### Brand Voice
- Confident and authoritative — tell clients what they need to hear, not what they want to hear
- Not yes men — too many professionals let the customer lead the design and it ends up looking bad
- Professional but direct — warm enough to be approachable, firm enough to be trusted
- 20+ years of photo-realistic renders at the highest quality — others use AI shortcuts and can't create realistic renders of the actual space

---

## PHASE 2: BLOG POSTS (68 new posts)

Blog posts are stored in the PostgreSQL database (`blog_posts` table), NOT as static HTML files. Use the existing blog infrastructure.

### Neighborhood Spotlights (15 posts)
1. "Remodeling Your Blackhawk Estate: What Luxury Homeowners Should Know"
2. "Kitchen Design Trends in Walnut Creek's Mid-Century Homes"
3. "Whole House Remodels in Alamo: Preserving Character While Modernizing"
4. "Why Pleasanton's Ruby Hill Homeowners Choose Design-Build"
5. "Hillside Remodeling in Lafayette's Happy Valley"
6. "Updating Your Orinda Sleepy Hollow Home"
7. "San Ramon's Dougherty Valley: When New Homes Need Customization"
8. "Dublin Home Additions: Adding Space for Growing Families"
9. "Moraga Canyon Living: Remodel Considerations for Wooded Properties"
10. "Rossmoor Kitchen Remodels: Designing for Active Adults"
11. "Diablo Estates: Custom Home Design for California's Most Exclusive Neighborhood"
12. "Danville Downtown Homes: Blending Historic Charm with Modern Function"
13. "Sunol Homestead Properties: Rural Remodeling with Luxury Finishes"
14. "ADU Construction in Contra Costa County: 2026 Regulations Explained"
15. "Round Hill and Castlewood: Remodeling in East Bay's Country Club Communities"

Each links to 3-5 relevant service+city pages for that area.

### Service Guides (15 posts)
1. "How Much Does a Kitchen Remodel Cost in the East Bay? (2026 Guide)"
2. "Design-Build vs. Traditional Contractor: Which Is Right for Your Project?"
3. "What to Expect During a Whole House Remodel"
4. "How to Choose an Interior Designer in the East Bay"
5. "ADU Construction in California: Everything You Need to Know in 2026"
6. "The Truth About Home Remodeling Timelines"
7. "Why We Use Photo-Realistic 3D Renders — And Why AI Shortcuts Don't Cut It"
8. "Home Additions vs. ADUs: Which Adds More Value?"
9. "What Does a Residential Architect Actually Do?"
10. "The Real Cost of a Master Bathroom Remodel"
11. "Custom Home Building in the East Bay: A Complete Process Guide"
12. "Why Your Remodel Needs a Design-Build Firm, Not Just a Contractor"
13. "Permit Requirements for Home Remodeling in Contra Costa County"
14. "How to Prepare Your Home and Family for a Major Remodel"
15. "5 Signs It's Time for a Whole House Remodel"

### Material & Design Trend Posts (15 posts)
1. "Top Kitchen Countertop Materials for 2026"
2. "Bathroom Tile Trends for Luxury East Bay Homes"
3. "Open Floor Plan vs. Defined Rooms: What Works for East Bay Living"
4. "Sustainable Building Materials for California Homes"
5. "Cabinet Trends: Shaker, Flat Panel, or Custom?"
6. "Lighting Design for Whole House Remodels"
7. "Flooring Options for High-End Kitchen Remodels"
8. "Smart Home Integration During Your Remodel"
9. "Indoor-Outdoor Living: Designing for East Bay's Climate"
10. "Color Trends in Luxury Interior Design for 2026"
11. "Natural Stone vs. Engineered Quartz: The Real Comparison"
12. "Window and Door Upgrades That Transform Your Home"
13. "Custom Cabinetry vs. Semi-Custom: When to Invest"
14. "The Rise of Multi-Functional Spaces in Home Design"
15. "Luxury Bathroom Fixtures: What's Worth the Investment"

### Process & Education Posts (13 posts)
1. "Our 5-Step Design-Build Process Explained"
2. "What Happens During a Ridgecrest Design Consultation"
3. "How Photo-Realistic 3D Renders Save You Money Before Construction Starts"
4. "Understanding Construction Phases: From Demo to Final Walkthrough"
5. "How We Manage Budgets Without Cutting Corners"
6. "Why We Say No to Bad Ideas — And Why That's Good for You"
7. "The Importance of Structural Engineering in Home Remodeling"
8. "How to Evaluate a Contractor's Portfolio"
9. "What to Look for in a Design-Build Contract"
10. "Living in Your Home During a Remodel: Tips and Reality"
11. "How Long Does Each Type of Remodel Actually Take?"
12. "The Hidden Costs of Cheap Remodels"
13. "Why Experience Matters: 20+ Years of East Bay Remodeling"

### FAQ Posts (10 posts)
1. "How Long Does a Kitchen Remodel Take in the East Bay?"
2. "Do I Need an Architect for My Home Remodel?"
3. "What Is the ROI of a Bathroom Remodel in California?"
4. "Can I Build an ADU on My Property? East Bay Rules Explained"
5. "How Much Should I Budget for a Whole House Remodel?"
6. "What Is Design-Build and How Is It Different from a General Contractor?"
7. "Do I Need Permits for My Kitchen Remodel?"
8. "How Do I Choose Between Renovation and New Construction?"
9. "What Makes a Good Interior Designer?"
10. "Is It Worth Hiring a Residential Architect?"

---

## PHASE 3: TEAM MEMBER PAGES (5-10)

- Individual page per key team member in `/home/claudeuser/agent/preview/team/[name].html`
- Bio, experience, areas of expertise
- Links to projects they worked on
- Linked from the team.html page
- JSON-LD Person schema markup

---

## PHASE 4: INTERNAL LINKING ARCHITECTURE

This is critical. Every page must be woven into the site structure.

### Required Links Per New Service+City Page
1. **UP** to its service category page (e.g., `home-addition-danville` → `services.html` or a new Home Additions service hub page)
2. **UP** to its city location hub page (e.g., `home-addition-danville` → `services/danville.html`)
3. **SIDEWAYS** to 2-3 sibling service+city pages for the SAME city (e.g., `home-addition-danville` → `kitchen-remodel-danville`, `bathroom-remodel-danville`)
4. **SIDEWAYS** to the SAME service in 2-3 neighboring cities (e.g., `home-addition-danville` → `home-addition-alamo`, `home-addition-walnut-creek`)
5. **DOWN** to a relevant project page if one exists for that city
6. **CTA** link to `/start-a-project.html`

### Required Updates to EXISTING Pages
After new pages are created:
1. Each existing **location hub page** (`services/danville.html`, etc.) must get links to ALL service+city pages for that city — including the new ones
2. The **services.html** page must link to all service categories including new ones (Home Additions, ADU, Interior Design, Architecture, General Contracting, Home Renovation)
3. Create **new service hub pages** if they don't exist: `home-additions.html`, `adu.html`, `interior-design.html`, `architecture.html`, `general-contracting.html`, `home-renovations.html` — each links to all 13 city variants
4. **Blog posts** must link to 3-5 relevant service+city pages within the content body

### Required Links Per Blog Post
1. 3-5 contextual links to relevant service+city pages within the post body
2. Link to related project pages where applicable
3. CTA link to `/start-a-project.html`

### Click Depth Rule
Every page must be reachable within 3 clicks from the homepage:
- Homepage → Services → Service Category Hub → Service+City (3 clicks)
- Homepage → Services → Location Hub → Service+City (3 clicks)
- Homepage → Blog → Blog Post (3 clicks if blog is in nav, which it is as "The RD Edit")

### No Orphan Pages
Every page must have at least 3 internal links pointing TO it. Zero exceptions. After building all pages, run an audit to verify.

---

## PHASE 5: SITEMAP & TECHNICAL SEO

1. **Regenerate sitemap.xml** after every batch — include ALL new pages
2. Add `<lastmod>` dates to sitemap entries
3. Verify all canonical URLs are correct (use `https://www.ridgecrestdesigns.com/services/[slug]` format)
4. Verify all pages return HTTP 200 via the preview server
5. Verify no duplicate title tags or meta descriptions across pages

---

## EXECUTION BATCHES

### Batch 1: Proof of Concept (3 pages)
- `home-addition-danville.html` (Type A — reference Danville projects)
- `adu-contractor-blackhawk.html` (Type B — no project, area expertise)
- `interior-designer-walnut-creek.html` (Type B — area expertise)

**STOP after Batch 1.** Post results to `/home/claudeuser/agent/ridgecrest-agency/task_status/`. Henry and Perplexity review before proceeding.

### Batch 2: One Full Service Type (13 pages)
- `home-addition` for all 12 cities + Blackhawk

### Batch 3-7: Remaining Service Types (13 pages each)
- `adu-contractor` × 13
- `interior-designer` × 13
- `architect` × 13
- `general-contractor` × 13
- `home-renovation` × 13

### Batch 8: Blackhawk remaining 5 service types
- The 5 existing service types that need Blackhawk variants (kitchen, bathroom, whole-house, design-build, custom-home-builder)

### Batch 9: New service hub pages + update existing location hubs + update services.html

### Batch 10: Blackhawk location hub page

### Batch 11-14: Blog Posts (17 per batch)

### Batch 15: Team pages

### Batch 16: Internal linking audit + sitemap regeneration + orphan page check

### After EVERY Batch:
1. Verify all new pages return HTTP 200
2. Verify all EXISTING pages still return HTTP 200
3. Verify every new page has 3+ internal links pointing to it
4. Regenerate sitemap.xml
5. Post results to `/home/claudeuser/agent/ridgecrest-agency/task_status/`
6. Git commit: `cd /home/claudeuser/agent && git add -A && git commit -m "POST: SEO Batch [N] — [description]"`

---

## SAFETY GUARDRAILS

- Do NOT modify the top navigation bar structure
- Do NOT change the homepage layout or appearance
- Do NOT change CSS, fonts, colors, or spacing
- Do NOT modify existing page content above the fold
- Adding "Related Services" or "Areas We Serve" sections at the BOTTOM of existing pages is allowed
- Back up all files before changes
- Zero orphan pages — every page must have 3+ internal links pointing to it
- Every page reachable within 3 clicks from homepage
- Do NOT create fake project references — only reference real completed work
- For cities/services with no completed projects, use Type B content (area expertise only)
- Git commit after every batch
- All CTAs link to `/start-a-project.html`

SAFETY: Do not delete existing files. Do not modify existing code unless this task explicitly instructs it. Do not redeploy or overwrite live applications. Back up any file before modifying. Read all rules/ files before starting. Report what you plan to do before doing it.

---

## BLOG POST CREATIVE BRIEFS

Detailed creative briefs for all 68 blog posts are in:
`/home/claudeuser/agent/ridgecrest-agency/blog_creative_briefs.md`

Each brief contains:
1. Title
2. Angle — the specific hook and why a luxury homeowner would click
3. Key Points — 5-7 specific, actionable bullets (real costs, real jurisdictions, real materials)
4. Internal Links — which service+city and project pages to link to
5. Target Reader — who is reading and what decision they are making

You MUST read and follow these briefs when writing each blog post. Do NOT write generic content. Every post must deliver the specific value outlined in its brief.

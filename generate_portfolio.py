#!/usr/bin/env python3
"""
Portfolio Migration Generator
Generates all 18 project pages, portfolio.html (featured), allprojects.html (full grid)
Uses local WebP images where available, Wix CDN as fallback for missing ones.
"""

import os, json, re

PREVIEW = '/home/claudeuser/agent/preview'
OPT_DIR = os.path.join(PREVIEW, 'assets', 'images-opt')
INQUIRY_URL = 'https://elevate-scheduling-6b2fdec8.base44.app/ProjectInquiryForm'

# ── Image helpers ─────────────────────────────────────────────────────────────

def local_webp(hash_mv2):
    """Return local path if the base WebP exists, else None."""
    fname = f'{hash_mv2}.webp'
    if os.path.isfile(os.path.join(OPT_DIR, fname)):
        return f'/assets/images-opt/{fname}'
    return None

def img_src(hash_mv2, wix_ext='jpg', wix_w=1920, wix_h=1280):
    """Return best available src: local WebP or Wix CDN."""
    local = local_webp(hash_mv2)
    if local:
        return local
    # Wix CDN fallback — renders fine in browser, only fails on server-side fetch
    return (f'https://static.wixstatic.com/media/{hash_mv2.replace("_mv2","~mv2")}'
            f'.{wix_ext}/v1/fill/w_{wix_w},h_{wix_h},q_90,enc_avif,qual_90')

# ── Project data ──────────────────────────────────────────────────────────────
# type_filter: custom-home | whole-house | kitchen-bath | garage-specialty

PROJECTS = [
    {
        'slug': 'sierra-mountain-ranch',
        'wix_slug': 'sierramountainranch',
        'name': 'Sierra Mountain Ranch House',
        'city': 'Sierra Mountains', 'state': 'CA',
        'type': 'Luxury Mountain Remodel', 'type_filter': 'whole-house',
        'year': '2024',
        'desc_short': 'A two-year labor of love — Ridgecrest Designs transformed this lakeside mountain retreat into a high-end, multi-functional luxury home combining rustic charm with modern precision.',
        'desc_detail': """The Sierra Mountain Ranch project is a true labor of love—the Ridgecrest team spent over two years bringing this luxury mountain retreat to life. Nestled in a breathtaking lakeside setting, this custom home required a comprehensive remodel of both the interior and exterior. The goal? To create a high-end, multi-functional space that combines rustic charm and modern luxury.

The exterior transformation included new custom siding, real stonework, and wood-trimmed windows and doors. We extended the outdoor living space with a new deck, custom steel stair risers, and a durable standing seam metal roof. To reflect the client's vision of authenticity, we used reclaimed wood siding—finished with a Ridgecrest-exclusive custom stain—and weathered corrugated metal for a rugged, yet refined look.

Inside, the kitchen was reimagined with large family gatherings in mind. The reconfigured layout features dual islands—one with seating for seven grandchildren and another for prepping—crafted to support multiple cooks at once. A standout feature is the master bath's outdoor "bath porch," complete with a deep copper soaking tub, inviting year-round relaxation. Custom metal details and Ridgecrest Metalworks fabrications appear throughout, tying the interior and exterior into a cohesive, intentional design.""",
        'specs': {'What': 'Whole Home Remodel', 'Where': 'Sierra Mountains, CA', 'When': '2024', 'Duration': '2+ years'},
        'hero': 'ff5b18_6f6dc7ef92684e7e8af496c4f83f06be_mv2', 'hero_ext': 'jpg',
        'gallery': [
            ('ff5b18_d591e3f65da44f76bfd8088b70370caf_mv2', 'jpg'),
            ('ff5b18_29ec897c45d74caabd831b08f46ec1bc_mv2', 'jpg'),
            ('ff5b18_6f6dc7ef92684e7e8af496c4f83f06be_mv2', 'jpg'),
        ],
        'featured': True,
    },
    {
        'slug': 'pleasanton-custom',
        'wix_slug': 'pleasantoncustomhome',
        'name': 'Pleasanton Custom Home',
        'city': 'Pleasanton', 'state': 'CA',
        'type': 'New Custom Home', 'type_filter': 'custom-home',
        'year': '2020',
        'desc_short': 'A 5,000 sq ft modern farmhouse custom home designed and built for a growing family on 1.4 acres in Pleasanton\'s Happy Valley — from first render to final nail.',
        'desc_detail': """In 2017, a couple with three young children came to us with a dream of a 5,000 square foot modern farmhouse home, customized for their own family. Ridgecrest began designing their home, nestled between heritage trees on a 1.4 acre plot of land in Pleasanton's Happy Valley.

The open floor plan creates an inviting home for a close-knit family. The kitchen, which is illuminated by a custom wood beam suspended fixture, opens up to an outdoor living space and pool. A pantry allows for easy clean-up after dinner parties, and acts as a second kitchen when needed. The dining room, which opens up to the backyard garden, features a wine room with authentic steel doors, reclaimed wood cladding and a ladder to reach the top-shelf wines. The craft room is the perfect place for the kids to do homework and let their creativity flourish.

Across the hall is the downstairs powder room, featuring a marble floor and custom floating vanity. On the second floor, the master bathroom is flooded with light from the full glass wall and looks out to a balcony with an outdoor shower. The girl's bathroom, painted in a soft pink, is perfect for two sisters to get ready for the day.""",
        'specs': {'What': 'New Custom Home', 'Where': 'Pleasanton, CA', 'When': '2020', 'Size': '5,000 sq ft'},
        'hero': 'ff5b18_9820c1603a9c414d8cc8009784d1ca7c_mv2', 'hero_ext': 'jpg',
        'gallery': [
            ('ff5b18_53f46b46f9094468addb44305dff0a55_mv2', 'jpg'),
            ('ff5b18_42db29ccfa3949e6ae1e773888bcac59_mv2', 'jpg'),
            ('ff5b18_8e8a0acd45874a41a17619c8f12ee4cc_mv2', 'jpg'),
            ('ff5b18_9820c1603a9c414d8cc8009784d1ca7c_mv2', 'jpg'),
            ('ff5b18_4161051f37ba482fafc49baddabc8a96_mv2', 'jpg'),
            ('ff5b18_8f25d193b0a2414a89b864f14a54e442_mv2', 'jpg'),
        ],
        'featured': True,
    },
    {
        'slug': 'sunol-homestead',
        'wix_slug': 'sunolhomestead',
        'name': 'Sunol Homestead',
        'city': 'Sunol', 'state': 'CA',
        'type': 'New Custom Home', 'type_filter': 'custom-home',
        'year': '2023',
        'desc_short': 'Settled on a Sunol hillside, this brand-new custom home looks like it\'s been there a hundred years — in the best possible way. Craftsman character, modern amenities, handcrafted at every level.',
        'desc_detail': """Settled on a hillside in Sunol, where the cows come to graze at dawn, lies a brand new custom home that looks like it has been there for a hundred years — in a good way. Our clients came to us with an architect's house plans, but needed a builder to make their dream home come to life. In true Ridgecrest fashion, we ended up redesigning the entire home inside and out — creating what we now call the Sunol Homestead.

A multitude of details came together to give us the perfect mix of a traditional Craftsman style home with modern amenities. We commissioned a local stone mason to hand-place every river stone on the exterior of the house — no veneer here. Floor to ceiling windows and doors lead out to the wrap-around porch to let in beautiful natural light.

The custom stained wood floors and trim exude warmth and richness throughout the entire home. Every detail of this meticulously designed residence reflects a commitment to quality and comfort, making it the perfect haven for those seeking a harmonious balance between refined living and the peaceful serenity of Sunol's idyllic landscape.""",
        'specs': {'What': 'New Custom Home', 'Where': 'Sunol, CA', 'When': '2023'},
        'hero': 'ff5b18_5ad4349859fe4e728734e05bf49f85e3_mv2', 'hero_ext': 'webp',
        'gallery': [
            ('ff5b18_296b1e9ff5d14e128006c21217e3f3e9_mv2', 'jpg'),
            ('ff5b18_5b8b92bdb42f488681d9bad5096f781a_mv2', 'png'),
            ('ff5b18_017e7503e4ea4fe19c98e6a31e9f48d7_mv2', 'png'),
            ('ff5b18_5ad4349859fe4e728734e05bf49f85e3_mv2', 'webp'),
        ],
        'featured': True,
    },
    {
        'slug': 'danville-hilltop',
        'wix_slug': 'danvillehilltophideaway',
        'name': 'Danville Hilltop Hideaway',
        'city': 'Danville', 'state': 'CA',
        'type': 'Kitchen Remodel', 'type_filter': 'kitchen-bath',
        'year': '2020',
        'desc_short': 'A mid-century hilltop kitchen at the top of Eugene O\'Neill National Historic Park, reimagined with custom cabinetry, hand-fabricated steel wall storage, and an iconic blue-and-walnut contrast that turns heads.',
        'desc_detail': """Situated at the top of the Eugene O'Neill National Historic Park in Danville, this mid-century modern hilltop home had great architectural features, but needed a kitchen update that spoke to the design style of the rest of the house. We would have to say this project was one of our most challenging when it came to blending the mid-century style of the house with an eclectic and modern look that the clients were drawn to. But, who doesn't love a good challenge?

We removed the builder-grade cabinetry put in by a previous owner and took down a wall to open up the kitchen to the rest of the great room. The kitchen features a custom designed hood as well as custom cabinetry with an intricate beaded detail, setting it apart from all other cabinetry designs.

The pop of blue paired with the dark walnut creates an eye-catching contrast. Ridgecrest also designed and fabricated solid steel wall cabinetry to store countertop appliances and display dishes and glasses. The copper accents on the range and faucets bring the design full circle and finish this gorgeous one-of-a-kind kitchen.""",
        'specs': {'What': 'Kitchen Remodel', 'Where': 'Danville, CA', 'When': '2020'},
        'hero': 'ff5b18_598ba1466dbb45249778e2ea0e0b95e3_mv2', 'hero_ext': 'jpg',
        'gallery': [
            ('ff5b18_598ba1466dbb45249778e2ea0e0b95e3_mv2', 'jpg'),
            ('ff5b18_b246a630ba864e2a8fe67d964745b9b5_mv2', 'jpg'),
            ('ff5b18_4a378f6899d24b5ba7bc7551ea53540a_mv2', 'jpg'),
            ('ff5b18_63757c728db94733b4f60a7102c0f722_mv2', 'jpg'),
            ('ff5b18_487bdc0f0af642d9b49405d476c80c5e_mv2', 'jpg'),
            ('ff5b18_c0e8f9e9008c498eac5efafae3c46b04_mv2', 'jpg'),
        ],
        'featured': True,
    },
    {
        'slug': 'napa-retreat',
        'wix_slug': 'naparetreat',
        'name': 'Napa Retreat',
        'city': 'Napa', 'state': 'CA',
        'type': 'Luxury Home Remodel', 'type_filter': 'whole-house',
        'year': '2020',
        'desc_short': 'A stunning vacation home overlooking 800 acres on Napa\'s Longhorn Ridge — muted palette, rich textures, ultra-modern kitchen with white oak and custom metal throughout.',
        'desc_detail': """The Napa Retreat is a stunning vacation home that overlooks 800 acres of beautiful trees on Napa's Longhorn Ridge. Our clients, who normally are drawn to bold and funky designs, wanted something more neutral and calming for their weekend home on the hill.

While keeping a touch of eclecticism in each room, we stayed with a muted color palette and focused on texture and finish to bring life to each space. The ultra modern kitchen is tied to the other spaces throughout the house with the use of white oak and custom metal elements.

The master bathroom is a minimalist's dream with neutral tones and clean lines. Glass tile in the hall cabinetry and powder room bring in our client's out of the box design taste while adding interest to the spaces they occupy.""",
        'specs': {'What': 'Home Remodel', 'Where': 'Napa, CA', 'When': '2020'},
        'hero': 'ff5b18_38c7317e1d4b4773ab0a16ed48332f31_mv2', 'hero_ext': 'jpg',
        'gallery': [
            ('ff5b18_38c7317e1d4b4773ab0a16ed48332f31_mv2', 'jpg'),
            ('ff5b18_938143f6f9374aa88d8ed87d5de5bb73_mv2', 'jpg'),
            ('ff5b18_e25234795a7a4ed08b1bea59751199a9_mv2', 'jpg'),
            ('ff5b18_bb1013e8034740828826f718ad2216d9_mv2', 'png'),
        ],
        'featured': False,
    },
    {
        'slug': 'lafayette-luxury',
        'wix_slug': 'lafayette-laid-back-luxury',
        'name': 'Lafayette Laid-Back Luxury',
        'city': 'Lafayette', 'state': 'CA',
        'type': 'Home Addition & Remodel', 'type_filter': 'whole-house',
        'year': '2022',
        'desc_short': 'Four family members, one bathroom. The solution: a full master suite addition and extra bath, transforming a compact rancher into what we can only call laid-back luxury.',
        'desc_detail': """Our clients had been living in a rancher with just one bathroom for four family members. Needless to say, it was time to expand. There was plenty of room on their lot to add an entire master suite and an extra bathroom. We transformed their small rancher into what we can only describe as laid back luxury.

Since natural light would now flood the addition through new window placements, we wanted to build off the airy feeling that the new space would evoke. We chose classic finishes like light wood tones, marble and penny tile, and hues of calming blue in the kids bathrooms, to add a pop of color.

Classic polished nickel fixtures adorn the bathroom walls and countertops, and elegant bronze lighting and hardware add just enough contrast to pull the whole look together.""",
        'specs': {'What': 'Home Addition & Remodel', 'Where': 'Lafayette, CA', 'When': '2022'},
        'hero': 'ff5b18_94919d08fc9245fc849ac03c4ea2caaf_mv2', 'hero_ext': 'jpg',
        'gallery': [
            ('ff5b18_94919d08fc9245fc849ac03c4ea2caaf_mv2', 'jpg'),
            ('ff5b18_c1e5fd8a13c34fa985b5b84f87a8f7d1_mv2', 'jpg'),
            ('ff5b18_bcab10ed365d4e7183fdfd58fa581372_mv2', 'jpg'),
            ('ff5b18_c1637bae333840e4a71cbdaac8405213_mv2', 'png'),
        ],
        'featured': False,
    },
    {
        'slug': 'orinda-kitchen',
        'wix_slug': 'orinda',
        'name': 'Orinda Urban Modern Kitchen',
        'city': 'Orinda', 'state': 'CA',
        'type': 'Kitchen Remodel', 'type_filter': 'kitchen-bath',
        'year': '2019',
        'desc_short': 'An outdated Orinda kitchen turned jaw-dropping art gallery space — four skylights, a commissioned warehouse wall mural, glossy white cabinets with white oak and black accents, Turkish limestone floors.',
        'desc_detail': """Nestled in the wooded hills of Orinda lies an old home with great potential. Ridgecrest Designs turned an outdated kitchen into a jaw-dropping space fit for a contemporary art gallery.

To give the kitchen an artistic urban feel, we commissioned a local artist to paint a textured "warehouse wall" on the tallest wall of the kitchen. Four skylights allow natural light to shine down and highlight the warehouse wall.

Bright, white, glossy cabinets with hints of white oak and black accents pop on the light landscape this home has to offer. Real Turkish limestone covers the floor in a random set pattern for an old-world look, in an otherwise ultra-modern space.""",
        'specs': {'What': 'Kitchen Remodel', 'Where': 'Orinda, CA', 'When': '2019'},
        'hero': 'ff5b18_d741bf6a821b40e8b4730181bcf0fc48_mv2', 'hero_ext': 'jpg',
        'gallery': [
            ('ff5b18_d741bf6a821b40e8b4730181bcf0fc48_mv2', 'jpg'),
            ('ff5b18_fa8d30d31488413ca93cf28ed74c8e05_mv2', 'jpg'),
            ('ff5b18_c8f3843d541b4a9cbd5d0b7890f93880_mv2', 'jpg'),
            ('ff5b18_de2ed75da1a541abb0861b82d04e1135_mv2', 'png'),
            ('ff5b18_a69a1fba43ec4dd98ec66e582d5ec86f_mv2', 'png'),
        ],
        'featured': False,
    },
    {
        'slug': 'danville-dream',
        'wix_slug': 'danvilledreamhome',
        'name': 'Danville Dream Home',
        'city': 'Danville', 'state': 'CA',
        'type': 'Luxury Home Remodel', 'type_filter': 'whole-house',
        'year': '2024',
        'desc_short': 'Ridgecrest Designs transformed this Danville dream home into a stunning showcase of luxury design, craftsmanship, and custom detail — where every finish was chosen with precision and every space tells a story.',
        'desc_detail': """Ridgecrest Designs transformed this Danville dream home into a stunning showcase of luxury design, craftsmanship, and custom detail. This whole-home remodel required deep coordination across design, engineering, and construction — hallmarks of the Ridgecrest design-build approach.

Every room was thoughtfully reimagined with high-end finishes, custom millwork, and bespoke fixtures sourced to exact specification. The result is a home that feels entirely tailored — not assembled — because it was built with the same care Ridgecrest brings to every project, from first render to final walkthrough.

The clients came with a vision. Ridgecrest made it precise, then built it flawlessly.""",
        'specs': {'What': 'Luxury Home Remodel', 'Where': 'Danville, CA', 'When': '2024'},
        'hero': 'ff5b18_83cbc49d23a5436294574e1dd9db3819_mv2', 'hero_ext': 'png',
        'gallery': [
            ('ff5b18_83cbc49d23a5436294574e1dd9db3819_mv2', 'png'),
            ('ff5b18_aac54aec732d47c7b4d53e34ae6aa5ff_mv2', 'png'),
        ],
        'featured': False,
    },
    {
        'slug': 'alamo-luxury',
        'wix_slug': 'alamoluxury',
        'name': 'Alamo Luxury Remodel',
        'city': 'Alamo', 'state': 'CA',
        'type': 'Luxury Home Remodel', 'type_filter': 'whole-house',
        'year': '2023',
        'desc_short': 'A high-end luxury remodel in one of the East Bay\'s most prestigious neighborhoods — refined finishes, seamless execution, and the kind of attention to detail that only a true design-build firm delivers.',
        'desc_detail': """Alamo is one of the East Bay's most prestigious addresses, and this luxury remodel was built to match. Ridgecrest Designs approached this project with the same integrated design-build process that defines every engagement — beginning with detailed renders that gave the clients visual certainty before a single wall was touched.

Custom millwork, premium stone surfaces, and curated hardware selections were layered together to create a home that feels elevated without being cold. The result is a refined, livable luxury that reflects the character of the neighborhood and the personality of the owners.

From concept through construction, every decision was deliberate — no compromises, no shortcuts, no surprises.""",
        'specs': {'What': 'Luxury Home Remodel', 'Where': 'Alamo, CA', 'When': '2023'},
        'hero': 'ff5b18_39536b28ce0447b9a87797bb4c70ee51_mv2', 'hero_ext': 'jpg',
        'gallery': [
            ('ff5b18_39536b28ce0447b9a87797bb4c70ee51_mv2', 'jpg'),
            ('ff5b18_b3b82b5920dd48509b6b78c1a91dcaec_mv2', 'png'),
        ],
        'featured': False,
    },
    {
        'slug': 'lafayette-bistro',
        'wix_slug': 'lafayette-modern-bistro',
        'name': 'Lafayette Modern Bistro',
        'city': 'Lafayette', 'state': 'CA',
        'type': 'Kitchen Remodel', 'type_filter': 'kitchen-bath',
        'year': '2024',
        'desc_short': 'A cramped Lafayette kitchen transformed into a bright, modern bistro-style culinary space — custom cabinetry, white oak finishes, and an open floor plan designed for both daily life and entertaining.',
        'desc_detail': """Ridgecrest Designs transformed a cramped Lafayette kitchen into a bright, modern bistro-style culinary space with custom cabinetry and high-end finishes. The project began — like all Ridgecrest projects — with photo-realistic renders that let the clients see exactly what they were getting before demolition started.

The open floor plan was created by removing a non-structural wall, flooding the space with natural light and creating a flow between the kitchen and living areas. White oak accents, integrated appliances, and a custom range hood bring warmth and precision to the space.

The result is a kitchen that functions as the heart of the home — equally suited for a quiet weeknight dinner or a full dinner party.

""",
        'specs': {'What': 'Kitchen Remodel', 'Where': 'Lafayette, CA', 'When': '2024'},
        'hero': 'ff5b18_76c5e504c9114ef09ad8233549a16b39_mv2', 'hero_ext': 'jpg',
        'gallery': [
            ('ff5b18_76c5e504c9114ef09ad8233549a16b39_mv2', 'jpg'),
            ('ff5b18_1012816bc1d7431cbdba88c8a138d06d_mv2', 'jpg'),
        ],
        'featured': False,
    },
    {
        'slug': 'san-ramon',
        'wix_slug': 'sanramon',
        'name': 'San Ramon Transitional Kitchen',
        'city': 'San Ramon', 'state': 'CA',
        'type': 'Kitchen Remodel', 'type_filter': 'kitchen-bath',
        'year': '2024',
        'desc_short': 'A transitional kitchen remodel in San Ramon that balances classic sensibility with modern clean lines — refined cabinetry, premium countertops, and a layout optimized for how a family actually cooks.',
        'desc_detail': """This San Ramon kitchen remodel sits at the intersection of classic and contemporary — what designers call transitional style. Ridgecrest Designs worked with the clients to develop a layout that functions efficiently for a busy household while delivering the elevated aesthetic they wanted.

Clean-lined cabinetry in a warm neutral palette is paired with premium stone countertops and carefully selected hardware that bridges traditional and modern sensibilities. The result is a kitchen that feels timeless rather than trend-driven.

As with every Ridgecrest project, photo-realistic renders were produced before a single cabinet was ordered — so the clients knew exactly what they were getting, down to the pull finish.""",
        'specs': {'What': 'Kitchen Remodel', 'Where': 'San Ramon, CA', 'When': '2024'},
        'hero': 'ff5b18_6eed718eb2ab4ca0887717d1a39285ea_mv2', 'hero_ext': 'png',
        'gallery': [
            ('ff5b18_6eed718eb2ab4ca0887717d1a39285ea_mv2', 'png'),
            ('ff5b18_b64b65b40c1f44e4a4f6b21baac8ed72_mv2', 'png'),
            ('ff5b18_708d458832504cbd94bd7cdd7913c664_mv2', 'png'),
        ],
        'featured': False,
    },
    {
        'slug': 'pleasanton-garage',
        'wix_slug': 'pleasanton-garage-renovation',
        'name': 'Pleasanton Garage Renovation',
        'city': 'Pleasanton', 'state': 'CA',
        'type': 'Garage Remodel', 'type_filter': 'garage-specialty',
        'year': '2025',
        'desc_short': 'The detached garage of our Pleasanton Modern Farmhouse — stripped of its stucco and rebuilt inside and out with reclaimed wood siding, a workshop, bathroom, and traditional barn sconces.',
        'desc_detail': """Our clients from the Pleasanton Modern Farmhouse had a detached garage that had been plastered with stucco by a previous property owner. They had a vision to remodel the garage inside and out to better fit their family's needs and to blend in with the surrounding property.

The new interior includes a bathroom, a workshop space and a traditional double carport. The exterior is re-clad with reclaimed wood on the siding and new garage doors. A metal roll up door on the backside lets fresh air into the workshop.

Traditional barn sconces flank the doors to make this structure look more like an original barn than a garage — blending seamlessly with the farmhouse character of the main property.""",
        'specs': {'What': 'Garage Remodel', 'Where': 'Pleasanton, CA', 'When': '2025'},
        'hero': 'ff5b18_042b3d66e8904b4188c0ec509b2595d6_mv2', 'hero_ext': 'jpg',
        'gallery': [
            ('ff5b18_042b3d66e8904b4188c0ec509b2595d6_mv2', 'jpg'),
            ('ff5b18_dab676506e77455e942b02a857f21cc3_mv2', 'jpg'),
            ('ff5b18_f8bf8933487f45db825a713b4ea4c540_mv2', 'jpg'),
            ('ff5b18_5f016abc7ce04830a7f65e61c2b4a3fa_mv2', 'jpg'),
        ],
        'featured': False,
    },
    {
        'slug': 'livermore-farmhouse-chic',
        'wix_slug': 'livermorefarmhousechic',
        'name': 'Livermore Farmhouse Chic',
        'city': 'Livermore', 'state': 'CA',
        'type': 'Home Remodel', 'type_filter': 'whole-house',
        'year': '2022',
        'desc_short': 'A warm, modern-farmhouse transformation in Livermore — exposed beams, rustic textures, refined finishes, and custom millwork that bring that effortlessly chic farmhouse aesthetic to life.',
        'desc_detail': """Livermore Farmhouse Chic is exactly what it sounds like: the warmth and character of a classic farmhouse, elevated with the precision and polish that Ridgecrest Designs is known for.

Exposed beams, warm wood tones, and rustic textures provide the soul of the design, while refined finishes, clean-lined cabinetry, and a carefully curated material palette bring a modern sophistication that keeps the space from ever feeling heavy.

Custom millwork throughout — from built-in shelving to coffered ceilings — adds a level of craftsmanship that sets this project apart. The result is a home that feels both timeless and entirely personal, exactly the way a Ridgecrest project should.""",
        'specs': {'What': 'Home Remodel', 'Where': 'Livermore, CA', 'When': '2022'},
        'hero': 'ff5b18_e1ef86fee44b4c14b077ecbdb2ca10f5_mv2', 'hero_ext': 'png',
        'gallery': [
            ('ff5b18_e1ef86fee44b4c14b077ecbdb2ca10f5_mv2', 'png'),
            ('ff5b18_73ddf9ebf03a4477926cbf2283271380_mv2', 'png'),
        ],
        'featured': False,
    },
    {
        'slug': 'pleasanton-cottage-kitchen',
        'wix_slug': 'pleasantoncottagekitchen',
        'name': 'Pleasanton Cottage Kitchen',
        'city': 'Pleasanton', 'state': 'CA',
        'type': 'Kitchen Remodel', 'type_filter': 'kitchen-bath',
        'year': '2021',
        'desc_short': 'A cottage-style kitchen remodel in Pleasanton that leans into charm without sacrificing function — shaker cabinetry, classic hardware, and a layout designed around how the family actually lives.',
        'desc_detail': """Sometimes a kitchen doesn't need to make a bold statement — it just needs to be perfect. The Pleasanton Cottage Kitchen is exactly that: a beautifully resolved remodel that feels at home in a cottage-style residence without ever feeling small or dated.

Shaker-style cabinetry in a warm white finish, classic hardware, and a thoughtfully designed layout create a kitchen that's as functional as it is charming. Every storage decision was deliberate — maximizing usable space while keeping the aesthetic clean and inviting.

Ridgecrest Designs produced full photo-realistic renders before breaking ground, giving the clients complete confidence in every material choice before the first cabinet was installed.""",
        'specs': {'What': 'Kitchen Remodel', 'Where': 'Pleasanton, CA', 'When': '2021'},
        'hero': 'ff5b18_f575a25ba7f14e1389d0ae63bb2d356f_mv2', 'hero_ext': 'png',
        'gallery': [
            ('ff5b18_f575a25ba7f14e1389d0ae63bb2d356f_mv2', 'png'),
            ('ff5b18_9a3cb5be52fb466ebd047a075c89ee74_mv2', 'png'),
        ],
        'featured': False,
    },
    {
        'slug': 'san-ramon-eclectic-bath',
        'wix_slug': 'san-ramon-eclectic-bath',
        'name': 'San Ramon Eclectic Bath',
        'city': 'San Ramon', 'state': 'CA',
        'type': 'Bathroom Remodel', 'type_filter': 'kitchen-bath',
        'year': '2022',
        'desc_short': 'An eclectic, personality-driven bathroom remodel in San Ramon — bold tile choices, unexpected material combinations, and a design sensibility that\'s anything but builder-grade.',
        'desc_detail': """Not every client wants neutral. The San Ramon Eclectic Bath was designed for clients with a clear point of view — and Ridgecrest Designs was the right partner to execute it without compromise.

Bold tile selections, an unexpected mix of materials, and carefully chosen fixtures combine to create a bathroom that feels curated and personal. The design walks a confident line between eclectic and elevated — expressive without being chaotic.

Ridgecrest's design-build model was essential here: having design and construction under one roof allowed for precise coordination on every detail, from tile layout to fixture placement, ensuring the finished space matched the render exactly.""",
        'specs': {'What': 'Bathroom Remodel', 'Where': 'San Ramon, CA', 'When': '2022'},
        'hero': 'ff5b18_7bb937306ca1481894944e9f7b7b64c4_mv2', 'hero_ext': 'png',
        'gallery': [
            ('ff5b18_7bb937306ca1481894944e9f7b7b64c4_mv2', 'png'),
            ('ff5b18_8fec027febcb4fdb9a1f34db0e462fac_mv2', 'png'),
        ],
        'featured': False,
    },
    {
        'slug': 'castro-valley-villa',
        'wix_slug': 'castro-valley-villa',
        'name': 'Castro Valley Villa',
        'city': 'Castro Valley', 'state': 'CA',
        'type': 'Home Remodel', 'type_filter': 'whole-house',
        'year': '2023',
        'desc_short': 'A villa-style home remodel in Castro Valley — refined materials, architectural details, and a seamless indoor-outdoor flow that transforms a standard home into something genuinely special.',
        'desc_detail': """The Castro Valley Villa project demonstrates what's possible when a home is approached as a whole rather than a series of individual rooms. Ridgecrest Designs brought its integrated design-build process to this villa-style remodel, coordinating every element from architectural detailing to finish selection.

Refined materials — natural stone, custom millwork, and warm metal accents — are layered throughout to create a sense of continuity from space to space. The indoor-outdoor relationship was a priority: living areas open naturally to exterior spaces in a way that feels architectural rather than incidental.

The result is a home that punches well above its original footprint — not because it was expanded, but because every inch was intentional.""",
        'specs': {'What': 'Home Remodel', 'Where': 'Castro Valley, CA', 'When': '2023'},
        'hero': 'ff5b18_fa64df3266cb4f5687726c7ab5ac76f7_mv2', 'hero_ext': 'jpg',
        'gallery': [
            ('ff5b18_fa64df3266cb4f5687726c7ab5ac76f7_mv2', 'jpg'),
            ('ff5b18_8534e71718a54408b57038ba0fc8c02f_mv2', 'jpg'),
        ],
        'featured': False,
    },
    {
        'slug': 'lakeside-cozy-cabin',
        'wix_slug': 'lakeside-cozy-cabin',
        'name': 'Lakeside Cozy Cabin',
        'city': 'Sierra Mountains', 'state': 'CA',
        'type': 'Cabin Remodel', 'type_filter': 'whole-house',
        'year': '2025',
        'desc_short': 'A guesthouse on the Sierra Mountain Ranch property, rebuilt to match the main house — reclaimed wood, custom metalwork, soft green cabinetry, and a new deck overlooking a private lake.',
        'desc_detail': """This small cabin, a guesthouse on the property of our Sierra Mountain Ranch House project, overlooks a gorgeous private lake. The finishes of this cabin were selected to match and complement the material choices from the main house.

Soft green kitchen cabinets give the space a more fun, playful look, contrasted with the rugged look of authentic reclaimed wood. Clean and simple bathrooms ensure easy maintenance for sporadic visitors. Custom metal air registers throughout were fabricated by Ridgecrest Metalworks, adding a unique and personal touch.

The exterior was completely refaced to match the ranch house look of the main property, while maintaining the cabin-style A-frame architecture. We installed a new deck with a custom metal guardrail that overlooks the lake, and a durable standing seam metal roof. Reclaimed wood siding finished with a Ridgecrest-exclusive custom stain completes the look.""",
        'specs': {'What': 'Cabin Remodel', 'Where': 'Sierra Mountains, CA', 'When': '2025'},
        'hero': 'ff5b18_349218a966f148919fc38da254ca4619_mv2', 'hero_ext': 'jpg',
        'gallery': [
            ('ff5b18_349218a966f148919fc38da254ca4619_mv2', 'jpg'),
            ('ff5b18_29f3aa1ef62549ecbc7c5dd6b4aac717_mv2', 'jpg'),
            ('ff5b18_c1bace39ccc64636b710dc307c31bb77_mv2', 'jpg'),
        ],
        'featured': False,
    },
    {
        'slug': 'newark-minimal-kitchen',
        'wix_slug': 'newarkminimalkitchen',
        'name': 'Newark Minimalist Kitchen',
        'city': 'Newark', 'state': 'CA',
        'type': 'Kitchen Remodel', 'type_filter': 'kitchen-bath',
        'year': '2020',
        'desc_short': 'A minimal kitchen designed to bring a large family together — ample counter space, clean lines, neutral palette, and a layout that lets natural light and natural wood tones do all the talking.',
        'desc_detail': """This minimal kitchen was designed to bring a large family together in the heart of their home. The ample counter space and clean, minimal lines lay the backdrop for inviting gatherings and colorful dishes. The neutral color palette allows for light to penetrate the space and highlight the natural wood tones.

Minimalism done well isn't about removing personality — it's about removing noise. Every cabinet, countertop edge, and hardware choice was selected to contribute to a sense of calm and openness. The result is a kitchen that feels generous even in a modest footprint.

Ridgecrest Designs produced renders for this project that made the minimal design legible to the clients before a single measurement was taken — allowing them to commit to the vision with total confidence.""",
        'specs': {'What': 'Kitchen Remodel', 'Where': 'Newark, CA', 'When': '2020'},
        'hero': 'ff5b18_0ab4862750bf42ac8c38304bf1a054ed_mv2', 'hero_ext': 'jpg',
        'gallery': [
            ('ff5b18_0ab4862750bf42ac8c38304bf1a054ed_mv2', 'jpg'),
            ('ff5b18_f81286bb193b4eceade91c476d030da2_mv2', 'png'),
            ('ff5b18_f2d002a1b71342199e013a4389c24d40_mv2', 'jpg'),
        ],
        'featured': False,
    },
]

# ── Shared HTML fragments ─────────────────────────────────────────────────────

LD_BUSINESS = """{
  "@context": "https://schema.org",
  "@type": ["LocalBusiness","HomeAndConstructionBusiness"],
  "name": "Ridgecrest Designs",
  "description": "Luxury design-build firm specializing in custom homes and high-end remodels across Pleasanton, Danville, Walnut Creek, Lafayette, Orinda, Alamo, San Ramon and the East Bay.",
  "url": "https://www.ridgecrestdesigns.com",
  "telephone": "+19257842798",
  "email": "info@ridgecrestdesigns.com",
  "foundingDate": "2013",
  "founder": {"@type":"Person","name":"Tyler Ridgecrest"},
  "priceRange": "$$$$$",
  "address": {"@type":"PostalAddress","streetAddress":"5502 Sunol Blvd Suite 100","addressLocality":"Pleasanton","addressRegion":"CA","postalCode":"94566","addressCountry":"US"},
  "geo": {"@type":"GeoCoordinates","latitude":37.6624,"longitude":-121.8747},
  "areaServed": [
    {"@type":"City","name":"Pleasanton"},{"@type":"City","name":"Danville"},
    {"@type":"City","name":"Walnut Creek"},{"@type":"City","name":"Lafayette"},
    {"@type":"City","name":"Orinda"},{"@type":"City","name":"Alamo"},
    {"@type":"City","name":"San Ramon"},{"@type":"City","name":"Sunol"}
  ],
  "sameAs": [
    "https://www.facebook.com/ridgecrestdesigns",
    "https://www.instagram.com/ridgecrestdesigns",
    "https://www.houzz.com/pro/ridgecrestdesigns"
  ]
}"""

def nav_html():
    return """  <nav class="nav nav--scrolled" id="nav">
    <a href="index.html" class="nav__logo">RIDGECREST DESIGNS</a>
    <button class="nav__toggle" id="navToggle" aria-label="Menu">
      <span></span><span></span><span></span>
    </button>
    <ul class="nav__links" id="navLinks">
      <li><a href="about.html">About</a></li>
      <li><a href="process.html">Process</a></li>
      <li><a href="services.html">Services</a></li>
      <li><a href="portfolio.html">Portfolio</a></li>
      <li><a href="/blog">The RD Edit</a></li>
      <li><a href="team.html">Team</a></li>
      <li><a href="contact.html" class="nav__cta">Start a Project</a></li>
    </ul>
  </nav>"""

def footer_html():
    return """  <footer class="footer">
    <div class="container footer__inner">
      <div class="footer__brand">
        <span class="footer__logo">RIDGECREST DESIGNS</span>
        <p class="footer__tagline">Luxury Design-Build &middot; Est. 2013</p>
        <p class="footer__tagline" style="font-style:italic; opacity:0.6">Experience the Ridgecrest difference.</p>
        <p class="footer__address">5502 Sunol Blvd, Suite 100<br>Pleasanton, CA 94566</p>
        <p><a href="tel:9257842798">925-784-2798</a> &middot; <a href="mailto:info@ridgecrestdesigns.com">info@ridgecrestdesigns.com</a></p>
      </div>
      <div class="footer__nav">
        <div class="footer__col">
          <p class="footer__col-head">Company</p>
          <a href="about.html">About</a>
          <a href="team.html">Team</a>
          <a href="process.html">Process</a>
          <a href="portfolio.html">Portfolio</a>
        </div>
        <div class="footer__col">
          <p class="footer__col-head">Services</p>
          <a href="services/custom-home-builder-danville.html">Custom Homes</a>
          <a href="services/whole-house-remodel-danville.html">Whole House Remodels</a>
          <a href="services/kitchen-remodel-danville.html">Kitchen Remodels</a>
          <a href="services/bathroom-remodel-danville.html">Bathroom Remodels</a>
        </div>
        <div class="footer__col">
          <p class="footer__col-head">Service Areas</p>
          <a href="services/danville.html">Danville</a>
          <a href="services/lafayette.html">Lafayette</a>
          <a href="services/walnut-creek.html">Walnut Creek</a>
          <a href="services/alamo.html">Alamo</a>
          <a href="services/orinda.html">Orinda</a>
          <a href="services/pleasanton.html">Pleasanton</a>
          <a href="services/san-ramon.html">San Ramon</a>
          <a href="services/dublin.html">Dublin</a>
        </div>
        <div class="footer__col">
          <p class="footer__col-head">Connect</p>
          <a href="https://elevate-scheduling-6b2fdec8.base44.app/ProjectInquiryForm">Start a Project</a>
          <a href="contact.html">Contact Us</a>
          <a href="/blog">The RD Edit</a>
          <a href="https://www.instagram.com/ridgecrestdesigns" target="_blank" rel="noopener">Instagram</a>
          <a href="https://www.facebook.com/ridgecrestdesigns" target="_blank" rel="noopener">Facebook</a>
          <a href="https://www.houzz.com/pro/ridgecrestdesigns" target="_blank" rel="noopener">Houzz</a>
        </div>
      </div>
    </div>
    <div class="footer__bottom">
      <div class="container">
        <p>&copy; 2026 Ridgecrest Designs. All rights reserved.</p>
        <p>Licensed &amp; Insured &middot; California Contractor</p>
      </div>
    </div>
  </footer>"""

def cta_section():
    return f"""  <section class="cta section section--dark">
    <div class="container container--narrow cta__inner">
      <h2 class="cta__headline">Start your own<br><em>extraordinary project.</em></h2>
      <p class="cta__sub">We take on a limited number of projects each year. Tell us about yours.</p>
      <a href="{INQUIRY_URL}" class="btn btn--primary btn--lg">Submit a Project Inquiry</a>
      <p class="cta__note">Or call <a href="tel:9257842798">925-784-2798</a></p>
    </div>
  </section>"""

def head_html(title, desc, canonical, og_img):
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{title}</title>
  <meta name="description" content="{desc}" />
  <link rel="stylesheet" href="css/main.css" />
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;0,400;0,500;1,300;1,400&family=Jost:wght@300;400;500&display=block" rel="stylesheet" />
  <link rel="canonical" href="https://www.ridgecrestdesigns.com/{canonical}" />
  <meta property="og:type" content="website" />
  <meta property="og:site_name" content="Ridgecrest Designs" />
  <meta property="og:title" content="{title}" />
  <meta property="og:description" content="{desc}" />
  <meta property="og:url" content="https://www.ridgecrestdesigns.com/{canonical}" />
  <meta property="og:image" content="{og_img}" />
  <meta name="twitter:card" content="summary_large_image" />
  <meta name="twitter:title" content="{title}" />
  <meta name="twitter:description" content="{desc}" />
  <meta name="twitter:image" content="{og_img}" />"""

# ── Project page generator ────────────────────────────────────────────────────

def generate_project_page(p):
    hero_src = img_src(p['hero'], p['hero_ext'])
    og_img = hero_src if hero_src.startswith('http') else f"https://www.ridgecrestdesigns.com{hero_src}"

    # Specs block
    specs_html = ''
    if p.get('specs'):
        items = ''.join(f'<div class="project-spec"><span class="project-spec__label">{k}</span><span class="project-spec__val">{v}</span></div>' for k, v in p['specs'].items())
        specs_html = f'\n      <div class="project-specs">{items}</div>'

    # Gallery items
    gallery_items = ''
    for i, (gh, ge) in enumerate(p['gallery'], 1):
        src = img_src(gh, ge)
        gallery_items += f"""        <div class="gallery-item" data-src="{src}">
          <div class="gallery-item__img" role="img" aria-label="{p['name']} — photo {i}" style="background-image:url('{src}')"></div>
          <div class="gallery-item__overlay"><span class="gallery-item__zoom">+</span></div>
        </div>\n"""

    # JSON-LD for project
    ld_project = f"""{{
  "@context": "https://schema.org",
  "@type": "CreativeWork",
  "name": "{p['name']}",
  "description": "{p['desc_short']}",
  "url": "https://www.ridgecrestdesigns.com/{p['slug']}",
  "creator": {{"@type":"Organization","name":"Ridgecrest Designs"}},
  "locationCreated": {{"@type":"Place","address":{{"@type":"PostalAddress","addressLocality":"{p['city']}","addressRegion":"{p['state']}","addressCountry":"US"}}}},
  "breadcrumb": {{"@type":"BreadcrumbList","itemListElement":[
    {{"@type":"ListItem","position":1,"name":"Home","item":"https://www.ridgecrestdesigns.com"}},
    {{"@type":"ListItem","position":2,"name":"Portfolio","item":"https://www.ridgecrestdesigns.com/portfolio"}},
    {{"@type":"ListItem","position":3,"name":"{p['name']}","item":"https://www.ridgecrestdesigns.com/{p['slug']}"}}
  ]}}
}}"""

    desc_paras = ''.join(f'<p>{para.strip()}</p>\n        ' for para in p['desc_detail'].strip().split('\n\n') if para.strip())

    html = f"""{head_html(
        f"{p['name']} — Ridgecrest Designs | {p['type']}, {p['city']}, {p['state']}",
        p['desc_short'],
        p['slug'],
        og_img
    )}
  <script type="application/ld+json">
  {LD_BUSINESS}
  </script>
  <script type="application/ld+json">
  {ld_project}
  </script>
</head>
<body>

{nav_html()}

  <div class="project-hero">
    <div class="project-hero__img" role="img" aria-label="{p['name']} by Ridgecrest Designs, {p['city']}, {p['state']}" style="background-image:url('{hero_src}')"></div>
    <div class="project-hero__overlay"></div>
  </div>

  <section class="project-meta section" style="padding-bottom:0">
    <div class="container">
      <p class="breadcrumb-back"><a href="portfolio.html">← Portfolio</a></p>
      <div class="project-meta__inner">
        <div>
          <p class="section__label">{p['city']}, {p['state']}</p>
          <h1 class="project-meta__title">{p['name']}</h1>
          <div class="project-meta__tags">
            <span class="project-meta__tag">{p['type']}</span>
            <span class="project-meta__tag">{p['year']}</span>
          </div>
        </div>
        <div class="project-meta__cta">
          <a href="{INQUIRY_URL}" class="btn btn--dark">Start a Similar Project</a>
        </div>
      </div>
      <div class="project-description">
        {desc_paras}
      </div>{specs_html}
    </div>
  </section>

  <section class="project-gallery">
    <div class="container">
      <p class="project-gallery__label">Project Gallery</p>
      <div class="gallery-grid">
{gallery_items}      </div>
    </div>
  </section>

  <div class="lightbox" id="lightbox">
    <span class="lightbox__close">&times;</span>
    <span class="lightbox__prev">&#8592;</span>
    <img class="lightbox__img" src="" alt="Project photo" />
    <span class="lightbox__next">&#8594;</span>
    <span class="lightbox__counter"></span>
  </div>

{cta_section()}

{footer_html()}

  <script src="js/main.js"></script>
  <script src="js/lightbox.js"></script>
</body>
</html>"""
    return html

# ── portfolio.html (featured 4 + View All CTA) ───────────────────────────────

def generate_portfolio_page():
    featured = [p for p in PROJECTS if p.get('featured')]
    assert len(featured) == 4, f"Expected 4 featured, got {len(featured)}"

    cards = ''
    for p in featured:
        src = img_src(p['hero'], p['hero_ext'])
        cards += f"""        <a href="{p['slug']}.html" class="portfolio-featured__card">
          <div class="portfolio-featured__img" style="background-image:url('{src}')" role="img" aria-label="{p['name']} — {p['type']} by Ridgecrest Designs"></div>
          <div class="portfolio-featured__overlay"></div>
          <div class="portfolio-featured__info">
            <span class="portfolio-featured__loc">{p['city']}, {p['state']}</span>
            <h3 class="portfolio-featured__name">{p['name']}</h3>
            <span class="portfolio-featured__type">{p['type']} &middot; {p['year']}</span>
          </div>
        </a>\n"""

    # Schema ItemList — all 18
    item_parts = []
    for i, p in enumerate(PROJECTS):
        item_parts.append(
            '{{"@type":"ListItem","position":{pos},"name":"{name}","url":"https://www.ridgecrestdesigns.com/{slug}"}}'.format(
                pos=i+1, name=p['name'], slug=p['slug'])
        )
    item_list = ',\n      '.join(item_parts)

    html = f"""{head_html(
        "Portfolio — Ridgecrest Designs | Luxury Homes & Remodels, East Bay CA",
        "Explore Ridgecrest Designs' portfolio of luxury custom homes and high-end remodels across Pleasanton, Danville, Lafayette, Orinda, and the East Bay.",
        "portfolio",
        img_src(featured[0]['hero'], featured[0]['hero_ext'])
    )}
  <script type="application/ld+json">
  {LD_BUSINESS}
  </script>
  <script type="application/ld+json">
  {{
    "@context": "https://schema.org",
    "@type": "CollectionPage",
    "name": "Portfolio — Ridgecrest Designs",
    "url": "https://www.ridgecrestdesigns.com/portfolio",
    "description": "Luxury custom homes and high-end remodels across Pleasanton, Danville, Lafayette, Orinda, and the East Bay.",
    "mainEntity": {{
      "@type": "ItemList",
      "itemListElement": [
      {item_list}
      ]
    }}
  }}
  </script>
  <style>
    .portfolio-featured__grid {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 3px;
    }}
    .portfolio-featured__card {{
      position: relative;
      display: block;
      aspect-ratio: 4/3;
      overflow: hidden;
      text-decoration: none;
    }}
    .portfolio-featured__img {{
      width: 100%;
      height: 100%;
      background-size: cover;
      background-position: center;
      transition: transform 0.6s ease;
    }}
    .portfolio-featured__card:hover .portfolio-featured__img {{
      transform: scale(1.04);
    }}
    .portfolio-featured__overlay {{
      position: absolute; inset: 0;
      background: linear-gradient(to top, rgba(0,0,0,0.75) 0%, rgba(0,0,0,0.1) 50%, transparent 100%);
    }}
    .portfolio-featured__info {{
      position: absolute; bottom: 0; left: 0; right: 0;
      padding: 28px 24px 24px;
    }}
    .portfolio-featured__loc {{
      display: block;
      font-family: var(--font-body);
      font-size: 11px;
      letter-spacing: 0.12em;
      text-transform: uppercase;
      color: rgba(255,255,255,0.7);
      margin-bottom: 6px;
    }}
    .portfolio-featured__name {{
      font-family: var(--font-display);
      font-size: clamp(1.2rem, 2vw, 1.6rem);
      font-weight: 400;
      color: #fff;
      margin: 0 0 8px;
      line-height: 1.2;
    }}
    .portfolio-featured__type {{
      font-family: var(--font-body);
      font-size: 12px;
      letter-spacing: 0.08em;
      color: rgba(255,255,255,0.6);
    }}
    .portfolio-view-all {{
      text-align: center;
      padding: 48px 24px;
      background: #111;
    }}
    .portfolio-view-all p {{
      font-family: var(--font-body);
      font-size: 13px;
      color: rgba(255,255,255,0.5);
      letter-spacing: 0.06em;
      margin-bottom: 20px;
    }}
    @media (max-width: 640px) {{
      .portfolio-featured__grid {{ grid-template-columns: 1fr; }}
    }}
    .breadcrumb-back {{ display: none; }}
  </style>
</head>
<body>

{nav_html()}

  <div class="page-hero page-hero--service">
    <p class="page-hero__eyebrow">Our Work</p>
    <h1 class="page-hero__title">Selected projects<br><em>across the East Bay</em></h1>
    <p class="page-hero__sub">Every project begins with a render. Every render becomes a home.</p>
  </div>

  <section class="section section--dark" style="padding:0">
    <div class="portfolio-featured__grid">
{cards}    </div>
  </section>

  <div class="portfolio-view-all">
    <p>Showing 4 of 18 projects</p>
    <a href="allprojects.html" class="btn btn--primary">View All 18 Projects &rarr;</a>
  </div>

{cta_section()}

{footer_html()}

  <script src="js/main.js"></script>
</body>
</html>"""
    return html

# ── allprojects.html (full grid, filterable) ──────────────────────────────────

def generate_allprojects_page():
    # Build all 18 cards
    cards = ''
    for p in PROJECTS:
        src = img_src(p['hero'], p['hero_ext'])
        filter_class = p['type_filter']
        cards += f"""        <a href="{p['slug']}.html" class="proj-card" data-filter="{filter_class}">
          <div class="proj-card__img" style="background-image:url('{src}')" role="img" aria-label="{p['name']}"></div>
          <div class="proj-card__body">
            <span class="proj-card__loc">{p['city']}, {p['state']}</span>
            <h3 class="proj-card__name">{p['name']}</h3>
            <div class="proj-card__meta">
              <span class="proj-card__type">{p['type']}</span>
              <span class="proj-card__year">{p['year']}</span>
            </div>
          </div>
        </a>\n"""

    html = f"""{head_html(
        "All Projects — Ridgecrest Designs | 18 Luxury Homes & Remodels",
        "Browse all 18 Ridgecrest Designs projects — custom homes, whole house remodels, kitchen and bathroom renovations across the East Bay and Tri-Valley.",
        "allprojects",
        img_src(PROJECTS[0]['hero'], PROJECTS[0]['hero_ext'])
    )}
  <script type="application/ld+json">
  {LD_BUSINESS}
  </script>
  <style>
    .allprojects-hero {{
      background: #111;
      padding: 80px 24px 48px;
      text-align: center;
    }}
    .allprojects-hero__back {{
      display: inline-block;
      font-family: var(--font-body);
      font-size: 12px;
      letter-spacing: 0.1em;
      text-transform: uppercase;
      color: rgba(255,255,255,0.5);
      text-decoration: none;
      margin-bottom: 24px;
    }}
    .allprojects-hero__back:hover {{ color: rgba(255,255,255,0.8); }}
    .allprojects-hero h1 {{
      font-family: var(--font-display);
      font-size: clamp(2rem, 5vw, 3.2rem);
      font-weight: 300;
      color: #fff;
      margin: 0 0 12px;
    }}
    .allprojects-hero p {{
      font-family: var(--font-body);
      font-size: 14px;
      color: rgba(255,255,255,0.55);
      letter-spacing: 0.04em;
    }}
    .filter-tabs {{
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
      justify-content: center;
      padding: 32px 24px 0;
      background: #111;
    }}
    .filter-tab {{
      font-family: var(--font-body);
      font-size: 12px;
      letter-spacing: 0.1em;
      text-transform: uppercase;
      color: rgba(255,255,255,0.5);
      background: transparent;
      border: 1px solid rgba(255,255,255,0.15);
      border-radius: 2px;
      padding: 8px 18px;
      cursor: pointer;
      transition: all 0.2s;
    }}
    .filter-tab:hover {{ color: #fff; border-color: rgba(255,255,255,0.4); }}
    .filter-tab.active {{ color: #fff; border-color: #fff; background: rgba(255,255,255,0.08); }}
    .proj-grid {{
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 3px;
      background: #111;
      padding: 3px 0 0;
    }}
    .proj-card {{
      display: block;
      text-decoration: none;
      background: #1a1a1a;
      overflow: hidden;
      transition: opacity 0.3s;
    }}
    .proj-card.hidden {{ display: none; }}
    .proj-card__img {{
      aspect-ratio: 4/3;
      background-size: cover;
      background-position: center;
      transition: transform 0.5s ease;
    }}
    .proj-card:hover .proj-card__img {{ transform: scale(1.04); }}
    .proj-card__body {{
      padding: 16px 18px 20px;
    }}
    .proj-card__loc {{
      display: block;
      font-family: var(--font-body);
      font-size: 10px;
      letter-spacing: 0.12em;
      text-transform: uppercase;
      color: rgba(255,255,255,0.45);
      margin-bottom: 6px;
    }}
    .proj-card__name {{
      font-family: var(--font-display);
      font-size: 1.15rem;
      font-weight: 400;
      color: #fff;
      margin: 0 0 10px;
      line-height: 1.25;
    }}
    .proj-card__meta {{
      display: flex;
      align-items: center;
      gap: 10px;
    }}
    .proj-card__type {{
      font-family: var(--font-body);
      font-size: 11px;
      color: rgba(255,255,255,0.4);
      letter-spacing: 0.06em;
    }}
    .proj-card__year {{
      font-family: var(--font-body);
      font-size: 11px;
      color: rgba(255,255,255,0.25);
    }}
    .proj-count {{
      text-align: center;
      padding: 20px;
      background: #111;
      font-family: var(--font-body);
      font-size: 12px;
      color: rgba(255,255,255,0.35);
      letter-spacing: 0.06em;
    }}
    @media (max-width: 900px) {{ .proj-grid {{ grid-template-columns: repeat(2, 1fr); }} }}
    @media (max-width: 520px) {{ .proj-grid {{ grid-template-columns: 1fr; }} }}
    .breadcrumb-back {{ display: none; }}
  </style>
</head>
<body>

{nav_html()}

  <div class="allprojects-hero">
    <a href="portfolio.html" class="allprojects-hero__back">← Back to Portfolio</a>
    <h1>All Projects</h1>
    <p>18 projects &mdash; custom homes, remodels, kitchens &amp; baths across the East Bay</p>
  </div>

  <div class="filter-tabs" id="filterTabs">
    <button class="filter-tab active" data-filter="all">All (18)</button>
    <button class="filter-tab" data-filter="custom-home">Custom Homes</button>
    <button class="filter-tab" data-filter="whole-house">Whole House</button>
    <button class="filter-tab" data-filter="kitchen-bath">Kitchen &amp; Bath</button>
    <button class="filter-tab" data-filter="garage-specialty">Garage &amp; Specialty</button>
  </div>

  <div class="proj-count" id="projCount">Showing all 18 projects</div>

  <section style="background:#111; padding-bottom: 3px;">
    <div class="proj-grid" id="projGrid">
{cards}    </div>
  </section>

{cta_section()}

{footer_html()}

  <script src="js/main.js"></script>
  <script>
    const tabs = document.querySelectorAll('.filter-tab');
    const cards = document.querySelectorAll('.proj-card');
    const countEl = document.getElementById('projCount');
    const labels = {{
      'all': 'Showing all 18 projects',
      'custom-home': 'Custom Homes',
      'whole-house': 'Whole House Remodels',
      'kitchen-bath': 'Kitchen & Bath',
      'garage-specialty': 'Garage & Specialty'
    }};
    tabs.forEach(tab => {{
      tab.addEventListener('click', () => {{
        const filter = tab.dataset.filter;
        tabs.forEach(t => t.classList.remove('active'));
        tab.classList.add('active');
        let visible = 0;
        cards.forEach(card => {{
          const show = filter === 'all' || card.dataset.filter === filter;
          card.classList.toggle('hidden', !show);
          if (show) visible++;
        }});
        countEl.textContent = filter === 'all'
          ? 'Showing all 18 projects'
          : `Showing ${{visible}} project${{visible !== 1 ? 's' : ''}}: ${{labels[filter] || filter}}`;
      }});
    }});
  </script>
</body>
</html>"""
    return html

# ── Write all files ───────────────────────────────────────────────────────────

def write(path, content):
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f'  wrote {os.path.relpath(path, PREVIEW)}')

print('Generating portfolio pages...')
for p in PROJECTS:
    html = generate_project_page(p)
    write(os.path.join(PREVIEW, f"{p['slug']}.html"), html)

print('Generating portfolio.html...')
write(os.path.join(PREVIEW, 'portfolio.html'), generate_portfolio_page())

print('Generating allprojects.html...')
write(os.path.join(PREVIEW, 'allprojects.html'), generate_allprojects_page())

print(f'\nDone. {len(PROJECTS)} project pages + portfolio.html + allprojects.html')
print('\nMissing images (need migrate run from laptop):')
for p in PROJECTS:
    missing = [(h, e) for h, e in p['gallery'] if not local_webp(h)]
    if not local_webp(p['hero']):
        print(f"  {p['slug']} HERO: {p['hero']}.{p['hero_ext']}")
    for h, e in missing:
        print(f"  {p['slug']} gallery: {h}.{e}")

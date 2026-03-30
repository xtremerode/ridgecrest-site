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
            ('ff5b18_e4715d92a11c4c5682cb6b069075018a_mv2', 'jpg'),
            ('ff5b18_b67df4d5003d43ba8d6e8a160b23f2cd_mv2', 'jpg'),
            ('ff5b18_a363f7c834604c128cda653cf45e5367_mv2', 'jpg'),
            ('ff5b18_4f960eeba52c4a4c9ce82a2a55b52ec5_mv2', 'jpg'),
            ('ff5b18_574ad81d4b81481184c206a7be04578f_mv2', 'jpg'),
            ('ff5b18_e4aa7744fdb44b4f9637dfa469574648_mv2', 'jpg'),
            ('ff5b18_316eec2b39934fd7b0783b5c865f6f0c_mv2', 'jpg'),
            ('ff5b18_e27fd127d04f45f3a931f91210dabc07_mv2', 'jpg'),
            ('ff5b18_4516f51554374af3a122cd7ee3b5c06c_mv2', 'jpg'),
            ('ff5b18_0769ea7b226147ceb6eee9b632df5bae_mv2', 'jpg'),
            ('ff5b18_b73c2686fcf44f84a789d00e455f307b_mv2', 'jpg'),
            ('ff5b18_75a9ba9c5a87418daf6d2b69c70f60ff_mv2', 'jpg'),
            ('ff5b18_a3caf294dc5e4be68b36f626e9c42ea2_mv2', 'jpg'),
            ('ff5b18_1fbce4b2397a48f7991c87f8406ba67d_mv2', 'jpg'),
            ('ff5b18_65d7e65ebe3942c38054df7a5eba4302_mv2', 'jpg'),
            ('ff5b18_d0f8c15054d7404ab39b2e48dd2c4610_mv2', 'jpg'),
            ('ff5b18_e73241a2a89840e8b828d1a604830f17_mv2', 'jpg'),
            ('ff5b18_25b92e31b44346549995acfa378ad325_mv2', 'jpg'),
            ('ff5b18_037bd402192d4bd19879917e9f9dc7b1_mv2', 'jpg'),
            ('ff5b18_66c5153a1ec44adab9d8603f0eceec8f_mv2', 'jpg'),
            ('ff5b18_5843843f2d0141e987c0e96a1e68b6b1_mv2', 'jpg'),
            ('ff5b18_789d474d6d0149eea64b9629dc7a9d7b_mv2', 'jpg'),
            ('ff5b18_7c54ccfe90ad4065ae0f0aa063a629e4_mv2', 'jpg'),
            ('ff5b18_6a5a8b093a7d4ec1bfb1eddf7fe753b4_mv2', 'jpg'),
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
            ('ff5b18_42db29ccfa3949e6ae1e773888bcac59_mv2', 'jpg'),
            ('ff5b18_8e8a0acd45874a41a17619c8f12ee4cc_mv2', 'jpg'),
            ('ff5b18_8f25d193b0a2414a89b864f14a54e442_mv2', 'jpg'),
            ('ff5b18_dd094f46b3f14424a266355c7bd4a7c0_mv2', 'jpg'),
            ('ff5b18_8b88af1e6d69497fb210d95ceab32ad6_mv2', 'jpg'),
            ('ff5b18_acf2d49760f546539ec1e543ee39e702_mv2', 'jpg'),
            ('ff5b18_b2ea32008e8748c29e682596df620cf9_mv2', 'jpg'),
            ('ff5b18_c4feea2667c647bba02523520c5ca48d_mv2', 'jpg'),
            ('ff5b18_236ae3c88608452fb5e63a8881ad1e46_mv2', 'jpg'),
            ('ff5b18_1239f1bef81a42ad83438ee930016733_mv2', 'jpg'),
            ('ff5b18_3864f91962544bb2abb00e69f079ba8e_mv2', 'jpg'),
            ('ff5b18_1479b0c3a4fc4182b307f5214a2d25cd_mv2', 'jpg'),
            ('ff5b18_d30dfa95656540f18cc8cb06d7c673ad_mv2', 'jpg'),
            ('ff5b18_e04bfbab22294ca784254c5d6da8b89c_mv2', 'jpg'),
            ('ff5b18_a8c2aa57b915444dafebb604985e0621_mv2', 'jpg'),
            ('ff5b18_5032c1aca2484f22a7cb801306f1c2cf_mv2', 'jpg'),
            ('ff5b18_b927c23da6da4311b72d3c22d39a209d_mv2', 'jpg'),
            ('ff5b18_ef7e9248effd4b65bbf792589cec128a_mv2', 'jpg'),
            ('ff5b18_5b97bf4ab5144c2da7f3e3aa80fb8532_mv2', 'png'),
            ('ff5b18_0f8e248ff1424e8a9016fcac13a94cea_mv2', 'png'),
            ('ff5b18_53f46b46f9094468addb44305dff0a55_mv2', 'jpg'),
            ('ff5b18_1939fb8d8df2493a9c28bfc35dc8a9c3_mv2', 'jpg'),
            ('ff5b18_8169ea986d9a426abe1ee95d8120e794_mv2', 'jpg'),
            ('ff5b18_094ff86fd81c4a47a3ee9d0554b0303e_mv2', 'jpg'),
            ('ff5b18_5734da78eec545329fe074dc71f86326_mv2', 'jpg'),
            ('ff5b18_3d54d629081b4cffac259ea08ed0f552_mv2', 'jpg'),
            ('ff5b18_68336ad7449c4a6bb9502b541afd244c_mv2', 'jpg'),
            ('ff5b18_376077d7fb0e40f2b394154c6aed5771_mv2', 'jpg'),
            ('ff5b18_a506a1b7c3094574919d609aaedf310e_mv2', 'jpg'),
            ('ff5b18_9ddef3ad9b24428e8782634a3dd2a92d_mv2', 'jpg'),
            ('ff5b18_8063b45cadc54b20a7d6eb9928d73e06_mv2', 'jpg'),
            ('ff5b18_6b5fc44e62c548f88f43648494248b8d_mv2', 'jpg'),
            ('ff5b18_b28412dbf897438591f8b93f12d53dcf_mv2', 'jpg'),
            ('ff5b18_52079e7283d74abf8837e9acd2730309_mv2', 'jpg'),
            ('ff5b18_689c82335590480bab8687093b788f39_mv2', 'png'),
            ('ff5b18_4dbbff9e350e432980cccfc598f0dc7f_mv2', 'png'),
            ('ff5b18_a74c7ef598444446bb8d03653c3328e8_mv2', 'png'),
            ('ff5b18_7afabe08804f4547850b618be2d91ae6_mv2', 'png'),
            ('ff5b18_ff725c980f7a43dcb69904fdbc47bd24_mv2', 'png'),
            ('ff5b18_9cd0d8a66b364c1ea15c032acb7da0cc_mv2', 'png'),
            ('ff5b18_3f1b7aa631894aa8b3345db56bc8fdc2_mv2', 'png'),
            ('ff5b18_bff1a21d68894b1485619571dec937c1_mv2', 'jpg'),
            ('ff5b18_166b3d9326fb475aa78e1c30e2f70208_mv2', 'jpg'),
            ('ff5b18_dd853c2703794d2b930b3be2a8fc483f_mv2', 'jpg'),
            ('ff5b18_1d319e46d16c42edb618f929d78be1ce_mv2', 'jpg'),
            ('ff5b18_56709ef3ab734ab79dac77379f00eb78_mv2', 'jpg'),
            ('ff5b18_3ea2da7dae7046758adcc27e54b5b865_mv2', 'jpg'),
            ('ff5b18_ef9b9e4c9e8048c0b21b0d5ad19143b3_mv2', 'jpg'),
            ('ff5b18_5e380d36f3d64940a665de8a281fe23f_mv2', 'jpg'),
            ('ff5b18_f399ea12bfd842d48f6f1a70f5c199bc_mv2', 'jpg'),
            ('ff5b18_ecc34a03656549caa7e8d6ee648480dc_mv2', 'jpg'),
            ('ff5b18_ef43f9ef1b89406a8ed43208ece970c8_mv2', 'jpg'),
            ('ff5b18_290d185c4a514099b505fa1baa0adcc7_mv2', 'jpg'),
            ('ff5b18_1f525ab949e548f39a3a614b47579b62_mv2', 'jpg'),
            ('ff5b18_8ae6f73e058844489a19f7cb714ddf51_mv2', 'jpg'),
            ('ff5b18_5ab5e51647d5480687a20189d68a382e_mv2', 'jpg'),
            ('ff5b18_b81ad19e857d4e99b57edf295d8732b7_mv2', 'jpg'),
            ('ff5b18_a9a4054d937b4d2f87b68ae86f8e6505_mv2', 'jpg'),
            ('ff5b18_ec34ac50f5ed421b8914a9ed0c9d168e_mv2', 'jpg'),
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
            ('ff5b18_5b8b92bdb42f488681d9bad5096f781a_mv2', 'png'),
            ('ff5b18_82e5d2a1febd4d1abc6eecd7aadb0101_mv2', 'jpg'),
            ('ff5b18_411783f880354934a6a03443a1e94e6f_mv2', 'jpg'),
            ('ff5b18_a9e73e816d92428fa51524289a3ba901_mv2', 'png'),
            ('ff5b18_0db20a1095e04ff6ad6057d18ebc0e8d_mv2', 'jpg'),
            ('ff5b18_d1fe2e4614164cc5ab55600fad820ddb_mv2', 'png'),
            ('ff5b18_ca306e63f3814f06a60e7424c862f8d6_mv2', 'jpg'),
            ('ff5b18_4d337f2682cc4aa682f48fcba262108a_mv2', 'jpg'),
            ('ff5b18_850e80bfbef5485c9f404e689754d7ec_mv2', 'jpg'),
            ('ff5b18_735de630b9844dfbb108f96cb0773617_mv2', 'jpg'),
            ('ff5b18_5c5dd50218d24abf9b582502b894f21e_mv2', 'jpg'),
            ('ff5b18_4945f79c5e534a089a92f11cc8a7f277_mv2', 'jpg'),
            ('ff5b18_a590a45838f64727a3355c5724cf57d4_mv2', 'jpg'),
            ('ff5b18_ab748d2b2e4047119ad34df519ba81ea_mv2', 'png'),
            ('ff5b18_46718a5e04de4b499d1eb8861d5b31fb_mv2', 'png'),
            ('ff5b18_017e7503e4ea4fe19c98e6a31e9f48d7_mv2', 'png'),
            ('ff5b18_296b1e9ff5d14e128006c21217e3f3e9_mv2', 'jpg'),
            ('ff5b18_2db5ae87de214033b21a25b8954c6417_mv2', 'png'),
            ('ff5b18_5571ae405db6439f8950f603ac6f2fd7_mv2', 'jpg'),
            ('ff5b18_4dc535e7fe1a421da4b764db096f79a3_mv2', 'jpg'),
            ('ff5b18_60530d19612e4d45b5cb8fb021a681ca_mv2', 'jpg'),
            ('ff5b18_4356ca161d1a40a9bd7f451dfc598c74_mv2', 'png'),
            ('ff5b18_fec9947150e94990883c158ac7fbb2b6_mv2', 'jpg'),
            ('ff5b18_8c3d6a47a7af4c5986cf968aac8a0545_mv2', 'jpg'),
            ('ff5b18_86e17388126b47e3b08d204ff3f39b68_mv2', 'jpg'),
            ('ff5b18_1d617606c21b4ce3ad875459e690ba91_mv2', 'jpg'),
            ('ff5b18_d61183070b3b4e2f856f0c271ae55b5a_mv2', 'png'),
            ('ff5b18_fc8284a96978430ba265e928d858b15d_mv2', 'png'),
            ('ff5b18_7e7176ba86d043e7a79be3fcd53aa7c0_mv2', 'png'),
            ('ff5b18_29d906c1527b408a99118280841bbd42_mv2', 'png'),
            ('ff5b18_2e1838a06bff4e77960eaba2a20242a5_mv2', 'png'),
            ('ff5b18_265b8cd6595d4ba9a608381a18222fde_mv2', 'png'),
            ('ff5b18_de323270e3574f2582de93c63a85e584_mv2', 'png'),
            ('ff5b18_ef630f1a109d4f1aa6e918307c0e02a6_mv2', 'png'),
            ('ff5b18_b651e8713e0749368367a9e5e840fa55_mv2', 'jpg'),
            ('ff5b18_8263a2cdc43a4f9d9f5b0b6945039c77_mv2', 'png'),
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
            ('ff5b18_4a378f6899d24b5ba7bc7551ea53540a_mv2', 'png'),
            ('ff5b18_c0e8f9e9008c498eac5efafae3c46b04_mv2', 'jpg'),
            ('ff5b18_1ef4108f78534aa59c515d38946c4644_mv2', 'jpg'),
            ('ff5b18_b246a630ba864e2a8fe67d964745b9b5_mv2', 'jpg'),
            ('ff5b18_7e0f0e5602694ed280e46ec708e7b068_mv2', 'jpg'),
            ('ff5b18_63757c728db94733b4f60a7102c0f722_mv2', 'jpg'),
            ('ff5b18_487bdc0f0af642d9b49405d476c80c5e_mv2', 'jpg'),
            ('ff5b18_7bdab37a61b24537af57e91ce2978f4c_mv2', 'jpg'),
            ('ff5b18_b0f0c5eecc8d4f7ba7ae030a334d5f93_mv2', 'jpg'),
            ('ff5b18_19b678ef0cf34b9ca705133688ea91b1_mv2', 'jpg'),
            ('ff5b18_10521de8c90243f58322ebef9335a4c8_mv2', 'jpg'),
            ('ff5b18_864272d4755d468096cd4e388a01a773_mv2', 'jpg'),
            ('ff5b18_5ed3b0005abb494885a58ee0c4508248_mv2', 'jpg'),
            ('ff5b18_b93571ff11674224b7489b5e425116ee_mv2', 'jpg'),
            ('ff5b18_c520c9ca384d4c3ebe02707d0c8f45ab_mv2', 'jpg'),
            ('ff5b18_33d2068cd10941fbad0293bdc73d63d5_mv2', 'jpg'),
            ('ff5b18_4e56d06b0c6e4c80aabe636642bf8346_mv2', 'jpg'),
            ('ff5b18_cd0bbd1ca0924ba38e0578501a1958ec_mv2', 'jpg'),
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
            ('ff5b18_bb1013e8034740828826f718ad2216d9_mv2', 'png'),
            ('ff5b18_938143f6f9374aa88d8ed87d5de5bb73_mv2', 'jpg'),
            ('ff5b18_e25234795a7a4ed08b1bea59751199a9_mv2', 'jpg'),
            ('ff5b18_0d88c8d60a794608ae52e386cb653c92_mv2', 'jpg'),
            ('ff5b18_672125820d5a46069583b4cc0f2a6335_mv2', 'jpg'),
            ('ff5b18_2780ac2b8ec84080a5eca2658e4a8f27_mv2', 'jpg'),
            ('ff5b18_831537efc37e4610adff9f8e982c8039_mv2', 'jpg'),
            ('ff5b18_76ec6d9dbc3b4d29ab02bc08c56cf7e5_mv2', 'png'),
            ('ff5b18_8d75523812e941f2a37fafd4d1f65557_mv2', 'jpg'),
            ('ff5b18_0b701547bc92489cbf3985cef0ed0275_mv2', 'png'),
            ('ff5b18_3f272f8928964dc8a4ef4c4100ebcbb9_mv2', 'png'),
            ('ff5b18_180583f962c742faaa90d6b0adda3528_mv2', 'png'),
            ('ff5b18_41d97144818e40e09ddddd7357704009_mv2', 'png'),
            ('ff5b18_a6a474bf0bef4095af1c07f5505da43f_mv2', 'png'),
            ('ff5b18_deb303a4cdf1412291032c4e55be8128_mv2', 'png'),
            ('ff5b18_a0ebb85eb6174c0eb286208f5bf564ca_mv2', 'png'),
            ('ff5b18_bee090a1db814d60844aed6337fc984d_mv2', 'png'),
            ('ff5b18_17b3952b932d497d8734d0ee1254a6b7_mv2', 'jpg'),
            ('ff5b18_8987814f88814d3aaf441bd83b524f9d_mv2', 'jpg'),
            ('ff5b18_5f782d175d304c39bd1a5a68ecd17837_mv2', 'jpg'),
            ('ff5b18_bcd726fa503f41e8ae32288d50273c8e_mv2', 'jpg'),
            ('ff5b18_282f835436004b0d9b5de972e29a5d5f_mv2', 'jpg'),
            ('ff5b18_374f5820e34b4e66992972e7c6124b55_mv2', 'jpg'),
            ('ff5b18_573d3c0f5dad490897ba75af9370d696_mv2', 'jpg'),
            ('ff5b18_56d7f44285954670840a9274a0dcc8dc_mv2', 'jpg'),
            ('ff5b18_8439227c1cde4a3f8687607a2b2d7282_mv2', 'jpg'),
            ('ff5b18_d6990ae171234dd1bbd4ca896c45c0c0_mv2', 'jpg'),
            ('ff5b18_47b90fee8ee54b1281403a55b433a3d1_mv2', 'jpg'),
            ('ff5b18_f38f6e2f56dc45948213c61e22ae354a_mv2', 'jpg'),
            ('ff5b18_a7c7f26a79b44b539bd15ec69632c520_mv2', 'jpg'),
            ('ff5b18_e611e808bcca468690b28ccea00566f3_mv2', 'jpg'),
            ('ff5b18_d4a890f899554194b71163ed3228ad40_mv2', 'jpg'),
            ('ff5b18_60dcea6c584443c786986468f367b604_mv2', 'jpg'),
            ('ff5b18_972295aeee794eb793ab8d1c9f066f0c_mv2', 'jpg'),
            ('ff5b18_6851d4154ba84f9d9fecc60cf88f9ad5_mv2', 'jpg'),
            ('ff5b18_6c49c91ca5d1455f9d9035d0a4cc3a4a_mv2', 'jpg'),
            ('ff5b18_9ad5ceb2247b4dbfb5382b6cd47974e8_mv2', 'jpg'),
            ('ff5b18_ada0f19a57c548ea93ead7ed89a8b568_mv2', 'jpg'),
            ('ff5b18_9549cbaddd59469e8c0e7335fb83fcd3_mv2', 'jpg'),
            ('ff5b18_6b774e563986424c88cb4a867ddbcfa3_mv2', 'jpg'),
            ('ff5b18_2a98f5aa4f384219b7c48068558b230a_mv2', 'jpg'),
            ('ff5b18_5b2a034ec6cc483baa376f49e147dc08_mv2', 'jpg'),
            ('ff5b18_e770197d24e4436aae7c1c05d9d07a62_mv2', 'jpg'),
            ('ff5b18_287252fbc1f0474c8c5448c350dcfad2_mv2', 'jpg'),
            ('ff5b18_8d194ec65ece42e1a9a046dacdd67157_mv2', 'jpg'),
            ('ff5b18_d21a6cfecad9421bb43dbd6d1a63828f_mv2', 'jpg'),
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
            ('ff5b18_c1e5fd8a13c34fa985b5b84f87a8f7d1_mv2', 'jpg'),
            ('ff5b18_bcab10ed365d4e7183fdfd58fa581372_mv2', 'jpg'),
            ('ff5b18_c1637bae333840e4a71cbdaac8405213_mv2', 'png'),
            ('ff5b18_8f94e57d36c84799bacb3aec32cd1418_mv2', 'png'),
            ('ff5b18_c1c8fff952dd4e6d878c60e6d6117d56_mv2', 'png'),
            ('ff5b18_af3d4948b1c349bcaf72ebff882f4ad6_mv2', 'png'),
            ('ff5b18_933c6fe0073f459dba6c4f077fd9704a_mv2', 'png'),
            ('ff5b18_1b7372e889bd4b6793da6f9a0c159dfb_mv2', 'png'),
            ('ff5b18_7f1d04c690b0453fbb22aaf1d443dc76_mv2', 'jpg'),
            ('ff5b18_4115fae529ce4974a6b6ead3ded507a9_mv2', 'jpg'),
            ('ff5b18_6ce3779e8542406db45d54ee9e8a9d33_mv2', 'jpg'),
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
            ('ff5b18_fa8d30d31488413ca93cf28ed74c8e05_mv2', 'jpg'),
            ('ff5b18_c8f3843d541b4a9cbd5d0b7890f93880_mv2', 'jpg'),
            ('ff5b18_e39d6cfcd0cf4fafbe6cbcef4c35e47a_mv2', 'jpg'),
            ('ff5b18_096e22af570b4c509e3a8b7d085076ee_mv2', 'jpg'),
            ('ff5b18_23e5e93fc68647b6a7a0dd359c143088_mv2', 'png'),
            ('ff5b18_de2ed75da1a541abb0861b82d04e1135_mv2', 'png'),
            ('ff5b18_a69a1fba43ec4dd98ec66e582d5ec86f_mv2', 'png'),
            ('ff5b18_7d9860cd5e234283aebffeff9b4bfbc9_mv2', 'png'),
            ('ff5b18_5ef00a1c27fa49929b6841b112dedb12_mv2', 'png'),
            ('ff5b18_b8e188bd228f4ea990fd6c1c7120140f_mv2', 'png'),
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
            ('ff5b18_aac54aec732d47c7b4d53e34ae6aa5ff_mv2', 'png'),
            ('ff5b18_3c0cef18e48849089c5ed48614041900_mv2', 'png'),
            ('ff5b18_5135a6cf3a664817ae02184154c06024_mv2', 'png'),
            ('ff5b18_7e41713f38d54a9d925d14c4bb72b01b_mv2', 'png'),
            ('ff5b18_105d9435292548ff9f61e8cae0711f9f_mv2', 'png'),
            ('ff5b18_e5a7d0e7216249bfbb6fbebba64021a8_mv2', 'png'),
            ('ff5b18_cbf6c17a98f949e19d6969e9e377f278_mv2', 'png'),
            ('ff5b18_02bdae21cf9549b38aecd09306a4842c_mv2', 'png'),
            ('ff5b18_1a145219498d4e75a79bbe13d3ab23ae_mv2', 'png'),
            ('ff5b18_f406990c34ad4a039524b10579cc5295_mv2', 'png'),
            ('ff5b18_56b178a8e1854af29fed0a75961a5a6f_mv2', 'png'),
            ('ff5b18_a466dbb965e94f008c62bfb48a04ab21_mv2', 'png'),
            ('ff5b18_f9b4f2ba1f81409a86985fabcbbea3be_mv2', 'png'),
            ('ff5b18_2b1800ac28b247f98060b77e9034f227_mv2', 'png'),
            ('ff5b18_bd546d2e47244fdcbda2e0bf2e07c43d_mv2', 'png'),
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
            ('ff5b18_b3b82b5920dd48509b6b78c1a91dcaec_mv2', 'png'),
            ('ff5b18_2aaf8ea933cc4fcc9e59d23197e3b35f_mv2', 'png'),
            ('ff5b18_d8789d39f2f54918b05ecc999eba639b_mv2', 'png'),
            ('ff5b18_920a949ef5b541cc85ea6be49efebb96_mv2', 'png'),
            ('ff5b18_cd5a5fdbf7ed4b23b03a9a3e7533e051_mv2', 'png'),
            ('ff5b18_ef18abb4037848e3b75100bef53ef666_mv2', 'png'),
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
            ('ff5b18_1012816bc1d7431cbdba88c8a138d06d_mv2', 'jpg'),
            ('ff5b18_62872dfca32e4164a0aae5c292352ece_mv2', 'jpg'),
            ('ff5b18_5d2794ad0a8c491484471454087410bb_mv2', 'jpg'),
            ('ff5b18_3e1808f4f0464106ae1905f8723d25d3_mv2', 'jpg'),
            ('ff5b18_d7eb886d364544c1993777e2db5e8bb6_mv2', 'jpg'),
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
            ('ff5b18_b64b65b40c1f44e4a4f6b21baac8ed72_mv2', 'png'),
            ('ff5b18_708d458832504cbd94bd7cdd7913c664_mv2', 'png'),
            ('ff5b18_f26349e8012041cbbae1f628716c19dc_mv2', 'png'),
            ('ff5b18_4d5fdc218b3548c0a2ad0b47802d0ca3_mv2', 'png'),
            ('ff5b18_09e7d253bf96411a9fe30835cc9ee34b_mv2', 'png'),
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
            ('ff5b18_dab676506e77455e942b02a857f21cc3_mv2', 'jpg'),
            ('ff5b18_f8bf8933487f45db825a713b4ea4c540_mv2', 'jpg'),
            ('ff5b18_5f016abc7ce04830a7f65e61c2b4a3fa_mv2', 'jpg'),
            ('ff5b18_fa6237e022fb42d5812a4e932b054bee_mv2', 'jpg'),
            ('ff5b18_e9017ba51d1544b789d5add8c4ecc484_mv2', 'jpg'),
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
            ('ff5b18_73ddf9ebf03a4477926cbf2283271380_mv2', 'png'),
            ('ff5b18_50c83d3193bf45818fc0ba11ae615bed_mv2', 'png'),
            ('ff5b18_cac57df9732942439511bdf23455bae9_mv2', 'png'),
            ('ff5b18_2bff65721a084bfb839c2c52bf19c666_mv2', 'png'),
            ('ff5b18_5a87c321b5db4ad99b66177a8685ee53_mv2', 'png'),
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
            ('ff5b18_8fec027febcb4fdb9a1f34db0e462fac_mv2', 'png'),
            ('ff5b18_6e14ea0a4cdd4f5c88885680df88f8af_mv2', 'png'),
            ('ff5b18_727f447718cc420c89065988a2d0f818_mv2', 'png'),
            ('ff5b18_fa07e12f600447eb9ef4801fa17bf8bc_mv2', 'png'),
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
            ('ff5b18_8534e71718a54408b57038ba0fc8c02f_mv2', 'jpg'),
            ('ff5b18_d7eb886d364544c1993777e2db5e8bb6_mv2', 'jpg'),
            ('ff5b18_60cc1d030a0345f9842e564e4f3dbeae_mv2', 'jpg'),
            ('ff5b18_4b1779cf3392422587cb7f1388175437_mv2', 'jpg'),
            ('ff5b18_92fd4a14ebbe454eadd6715a9ccf6053_mv2', 'jpg'),
            ('ff5b18_5790c7262fb04a25a5f08dc6b385e4c9_mv2', 'jpg'),
            ('ff5b18_da172978dd76485a9d179ca34d1c936b_mv2', 'jpg'),
            ('ff5b18_1eda3d15c3f849579ab21c436e0ceb0d_mv2', 'jpg'),
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
            ('ff5b18_29f3aa1ef62549ecbc7c5dd6b4aac717_mv2', 'jpg'),
            ('ff5b18_c1bace39ccc64636b710dc307c31bb77_mv2', 'jpg'),
            ('ff5b18_72165d4890b24a7f93d18df04d473da9_mv2', 'jpg'),
            ('ff5b18_88c5c1ca33004b5bb5be4c9d6cdfa968_mv2', 'jpg'),
            ('ff5b18_5ac00492e13c47a9b02bad9e8a10bdae_mv2', 'jpg'),
            ('ff5b18_f2d3db3381af451ebbb7ce65d407c99b_mv2', 'jpg'),
            ('ff5b18_5b8b0ffc05f041c1bac1baa89ee201e3_mv2', 'jpg'),
            ('ff5b18_068672b4c90e4610b467c3569fda0658_mv2', 'jpg'),
            ('ff5b18_9722b896c36d42cf8a61833d4caa389f_mv2', 'jpg'),
            ('ff5b18_b15ebdc0b69a4cdb902a74bf1a0e1c72_mv2', 'jpg'),
            ('ff5b18_55920f3db2594268a5fd35adf593a130_mv2', 'jpg'),
            ('ff5b18_a99b2d9dbfe04a39a3aee368c065c00c_mv2', 'jpg'),
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
            ('ff5b18_f81286bb193b4eceade91c476d030da2_mv2', 'png'),
            ('ff5b18_f2d002a1b71342199e013a4389c24d40_mv2', 'jpg'),
            ('ff5b18_54560c45e21d46688e1c6ed98ed51d37_mv2', 'png'),
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

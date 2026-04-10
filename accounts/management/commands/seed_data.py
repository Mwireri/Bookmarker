import io
import random
from datetime import date, timedelta
from urllib.error import URLError
from urllib.request import Request, urlopen

from django.contrib.contenttypes.models import ContentType
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.utils import timezone
from PIL import Image as PILImage, ImageDraw

from accounts.models import (
    Activity,
    FollowRelationship,
    NotificationPreference,
    User,
)
from images.models import Image

PASSWORD = "pass 1234 $"

# ── User profiles ──────────────────────────────────────────────────────
USERS = [
    {
        "username": "nature_lover",
        "email": "nature@example.com",
        "first_name": "Lena",
        "last_name": "Forester",
        "about": "Wildlife photographer capturing the beauty of mother nature. 🌿 Based in Costa Rica.",
        "country": "Costa Rica",
        "date_of_birth": date(1992, 5, 14),
        "phone_number": "+50688001234",
    },
    {
        "username": "city_explorer",
        "email": "cityexplorer@example.com",
        "first_name": "Marco",
        "last_name": "Ricci",
        "about": "Urban photographer. I find beauty in concrete jungles and neon lights.",
        "country": "Italy",
        "date_of_birth": date(1988, 11, 3),
        "phone_number": "+393201234567",
    },
    {
        "username": "tech_guru",
        "email": "techguru@example.com",
        "first_name": "Aisha",
        "last_name": "Patel",
        "about": "Software engineer by day, tech photographer by night. Gadgets, code, and coffee.",
        "country": "India",
        "date_of_birth": date(1995, 8, 21),
        "phone_number": "+919876543210",
    },
    {
        "username": "foodie_alice",
        "email": "foodie@example.com",
        "first_name": "Alice",
        "last_name": "Dubois",
        "about": "Parisian food lover. Every meal is a photo opportunity. 🍽️",
        "country": "France",
        "date_of_birth": date(1990, 2, 28),
        "phone_number": "+33612345678",
    },
    {
        "username": "travel_bug",
        "email": "travelbug@example.com",
        "first_name": "Kenji",
        "last_name": "Tanaka",
        "about": "30 countries and counting. Collecting moments, not things.",
        "country": "Japan",
        "date_of_birth": date(1987, 7, 10),
        "phone_number": "+818012345678",
    },
    {
        "username": "art_master",
        "email": "artmaster@example.com",
        "first_name": "Sofia",
        "last_name": "Müller",
        "about": "Mixed-media artist and visual storyteller from Berlin.",
        "country": "Germany",
        "date_of_birth": date(1993, 12, 5),
        "phone_number": "+491601234567",
    },
    {
        "username": "pet_parent",
        "email": "petparent@example.com",
        "first_name": "Emma",
        "last_name": "Wilson",
        "about": "Proud parent of 3 cats and 2 dogs. My feed is 100% fur babies.",
        "country": "United Kingdom",
        "date_of_birth": date(1996, 4, 18),
        "phone_number": "+447911123456",
    },
    {
        "username": "fitness_fan",
        "email": "fitfan@example.com",
        "first_name": "Carlos",
        "last_name": "Mendez",
        "about": "Personal trainer and outdoor enthusiast. Adventure is out there! 💪",
        "country": "Brazil",
        "date_of_birth": date(1991, 9, 22),
        "phone_number": "+5511987654321",
    },
    {
        "username": "minimal_matt",
        "email": "minimal@example.com",
        "first_name": "Matt",
        "last_name": "Larsson",
        "about": "Less is more. Scandinavian design and clean aesthetics.",
        "country": "Sweden",
        "date_of_birth": date(1994, 1, 30),
        "phone_number": "+46701234567",
    },
    {
        "username": "retro_rachel",
        "email": "retro@example.com",
        "first_name": "Rachel",
        "last_name": "Kim",
        "about": "Vintage vibes only. Film photography, old cameras, and nostalgia.",
        "country": "South Korea",
        "date_of_birth": date(1989, 6, 15),
        "phone_number": "+821012345678",
    },
]

# ── Images per user (title, pixabay_url, caption, description, tags, is_public) ─
IMAGES = {
    "nature_lover": [
        (
            "Coastal Forest Overlook",
            "https://pixabay.com/photos/fox-wildlife-wild-animal-5303221/",
            "Where the forest meets the ocean",
            "Stunning view from above the treeline looking out over turquoise waters to distant mountains. One of my favourite hikes.",
            ["forest", "ocean", "coast", "nature", "landscape"],
            True,
        ),
        (
            "Misty Mountain Stream",
            "https://pixabay.com/photos/tiger-animal-jungle-mammal-big-cat-1098607/",
            "Morning mist in the valley",
            "A winding stream cutting through green meadows with misty mountains rising on either side. So peaceful.",
            ["mountains", "stream", "mist", "valley", "nature"],
            True,
        ),
        (
            "Rocky Shoreline",
            "https://pixabay.com/photos/hedgehog-animal-hannah-nager-1584351/",
            "Pebbles and driftwood by the sea",
            "A pebbly beach with driftwood scattered along the shore, and the vast ocean stretching to the horizon.",
            ["beach", "shoreline", "driftwood", "ocean", "nature"],
            True,
        ),
        (
            "Rocky Coast at Dusk",
            "https://pixabay.com/photos/lynx-wildcat-nature-animal-8443540/",
            "Dark rocks meeting the grey sea",
            "Rugged rocks jutting out into a calm, overcast sea. The muted tones make it feel timeless.",
            ["rocks", "coast", "ocean", "moody", "nature"],
            True,
        ),
        (
            "Hidden Forest Waterfall",
            "https://pixabay.com/photos/squirrel-rodent-foraging-eating-3662681/",
            "Discovered this beauty on a trail hike",
            "A tall waterfall cascading into a pool surrounded by lush green forest and mossy boulders.",
            ["waterfall", "forest", "nature", "hiking"],
            False,
        ),
        (
            "Misty Island Shore",
            "https://pixabay.com/photos/frog-water-frog-lily-pads-amphibian-2211972/",
            "Fog rolling over the island",
            "Rocky shore with driftwood, turquoise water, and a fog-wrapped island in the distance.",
            ["island", "shore", "mist", "nature", "ocean"],
            True,
        ),
        (
            "Garden Path in Spring",
            "https://pixabay.com/photos/snail-shell-invertebrate-sensor-6290772/",
            "Follow the trail through the orchard",
            "A gravel path leading through a green meadow with blooming cherry trees and tall evergreens.",
            ["path", "garden", "spring", "nature", "trees"],
            True,
        ),
    ],
    "city_explorer": [
        (
            "Times Square at Night",
            "https://pixabay.com/photos/prague-praha-winter-night-3010407/",
            "The neon heartbeat of New York",
            "Times Square buzzing with neon signs, giant billboards, and crowds under the night sky. Pure urban energy.",
            ["times-square", "night", "neon", "nyc", "urban"],
            True,
        ),
        (
            "Seagull by the Sea",
            "https://pixabay.com/photos/sunset-skyscrapers-buildings-city-8214498/",
            "Standing guard on the railing",
            "A white seagull perched on a railing overlooking the calm grey ocean. Simple and serene.",
            ["seagull", "bird", "ocean", "minimal", "coastal"],
            True,
        ),
        (
            "Country Path at Dusk",
            "https://pixabay.com/photos/river-bridges-buildings-structures-6175173/",
            "Golden fields under a dramatic sky",
            "A grassy country track stretching to the horizon beneath heavy sunset clouds. The golden light was incredible.",
            ["countryside", "path", "sunset", "landscape", "dramatic-sky"],
            True,
        ),
        (
            "Mountain Road Tunnel",
            "https://pixabay.com/photos/city-night-birds-eye-view-5644601/",
            "Into the mountain",
            "A winding road carved into the mountainside leading into a tunnel through solid rock. What an engineering feat.",
            ["road", "tunnel", "mountain", "travel", "adventure"],
            True,
        ),
        (
            "Venice Beach Skatepark",
            "https://pixabay.com/photos/tokyo-japan-buildings-city-8650941/",
            "Catching air at Venice",
            "A skateboarder mid-trick at Venice Beach skatepark with palm trees and pastel buildings in the background.",
            ["skateboarding", "venice-beach", "urban", "sports", "california"],
            False,
        ),
        (
            "Dubai Skyline",
            "https://pixabay.com/photos/dubai-emirates-burj-khalifa-skyline-4044183/",
            "Futuristic Dubai",
            "The Burj Khalifa piercing through the clouds. Dubai is a city from the future.",
            ["dubai", "burj-khalifa", "skyline", "luxury", "architecture"],
            True,
        ),
        (
            "Classical Dome Architecture",
            "https://pixabay.com/photos/city-buildings-night-city-lights-5772121/",
            "Grand domes against the sky",
            "Majestic classical architecture with twin domes and ornate stonework. Timeless elegance in the city.",
            ["architecture", "dome", "classical", "historic", "photography"],
            True,
        ),
    ],
    "tech_guru": [
        (
            "MacBook and Coffee",
            "https://pixabay.com/photos/hands-laptop-working-businessman-2178566/",
            "My daily setup",
            "MacBook Air on a rustic wooden table beside an espresso cup and phone. Clean and focused.",
            ["laptop", "workspace", "coffee", "productivity", "tech"],
            True,
        ),
        (
            "Typing at the Café",
            "https://pixabay.com/photos/startup-start-up-people-593341/",
            "Getting things done over coffee",
            "Hands on the keyboard, coffee on the side, phone in reach. The café workflow in full swing.",
            ["typing", "cafe", "laptop", "remote-work", "coding"],
            True,
        ),
        (
            "Laptop Notebook and Espresso",
            "https://pixabay.com/photos/code-coding-computer-data-1839406/",
            "Analog meets digital",
            "An open notebook with a pen beside a laptop and a small espresso. Best of both worlds for brainstorming.",
            ["notebook", "laptop", "espresso", "workspace", "tech"],
            True,
        ),
        (
            "Phone and Laptop",
            "https://pixabay.com/photos/earth-internet-globalization-2254769/",
            "Always connected",
            "Checking the phone while working on the laptop. The multi-screen life of a developer.",
            ["phone", "laptop", "multitask", "technology", "mobile"],
            True,
        ),
        (
            "Writing Notes by Laptop",
            "https://pixabay.com/photos/bitcoin-cryptocurrency-digital-2007769/",
            "Pen and paper still matter",
            "Close-up of hands writing in a notebook next to a laptop. Some ideas need to be sketched first.",
            ["notes", "writing", "laptop", "planning", "analog"],
            False,
        ),
        (
            "Coding at the Desk",
            "https://pixabay.com/photos/rocket-launch-rocket-take-off-67643/",
            "Deep work mode",
            "Overhead view of focused typing on a MacBook. Phone and notebook close by, coffee fuelled.",
            ["coding", "macbook", "developer", "focus", "tech"],
            True,
        ),
    ],
    "foodie_alice": [
        (
            "Herbal Tea Brewing",
            "https://pixabay.com/photos/laptop-coffee-arm-desktop-notebook-1205256/",
            "Morning ritual with green tea",
            "Glass teapot of herbal tea steeping on the counter with yellow roses in the background. A calm start to the day.",
            ["tea", "herbal", "morning", "cozy", "kitchen"],
            True,
        ),
        (
            "Fresh Ingredients on Board",
            "https://pixabay.com/photos/coffee-caffeine-beverage-table-2425303/",
            "Prep time is the best time",
            "Red onion, fresh herbs, and scattered peppercorns on a wooden cutting board. Ready to cook!",
            ["ingredients", "cooking", "herbs", "food-prep", "food"],
            True,
        ),
        (
            "Honey Jar Close-Up",
            "https://pixabay.com/photos/desktop-laptop-crafts-still-life-1985856/",
            "Liquid gold",
            "A wooden honey dipper resting in a ceramic honey pot. Such a beautiful deep amber colour.",
            ["honey", "food", "close-up", "natural", "kitchen"],
            True,
        ),
        (
            "Lemon Ginger Tea",
            "https://pixabay.com/photos/office-notes-notepad-entrepreneur-620817/",
            "My go-to wellness drink",
            "Top-down view of a hand holding a cup of lemon and ginger tea. The ultimate comfort drink.",
            ["lemon", "ginger", "tea", "wellness", "lifestyle"],
            False,
        ),
        (
            "Morning Tea in Bed",
            "https://pixabay.com/photos/camera-digital-photography-1362419/",
            "Steaming cup and a good book",
            "A delicate teacup steaming on white bedsheets next to an open book and a pink flower. Pure bliss.",
            ["tea", "morning", "cozy", "reading", "lifestyle"],
            True,
        ),
        (
            "Busy Café Counter",
            "https://pixabay.com/photos/home-office-workspace-desk-design-820389/",
            "The heart of a neighbourhood café",
            "Customers crowding a rustic café counter under chalkboard menus and vintage pendant lights.",
            ["cafe", "coffee-shop", "people", "community", "food"],
            True,
        ),
    ],
    "travel_bug": [
        (
            "Hazy Beach Day",
            "https://pixabay.com/photos/lisbon-tram-portugal-8275988/",
            "Summer vibes at the shore",
            "A crowded beach as waves roll in under a hazy sky. People swimming and sunbathing in the golden light.",
            ["beach", "summer", "ocean", "travel", "people"],
            True,
        ),
        (
            "Brutalist Architecture",
            "https://pixabay.com/photos/szechenyi-chain-bridge-1758196/",
            "Concrete poetry",
            "A raw concrete building with dramatic geometric shapes silhouetted against a teal sky. Bold and unapologetic.",
            ["brutalist", "architecture", "concrete", "urban", "travel"],
            True,
        ),
        (
            "Raspberries in Sunlight",
            "https://pixabay.com/photos/eiffel-tower-france-paris-9235220/",
            "Summer berries glowing",
            "Fresh raspberries on a wooden railing backlit by warm golden sunlight. A tiny perfect moment.",
            ["raspberries", "fruit", "sunlight", "summer", "nature"],
            True,
        ),
        (
            "Lazy Park Afternoon",
            "https://pixabay.com/photos/architecture-avenue-buildings-city-1846023/",
            "Kicked back in the grass",
            "POV of comfy sneakers stretched out on a golden park lawn under a blue sky. This is the life.",
            ["park", "relaxing", "sneakers", "grass", "leisure"],
            True,
        ),
        (
            "Dreamcatcher at Sunset",
            "https://pixabay.com/photos/subway-metro-tunnel-lights-urban-7381618/",
            "Catching golden light",
            "A dreamcatcher with feathers and beads silhouetted against the warm sunset sky. Beautiful craft.",
            ["dreamcatcher", "sunset", "craft", "bohemian", "travel"],
            False,
        ),
        (
            "Frangipani Blossoms",
            "https://pixabay.com/photos/helicopter-flight-mountains-3011983/",
            "Tropical flowers reaching for the sky",
            "Clusters of pink frangipani flowers on branches reaching up against a bright blue sky. Island paradise.",
            ["frangipani", "flowers", "tropical", "nature", "travel"],
            True,
        ),
        (
            "Wheat Field Close-Up",
            "https://pixabay.com/photos/prague-czech-republic-bohemia-7172594/",
            "Grain as far as the eye can see",
            "Close-up of green wheat ears standing tall in a vast field. The countryside is endlessly photogenic.",
            ["wheat", "field", "countryside", "nature", "agriculture"],
            True,
        ),
    ],
    "art_master": [
        (
            "Guitar Headstock Detail",
            "https://pixabay.com/photos/typewriter-vintage-old-1248088/",
            "All in the tuning pegs",
            "Close-up of a guitar headstock and tuning pegs in moody vintage tones. Music is art.",
            ["guitar", "music", "vintage", "detail", "art"],
            True,
        ),
        (
            "Red Tricycle on the Street",
            "https://pixabay.com/photos/startup-whiteboard-room-indoors-3267505/",
            "Street scene nostalgia",
            "A vintage red children's tricycle parked on a sidewalk. Childhood frozen in time.",
            ["tricycle", "street", "vintage", "nostalgia", "urban"],
            True,
        ),
        (
            "Moody Ocean Horizon",
            "https://pixabay.com/photos/macro-cogwheel-gear-engine-vintage-1452987/",
            "Where sky meets water",
            "Dark rippling ocean stretching to a brooding horizon under heavy clouds. A study in blue and grey.",
            ["ocean", "moody", "seascape", "dramatic", "art"],
            True,
        ),
        (
            "Lightning over the Coast",
            "https://pixabay.com/photos/cyberpunk-street-city-platform-6061251/",
            "Nature's light show",
            "A bolt of lightning strikes the coast at night with city lights glimmering along the shore. Electric.",
            ["lightning", "night", "coast", "storm", "photography"],
            True,
        ),
        (
            "Skateboard and Blanket Still Life",
            "https://pixabay.com/photos/innovation-business-businessman-561388/",
            "Objects telling a story",
            "A skateboard leaning against a white wall beside a stool draped with a patterned blanket. Composed chaos.",
            ["skateboard", "still-life", "art", "objects", "creative"],
            False,
        ),
        (
            "Concert Light Show",
            "https://pixabay.com/photos/camera-lens-shutter-equipment-5940588/",
            "Lost in the music and lights",
            "Stage lights and lasers cutting through haze above a cheering concert crowd. Pure energy captured.",
            ["concert", "lights", "music", "crowd", "art"],
            True,
        ),
    ],
    "pet_parent": [
        (
            "Black Lab Puppy",
            "https://pixabay.com/photos/cat-animal-cat-portrait-cats-eyes-1045782/",
            "Best boy on the porch",
            "A sweet black Labrador puppy sitting on a wooden deck and looking up with curious eyes.",
            ["puppy", "labrador", "dog", "cute", "pets"],
            True,
        ),
        (
            "Cat Nose Macro",
            "https://pixabay.com/photos/cat-tabby-face-whiskers-pet-1508613/",
            "Extreme close-up",
            "Macro shot of a cat's pink nose and whiskers. You can count every single whisker.",
            ["cat", "macro", "nose", "whiskers", "pets"],
            True,
        ),
        (
            "Dachshunds in the Garden",
            "https://pixabay.com/photos/monkey-animal-ape-primate-mammal-3508374/",
            "Double the wiener",
            "Two adorable dachshunds sniffing around in the grass. Tiny legs, big personalities.",
            ["dachshund", "dogs", "garden", "cute", "pets"],
            True,
        ),
        (
            "Highland Cow by the Sea",
            "https://pixabay.com/photos/pug-dog-pet-canine-animal-fur-4314106/",
            "Majestic and fluffy",
            "A Highland cow with shaggy hair standing on rocky coastal terrain. Wild and unmistakable.",
            ["highland-cow", "coast", "scotland", "animals", "nature"],
            True,
        ),
        (
            "Laptop and Glasses on Desk",
            "https://pixabay.com/photos/dog-animal-puppy-cute-young-male-5357794/",
            "Clean workspace vibes",
            "A closed laptop with round glasses and a mouse on a warm wooden desk. Minimal and serene.",
            ["laptop", "desk", "workspace", "minimal", "glasses"],
            True,
        ),
        (
            "Sunset Tree-Lined Road",
            "https://pixabay.com/photos/bunny-cute-grass-animal-outdoors-1845263/",
            "Golden light through the trees",
            "A beautiful road flanked by tall trees with golden sunlight streaming through. An evening drive.",
            ["road", "trees", "sunset", "golden-hour", "landscape"],
            False,
        ),
        (
            "Leopard on Safari Road",
            "https://pixabay.com/photos/cat-domestic-animal-animal-gray-3261420/",
            "Wild encounter",
            "A leopard casually walking down a dusty red safari road. Grace and power in every step.",
            ["leopard", "safari", "wildlife", "africa", "nature"],
            True,
        ),
        (
            "Pelicans on the Pier",
            "https://pixabay.com/photos/cat-cat-eyes-whiskers-cat-face-6664360/",
            "Old pier residents",
            "Pelicans perched on wooden pier posts against a turquoise ocean backdrop. Pacific coast charm.",
            ["pelicans", "pier", "ocean", "birds", "coast"],
            True,
        ),
    ],
    "fitness_fan": [
        (
            "Snow-Capped Mountain Valley",
            "https://pixabay.com/photos/domestic-animal-dog-vizsla-5173354/",
            "Alpine majesty",
            "A breathtaking snowy mountain valley stretching out under dramatic clouds. The scale is humbling.",
            ["mountains", "snow", "valley", "landscape", "nature"],
            True,
        ),
        (
            "Cuban Souvenir Mug",
            "https://pixabay.com/photos/sheep-animal-mammal-horns-3742999/",
            "Coffee and memories",
            "A charming coffee mug with a vintage Cuba stamp design. A little souvenir with a lot of character.",
            ["mug", "cuba", "souvenir", "coffee", "vintage"],
            True,
        ),
        (
            "Camera Teardown Flat Lay",
            "https://pixabay.com/photos/animal-goat-mammal-livestock-farm-6756751/",
            "Every single piece",
            "A Canon camera disassembled and laid out flat — every lens, screw, and circuit board on display.",
            ["camera", "teardown", "flat-lay", "canon", "photography"],
            True,
        ),
        (
            "Coastal Cliff View",
            "https://pixabay.com/photos/animal-mammal-antelope-wildlife-6902437/",
            "Edge of the world",
            "Ocean waves far below a cliff edge dotted with wildflowers. Breathtaking drop.",
            ["cliff", "coast", "ocean", "flowers", "landscape"],
            True,
        ),
        (
            "Jet Trail Above the Clouds",
            "https://pixabay.com/photos/alpaca-head-black-animals-cute-5405469/",
            "Always looking up",
            "A stark white contrail stretching across a deep blue sky. Minimalism in the skies.",
            ["contrail", "sky", "blue", "aviation", "minimal"],
            False,
        ),
        (
            "Vinyl Record Player",
            "https://pixabay.com/photos/lamb-farm-sheep-livestock-2216160/",
            "Needle on the groove",
            "Close-up of a turntable needle resting on spinning vinyl. Warm analog sound captured visually.",
            ["vinyl", "turntable", "music", "analog", "retro"],
            True,
        ),
    ],
    "minimal_matt": [
        (
            "Organized Desk Flat Lay",
            "https://pixabay.com/photos/workplace-macbook-computer-digital-4155023/",
            "Everything in its place",
            "Top-down view of a perfectly organized iMac desk with keyboard, mouse, tablet, and glasses.",
            ["desk", "flat-lay", "organized", "minimal", "workspace"],
            True,
        ),
        (
            "Old Town Aerial in Monochrome",
            "https://pixabay.com/photos/desktop-computer-work-space-5636733/",
            "City from above",
            "Black-and-white aerial photograph of a European old town with church spires and tightly packed rooftops.",
            ["aerial", "monochrome", "old-town", "architecture", "minimal"],
            True,
        ),
        (
            "Tuscan Sunrise",
            "https://pixabay.com/photos/office-business-accountant-620822/",
            "Golden hills at dawn",
            "Rolling Tuscan hills at sunrise with warm golden light and distant trees. Peaceful simplicity.",
            ["tuscany", "sunrise", "landscape", "hills", "nature"],
            True,
        ),
        (
            "Coffee on Red",
            "https://pixabay.com/photos/laptop-digital-device-technology-5673901/",
            "Top-down minimalism",
            "A white coffee cup seen from directly above against a bold red surface. Simple and graphic.",
            ["coffee", "minimal", "top-down", "red", "graphic"],
            False,
        ),
        (
            "Golden Hour Silhouette",
            "https://pixabay.com/photos/keyboard-computer-technology-light-5017973/",
            "Warmth and shadow",
            "Silhouette of a girl standing in a vast golden wheat field at sunset. Pure magic light.",
            ["silhouette", "sunset", "golden-hour", "field", "portrait"],
            True,
        ),
        (
            "Hillside in Monochrome",
            "https://pixabay.com/photos/skyscraper-architecture-city-facade-9226515/",
            "Dramatic light and dark",
            "Black-and-white photograph of a forested hillside with dramatic shadows and cloud formations.",
            ["monochrome", "hillside", "landscape", "dramatic", "nature"],
            True,
        ),
    ],
    "retro_rachel": [
        (
            "Vintage Camera on Piano Keys",
            "https://pixabay.com/photos/camera-shutter-speed-digital-camera-7271284/",
            "Two classics in one frame",
            "A Zeiss Ikon film camera resting on ivory piano keys. Music and photography united in vintage charm.",
            ["camera", "piano", "vintage", "retro", "photography"],
            True,
        ),
        (
            "Rolling Hills at Golden Hour",
            "https://pixabay.com/photos/stock-trading-monitor-business-1863880/",
            "Panoramic beauty",
            "Sweeping panoramic view of rolling hills and valleys under a dramatic golden sky.",
            ["panorama", "hills", "golden-hour", "landscape", "nature"],
            True,
        ),
        (
            "Typewriter Teardown Flat Lay",
            "https://pixabay.com/photos/mobile-phone-smartphone-keyboard-1917737/",
            "Every key and lever",
            "A vintage Adler typewriter disassembled and laid out flat, revealing the beautiful mechanics inside.",
            ["typewriter", "teardown", "flat-lay", "vintage", "retro"],
            True,
        ),
        (
            "Forest Floor Still Life",
            "https://pixabay.com/photos/mobile-phone-smartphone-hand-1419275/",
            "Nature's composition",
            "A smooth stone resting among autumn leaves and grass on the forest floor. Quiet beauty.",
            ["stone", "autumn", "leaves", "nature", "still-life"],
            True,
        ),
        (
            "Tree Tunnel Road",
            "https://pixabay.com/photos/lion-predator-dangerous-mane-3574819/",
            "Into the vanishing point",
            "A black-and-white photograph of a road disappearing into a tunnel of arching trees.",
            ["road", "trees", "tunnel", "monochrome", "perspective"],
            False,
        ),
        (
            "Path to the Winter Trees",
            "https://pixabay.com/photos/sheep-can-fun-animal-1649212/",
            "Quiet walk ahead",
            "A gravel path leading through a green lawn toward bare winter trees. Still and contemplative.",
            ["path", "trees", "winter", "landscape", "peaceful"],
            True,
        ),
        (
            "Snow-Capped Peaks",
            "https://pixabay.com/photos/drone-tech-camera-recording-8499903/",
            "Mountains in the clouds",
            "Towering snow-capped mountain peaks partially wrapped in clouds. Alpine grandeur.",
            ["mountains", "snow", "peaks", "clouds", "landscape"],
            True,
        ),
    ],
}

# ── Follow graph (diverse: chains, mutual, one-directional, clusters) ─
FOLLOW_PAIRS = [
    # Mutual follows (close friends)
    ("nature_lover", "pet_parent"),
    ("pet_parent", "nature_lover"),
    ("city_explorer", "travel_bug"),
    ("travel_bug", "city_explorer"),
    ("tech_guru", "minimal_matt"),
    ("minimal_matt", "tech_guru"),
    ("art_master", "retro_rachel"),
    ("retro_rachel", "art_master"),
    # One-directional follows (fan → creator)
    ("foodie_alice", "nature_lover"),
    ("fitness_fan", "nature_lover"),
    ("travel_bug", "nature_lover"),
    ("pet_parent", "foodie_alice"),
    ("city_explorer", "art_master"),
    ("tech_guru", "city_explorer"),
    ("retro_rachel", "tech_guru"),
    ("fitness_fan", "travel_bug"),
    ("minimal_matt", "art_master"),
    ("foodie_alice", "retro_rachel"),
    # Popular user cluster (nature_lover has many followers)
    ("art_master", "nature_lover"),
    ("minimal_matt", "nature_lover"),
    ("retro_rachel", "nature_lover"),
    # Chain follow
    ("nature_lover", "city_explorer"),
    ("city_explorer", "tech_guru"),
    ("tech_guru", "foodie_alice"),
    ("foodie_alice", "travel_bug"),
    ("travel_bug", "art_master"),
    ("art_master", "pet_parent"),
    ("pet_parent", "fitness_fan"),
    ("fitness_fan", "minimal_matt"),
    ("minimal_matt", "retro_rachel"),
    ("retro_rachel", "nature_lover"),
]

# ── Notification preference profiles ────────────────────────────────
NOTIFICATION_PREFS = {
    "nature_lover": {
        "email_new_follower": True,
        "email_likes": True,
        "email_comments": True,
        "email_weekly_digest": True,
        "push_enabled": True,
        "notification_frequency": "immediate",
    },
    "city_explorer": {
        "email_new_follower": True,
        "email_likes": False,
        "email_comments": True,
        "email_weekly_digest": True,
        "push_enabled": True,
        "notification_frequency": "daily",
    },
    "tech_guru": {
        "email_new_follower": False,
        "email_likes": False,
        "email_comments": False,
        "email_weekly_digest": False,
        "push_enabled": False,
        "notification_frequency": "never",
    },
    "foodie_alice": {
        "email_new_follower": True,
        "email_likes": True,
        "email_comments": True,
        "email_weekly_digest": False,
        "push_enabled": True,
        "notification_frequency": "immediate",
    },
    "travel_bug": {
        "email_new_follower": True,
        "email_likes": True,
        "email_comments": True,
        "email_weekly_digest": True,
        "push_enabled": True,
        "notification_frequency": "weekly",
    },
    "art_master": {
        "email_new_follower": True,
        "email_likes": True,
        "email_comments": False,
        "email_weekly_digest": True,
        "push_enabled": True,
        "notification_frequency": "daily",
    },
    "pet_parent": {
        "email_new_follower": True,
        "email_likes": True,
        "email_comments": True,
        "email_weekly_digest": True,
        "push_enabled": True,
        "notification_frequency": "immediate",
    },
    "fitness_fan": {
        "email_new_follower": False,
        "email_likes": True,
        "email_comments": True,
        "email_weekly_digest": False,
        "push_enabled": True,
        "notification_frequency": "daily",
    },
    "minimal_matt": {
        "email_new_follower": False,
        "email_likes": False,
        "email_comments": True,
        "email_weekly_digest": False,
        "push_enabled": False,
        "notification_frequency": "weekly",
    },
    "retro_rachel": {
        "email_new_follower": True,
        "email_likes": True,
        "email_comments": True,
        "email_weekly_digest": True,
        "push_enabled": True,
        "notification_frequency": "immediate",
    },
}

# ── Picsum photo IDs mapped per user for themed, reproducible downloads ──
# Each user gets unique picsum IDs that loosely match their theme
PICSUM_IDS = {
    "nature_lover": [10, 11, 13, 14, 15, 16, 17],
    "city_explorer": [274, 275, 277, 278, 281, 286, 290],
    "tech_guru": [0, 1, 2, 3, 4, 5],
    "foodie_alice": [225, 292, 312, 326, 365, 395],
    "travel_bug": [100, 101, 102, 103, 104, 106, 107],
    "art_master": [145, 146, 147, 149, 157, 158],
    "pet_parent": [237, 40, 169, 200, 201, 202, 219, 244],
    "fitness_fan": [29, 30, 36, 37, 38, 39],
    "minimal_matt": [60, 61, 62, 63, 65, 67],
    "retro_rachel": [250, 251, 252, 253, 254, 255, 256],
}


def _download_image(picsum_id, stdout=None):
    """Download a real photo from picsum.photos. Returns image bytes or None."""
    url = f"https://picsum.photos/id/{picsum_id}/800/600.jpg"
    for attempt in range(3):
        try:
            request = Request(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                },
            )
            response = urlopen(request, timeout=30)
            return response.read()
        except (URLError, OSError, TimeoutError) as e:
            if stdout:
                stdout.write(
                    f"    Attempt {attempt + 1}/3 failed for picsum id {picsum_id}: {e}\n"
                )
            import time

            time.sleep(2 * (attempt + 1))
    return None


def _generate_placeholder(title):
    """Fallback: generate a colored placeholder if download fails."""
    img = PILImage.new("RGB", (800, 600), (100, 100, 100))
    draw = ImageDraw.Draw(img)
    text = title[:40]
    bbox = draw.textbbox((0, 0), text)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    x = (800 - tw) // 2
    y = (600 - th) // 2
    draw.rectangle([x - 10, y - 10, x + tw + 10, y + th + 10], fill=(0, 0, 0))
    draw.text((x, y), text, fill=(255, 255, 255))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return buf.getvalue()


class Command(BaseCommand):
    help = "Seed database with 10 diverse users, images, follows, likes, activities, and notification preferences"

    def add_arguments(self, parser):
        parser.add_argument(
            "--flush",
            action="store_true",
            help="Delete all seed users and their data before seeding",
        )

    def handle(self, *args, **options):
        if options["flush"]:
            self._flush()

        users = self._create_users()
        images = self._create_images(users)
        self._create_follows(users)
        self._create_likes(users, images)
        self._create_activities(users, images)
        self._create_notification_preferences(users)
        self._print_summary(users, images)

    # ── Users ──────────────────────────────────────────────────────
    def _create_users(self):
        users = {}
        for profile in USERS:
            username = profile["username"]
            if User.objects.filter(username=username).exists():
                users[username] = User.objects.get(username=username)
                self.stdout.write(f"  User '{username}' already exists, skipping")
                continue

            user = User.objects.create_user(
                username=username,
                email=profile["email"],
                password=PASSWORD,
                first_name=profile["first_name"],
                last_name=profile["last_name"],
            )
            user.about = profile["about"]
            user.country = profile["country"]
            user.date_of_birth = profile["date_of_birth"]
            user.phone_number = profile.get("phone_number", "")

            # Download a profile picture
            avatar_picsum_id = PICSUM_IDS.get(username, [200])[0]
            pp_data = _download_image(avatar_picsum_id, self.stdout)
            if not pp_data:
                pp_data = _generate_placeholder(profile["first_name"])
            user.profile_picture.save(
                f"{username}_avatar.jpg", ContentFile(pp_data), save=False
            )
            user.save()
            users[username] = user
            self.stdout.write(self.style.SUCCESS(f"  Created user: {username}"))

        return users

    # ── Images ─────────────────────────────────────────────────────
    def _create_images(self, users):
        all_images = []
        base_time = timezone.now() - timedelta(days=25)

        for username, image_list in IMAGES.items():
            user = users.get(username)
            if not user:
                continue

            for idx, (title, url, caption, description, tags, is_public) in enumerate(
                image_list
            ):
                if Image.objects.filter(user=user, url=url).exists():
                    img = Image.objects.get(user=user, url=url)
                    all_images.append(img)
                    self.stdout.write(f"  Image '{title}' already exists, skipping")
                    continue

                picsum_ids = PICSUM_IDS.get(username, [200])
                picsum_id = picsum_ids[idx % len(picsum_ids)]
                img_data = _download_image(picsum_id, self.stdout)
                if not img_data:
                    img_data = _generate_placeholder(title)
                img = Image(
                    user=user,
                    title=title,
                    url=url,
                    caption=caption,
                    description=description,
                    is_public=is_public,
                    views=random.randint(5, 2000),
                )
                img.image.save(
                    f"{username}_{idx}.jpg", ContentFile(img_data), save=False
                )
                # Stagger creation dates so images appear at different times
                img.save()
                # Backdate created timestamp via update to bypass auto_now_add
                created_time = base_time + timedelta(
                    days=idx * 3 + random.randint(0, 5),
                    hours=random.randint(0, 23),
                    minutes=random.randint(0, 59),
                )
                Image.objects.filter(pk=img.pk).update(created=created_time)

                # Add tags
                img.tags.add(*tags)

                all_images.append(img)
                self.stdout.write(
                    self.style.SUCCESS(
                        f"  Created image: '{title}' by {username} "
                        f"({'public' if is_public else 'private'}) "
                        f"[tags: {', '.join(tags)}]"
                    )
                )

        return all_images

    # ── Follows ────────────────────────────────────────────────────
    def _create_follows(self, users):
        created_count = 0
        for follower_name, following_name in FOLLOW_PAIRS:
            follower = users.get(follower_name)
            following = users.get(following_name)
            if not follower or not following:
                continue
            _, created = FollowRelationship.objects.get_or_create(
                follower=follower, following=following
            )
            if created:
                created_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"  Created {created_count} follow relationships "
                f"({len(FOLLOW_PAIRS)} total defined)"
            )
        )

    # ── Likes ──────────────────────────────────────────────────────
    def _create_likes(self, users, images):
        random.seed(42)  # Reproducible randomness
        user_list = list(users.values())
        like_count = 0

        for img in images:
            # Each image gets liked by 1–7 random users (not the owner)
            potential_likers = [u for u in user_list if u != img.user]
            num_likes = random.randint(1, min(7, len(potential_likers)))
            likers = random.sample(potential_likers, num_likes)

            for liker in likers:
                if not img.users_like.filter(pk=liker.pk).exists():
                    img.users_like.add(liker)
                    like_count += 1

            # Update total_likes denormalized field
            img.total_likes = img.users_like.count()
            img.save(update_fields=["total_likes"])

        self.stdout.write(
            self.style.SUCCESS(
                f"  Created {like_count} likes across {len(images)} images"
            )
        )

    # ── Activities ─────────────────────────────────────────────────
    def _create_activities(self, users, images):
        activity_count = 0
        base_time = timezone.now() - timedelta(days=30)
        image_ct = ContentType.objects.get_for_model(Image)
        user_ct = ContentType.objects.get_for_model(User)

        # Follow activities
        for follower_name, following_name in FOLLOW_PAIRS:
            follower = users.get(follower_name)
            following = users.get(following_name)
            if not follower or not following or follower == following:
                continue

            if not Activity.objects.filter(
                user=following,
                actor=follower,
                verb="follow",
                target_content_type=user_ct,
                target_object_id=following.pk,
            ).exists():
                a = Activity.objects.create(
                    user=following,
                    actor=follower,
                    verb="follow",
                    target_content_type=user_ct,
                    target_object_id=following.pk,
                )
                # Backdate
                ts = base_time + timedelta(
                    days=random.randint(0, 25), hours=random.randint(0, 23)
                )
                Activity.objects.filter(pk=a.pk).update(created_at=ts)
                activity_count += 1

        # Like activities (sample — not every like gets a notification)
        random.seed(99)
        for img in images:
            likers = list(img.users_like.all())
            # Generate like notifications for up to 3 likers per image
            for liker in likers[:3]:
                if liker == img.user:
                    continue
                if not Activity.objects.filter(
                    user=img.user,
                    actor=liker,
                    verb="like",
                    target_content_type=image_ct,
                    target_object_id=img.pk,
                ).exists():
                    a = Activity.objects.create(
                        user=img.user,
                        actor=liker,
                        verb="like",
                        target_content_type=image_ct,
                        target_object_id=img.pk,
                    )
                    ts = base_time + timedelta(
                        days=random.randint(0, 28), hours=random.randint(0, 23)
                    )
                    Activity.objects.filter(pk=a.pk).update(created_at=ts)
                    activity_count += 1

        # Mark some activities as read (about 40%)
        all_activities = Activity.objects.filter(
            user__username__in=[u["username"] for u in USERS]
        )
        read_ids = random.sample(
            list(all_activities.values_list("id", flat=True)),
            k=int(all_activities.count() * 0.4),
        )
        Activity.objects.filter(id__in=read_ids).update(is_read=True)

        self.stdout.write(
            self.style.SUCCESS(
                f"  Created {activity_count} activity notifications "
                f"({int(len(read_ids))} marked as read)"
            )
        )

    # ── Notification preferences ──────────────────────────────────
    def _create_notification_preferences(self, users):
        created_count = 0
        for username, prefs in NOTIFICATION_PREFS.items():
            user = users.get(username)
            if not user:
                continue
            _, created = NotificationPreference.objects.get_or_create(
                user=user, defaults=prefs
            )
            if created:
                created_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"  Created {created_count} notification preference profiles"
            )
        )

    # ── Flush seed data ───────────────────────────────────────────
    def _flush(self):
        seed_usernames = [u["username"] for u in USERS]
        seed_users = User.objects.filter(username__in=seed_usernames)

        img_count = Image.objects.filter(user__in=seed_users).count()
        Image.objects.filter(user__in=seed_users).delete()

        activity_count = Activity.objects.filter(user__in=seed_users).count()
        Activity.objects.filter(user__in=seed_users).delete()
        Activity.objects.filter(actor__in=seed_users).delete()

        NotificationPreference.objects.filter(user__in=seed_users).delete()
        FollowRelationship.objects.filter(follower__in=seed_users).delete()
        FollowRelationship.objects.filter(following__in=seed_users).delete()

        user_count = seed_users.count()
        seed_users.delete()

        self.stdout.write(
            self.style.WARNING(
                f"  Flushed: {user_count} users, {img_count} images, "
                f"{activity_count} activities"
            )
        )

    # ── Summary ───────────────────────────────────────────────────
    def _print_summary(self, users, images):
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.SUCCESS("SEED DATA SUMMARY"))
        self.stdout.write("=" * 60)
        self.stdout.write(f"  Users created:       {len(users)}")
        self.stdout.write(f"  Images created:      {len(images)}")
        self.stdout.write(
            f"  Public images:       {sum(1 for i in images if i.is_public)}"
        )
        self.stdout.write(
            f"  Private images:      {sum(1 for i in images if not i.is_public)}"
        )
        self.stdout.write(
            f"  Follow relationships: {FollowRelationship.objects.filter(follower__in=users.values()).count()}"
        )
        self.stdout.write(
            f"  Total likes:         {sum(i.total_likes for i in images)}"
        )
        self.stdout.write(
            f"  Activities:          {Activity.objects.filter(user__in=users.values()).count()}"
        )
        self.stdout.write(
            f"  Notification prefs:  {NotificationPreference.objects.filter(user__in=users.values()).count()}"
        )
        self.stdout.write("=" * 60)
        self.stdout.write(f'  All users password:  "{PASSWORD}"')
        self.stdout.write("  Usernames:")
        for username in users:
            u = users[username]
            self.stdout.write(
                f"    - {username} ({u.first_name} {u.last_name}, {u.country})"
            )
        self.stdout.write("=" * 60 + "\n")

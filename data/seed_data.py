"""
ORACLE-X/N — Seed Data
========================
Realistic Nigerian user profiles and product catalogue for demo + evaluation.
Each user is a fully realised behavioural persona, not just a preference vector.
"""

from __future__ import annotations

from typing import List, Dict, Any


# ══════════════════════════════════════════════════════════════════════════════
# SEED USER PROFILES
# ══════════════════════════════════════════════════════════════════════════════

SEED_USERS: List[Dict[str, Any]] = [
    {
        "user_id": "user_001",
        "display_name": "Chukwuemeka Obi",
        "age": 28,
        "region": "Lagos",
        "occupation": "Software Engineer (Fintech)",
        "price_sensitivity": 0.55,
        "quality_weight": 0.85,
        "delivery_speed_importance": 0.80,
        "personality": {
            "openness": 0.82,
            "conscientiousness": 0.78,
            "extraversion": 0.55,
            "agreeableness": 0.65,
            "neuroticism": 0.35,
            "value_consciousness": 0.55,
            "social_proof_sensitivity": 0.50,
            "brand_loyalty": 0.60,
            "patience_score": 0.40,
        },
        "linguistic_style": {
            "uses_pidgin": True,
            "uses_igbo_phrases": True,
            "formality_level": 0.45,
            "emoji_usage": 0.55,
            "verbosity": 0.70,
            "characteristic_phrases": ["Nna men!", "The build quality is...", "Value for money?"],
        },
        "category_preferences": {
            "Electronics": 0.90,
            "Mobile Phones": 0.85,
            "Books & Stationery": 0.70,
            "Health & Wellness": 0.55,
            "Sports & Fitness": 0.60,
        },
        "narrative_identity": (
            "Chukwuemeka is a Lagos-based fintech engineer who treats every purchase "
            "like a system design decision — researched, justified, documented. He grew up "
            "in Enugu before moving to Lekki for work. He earns well but the naira's "
            "instability has made him increasingly tactical about spending. He compares "
            "specs obsessively before buying tech and reads at least 10 reviews. His pain "
            "points are fake products and sellers who disappear after delivery. He writes "
            "detailed, honest reviews because he 'wants to help the next person.'"
        ),
        "current_emotion": {"emotion": "content", "intensity": 0.6, "life_context": "at_work"},
        "average_rating_given": 3.8,
        "interaction_count": 47,
    },
    {
        "user_id": "user_002",
        "display_name": "Fatima Al-Hassan",
        "age": 34,
        "region": "Abuja",
        "occupation": "Government Procurement Officer",
        "price_sensitivity": 0.45,
        "quality_weight": 0.90,
        "delivery_speed_importance": 0.55,
        "personality": {
            "openness": 0.50,
            "conscientiousness": 0.90,
            "extraversion": 0.40,
            "agreeableness": 0.75,
            "neuroticism": 0.45,
            "value_consciousness": 0.65,
            "social_proof_sensitivity": 0.70,
            "brand_loyalty": 0.80,
            "patience_score": 0.75,
        },
        "linguistic_style": {
            "uses_pidgin": False,
            "uses_hausa_phrases": True,
            "formality_level": 0.80,
            "emoji_usage": 0.20,
            "verbosity": 0.55,
            "characteristic_phrases": ["Wallahi", "Alhamdulillah it works well", "Halal certified?"],
        },
        "category_preferences": {
            "Home & Living": 0.85,
            "Health & Wellness": 0.80,
            "Baby & Kids": 0.75,
            "Food & Groceries": 0.70,
            "Fashion": 0.65,
        },
        "narrative_identity": (
            "Fatima is a meticulous government officer in Abuja who shops with the same "
            "rigour she applies to procurement processes. She values brand reputation above "
            "all — she'd rather pay ₦20,000 more for a product from a known brand than risk "
            "counterfeit. As a mother of three, she takes children's product safety very "
            "seriously. She checks for NAFDAC numbers before buying health/food items. "
            "She rarely impulse-buys and always reads the 3-star reviews first."
        ),
        "current_emotion": {"emotion": "neutral", "intensity": 0.5, "life_context": "at_work"},
        "average_rating_given": 4.1,
        "interaction_count": 63,
    },
    {
        "user_id": "user_003",
        "display_name": "Adaeze Nwosu-Williams",
        "age": 26,
        "region": "Lagos",
        "occupation": "Content Creator / Influencer",
        "price_sensitivity": 0.35,
        "quality_weight": 0.75,
        "delivery_speed_importance": 0.90,
        "personality": {
            "openness": 0.95,
            "conscientiousness": 0.45,
            "extraversion": 0.92,
            "agreeableness": 0.80,
            "neuroticism": 0.50,
            "value_consciousness": 0.40,
            "social_proof_sensitivity": 0.85,
            "brand_loyalty": 0.35,
            "patience_score": 0.20,
        },
        "linguistic_style": {
            "uses_pidgin": True,
            "uses_igbo_phrases": True,
            "formality_level": 0.20,
            "emoji_usage": 0.90,
            "verbosity": 0.85,
            "characteristic_phrases": ["Bestieee!", "Slay!", "The vibes!", "Notify me!"],
        },
        "category_preferences": {
            "Fashion": 0.95,
            "Beauty & Personal Care": 0.92,
            "Mobile Phones": 0.75,
            "Electronics": 0.65,
            "Home & Living": 0.60,
        },
        "narrative_identity": (
            "Adaeze is Lagos Island's favourite content creator — her aesthetic is everything. "
            "She buys products as much for their 'Instagrammability' as their utility. "
            "Fast delivery is non-negotiable because her content calendar waits for no one. "
            "She's deeply influenced by what's trending on Instagram and TikTok, often "
            "making purchase decisions within hours of seeing a post. She's generous with "
            "5-star reviews for fast senders but viral with 1-star complaints. "
            "Her reviews are short, punchy, and emoji-heavy."
        ),
        "current_emotion": {"emotion": "excited", "intensity": 0.8, "life_context": "at_home"},
        "average_rating_given": 4.2,
        "interaction_count": 112,
    },
    {
        "user_id": "user_004",
        "display_name": "Bello Musa Garba",
        "age": 42,
        "region": "Kano",
        "occupation": "Trader / Wholesale Distributor",
        "price_sensitivity": 0.92,
        "quality_weight": 0.70,
        "delivery_speed_importance": 0.65,
        "personality": {
            "openness": 0.40,
            "conscientiousness": 0.85,
            "extraversion": 0.60,
            "agreeableness": 0.65,
            "neuroticism": 0.30,
            "value_consciousness": 0.95,
            "social_proof_sensitivity": 0.80,
            "brand_loyalty": 0.50,
            "patience_score": 0.80,
        },
        "linguistic_style": {
            "uses_pidgin": False,
            "uses_hausa_phrases": True,
            "formality_level": 0.65,
            "emoji_usage": 0.15,
            "verbosity": 0.40,
            "characteristic_phrases": ["Wallahi", "Na gode", "Good price?", "Original?"],
        },
        "category_preferences": {
            "Food & Groceries": 0.80,
            "Automotive": 0.75,
            "Health & Wellness": 0.65,
            "Baby & Kids": 0.70,
            "Home & Living": 0.60,
        },
        "narrative_identity": (
            "Bello is a Kano-based wholesale distributor who has seen every pricing trick "
            "in the market. He buys in bulk for his shop and resells, so price is everything. "
            "He's deeply community-influenced — if his masjid brothers recommend a product, "
            "he buys without question; if they warn against a seller, that relationship is dead. "
            "He's patient about delivery but extremely unforgiving about wrong quantities or "
            "quality deviations. His reviews are terse, factual, and trust-community-focused."
        ),
        "current_emotion": {"emotion": "neutral", "intensity": 0.4, "life_context": "at_work"},
        "average_rating_given": 3.5,
        "interaction_count": 88,
    },
    {
        "user_id": "user_005",
        "display_name": "Ngozi Okafor-Eze",
        "age": 38,
        "region": "Port Harcourt",
        "occupation": "Oil & Gas HR Manager",
        "price_sensitivity": 0.40,
        "quality_weight": 0.88,
        "delivery_speed_importance": 0.75,
        "personality": {
            "openness": 0.65,
            "conscientiousness": 0.82,
            "extraversion": 0.68,
            "agreeableness": 0.72,
            "neuroticism": 0.40,
            "value_consciousness": 0.55,
            "social_proof_sensitivity": 0.65,
            "brand_loyalty": 0.70,
            "patience_score": 0.55,
        },
        "linguistic_style": {
            "uses_pidgin": True,
            "uses_igbo_phrases": True,
            "formality_level": 0.60,
            "emoji_usage": 0.50,
            "verbosity": 0.65,
            "characteristic_phrases": ["Nna men", "Port Harcourt people know quality", "e pain me"],
        },
        "category_preferences": {
            "Fashion": 0.80,
            "Beauty & Personal Care": 0.85,
            "Health & Wellness": 0.75,
            "Home & Living": 0.70,
            "Baby & Kids": 0.65,
        },
        "narrative_identity": (
            "Ngozi is a PH-based HR manager with oil & gas lifestyle expectations but "
            "growing frustration with the naira's depreciation eroding her purchasing power. "
            "She used to buy premium without a second thought; now she calculates more carefully. "
            "She's deeply frustrated by delivery services that treat Port Harcourt as a "
            "second-tier city. Her reviews often mention PH-specific delivery experiences. "
            "She influences her office colleagues' buying decisions regularly."
        ),
        "current_emotion": {"emotion": "frustrated", "intensity": 0.65, "life_context": "end_of_month"},
        "average_rating_given": 3.7,
        "interaction_count": 74,
    },
    {
        "user_id": "user_006",
        "display_name": "Taiwo Adeyemi",
        "age": 22,
        "region": "Ibadan",
        "occupation": "University Student (Final Year)",
        "price_sensitivity": 0.88,
        "quality_weight": 0.60,
        "delivery_speed_importance": 0.50,
        "personality": {
            "openness": 0.78,
            "conscientiousness": 0.55,
            "extraversion": 0.70,
            "agreeableness": 0.75,
            "neuroticism": 0.55,
            "value_consciousness": 0.90,
            "social_proof_sensitivity": 0.85,
            "brand_loyalty": 0.25,
            "patience_score": 0.60,
        },
        "linguistic_style": {
            "uses_pidgin": True,
            "uses_yoruba_phrases": True,
            "formality_level": 0.25,
            "emoji_usage": 0.80,
            "verbosity": 0.55,
            "characteristic_phrases": ["Jare!", "No cap", "The thing do work o", "Ehn e do am"],
        },
        "category_preferences": {
            "Books & Stationery": 0.80,
            "Mobile Phones": 0.75,
            "Electronics": 0.65,
            "Fashion": 0.70,
            "Food & Groceries": 0.60,
        },
        "narrative_identity": (
            "Taiwo is a final-year UI student surviving on allowance and part-time income. "
            "Every naira is a negotiation. She uses Twitter/X and WhatsApp groups to find "
            "the best deals and student discounts. Brand means nothing to her — value means "
            "everything. She's heavily influenced by her hostel roommates and course mates. "
            "She writes enthusiastic reviews when something beats her low expectations, "
            "and passionate complaints when she feels cheated. She loves student deal threads."
        ),
        "current_emotion": {"emotion": "value_hunting", "intensity": 0.85, "life_context": "budget_crunch"},
        "average_rating_given": 3.3,
        "interaction_count": 31,
    },
    {
        "user_id": "user_007",
        "display_name": "Emeka Duru",
        "age": 45,
        "region": "Enugu",
        "occupation": "Medical Doctor / Entrepreneur",
        "price_sensitivity": 0.30,
        "quality_weight": 0.95,
        "delivery_speed_importance": 0.60,
        "personality": {
            "openness": 0.60,
            "conscientiousness": 0.95,
            "extraversion": 0.45,
            "agreeableness": 0.60,
            "neuroticism": 0.25,
            "value_consciousness": 0.40,
            "social_proof_sensitivity": 0.45,
            "brand_loyalty": 0.85,
            "patience_score": 0.80,
        },
        "linguistic_style": {
            "uses_pidgin": False,
            "uses_igbo_phrases": True,
            "formality_level": 0.85,
            "emoji_usage": 0.15,
            "verbosity": 0.80,
            "characteristic_phrases": ["From a clinical perspective", "Quality is non-negotiable", "I've verified"],
        },
        "category_preferences": {
            "Health & Wellness": 0.92,
            "Books & Stationery": 0.80,
            "Electronics": 0.75,
            "Appliances": 0.70,
            "Sports & Fitness": 0.65,
        },
        "narrative_identity": (
            "Dr. Emeka Duru is an Enugu-based doctor who runs a private clinic. "
            "He approaches product purchases like clinical trials — systematic, evidence-based, "
            "uncompromising on quality. He will pay any price for genuinely good products "
            "but is ferociously critical of substandard quality. He particularly scrutinises "
            "health and wellness products for NAFDAC certification and ingredient honesty. "
            "His reviews are long, clinical, and authoritative — other users trust them."
        ),
        "current_emotion": {"emotion": "content", "intensity": 0.55, "life_context": "at_work"},
        "average_rating_given": 3.6,
        "interaction_count": 55,
    },
]


# ══════════════════════════════════════════════════════════════════════════════
# SEED ITEM CATALOGUE
# ══════════════════════════════════════════════════════════════════════════════

SEED_ITEMS: List[Dict[str, Any]] = [
    # ── Electronics ──────────────────────────────────────────────────────────
    {
        "item_id": "item_001",
        "title": "Xiaomi Redmi Note 13 Pro+ — 256GB",
        "description": "Flagship-killer with 200MP camera, 120W HyperCharge, AMOLED display. Popular among Nigerian tech enthusiasts for its specs-to-price ratio.",
        "category": "Mobile Phones",
        "brand": "Xiaomi",
        "price_naira": 285_000,
        "price_tier": "premium",
        "average_rating": 4.3,
        "review_count": 892,
        "popularity_score": 0.82,
        "locally_available": True,
        "delivery_profile": "2-3_days",
        "fake_risk_score": 0.25,
        "seller_trust_score": 0.75,
        "tags": ["smartphone", "camera phone", "fast charging", "AMOLED", "Xiaomi", "budget flagship"],
        "attributes": {
            "RAM": "12GB",
            "Storage": "256GB",
            "Camera": "200MP",
            "Battery": "5000mAh",
            "Charging": "120W HyperCharge",
        },
    },
    {
        "item_id": "item_002",
        "title": "Samsung Galaxy S24 FE — 128GB (Midnight Green)",
        "description": "Samsung Fan Edition with Galaxy AI features. Trusted brand, reliable performance, available at Samsung Experience Stores in Lagos and Abuja.",
        "category": "Mobile Phones",
        "brand": "Samsung",
        "price_naira": 620_000,
        "price_tier": "luxury",
        "average_rating": 4.5,
        "review_count": 1203,
        "popularity_score": 0.88,
        "locally_available": True,
        "delivery_profile": "next_day",
        "fake_risk_score": 0.08,
        "seller_trust_score": 0.92,
        "tags": ["Samsung", "Galaxy AI", "flagship", "official store", "trusted brand", "camera"],
        "attributes": {
            "RAM": "8GB",
            "Storage": "128GB",
            "Camera": "50MP Triple",
            "Battery": "4700mAh",
            "OS": "Android 14 / One UI 6.1",
        },
    },
    {
        "item_id": "item_003",
        "title": "Anker PowerCore 20100mAh Power Bank",
        "description": "High-capacity portable charger — a Lagos essential for NEPA-challenged lifestyles. Charges 2 phones simultaneously.",
        "category": "Electronics",
        "brand": "Anker",
        "price_naira": 42_000,
        "price_tier": "mid_range",
        "average_rating": 4.6,
        "review_count": 2341,
        "popularity_score": 0.91,
        "locally_available": True,
        "delivery_profile": "2-3_days",
        "fake_risk_score": 0.30,
        "seller_trust_score": 0.80,
        "tags": ["power bank", "Anker", "portable charger", "NEPA essential", "travel", "dual USB"],
        "attributes": {
            "Capacity": "20100mAh",
            "Output Ports": "2x USB-A + 1x USB-C",
            "Weight": "356g",
            "Charging Time": "~6 hours",
        },
    },
    {
        "item_id": "item_004",
        "title": "JBL Clip 4 Portable Bluetooth Speaker",
        "description": "Waterproof, dustproof mini speaker with rich JBL sound. Clips to bags, perfect for outdoor Lagos lifestyle.",
        "category": "Electronics",
        "brand": "JBL",
        "price_naira": 58_000,
        "price_tier": "mid_range",
        "average_rating": 4.4,
        "review_count": 674,
        "popularity_score": 0.74,
        "locally_available": True,
        "delivery_profile": "2-3_days",
        "fake_risk_score": 0.20,
        "seller_trust_score": 0.78,
        "tags": ["JBL", "bluetooth speaker", "waterproof", "portable", "outdoor", "music"],
        "attributes": {
            "Battery Life": "10 hours",
            "Waterproof": "IP67",
            "Connectivity": "Bluetooth 5.1",
            "Weight": "240g",
        },
    },
    # ── Laptops/Computers ────────────────────────────────────────────────────
    {
        "item_id": "item_005",
        "title": "HP Pavilion 15 — Intel i5 13th Gen, 8GB RAM, 512GB SSD",
        "description": "Reliable everyday laptop for students and professionals. Good battery life, decent build for Nigerian heat and humidity.",
        "category": "Electronics",
        "brand": "HP",
        "price_naira": 520_000,
        "price_tier": "premium",
        "average_rating": 4.2,
        "review_count": 438,
        "popularity_score": 0.72,
        "locally_available": True,
        "delivery_profile": "2-3_days",
        "fake_risk_score": 0.10,
        "seller_trust_score": 0.85,
        "tags": ["laptop", "HP", "student laptop", "i5", "SSD", "work from home"],
        "attributes": {
            "Processor": "Intel Core i5-1335U",
            "RAM": "8GB DDR4",
            "Storage": "512GB NVMe SSD",
            "Display": "15.6 inch FHD IPS",
            "Battery": "~8 hours",
        },
    },
    # ── Fashion ──────────────────────────────────────────────────────────────
    {
        "item_id": "item_006",
        "title": "Men's Senator Kaftan Set (Atiku Fabric) — Navy Blue",
        "description": "Elegant Nigerian men's senator suit in premium Atiku material. Perfect for Eid, weddings, and church occasions.",
        "category": "Fashion",
        "brand": None,
        "price_naira": 28_000,
        "price_tier": "mid_range",
        "average_rating": 4.5,
        "review_count": 1876,
        "popularity_score": 0.86,
        "locally_available": True,
        "delivery_profile": "2-3_days",
        "fake_risk_score": 0.05,
        "seller_trust_score": 0.82,
        "tags": ["senator", "Atiku", "Nigerian fashion", "Eid", "occasions", "kaftan", "aso-ebi"],
        "attributes": {
            "Material": "Atiku fabric",
            "Style": "Senator/Kaftan combo",
            "Sizes": "S, M, L, XL, XXL, XXXL",
            "Occasion": "Formal/traditional",
        },
    },
    {
        "item_id": "item_007",
        "title": "Ankara Bodycon Dress — Ankara Print",
        "description": "Stunning hand-tailored Ankara bodycon. Celebrates Nigerian femininity with bold, authentic African print patterns.",
        "category": "Fashion",
        "brand": None,
        "price_naira": 18_000,
        "price_tier": "mid_range",
        "average_rating": 4.3,
        "review_count": 2341,
        "popularity_score": 0.85,
        "locally_available": True,
        "delivery_profile": "same_day",
        "fake_risk_score": 0.03,
        "seller_trust_score": 0.88,
        "tags": ["Ankara", "African print", "bodycon", "Nigerian fashion", "slay", "occasions"],
        "attributes": {
            "Material": "100% Ankara cotton",
            "Style": "Bodycon midi",
            "Occasions": "Owambe, dates, outings",
        },
    },
    # ── Food & Groceries ─────────────────────────────────────────────────────
    {
        "item_id": "item_008",
        "title": "Indomie Instant Noodles — Chicken Flavour (40 packs)",
        "description": "Nigeria's ultimate comfort food survival pack. The Indomie chicken flavour that has powered a generation of students and workers.",
        "category": "Food & Groceries",
        "brand": "Indomie",
        "price_naira": 11_500,
        "price_tier": "budget",
        "average_rating": 4.7,
        "review_count": 8923,
        "popularity_score": 0.97,
        "locally_available": True,
        "delivery_profile": "same_day",
        "fake_risk_score": 0.02,
        "seller_trust_score": 0.95,
        "tags": ["Indomie", "noodles", "instant food", "student food", "budget", "bulk buy"],
        "attributes": {
            "Pack Size": "40 x 70g",
            "Flavour": "Chicken",
            "Brand": "Indomie (Dufil)",
            "Shelf Life": "12 months",
        },
    },
    {
        "item_id": "item_009",
        "title": "Golden Penny Semovita — 5kg",
        "description": "Premium semovita flour for the perfect swallow. Consistently smooth texture, trusted by Nigerian households for decades.",
        "category": "Food & Groceries",
        "brand": "Golden Penny",
        "price_naira": 4_800,
        "price_tier": "budget",
        "average_rating": 4.6,
        "review_count": 3412,
        "popularity_score": 0.88,
        "locally_available": True,
        "delivery_profile": "same_day",
        "fake_risk_score": 0.01,
        "seller_trust_score": 0.96,
        "tags": ["semovita", "swallow", "Golden Penny", "Nigerian food", "cooking essentials"],
        "attributes": {
            "Weight": "5kg",
            "Type": "Semovita",
            "Brand": "Golden Penny",
            "Usage": "Nigerian swallow (eba, egusi, ogbono)",
        },
    },
    # ── Beauty & Personal Care ────────────────────────────────────────────────
    {
        "item_id": "item_010",
        "title": "Neutrogena Fine Fairness Moisturizer SPF 30",
        "description": "Dermatologist-tested brightening moisturizer with SPF. Works well under Nigerian tropical sun without greasiness.",
        "category": "Beauty & Personal Care",
        "brand": "Neutrogena",
        "price_naira": 15_000,
        "price_tier": "mid_range",
        "average_rating": 4.2,
        "review_count": 1203,
        "popularity_score": 0.78,
        "locally_available": True,
        "delivery_profile": "2-3_days",
        "fake_risk_score": 0.30,
        "seller_trust_score": 0.72,
        "tags": ["Neutrogena", "moisturizer", "SPF", "skincare", "brightening", "face cream"],
        "attributes": {
            "SPF": "30",
            "Size": "40ml",
            "Skin Type": "All skin types",
            "NAFDAC": "Verify before buying",
        },
    },
    {
        "item_id": "item_011",
        "title": "Dove Body Lotion — Shea Butter (400ml)",
        "description": "Deep moisturizing body lotion with natural shea butter. Trusted for Nigerian skin tone and tropical climate compatibility.",
        "category": "Beauty & Personal Care",
        "brand": "Dove",
        "price_naira": 6_500,
        "price_tier": "budget",
        "average_rating": 4.5,
        "review_count": 4521,
        "popularity_score": 0.86,
        "locally_available": True,
        "delivery_profile": "2-3_days",
        "fake_risk_score": 0.20,
        "seller_trust_score": 0.80,
        "tags": ["Dove", "body lotion", "shea butter", "moisturizer", "skincare", "trusted brand"],
        "attributes": {
            "Volume": "400ml",
            "Key Ingredient": "Natural Shea Butter",
            "Scent": "Soft cream",
        },
    },
    # ── Home & Living ─────────────────────────────────────────────────────────
    {
        "item_id": "item_012",
        "title": "Thermocool 65-litre Chest Freezer",
        "description": "Energy-efficient chest freezer — the cornerstone of Nigerian home economics. Run on inverter when NEPA fails. Perfect for bulk buying and fish storage.",
        "category": "Appliances",
        "brand": "Thermocool",
        "price_naira": 195_000,
        "price_tier": "premium",
        "average_rating": 4.1,
        "review_count": 789,
        "popularity_score": 0.80,
        "locally_available": True,
        "delivery_profile": "one_week",
        "fake_risk_score": 0.05,
        "seller_trust_score": 0.88,
        "tags": ["freezer", "Thermocool", "chest freezer", "inverter compatible", "NEPA", "home appliance"],
        "attributes": {
            "Capacity": "65 litres",
            "Power": "100W",
            "Inverter Compatible": "Yes",
            "Warranty": "2 years compressor",
            "Color": "White",
        },
    },
    {
        "item_id": "item_013",
        "title": "Binatone Hand Blender & Smoothie Maker",
        "description": "Multifunctional blender for tomatoes, pepper, and morning smoothies. Nigerian kitchen essential with heavy-duty motor for tough blending tasks.",
        "category": "Appliances",
        "brand": "Binatone",
        "price_naira": 28_000,
        "price_tier": "mid_range",
        "average_rating": 4.0,
        "review_count": 2103,
        "popularity_score": 0.77,
        "locally_available": True,
        "delivery_profile": "2-3_days",
        "fake_risk_score": 0.08,
        "seller_trust_score": 0.83,
        "tags": ["blender", "Binatone", "kitchen appliance", "smoothie maker", "pepper blender", "Nigerian kitchen"],
        "attributes": {
            "Power": "600W",
            "Capacity": "1.5 Litres",
            "Functions": "Blending, chopping, smoothie",
            "Speed Settings": "3",
        },
    },
    # ── Health & Wellness ─────────────────────────────────────────────────────
    {
        "item_id": "item_014",
        "title": "Lifescan True Metrix Blood Glucose Meter + 50 Strips",
        "description": "Clinical-grade glucose monitoring kit. NAFDAC approved. Essential for the growing diabetic population in Nigeria.",
        "category": "Health & Wellness",
        "brand": "Lifescan",
        "price_naira": 32_000,
        "price_tier": "mid_range",
        "average_rating": 4.4,
        "review_count": 567,
        "popularity_score": 0.72,
        "locally_available": True,
        "delivery_profile": "2-3_days",
        "fake_risk_score": 0.15,
        "seller_trust_score": 0.85,
        "tags": ["glucose meter", "diabetes", "NAFDAC", "health", "medical device", "blood sugar"],
        "attributes": {
            "NAFDAC Registered": "Yes",
            "Test Speed": "5 seconds",
            "Memory": "500 readings",
            "Strips Included": "50",
        },
    },
    # ── Books & Education ─────────────────────────────────────────────────────
    {
        "item_id": "item_015",
        "title": "WAEC/NECO Integrated Science Past Questions (2015–2024)",
        "description": "10-year past question compilation with detailed solutions. Essential for SS3 students preparing for WAEC and NECO exams.",
        "category": "Books & Stationery",
        "brand": None,
        "price_naira": 3_500,
        "price_tier": "budget",
        "average_rating": 4.6,
        "review_count": 5621,
        "popularity_score": 0.92,
        "locally_available": True,
        "delivery_profile": "2-3_days",
        "fake_risk_score": 0.03,
        "seller_trust_score": 0.90,
        "tags": ["WAEC", "NECO", "past questions", "student", "exam prep", "secondary school", "science"],
        "attributes": {
            "Pages": "320",
            "Years Covered": "2015-2024",
            "Subject": "Integrated Science",
            "Includes": "Detailed solutions",
        },
    },
    {
        "item_id": "item_016",
        "title": "Atomic Habits by James Clear (Paperback)",
        "description": "Globally acclaimed self-improvement book on behaviour change. A favourite among Nigerian young professionals and entrepreneurs.",
        "category": "Books & Stationery",
        "brand": None,
        "price_naira": 12_000,
        "price_tier": "mid_range",
        "average_rating": 4.8,
        "review_count": 3201,
        "popularity_score": 0.88,
        "locally_available": True,
        "delivery_profile": "2-3_days",
        "fake_risk_score": 0.05,
        "seller_trust_score": 0.88,
        "tags": ["self-help", "James Clear", "habits", "productivity", "personal development", "bestseller"],
        "attributes": {
            "Author": "James Clear",
            "Pages": "320",
            "Format": "Paperback",
            "Publisher": "Avery Publishing",
        },
    },
    # ── Sports & Fitness ──────────────────────────────────────────────────────
    {
        "item_id": "item_017",
        "title": "Kipsta Football — FIFA Inspected Size 5",
        "description": "Official match ball standard football. Affordable, durable, perfect for Lagos estate leagues and Sunday matches.",
        "category": "Sports & Fitness",
        "brand": "Kipsta",
        "price_naira": 9_500,
        "price_tier": "budget",
        "average_rating": 4.3,
        "review_count": 1872,
        "popularity_score": 0.80,
        "locally_available": True,
        "delivery_profile": "2-3_days",
        "fake_risk_score": 0.08,
        "seller_trust_score": 0.80,
        "tags": ["football", "FIFA", "sports", "soccer ball", "outdoor", "estate league"],
        "attributes": {
            "Size": "5",
            "Standard": "FIFA Inspected",
            "Material": "Machine-stitched",
            "Panels": "32",
        },
    },
    # ── Baby & Kids ───────────────────────────────────────────────────────────
    {
        "item_id": "item_018",
        "title": "Pampers Active Baby Diapers (Mega Pack) — Size 4 (7-14kg)",
        "description": "Nigeria's most trusted diaper brand. Active-fit technology for active Nigerian babies who won't slow down.",
        "category": "Baby & Kids",
        "brand": "Pampers",
        "price_naira": 24_500,
        "price_tier": "mid_range",
        "average_rating": 4.6,
        "review_count": 7832,
        "popularity_score": 0.94,
        "locally_available": True,
        "delivery_profile": "same_day",
        "fake_risk_score": 0.05,
        "seller_trust_score": 0.92,
        "tags": ["Pampers", "diapers", "baby essentials", "mega pack", "value pack", "trusted brand"],
        "attributes": {
            "Size": "4 (7-14kg)",
            "Count": "68 diapers",
            "Feature": "Active-fit waistband",
            "Dry Factor": "Up to 12 hours",
        },
    },
    # ── Automotive ────────────────────────────────────────────────────────────
    {
        "item_id": "item_019",
        "title": "Meguiar's G17516 Ultimate Liquid Wax (473ml)",
        "description": "Premium synthetic car wax for Nigerian carowners who take their wheels seriously. Protects against tropical sun and dust.",
        "category": "Automotive",
        "brand": "Meguiar's",
        "price_naira": 18_000,
        "price_tier": "mid_range",
        "average_rating": 4.5,
        "review_count": 421,
        "popularity_score": 0.68,
        "locally_available": True,
        "delivery_profile": "2-3_days",
        "fake_risk_score": 0.15,
        "seller_trust_score": 0.78,
        "tags": ["car wax", "Meguiar's", "car care", "automotive", "detailing", "tropical climate"],
        "attributes": {
            "Volume": "473ml",
            "Type": "Synthetic polymer wax",
            "Application": "By hand or machine",
            "UV Protection": "Yes",
        },
    },
    # ── More Electronics ──────────────────────────────────────────────────────
    {
        "item_id": "item_020",
        "title": "TP-Link TL-WR845N N300 WiFi Router",
        "description": "Reliable home WiFi router for MTN/Airtel/Glo fiber subscribers. Handles multiple devices without dropping during Zoom calls.",
        "category": "Electronics",
        "brand": "TP-Link",
        "price_naira": 22_000,
        "price_tier": "mid_range",
        "average_rating": 4.2,
        "review_count": 1543,
        "popularity_score": 0.78,
        "locally_available": True,
        "delivery_profile": "2-3_days",
        "fake_risk_score": 0.12,
        "seller_trust_score": 0.82,
        "tags": ["router", "WiFi", "TP-Link", "home network", "internet", "fiber", "work from home"],
        "attributes": {
            "Speed": "N300 (300Mbps)",
            "Antennas": "3x fixed antennas",
            "Ports": "4x LAN, 1x WAN",
            "Band": "2.4GHz",
        },
    },
]


# ══════════════════════════════════════════════════════════════════════════════
# SAMPLE INTERACTION HISTORY (for graph seeding)
# ══════════════════════════════════════════════════════════════════════════════

SEED_INTERACTIONS: List[Dict[str, Any]] = [
    # Chukwuemeka — tech enthusiast
    {"user_id": "user_001", "item_id": "item_001", "type": "purchase", "rating": 4.5},
    {"user_id": "user_001", "item_id": "item_003", "type": "purchase", "rating": 5.0},
    {"user_id": "user_001", "item_id": "item_005", "type": "wishlist"},
    {"user_id": "user_001", "item_id": "item_016", "type": "purchase", "rating": 5.0},
    {"user_id": "user_001", "item_id": "item_020", "type": "purchase", "rating": 4.0},

    # Fatima — quality-focused family shopper
    {"user_id": "user_002", "item_id": "item_014", "type": "purchase", "rating": 4.5},
    {"user_id": "user_002", "item_id": "item_018", "type": "purchase", "rating": 5.0},
    {"user_id": "user_002", "item_id": "item_009", "type": "purchase", "rating": 4.5},
    {"user_id": "user_002", "item_id": "item_012", "type": "purchase", "rating": 4.0},
    {"user_id": "user_002", "item_id": "item_011", "type": "purchase", "rating": 4.5},

    # Adaeze — fashionista content creator
    {"user_id": "user_003", "item_id": "item_007", "type": "purchase", "rating": 5.0},
    {"user_id": "user_003", "item_id": "item_010", "type": "purchase", "rating": 4.0},
    {"user_id": "user_003", "item_id": "item_011", "type": "purchase", "rating": 5.0},
    {"user_id": "user_003", "item_id": "item_002", "type": "wishlist"},
    {"user_id": "user_003", "item_id": "item_004", "type": "purchase", "rating": 4.5},

    # Bello — price-conscious Kano trader
    {"user_id": "user_004", "item_id": "item_008", "type": "purchase", "rating": 4.5},
    {"user_id": "user_004", "item_id": "item_009", "type": "purchase", "rating": 4.5},
    {"user_id": "user_004", "item_id": "item_018", "type": "purchase", "rating": 5.0},
    {"user_id": "user_004", "item_id": "item_006", "type": "purchase", "rating": 4.0},

    # Ngozi — PH HR manager
    {"user_id": "user_005", "item_id": "item_010", "type": "purchase", "rating": 3.5},
    {"user_id": "user_005", "item_id": "item_011", "type": "purchase", "rating": 4.5},
    {"user_id": "user_005", "item_id": "item_007", "type": "wishlist"},
    {"user_id": "user_005", "item_id": "item_014", "type": "purchase", "rating": 4.0},

    # Taiwo — budget student
    {"user_id": "user_006", "item_id": "item_008", "type": "purchase", "rating": 5.0},
    {"user_id": "user_006", "item_id": "item_015", "type": "purchase", "rating": 5.0},
    {"user_id": "user_006", "item_id": "item_001", "type": "view"},
    {"user_id": "user_006", "item_id": "item_005", "type": "wishlist"},

    # Dr. Emeka — quality-obsessed doctor
    {"user_id": "user_007", "item_id": "item_014", "type": "purchase", "rating": 4.5},
    {"user_id": "user_007", "item_id": "item_016", "type": "purchase", "rating": 5.0},
    {"user_id": "user_007", "item_id": "item_017", "type": "purchase", "rating": 4.0},
    {"user_id": "user_007", "item_id": "item_005", "type": "purchase", "rating": 3.5},
]


def get_user_by_id(user_id: str) -> Dict[str, Any] | None:
    return next((u for u in SEED_USERS if u["user_id"] == user_id), None)


def get_item_by_id(item_id: str) -> Dict[str, Any] | None:
    return next((i for i in SEED_ITEMS if i["item_id"] == item_id), None)


def get_user_interactions(user_id: str) -> List[Dict[str, Any]]:
    return [i for i in SEED_INTERACTIONS if i["user_id"] == user_id]

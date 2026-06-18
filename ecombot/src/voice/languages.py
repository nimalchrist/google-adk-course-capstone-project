from dataclasses import dataclass


@dataclass
class LanguageConfig:
    code: str
    name: str
    greeting: str
    voice: str  # TTS voice name
    sample_prompts: list[str]
    confirm_yes: list[str]
    confirm_no: list[str]


LANGUAGES: dict[str, LanguageConfig] = {
    "en": LanguageConfig(
        code="en",
        name="English",
        greeting="Hello! I'm your ElectroMart voice assistant. How can I help you?",
        voice="nova",
        sample_prompts=[
            "Where is my order ORD-001?",
            "Recommend a phone under thirty thousand rupees.",
            "Compare iPhone 15 Pro with Samsung Galaxy S24.",
            "What is your return policy?",
        ],
        confirm_yes=["yes", "yeah", "yep", "correct", "that's right", "right"],
        confirm_no=["no", "nope", "wrong", "incorrect", "that's wrong"],
    ),
    "fr": LanguageConfig(
        code="fr",
        name="Français",
        greeting="Bonjour ! Je suis votre assistant vocal ElectroMart. Comment puis-je vous aider ?",
        voice="nova",
        sample_prompts=[
            "Où est ma commande ORD-001 ?",
            "Recommandez un téléphone à moins de trente mille roupies.",
            "Quelle est votre politique de retour ?",
        ],
        confirm_yes=["oui", "ouais", "correct", "c'est ça"],
        confirm_no=["non", "pas du tout", "incorrect"],
    ),
    "hi": LanguageConfig(
        code="hi",
        name="हिन्दी",
        greeting="नमस्ते! मैं आपका ElectroMart वॉइस असिस्टेंट हूँ। मैं आपकी कैसे मदद कर सकता हूँ?",
        voice="nova",
        sample_prompts=[
            "मेरा ऑर्डर ORD-001 कहाँ है?",
            "तीस हज़ार रुपये से कम का फ़ोन सुझाइए।",
            "आपकी रिटर्न पॉलिसी क्या है?",
        ],
        confirm_yes=["हाँ", "जी हाँ", "सही", "बिल्कुल"],
        confirm_no=["नहीं", "गलत", "ना"],
    ),
}


def get_language(code: str) -> LanguageConfig:
    return LANGUAGES.get(code, LANGUAGES["en"])

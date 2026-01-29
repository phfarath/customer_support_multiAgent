"""
Content Moderator - Detects and filters offensive or inappropriate content

This module provides local pattern-based content moderation to detect:
- Profanity and offensive language
- Harassment and threats
- Hate speech patterns
- Spam indicators

Optionally supports OpenAI Moderation API for more sophisticated detection.
"""
import re
import logging
from enum import Enum
from typing import Tuple, Optional, Dict, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class ModerationCategory(Enum):
    """Categories of content moderation"""
    SAFE = "safe"
    PROFANITY = "profanity"
    HARASSMENT = "harassment"
    HATE_SPEECH = "hate_speech"
    THREAT = "threat"
    SEXUAL = "sexual"
    SELF_HARM = "self_harm"
    SPAM = "spam"
    UNKNOWN = "unknown"


@dataclass
class ModerationResult:
    """Result of content moderation check"""
    is_safe: bool
    category: ModerationCategory
    confidence: float
    matched_patterns: list
    details: Optional[str] = None


# Profanity patterns (Portuguese and English common terms)
# Note: This is a simplified list - production should use more comprehensive lists
PROFANITY_PATTERNS = [
    # Portuguese
    r"\b(?:porra|caralho|merda|foda-se|fodase|puta|cacete|desgraca|filho\s*da\s*puta|fdp|vsf|tnc|pqp)\b",
    # English
    r"\b(?:fuck|shit|damn|bitch|bastard|asshole|crap|dick|cock|pussy)\b",
]

# Harassment patterns
HARASSMENT_PATTERNS = [
    r"\b(?:vou\s+te\s+(?:matar|pegar|acabar|destruir))",
    r"\b(?:te\s+(?:odeio|detesto))",
    r"\b(?:i\s+(?:will|gonna|going\s+to)\s+(?:kill|hurt|destroy|find)\s+you)",
    r"\b(?:you\s+(?:deserve|should)\s+(?:to\s+)?die)",
    r"\b(?:i\s+hate\s+you)",
    r"\b(?:sua?\s+(?:lixo|inutil|idiota|imbecil|retardado))",
    r"\b(?:you(?:'re|\s+are)\s+(?:garbage|worthless|useless|stupid|idiot|moron))\b",
]

# Threat patterns
THREAT_PATTERNS = [
    r"\b(?:vou\s+(?:te\s+)?(?:matar|assassinar|eliminar|acabar\s+com))",
    r"\b(?:te\s+(?:mato|acabo|elimino))",
    r"\b(?:i(?:'ll|'m\s+going\s+to|will)\s+(?:kill|murder|hurt|harm|attack)\s+you)",
    r"\b(?:you(?:'re|\s+are)\s+(?:dead|going\s+to\s+die))",
    r"\b(?:bomb|bomba|explosive|explosivo)\b.*(?:send|mandar|enviar)",
]

# Hate speech patterns (simplified)
HATE_SPEECH_PATTERNS = [
    r"\b(?:todos?\s+(?:os|as)\s+[\w]+\s+(?:devem|deveriam)\s+morrer)",
    r"\b(?:all\s+[\w]+\s+(?:should|must|deserve\s+to)\s+die)",
    r"\b(?:morte\s+(?:a|aos?|as?)\s+[\w]+)",
    r"\b(?:death\s+to\s+(?:all\s+)?[\w]+)",
]

# Self-harm patterns
SELF_HARM_PATTERNS = [
    r"\b(?:vou\s+(?:me\s+)?(?:matar|suicidar))",
    r"\b(?:quero\s+(?:morrer|me\s+matar))",
    r"\b(?:i\s+(?:want\s+to|will|gonna)\s+(?:kill\s+myself|end\s+(?:it|my\s+life)|commit\s+suicide))",
    r"\b(?:i(?:'m|\s+am)\s+going\s+to\s+(?:kill\s+myself|end\s+(?:it|my\s+life)))",
]

# Spam patterns
SPAM_PATTERNS = [
    r"(?:https?://[^\s]+){3,}",  # Multiple URLs
    r"(?:clique\s+(?:aqui|agora)|click\s+(?:here|now)){2,}",
    r"(?:ganhe|win|free|gratis|promo[cç][aã]o)\s*[!]{2,}",
    r"[A-Z\s]{20,}",  # All caps text
    r"(.)\1{5,}",  # Repeated characters
]


class ContentModerator:
    """
    Moderates content for offensive, harmful, or inappropriate material.

    Usage:
        moderator = ContentModerator()
        result = moderator.moderate(user_message)
        if not result.is_safe:
            # Handle inappropriate content
            pass
    """

    def __init__(self, strict_mode: bool = False):
        """
        Initialize the content moderator.

        Args:
            strict_mode: If True, use stricter matching thresholds
        """
        self.strict_mode = strict_mode

        # Compile all patterns
        self.profanity_regex = re.compile(
            "|".join(PROFANITY_PATTERNS),
            re.IGNORECASE
        )
        self.harassment_regex = re.compile(
            "|".join(HARASSMENT_PATTERNS),
            re.IGNORECASE
        )
        self.threat_regex = re.compile(
            "|".join(THREAT_PATTERNS),
            re.IGNORECASE
        )
        self.hate_regex = re.compile(
            "|".join(HATE_SPEECH_PATTERNS),
            re.IGNORECASE
        )
        self.self_harm_regex = re.compile(
            "|".join(SELF_HARM_PATTERNS),
            re.IGNORECASE
        )
        self.spam_regex = re.compile(
            "|".join(SPAM_PATTERNS),
            re.IGNORECASE
        )

    def moderate(self, text: str) -> ModerationResult:
        """
        Check text for inappropriate content.

        Args:
            text: The text to moderate

        Returns:
            ModerationResult with safety status and details
        """
        if not text:
            return ModerationResult(
                is_safe=True,
                category=ModerationCategory.SAFE,
                confidence=1.0,
                matched_patterns=[]
            )

        # Check each category in order of severity

        # 1. Self-harm (highest priority - may need special handling)
        self_harm_matches = self.self_harm_regex.findall(text)
        if self_harm_matches:
            logger.warning("Self-harm content detected - may need special handling")
            return ModerationResult(
                is_safe=False,
                category=ModerationCategory.SELF_HARM,
                confidence=0.9,
                matched_patterns=list(set(self_harm_matches))[:3],
                details="Self-harm related content detected. Consider providing crisis resources."
            )

        # 2. Threats
        threat_matches = self.threat_regex.findall(text)
        if threat_matches:
            logger.warning(f"Threat detected: {threat_matches}")
            return ModerationResult(
                is_safe=False,
                category=ModerationCategory.THREAT,
                confidence=0.95,
                matched_patterns=list(set(threat_matches))[:3]
            )

        # 3. Hate speech
        hate_matches = self.hate_regex.findall(text)
        if hate_matches:
            logger.warning(f"Hate speech detected: {hate_matches}")
            return ModerationResult(
                is_safe=False,
                category=ModerationCategory.HATE_SPEECH,
                confidence=0.9,
                matched_patterns=list(set(hate_matches))[:3]
            )

        # 4. Harassment
        harassment_matches = self.harassment_regex.findall(text)
        if harassment_matches:
            logger.warning(f"Harassment detected: {harassment_matches}")
            return ModerationResult(
                is_safe=False,
                category=ModerationCategory.HARASSMENT,
                confidence=0.85,
                matched_patterns=list(set(harassment_matches))[:3]
            )

        # 5. Profanity (may allow in non-strict mode)
        profanity_matches = self.profanity_regex.findall(text)
        if profanity_matches:
            logger.info(f"Profanity detected: {profanity_matches}")
            return ModerationResult(
                is_safe=not self.strict_mode,  # Allow profanity in non-strict mode
                category=ModerationCategory.PROFANITY,
                confidence=0.9,
                matched_patterns=list(set(profanity_matches))[:3],
                details="Profanity detected but allowed in standard mode" if not self.strict_mode else None
            )

        # 6. Spam
        spam_matches = self.spam_regex.findall(text)
        if spam_matches and len(spam_matches) >= 2:  # Require multiple spam indicators
            logger.info(f"Spam patterns detected: {len(spam_matches)} matches")
            return ModerationResult(
                is_safe=False,
                category=ModerationCategory.SPAM,
                confidence=0.7,
                matched_patterns=list(set(str(m) for m in spam_matches))[:3]
            )

        # Content is safe
        return ModerationResult(
            is_safe=True,
            category=ModerationCategory.SAFE,
            confidence=1.0,
            matched_patterns=[]
        )

    async def moderate_with_openai(
        self,
        text: str,
        use_local_fallback: bool = True
    ) -> ModerationResult:
        """
        Use OpenAI's Moderation API for content moderation.

        This provides more sophisticated detection but requires API calls.
        Falls back to local moderation if the API fails.

        Args:
            text: The text to moderate
            use_local_fallback: Whether to use local moderation on API failure

        Returns:
            ModerationResult
        """
        try:
            from openai import AsyncOpenAI
            from src.config import settings

            if not settings.openai_api_key:
                logger.warning("OpenAI API key not configured, using local moderation")
                return self.moderate(text)

            client = AsyncOpenAI(api_key=settings.openai_api_key)
            response = await client.moderations.create(input=text)

            result = response.results[0]

            # Map OpenAI categories to our categories
            if result.flagged:
                categories = result.categories

                if getattr(categories, 'self-harm', False) or getattr(categories, 'self_harm', False):
                    category = ModerationCategory.SELF_HARM
                elif getattr(categories, 'violence', False):
                    category = ModerationCategory.THREAT
                elif getattr(categories, 'hate', False):
                    category = ModerationCategory.HATE_SPEECH
                elif getattr(categories, 'harassment', False):
                    category = ModerationCategory.HARASSMENT
                elif getattr(categories, 'sexual', False):
                    category = ModerationCategory.SEXUAL
                else:
                    category = ModerationCategory.UNKNOWN

                return ModerationResult(
                    is_safe=False,
                    category=category,
                    confidence=0.95,  # OpenAI moderation is generally reliable
                    matched_patterns=["openai_moderation_flagged"],
                    details="Flagged by OpenAI Moderation API"
                )

            return ModerationResult(
                is_safe=True,
                category=ModerationCategory.SAFE,
                confidence=0.95,
                matched_patterns=[]
            )

        except Exception as e:
            logger.error(f"OpenAI Moderation API failed: {e}")
            if use_local_fallback:
                return self.moderate(text)
            raise

    def get_safe_response_for_category(self, category: ModerationCategory) -> str:
        """
        Get an appropriate safe response based on the moderation category.

        Args:
            category: The detected moderation category

        Returns:
            A safe response message
        """
        responses = {
            ModerationCategory.SELF_HARM: (
                "Percebi que voce pode estar passando por um momento dificil. "
                "Se precisar de ajuda, o CVV (Centro de Valorizacao da Vida) "
                "esta disponivel 24h pelo 188 ou cvv.org.br. "
                "Como posso ajudar com seu atendimento?"
            ),
            ModerationCategory.THREAT: (
                "Por favor, mantenha nossa conversa respeitosa. "
                "Ameacas nao sao toleradas. Como posso ajuda-lo hoje?"
            ),
            ModerationCategory.HATE_SPEECH: (
                "Por favor, mantenha nossa conversa respeitosa e inclusiva. "
                "Como posso ajuda-lo com seu atendimento?"
            ),
            ModerationCategory.HARASSMENT: (
                "Por favor, mantenha a conversa respeitosa. "
                "Estou aqui para ajudar. Como posso assisti-lo?"
            ),
            ModerationCategory.PROFANITY: (
                "Entendo que voce possa estar frustrado. "
                "Vamos tentar resolver seu problema. Como posso ajudar?"
            ),
            ModerationCategory.SPAM: (
                "Sua mensagem foi identificada como spam. "
                "Por favor, descreva como posso ajuda-lo."
            ),
        }

        return responses.get(
            category,
            "Desculpe, nao posso processar essa solicitacao. Como posso ajuda-lo?"
        )


# Singleton instance
_content_moderator: Optional[ContentModerator] = None


def get_content_moderator() -> ContentModerator:
    """Get or create the singleton ContentModerator instance"""
    global _content_moderator
    if _content_moderator is None:
        _content_moderator = ContentModerator()
    return _content_moderator

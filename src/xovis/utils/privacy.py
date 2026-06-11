"""
Xovis SDK - AI Privacy Engine

Operates at the DX (Developer Experience) boundary.
Provides a high-performance, recursive sanitization utility for scrubbing
sensitive fields from Pydantic models before they are exposed to LLMs.
"""

import hashlib
import logging
import uuid
from typing import Any, TypeVar, Union

from pydantic import BaseModel

T = TypeVar("T", bound=Union[BaseModel, list[BaseModel]])

logger = logging.getLogger(__name__)


class AIPrivacySession:
    """
    Session-bound Privacy Engine for two-way identifier mapping.

    Maintains a cryptographic mapping between real sensitive values (e.g., MAC addresses)
    and short, stable hashes used by the LLM.
    """

    def __init__(self):
        # Unique salt per session to prevent rainbow table attacks
        self._salt = uuid.uuid4().hex.encode()
        self._hash_to_real: dict[str, str] = {}
        self._real_to_hash: dict[str, str] = {}

    def _generate_hash(self, prefix: str, real_value: str) -> str:
        """Generates a stable, session-bound hash for a given value."""
        if real_value in self._real_to_hash:
            return self._real_to_hash[real_value]

        # Short 8-char hash for LLM context efficiency
        digest = hashlib.sha256(self._salt + real_value.encode()).hexdigest()[:8]
        safe_hash = f"{prefix}_{digest}"

        self._real_to_hash[real_value] = safe_hash
        self._hash_to_real[safe_hash] = real_value
        return safe_hash

    def restore(self, data: Any) -> Any:
        """
        The Reverse Pass: Restores real values from LLM-provided hashes.
        """
        if isinstance(data, list):
            return [self.restore(item) for item in data]
        if isinstance(data, dict):
            return {k: self.restore(v) for k, v in data.items()}
        if isinstance(data, str) and data in self._hash_to_real:
            return self._hash_to_real[data]

        return data

    def deanonymize_text(self, text: str) -> str:
        """
        Native Post-Processing: Replaces all LLM-facing hashes in a text
        block with their real plaintext values.
        """
        if not text:
            return text

        for hashed_val, real_val in self._hash_to_real.items():
            text = text.replace(hashed_val, str(real_val))

        return text

    def sanitize(self, data: Any) -> Any:
        """
        The Forward Pass: Scrubs or hashes fields based on Pydantic metadata.
        """
        if isinstance(data, (str, int, float, bool)) or data is None:
            return data

        if isinstance(data, list):
            return [self.sanitize(item) for item in data]

        if isinstance(data, BaseModel):
            return self._sanitize_model(data)

        if isinstance(data, dict):
            # Optimize: Only recurse if the dict contains potentially sensitive values
            return {k: self.sanitize(v) for k, v in data.items()}

        return data

    def _sanitize_model(self, model: BaseModel) -> dict[str, Any]:
        """
        Extracts and sanitizes a single Pydantic model based on metadata.
        """
        # Optimize: exclude_unset=True reduces the dictionary size significantly
        raw_dict = model.model_dump(mode="json", by_alias=True, exclude_unset=True)
        sanitized = {}

        for field_name, field_info in model.__class__.model_fields.items():
            alias = field_info.alias or field_name
            if alias not in raw_dict:
                continue

            value = raw_dict[alias]
            extra = field_info.json_schema_extra or {}
            privacy_rule = extra.get("ai_privacy") if isinstance(extra, dict) else None

            if privacy_rule == "BLOCK":
                continue

            if privacy_rule == "HASH" and (isinstance(value, str) or (isinstance(value, dict) and "root" in value)):
                # Handle RootModels or nested dicts that might be hashed
                str_val = str(value["root"]) if isinstance(value, dict) and "root" in value else str(value)
                prefix = alias.split("_")[0].capitalize()
                sanitized[alias] = self._generate_hash(prefix, str_val)
            else:
                sanitized[alias] = self.sanitize(value)

        return sanitized

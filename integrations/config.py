import os
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv()


@dataclass
class IntegrationConfig:
    kkb_base_url: str = field(
        default_factory=lambda: os.getenv("KKB_BASE_URL", "https://api.kkb.com.tr/v2")
    )
    kkb_client_id: str | None = field(
        default_factory=lambda: os.getenv("KKB_CLIENT_ID")
    )
    kkb_client_secret: str | None = field(
        default_factory=lambda: os.getenv("KKB_CLIENT_SECRET")
    )
    kkb_member_code: str | None = field(
        default_factory=lambda: os.getenv("KKB_MEMBER_CODE")
    )

    masak_base_url: str = field(
        default_factory=lambda: os.getenv("MASAK_BASE_URL", "https://api.masak.gov.tr/v1")
    )
    masak_api_key: str | None = field(
        default_factory=lambda: os.getenv("MASAK_API_KEY")
    )
    masak_institution_code: str | None = field(
        default_factory=lambda: os.getenv("MASAK_INSTITUTION_CODE")
    )

    boa_base_url: str = field(
        default_factory=lambda: os.getenv("BOA_BASE_URL", "http://localhost:8080/api")
    )
    boa_username: str | None = field(
        default_factory=lambda: os.getenv("BOA_USERNAME")
    )
    boa_password: str | None = field(
        default_factory=lambda: os.getenv("BOA_PASSWORD")
    )
    boa_api_key: str | None = field(
        default_factory=lambda: os.getenv("BOA_API_KEY")
    )

    tcmb_username: str | None = field(
        default_factory=lambda: os.getenv("TCMB_USERNAME")
    )
    tcmb_password: str | None = field(
        default_factory=lambda: os.getenv("TCMB_PASSWORD")
    )
    tcmb_api_key: str | None = field(
        default_factory=lambda: os.getenv("TCMB_API_KEY")
    )

    swift_base_url: str = field(
        default_factory=lambda: os.getenv("SWIFT_BASE_URL", "https://api.swiftnet.sipn.swift.com/swift-preval-pilot/v3")
    )
    swift_consumer_key: str | None = field(
        default_factory=lambda: os.getenv("SWIFT_CONSUMER_KEY")
    )
    swift_consumer_secret: str | None = field(
        default_factory=lambda: os.getenv("SWIFT_CONSUMER_SECRET")
    )
    swift_bic: str = field(
        default_factory=lambda: os.getenv("SWIFT_BIC", "BANKTRISBXXX")
    )

    http_timeout: float = field(
        default_factory=lambda: float(os.getenv("INTEGRATION_HTTP_TIMEOUT", "15.0"))
    )
    http_retries: int = field(
        default_factory=lambda: int(os.getenv("INTEGRATION_HTTP_RETRIES", "3"))
    )
    use_mocks: bool = field(
        default_factory=lambda: os.getenv("USE_MOCK_INTEGRATIONS", "true").lower() == "true"
    )

    def is_kkb_configured(self) -> bool:
        return bool(self.kkb_client_id and self.kkb_client_secret)

    def is_masak_configured(self) -> bool:
        return bool(self.masak_api_key and self.masak_institution_code)

    def is_boa_configured(self) -> bool:
        return bool(self.boa_username and self.boa_password)

    def is_tcmb_configured(self) -> bool:
        return bool(self.tcmb_username and self.tcmb_password)

    def is_swift_configured(self) -> bool:
        return bool(self.swift_consumer_key and self.swift_consumer_secret)

    def summary(self) -> dict:
        return {
            "kkb": "LIVE" if self.is_kkb_configured() else "MOCK",
            "masak": "LIVE" if self.is_masak_configured() else "MOCK",
            "boa": "LIVE" if self.is_boa_configured() else "MOCK",
            "tcmb": "LIVE" if self.is_tcmb_configured() else "MOCK",
            "swift": "LIVE" if self.is_swift_configured() else "MOCK",
        }


_config: IntegrationConfig | None = None


def get_config() -> IntegrationConfig:
    global _config
    if _config is None:
        _config = IntegrationConfig()
    return _config

"""UserIdentity model — links app users to external IdP subjects."""

import uuid

from sqlalchemy import Column, DateTime, ForeignKey, JSON, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.utils.datetime_utils import utc_now_lambda


class UserIdentity(Base):
    """Links a user account to one or more external identity-provider subjects.

    A single user can log in via multiple providers (built-in, Cognito, Google, etc.).
    Each row represents one (provider, subject) pair, e.g.::

        provider="cognito", provider_subject="us-east-1_XXXX|abc123"
        provider="google",  provider_subject="108542397012345678901"
        provider="builtin", provider_subject="<user_uuid>"
    """

    __tablename__ = "user_identities"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Provider name: 'builtin', 'cognito', 'keycloak', 'okta', 'google'
    provider = Column(String(50), nullable=False)
    # The IdP's stable subject identifier (sub claim)
    provider_subject = Column(String(255), nullable=False)
    # Email as seen by the IdP (may differ from the app's canonical email)
    provider_email = Column(String(255), nullable=True)
    # Last known group memberships from the IdP (stored as JSON array of strings)
    provider_groups = Column(JSON, nullable=False, default=list)

    linked_at = Column(DateTime, default=utc_now_lambda, nullable=False)
    last_seen_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", back_populates="identities")

    __table_args__ = (
        UniqueConstraint(
            "provider",
            "provider_subject",
            name="uq_user_identities_provider_subject",
        ),
    )

    def __repr__(self) -> str:
        return f"<UserIdentity provider={self.provider!r} subject={self.provider_subject!r}>"

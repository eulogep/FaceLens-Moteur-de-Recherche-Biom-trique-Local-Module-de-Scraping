import pytest
from pydantic import ValidationError

from app.routes.insta import InstagramProfileRequest
from spider.insta.service import InstagramIndexer


def test_retry_error_with_429_has_explicit_message():
    message = InstagramIndexer._exception_message(
        RuntimeError("too many 429 error responses")
    )
    assert message == (
        "Instagram public a répondu 429; job arrêté sans nouvelle tentative."
    )


def test_invalid_username_is_rejected_before_background_job():
    with pytest.raises(ValidationError):
        InstagramProfileRequest(username="../session")

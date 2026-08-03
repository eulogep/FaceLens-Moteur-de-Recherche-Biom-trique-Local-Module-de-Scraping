"""Small adapter around instagrapi's anonymous GraphQL methods."""

from __future__ import annotations

from typing import Any

from instagrapi import Client


class InstagramPublicClient:
    """Expose explicitly public-only operations used by FaceLens.

    instagrapi 2.16.25 names these methods ``*_gql``.  Keeping the
    ``*_public`` names in this adapter makes it impossible for this module to
    silently fall back to a private/mobile endpoint.
    """

    def __init__(self, client: Client | None = None) -> None:
        self._client = client or Client()
        self._client.public_request_retries_count = 1

    def user_info_by_username_public(self, username: str) -> Any:
        return self._client.user_info_by_username_gql(username)

    def user_medias_public(self, user_id: str, amount: int) -> list[Any]:
        return self._client.user_medias_gql(user_id, amount=amount, sleep=0)

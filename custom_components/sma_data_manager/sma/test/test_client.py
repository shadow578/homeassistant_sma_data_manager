"""unit test for SMA client implementation"""
import mock
import pytest
from urllib.parse import quote

from ..client import LOGIN_RESULT_ALREADY_LOGGED_IN, LOGIN_RESULT_NEW_TOKEN, LOGIN_RESULT_TOKEN_REFRESHED, SMAApiClient

from .http_response_mock import ClientResponseMock


@pytest.mark.asyncio
async def test_client_auth():
    """"""

    # mock for make_request
    did_get_token = False
    did_refresh_token = False
    did_delete_token = False
    async def make_request_mock(method: str, endpoint: str, data: dict, headers: dict, as_json: bool):
        """mock for make_request"""
        nonlocal did_get_token
        nonlocal did_refresh_token
        nonlocal did_delete_token

        # POST /api/v1/token (login, NEW and REFRESH)
        if method == "POST" and endpoint == "token":
            assert data is not None
            assert data["grant_type"] == "password" or data["grant_type"] == "refresh_token"

            # check common headers:
            # origin headers
            assert headers["Origin"] == "http://sma.local/api/v1"
            assert headers["Host"] == "sma.local"

            # content type headers
            assert headers["Content-Type"] == "application/x-www-form-urlencoded"
            assert headers["Accept"] == "application/json"


            if data["grant_type"] == "password":
                # check data
                assert data["username"] == "test"
                assert data["password"] == "test123"

                # should use form data instead of json
                assert as_json is False

                # return mock response
                did_get_token = True
                return ClientResponseMock(
                    data={
                        "access_token": "acc-token-1",
                        "refresh_token": "ref-token-1",
                        "token_type": "Bearer",
                        "expires_in": 30, # ultra short-lived to test token refresh
                    },
                    cookies=[
                        ("JSESSIONID", "session-id"),
                    ]
                )
            elif data["grant_type"] == "refresh_token":
                # token refresh requires session cookie
                assert headers["Cookie"] == "JSESSIONID=session-id"

                # check data
                assert data["refresh_token"] == "ref-token-1"

                # should use form data instead of json
                assert as_json is False

                # return mock response
                did_refresh_token = True
                return ClientResponseMock(
                    data={
                        "access_token": "acc-token-2",
                        "refresh_token": "ref-token-2",
                        "token_type": "Bearer",
                        "expires_in": 3600, # long-lived
                    },
                    cookies=[
                        ("JSESSIONID", "session-id"),
                    ]
                )

        # DELETE /api/v1/token (logout)
        if method == "DELETE":
            assert endpoint == f"refreshtoken?refreshToken={quote('ref-token-2')}"
            did_delete_token = True

            return ClientResponseMock(
                data={},
                cookies=[]
            )

        raise Exception(f"unexpected endpoint: {endpoint}")

    # create the client
    sma = SMAApiClient(
        host="sma.local",
        username="test",
        password="test123",
        session=mock.MagicMock(),
        use_ssl=False,
    )

    # patch make_request
    with mock.patch.object(sma, "make_request", wraps=make_request_mock):
        # login should get a new token
        assert (await sma.login()) == LOGIN_RESULT_NEW_TOKEN
        assert did_get_token is True
        assert did_refresh_token is False
        assert did_delete_token is False

        did_get_token = False

        # token is super short-lived, so another login should refresh it
        assert (await sma.login()) == LOGIN_RESULT_TOKEN_REFRESHED
        assert did_get_token is False
        assert did_refresh_token is True
        assert did_delete_token is False

        did_refresh_token = False

        # now the token is long-lived, so another login should do nothing
        assert (await sma.login()) == LOGIN_RESULT_ALREADY_LOGGED_IN
        assert did_get_token is False
        assert did_refresh_token is False
        assert did_delete_token is False

        # logout
        # TODO: logout test does not work...
        #await sma.logout()
        #assert did_delete_token is True




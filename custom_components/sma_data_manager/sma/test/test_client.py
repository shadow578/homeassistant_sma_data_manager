"""unit test for SMA client implementation"""
import mock
import pytest
from urllib.parse import quote

from ..client import LOGIN_RESULT_ALREADY_LOGGED_IN, LOGIN_RESULT_NEW_TOKEN, LOGIN_RESULT_TOKEN_REFRESHED, SMAApiClient

from .http_response_mock import ClientResponseMock


@pytest.mark.asyncio
async def test_client_auth():
    """test client login / logout methods"""

    # mock for make_request
    did_get_token = False
    did_refresh_token = False
    did_delete_token = False
    async def make_request_mock(method: str, endpoint: str, data: dict|None = None, headers: dict|None = None, as_json: bool = True):
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



@pytest.mark.asyncio
async def test_client_get_all_components():
    """test SMAApiClient.get_all_components"""

    # mock for make_request
    did_get_root = False
    did_get_children = False
    did_get_inv1_info = False
    did_get_inv2_info = False
    async def make_request_mock(method: str, endpoint: str, data: dict|None = None, headers: dict|None = None, as_json: bool = True):
        """mock for make_request"""
        nonlocal did_get_root
        nonlocal did_get_children
        nonlocal did_get_inv1_info
        nonlocal did_get_inv2_info

        # required for login
        if method == "POST" and endpoint == "token":
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


        # GET /api/v1/navigation (component discovery)
        if method == "GET" and endpoint.startswith("navigation"):
            # check common headers
            # origin headers
            assert headers["Origin"] == "http://sma.local/api/v1"
            assert headers["Host"] == "sma.local"
            # session cookie
            assert headers["Cookie"] == "JSESSIONID=session-id"
            # auth header
            assert headers["Authorization"] == "Bearer acc-token-1"
            # content type headers
            assert headers["Accept"] == "application/json"

            # body is json
            assert as_json is True

            # ROOT component
            if endpoint == "navigation":
                did_get_root = True
                return ClientResponseMock(
                    data=[
                        {
                            "componentId": "plant0",
                            "componentType": "Plant",
                            "name": "The Plant",
                        },
                    ]
                )

            # children of ROOT component
            if endpoint == f"navigation?parentId={quote('plant0')}":
                did_get_children = True
                return ClientResponseMock(
                    data=[
                        {
                            "componentId": "inv1",
                            "componentType": "Inverter",
                            "name": "The 1st Inverter",
                        },
                        {
                            "componentId": "inv2",
                            "componentType": "Inverter",
                            "name": "The 2nd Inverter",
                        },
                    ]
                )

        # GET /api/v1/widgets/deviceInfo (component extra info)
        if method == "GET" and endpoint.startswith("widgets/deviceinfo"):
            # check common headers
            # origin headers
            assert headers["Origin"] == "http://sma.local/api/v1"
            assert headers["Host"] == "sma.local"
            # session cookie
            assert headers["Cookie"] == "JSESSIONID=session-id"
            # auth header
            assert headers["Authorization"] == "Bearer acc-token-1"
            # content type headers
            assert headers["Accept"] == "application/json"

            # body is json
            assert as_json is True

            # inv1
            if endpoint == f"widgets/deviceinfo?deviceId=inv1":
                did_get_inv1_info = True
                return ClientResponseMock(
                    data={
                        "serial": "inv1-serial",
                        "deviceInfoFeatures": [
                            {
                                "infoWidgetType": "FirmwareVersion",
                                "value": "inv1-firmware",
                            }
                        ]
                    }
                )

            # inv2
            if endpoint == f"widgets/deviceinfo?deviceId=inv2":
                did_get_inv2_info = True
                return ClientResponseMock(
                    data={
                        "serial": "inv2-serial",
                        "deviceInfoFeatures": [
                            {
                                "infoWidgetType": "FirmwareVersion",
                                "value": "inv2-firmware",
                            }
                        ]
                    }
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
        assert (await sma.login()) == LOGIN_RESULT_NEW_TOKEN

        # get all components
        all_components = await sma.get_all_components()
        assert did_get_root is True
        assert did_get_children is True
        assert did_get_inv1_info is True
        assert did_get_inv2_info is True


        assert len(all_components) == 3

        # Plant
        assert all_components[0].component_id == "plant0"
        assert all_components[0].component_type == "Plant"
        assert all_components[0].name == "The Plant"

        # inv1
        assert all_components[1].component_id == "inv1"
        assert all_components[1].component_type == "Inverter"
        assert all_components[1].name == "The 1st Inverter"
        assert all_components[1].serial_number == "inv1-serial"
        assert all_components[1].firmware_version == "inv1-firmware"

        # inv2
        assert all_components[2].component_id == "inv2"
        assert all_components[2].component_type == "Inverter"
        assert all_components[2].name == "The 2nd Inverter"
        assert all_components[2].serial_number == "inv2-serial"
        assert all_components[2].firmware_version == "inv2-firmware"





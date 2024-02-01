class CookieMock:
        value: str

        def __init__(self, value: str):
            self.value = value

class CookieJarMock:

    _cookies: list[tuple[str, CookieMock]]

    def __init__(self, cookies: list[tuple[str, CookieMock]]):
        self._cookies = cookies

    def get(self, name: str) -> CookieMock:
        for cookie_name, cookie in self._cookies:
            if cookie_name == name:
                return cookie

        raise KeyError(f"cookie {name} not found")

class ClientResponseMock:

    data: any
    cookies: CookieJarMock

    def __init__(self, data: any, cookies: list[tuple[str, str]] = []):
        self.data = data
        self.cookies = CookieJarMock(
            cookies=[(name, CookieMock(value=value)) for name, value in cookies]
        )

    async def json(self) -> any:
        return self.data


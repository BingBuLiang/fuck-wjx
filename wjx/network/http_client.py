"""基于 httpx 的统一 HTTP 客户端（后台异步 + 同步封装）。"""
from __future__ import annotations

import asyncio
import atexit
import threading
from dataclasses import dataclass
from typing import Any, Dict, Iterator, Optional, Tuple, Union
from urllib.parse import urlsplit

import httpx


_MAX_CONCURRENT_REQUESTS = 6
_CLIENT_LIMITS = httpx.Limits(max_connections=20, max_keepalive_connections=10)


class _Exceptions:
    """兼容旧代码的异常命名。"""

    Timeout = httpx.TimeoutException
    ConnectTimeout = httpx.ConnectTimeout
    ReadTimeout = httpx.ReadTimeout
    ConnectionError = httpx.ConnectError
    HTTPError = httpx.HTTPStatusError
    RequestException = httpx.HTTPError


exceptions = _Exceptions()
RequestException = httpx.HTTPError


@dataclass(frozen=True)
class _ClientKey:
    proxy: Optional[str]
    verify: Union[bool, str]
    follow_redirects: bool
    trust_env: bool


class _StreamResponse:
    """把 httpx 异步流响应包装成同步 iter_content 接口。"""

    def __init__(self, response: httpx.Response, stream_ctx: Any):
        self._response = response
        self._stream_ctx = stream_ctx
        self._closed = False

    @property
    def status_code(self) -> int:
        return self._response.status_code

    @property
    def headers(self) -> httpx.Headers:
        return self._response.headers

    @property
    def text(self) -> str:
        return self._response.text

    @property
    def content(self) -> bytes:
        return self._response.content

    def json(self) -> Any:
        return self._response.json()

    def raise_for_status(self) -> None:
        self._response.raise_for_status()

    def iter_content(self, chunk_size: int = 8192) -> Iterator[bytes]:
        aiter = self._response.aiter_bytes(chunk_size=chunk_size)
        try:
            while True:
                try:
                    chunk = _loop_runner.run(aiter.__anext__())
                except StopAsyncIteration:
                    break
                if chunk:
                    yield chunk
        finally:
            self.close()

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        try:
            _loop_runner.run(self._stream_ctx.__aexit__(None, None, None))
        except Exception:
            pass

    def __del__(self) -> None:  # pragma: no cover
        self.close()


class _AsyncLoopRunner:
    """后台事件循环线程，承载所有异步 HTTP 调用。"""

    def __init__(self):
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._run_loop, daemon=True, name="HttpxAsyncLoop")
        self._thread.start()
        self._clients: Dict[_ClientKey, httpx.AsyncClient] = {}
        self._clients_lock = threading.Lock()
        self._semaphore: Optional[asyncio.Semaphore] = None

    def _run_loop(self) -> None:
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()

    def run(self, coro):
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return future.result()

    async def _get_client(
        self,
        proxy: Optional[str],
        verify: Union[bool, str],
        follow_redirects: bool,
        trust_env: bool,
    ) -> httpx.AsyncClient:
        key = _ClientKey(
            proxy=proxy,
            verify=verify,
            follow_redirects=follow_redirects,
            trust_env=trust_env,
        )
        with self._clients_lock:
            client = self._clients.get(key)
            if client is not None:
                return client
            client = httpx.AsyncClient(
                timeout=None,
                verify=verify,
                proxy=proxy,
                follow_redirects=follow_redirects,
                trust_env=trust_env,
                limits=_CLIENT_LIMITS,
            )
            self._clients[key] = client
            return client

    async def request(
        self,
        method: str,
        url: str,
        *,
        params: Any = None,
        data: Any = None,
        headers: Any = None,
        cookies: Any = None,
        files: Any = None,
        auth: Any = None,
        timeout: Any = None,
        allow_redirects: bool = True,
        proxies: Any = None,
        stream: bool = False,
        verify: Union[bool, str] = True,
        json: Any = None,
    ) -> Union[httpx.Response, _StreamResponse]:
        proxy, trust_env = _resolve_proxy(proxies, url)
        client = await self._get_client(
            proxy=proxy,
            verify=verify,
            follow_redirects=allow_redirects,
            trust_env=trust_env,
        )
        normalized_timeout = _normalize_timeout(timeout)

        if self._semaphore is None:
            self._semaphore = asyncio.Semaphore(_MAX_CONCURRENT_REQUESTS)
        async with self._semaphore:
            if stream:
                stream_ctx = client.stream(
                    method=method,
                    url=url,
                    params=params,
                    data=data,
                    headers=headers,
                    cookies=cookies,
                    files=files,
                    auth=auth,
                    json=json,
                    timeout=normalized_timeout,
                )
                response = await stream_ctx.__aenter__()
                return _StreamResponse(response, stream_ctx)
            response = await client.request(
                method=method,
                url=url,
                params=params,
                data=data,
                headers=headers,
                cookies=cookies,
                files=files,
                auth=auth,
                json=json,
                timeout=normalized_timeout,
            )
            return response

    async def close(self) -> None:
        with self._clients_lock:
            clients = list(self._clients.values())
            self._clients.clear()
        for client in clients:
            try:
                await client.aclose()
            except Exception:
                pass


def _resolve_proxy(proxies: Any, url: str) -> Tuple[Optional[str], bool]:
    """把 requests 风格 proxies 参数映射到 httpx。"""
    if proxies is None:
        return None, True
    if proxies == {}:
        return None, False
    if isinstance(proxies, str):
        return proxies, False
    if isinstance(proxies, dict):
        scheme = urlsplit(url).scheme.lower()
        http_proxy = proxies.get("http") or proxies.get("http://")
        https_proxy = proxies.get("https") or proxies.get("https://")
        if not http_proxy and not https_proxy:
            # 传了 dict 但为空值，明确禁用环境代理
            return None, False
        if scheme == "https":
            return str(https_proxy or http_proxy), False
        return str(http_proxy or https_proxy), False
    return None, False


def _normalize_timeout(timeout: Any) -> Any:
    """兼容 requests 的 timeout 形态。"""
    if timeout is None:
        return None
    if isinstance(timeout, (int, float)):
        return float(timeout)
    if isinstance(timeout, tuple):
        if len(timeout) == 2:
            connect, read = timeout
            connect_val = float(connect) if connect is not None else None
            read_val = float(read) if read is not None else None
            return httpx.Timeout(connect=connect_val, read=read_val, write=read_val, pool=connect_val)
        if len(timeout) == 4:
            connect, read, write, pool = timeout
            return httpx.Timeout(
                connect=float(connect) if connect is not None else None,
                read=float(read) if read is not None else None,
                write=float(write) if write is not None else None,
                pool=float(pool) if pool is not None else None,
            )
    return timeout


_loop_runner = _AsyncLoopRunner()


def close() -> None:
    """关闭异步客户端池。"""
    try:
        _loop_runner.run(_loop_runner.close())
    except Exception:
        pass


atexit.register(close)


def request(method: str, url: str, **kwargs: Any):
    return _loop_runner.run(_loop_runner.request(method, url, **kwargs))


def get(url: str, **kwargs: Any):
    return request("GET", url, **kwargs)


def post(url: str, **kwargs: Any):
    return request("POST", url, **kwargs)


def put(url: str, **kwargs: Any):
    return request("PUT", url, **kwargs)


def delete(url: str, **kwargs: Any):
    return request("DELETE", url, **kwargs)

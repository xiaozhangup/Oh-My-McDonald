"""User-triggered, read-only Streamable HTTP MCP transport."""
import json
import os
import tomllib
import urllib.error
import urllib.request
from pathlib import Path

TOOLS = frozenset(('query-nearby-stores', 'query-meals', 'query-meal-detail',
                   'query-my-coupons', 'query-store-coupons', 'calculate-price',
                   'campaign-calendar', 'list-nutrition-foods', 'order-list'))


class McdError(Exception):
    pass


def decode_rpc(raw):
    text = raw.decode('utf-8')
    if text.lstrip().startswith('{'):
        return json.loads(text)
    # SSE messages may contain multiple data lines and notifications.
    for event in text.replace('\r\n', '\n').split('\n\n'):
        lines = [line[5:].lstrip() for line in event.splitlines() if line.startswith('data:')]
        if lines:
            message = json.loads('\n'.join(lines))
            if 'result' in message or 'error' in message:
                return message
    raise McdError('MCP 返回中没有 RPC 结果')


class Client:
    def __init__(self, config=None):
        token = os.environ.get('MCD_MCP_TOKEN', '')
        if not token and config:
            server = tomllib.loads(Path(config).expanduser().read_text())['mcp_servers']['mcd-mcp']
            header = server['http_headers']['Authorization']
            if not header.startswith('Bearer '):
                raise McdError('配置中的 Authorization 需要 Bearer 前缀')
            token = header[7:]
        if not token or token == 'REPLACE_WITH_MCD_MCP_TOKEN':
            raise McdError('请配置 MCD_MCP_TOKEN，或通过 --codex-config 指定本机配置')
        self.token, self.session, self.counter = token, None, 0
        init = self.request('initialize', {'protocolVersion': '2025-06-18',
                            'capabilities': {}, 'clientInfo': {'name': 'oh-my-mcdonald', 'version': '0.1.0'}})
        self.protocol = init['protocolVersion']
        self.request('notifications/initialized', {}, notification=True)

    def request(self, method, params, notification=False):
        self.counter += 1
        payload = {'jsonrpc': '2.0', 'method': method, 'params': params}
        if not notification:
            payload['id'] = self.counter
        headers = {'Authorization': 'Bearer ' + self.token, 'Content-Type': 'application/json',
                   'Accept': 'application/json, text/event-stream'}
        if self.session:
            headers['Mcp-Session-Id'] = self.session
        if hasattr(self, 'protocol'):
            headers['MCP-Protocol-Version'] = self.protocol
        request = urllib.request.Request('https://mcp.mcd.cn', json.dumps(payload).encode(), headers)
        try:
            with urllib.request.urlopen(request, timeout=40) as response:
                self.session = response.headers.get('Mcp-Session-Id', self.session)
                raw = response.read()
        except urllib.error.HTTPError as exc:
            raise McdError(f'MCP HTTP {exc.code}，本次查询已停止') from None
        except (urllib.error.URLError, TimeoutError):
            raise McdError('MCP 连接失败或超时，本次查询已停止') from None
        if notification:
            return None
        message = decode_rpc(raw)
        if 'error' in message:
            raise McdError('MCP RPC 请求失败')
        return message['result']

    def call(self, name, arguments):
        if name not in TOOLS:
            raise McdError('该工具不在只读能力清单内')
        result = self.request('tools/call', {'name': name, 'arguments': arguments})
        if result.get('isError'):
            raise McdError(f'{name} 执行失败')
        data = result.get('structuredContent')
        if data is None:
            # Some MCP hosts serialize the business object as a text block.
            for block in result.get('content', []):
                if block.get('type') == 'text':
                    try:
                        value = json.loads(block['text'])
                    except json.JSONDecodeError:
                        continue
                    if isinstance(value, dict) and 'success' in value:
                        data = value
                        break
        if not isinstance(data, dict) or data.get('success') is not True:
            raise McdError(f'{name} 未返回成功的业务数据')
        return data['data']

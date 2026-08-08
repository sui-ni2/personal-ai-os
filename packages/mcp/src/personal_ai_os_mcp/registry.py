from __future__ import annotations

from urllib.parse import urlsplit

from .connectors import ConnectorDefinition, ConnectorTransport
from .gateway import MCPInvocationError
from .transports import ExternalMCPTransport, HTTPMCPTransport, StdioMCPTransport


class ConnectorRegistry:
    def __init__(self, stdio_commands: dict[str, tuple[str, ...]] | None = None) -> None:
        self._stdio_commands = dict(stdio_commands or {})

    @property
    def stdio_command_aliases(self) -> list[str]:
        return sorted(self._stdio_commands)

    def validate(self, connector: ConnectorDefinition) -> None:
        if connector.transport == ConnectorTransport.HTTP:
            if not connector.endpoint:
                raise MCPInvocationError("HTTP connector requires an endpoint")
            parsed = urlsplit(connector.endpoint)
            if parsed.scheme not in {"http", "https"} or not parsed.hostname:
                raise MCPInvocationError("HTTP connector endpoint must use http or https")
            if parsed.username or parsed.password:
                raise MCPInvocationError("HTTP connector endpoint must not contain credentials")
        elif connector.transport == ConnectorTransport.STDIO:
            if not connector.command or connector.command not in self._stdio_commands:
                raise MCPInvocationError("stdio connector command is not allowlisted")
        else:
            raise MCPInvocationError("Unsupported MCP connector transport")

    def create_transport(self, connector: ConnectorDefinition) -> ExternalMCPTransport:
        self.validate(connector)
        if connector.transport == ConnectorTransport.HTTP:
            assert connector.endpoint is not None
            return HTTPMCPTransport(connector.endpoint, connector.timeout_seconds)
        assert connector.command is not None
        return StdioMCPTransport(
            self._stdio_commands[connector.command], connector.timeout_seconds
        )

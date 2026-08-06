# dnscrypt-proxy

Encrypted upstream DNS resolution (DNS-over-HTTPS via Cloudflare) for the
Raspberry Pi, socket-activated by systemd so dnscrypt-proxy only starts
on demand rather than running as an always-on daemon.

## Deployment paths

| File                  | Target path                                              |
|------------------------|----------------------------------------------------------|
| `dnscrypt-proxy.toml`  | `/etc/dnscrypt-proxy/dnscrypt-proxy.toml`                 |
| `override.conf`        | `/etc/systemd/system/dnscrypt-proxy.socket.d/override.conf` |

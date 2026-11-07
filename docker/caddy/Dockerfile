# Caddy edge con el plugin DNS de Cloudflare: el wildcard *.dominio se emite
# por DNS-01 (ACME HTTP-01 no puede emitir wildcards) y se renueva solo.
# Mismo proveedor DNS que certbot (docker/certbot/cloudflare.ini).
FROM caddy:2-builder AS builder
# x/net v0.60.0 (la que resuelve caddy 2.11.x) tiene CVE-2026-78661 (DoS en
# x/net/html): --replace fuerza v0.62.0 hasta que upstream actualice go.mod.
RUN xcaddy build --with github.com/caddy-dns/cloudflare \
    --replace golang.org/x/net=golang.org/x/net@v0.62.0

FROM caddy:2
COPY --from=builder /usr/bin/caddy /usr/bin/caddy

# UID arbitrario: la imagen oficial ya trae /usr/bin/caddy con
# cap_net_bind_service y /data/caddy + /config/caddy en 1777, y Docker
# >=20.10 deja bindear 80/443 a cualquier usuario
# (net.ipv4.ip_unprivileged_port_start=0 en el netns del container).
# Sin root no hay escape por setuid ni escritura fuera de los volúmenes.
RUN addgroup -S -g 1001 caddy && adduser -S -D -H -u 1001 -G caddy -s /sbin/nologin caddy
USER caddy

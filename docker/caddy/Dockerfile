# Caddy edge con el plugin DNS de Cloudflare: el wildcard *.dominio se emite
# por DNS-01 (ACME HTTP-01 no puede emitir wildcards) y se renueva solo.
# Mismo proveedor DNS que certbot (docker/certbot/cloudflare.ini).
# Bases y plugin pineados por digest/versión: el edge es el terminador
# TLS de todo el tráfico y un `latest` mutable del plugin DNS-01 o de la
# imagen base era un build input no revisado (infra:caddy-xcaddy-unpinned).
# Para actualizar: bump explícito de los digests/versiones en este archivo.
FROM caddy:2-builder@sha256:6350162b3889ca32600b3c699c61572fa0eb3ad6b2a51874f19b158a7df77511 AS builder
# x/net v0.60.0 (la que resuelve caddy 2.11.x) tiene CVE-2026-78661 (DoS en
# x/net/html): --replace fuerza v0.62.0 hasta que upstream actualice go.mod.
# Versión de Caddy pineada como arg posicional de xcaddy: sin ella el build
# tomaba `latest` y el binario del edge flotaba entre rebuilds.
RUN xcaddy build v2.11.4 --with github.com/caddy-dns/cloudflare@v0.2.4 \
    --replace golang.org/x/net=golang.org/x/net@v0.62.0

FROM caddy:2@sha256:4e2425f6009577e7c651010f16679c28f7d12df3e7b1914f941a7a3370746b3c
COPY --from=builder /usr/bin/caddy /usr/bin/caddy

# UID arbitrario: la imagen oficial ya trae /usr/bin/caddy con
# cap_net_bind_service y /data/caddy + /config/caddy en 1777, y Docker
# >=20.10 deja bindear 80/443 a cualquier usuario
# (net.ipv4.ip_unprivileged_port_start=0 en el netns del container).
# Sin root no hay escape por setuid ni escritura fuera de los volúmenes.
RUN addgroup -S -g 1001 caddy && adduser -S -D -H -u 1001 -G caddy -s /sbin/nologin caddy
USER caddy

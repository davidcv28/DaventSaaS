# Caddy edge con el plugin DNS de Cloudflare: el wildcard *.dominio se emite
# por DNS-01 (ACME HTTP-01 no puede emitir wildcards) y se renueva solo.
# Mismo proveedor DNS que certbot (docker/certbot/cloudflare.ini).
FROM caddy:2-builder AS builder
RUN xcaddy build --with github.com/caddy-dns/cloudflare

FROM caddy:2
COPY --from=builder /usr/bin/caddy /usr/bin/caddy

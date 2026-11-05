# PHP + Python: Python is used for migration, launch and legacy password upgrade.
FROM php:8.3-cli-bookworm
RUN --mount=type=secret,id=proxy_ca \
    set -eu; \
    if [ -f /run/secrets/proxy_ca ]; then \
      printf 'Acquire::https::CaInfo "/run/secrets/proxy_ca";\n' > /etc/apt/apt.conf.d/99-evofit-ca; \
    fi; \
    apt-get update; \
    apt-get install -y --no-install-recommends python3; \
    docker-php-ext-install pdo_mysql; \
    rm -rf /var/lib/apt/lists/* /etc/apt/apt.conf.d/99-evofit-ca
WORKDIR /app
COPY . /app
EXPOSE 4173
CMD ["php", "-S", "0.0.0.0:4173", "-t", "static", "router.php"]

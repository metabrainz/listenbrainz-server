ARG GARAGE_VERSION=v2.3.0

FROM dxflrs/garage:${GARAGE_VERSION} AS upstream

# The upstream image is built FROM scratch and has no shell, so the (statically
# linked) binary is copied into an image that can run the provisioning script.
FROM alpine:3.24

COPY --from=upstream /garage /usr/local/bin/garage
COPY garage.toml /etc/garage.toml
COPY entrypoint.sh /usr/local/bin/entrypoint.sh

EXPOSE 3900 3901 3903

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]

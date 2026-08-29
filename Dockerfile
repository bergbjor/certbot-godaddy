ARG NPM_IMAGE=jc21/nginx-proxy-manager:latest
FROM ${NPM_IMAGE}

# NPM's GUI and backend read this provider registry. Installing only a Python
# package is not enough to make a provider selectable in the GUI.
COPY certbot-dns-godaddy-pat/ /opt/certbot-dns-godaddy-pat/
COPY docker/patch-dns-plugins.mjs /tmp/patch-dns-plugins.mjs

RUN /opt/certbot/bin/pip install --no-cache-dir /opt/certbot-dns-godaddy-pat \
    && node /tmp/patch-dns-plugins.mjs \
    && /opt/certbot/bin/certbot plugins 2>&1 | grep -q "dns-godaddy-pat" \
    && rm -f /tmp/patch-dns-plugins.mjs

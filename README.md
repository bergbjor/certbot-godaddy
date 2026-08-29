# GoDaddy PAT support for Nginx Proxy Manager

This project provides a custom [Nginx Proxy Manager](https://nginxproxymanager.com/)
image with a Certbot DNS-01 plugin for GoDaddy Personal Access Tokens (PATs).

It enables certificate requests and renewals from the NPM web interface,
including wildcard certificates such as `*.example.com`.

## How it works

NPM discovers DNS providers from its internal provider registry. The image in
this repository:

1. installs the `certbot-dns-godaddy-pat` plugin into NPM's Certbot environment;
2. registers **GoDaddy (PAT)** in NPM's DNS provider list;
3. lets the standard NPM certificate workflow manage installation, credentials,
   renewal, and cleanup.

The PAT is entered through the NPM UI. No credentials file needs to be created
or mounted on the Docker host.

## Requirements

- Docker Engine and Docker Compose;
- a GoDaddy-managed DNS zone;
- a GoDaddy **Production** PAT with permission to read and write domain DNS;
- ports 80, 81, and 443 available, unless you change the port mappings.

Create a token at the [GoDaddy Developer Portal](https://developer.godaddy.com/keys).
Never commit a real token to this repository. If a token has been exposed,
revoke it and create a new one.

## Installation

Copy `.env.example` to `.env` and adjust the values for the host running NPM:

```bash
cp .env.example .env
```

The `.env` file controls the image, timezone, host ports, persistent bind
mounts, external network name, and static container IP. It is ignored
by Git because it contains environment-specific settings. The two persistent
mounts are important: `/data` contains NPM's database and configuration,
while `/etc/letsencrypt` contains certificates and ACME state.

At minimum, set these values in `.env`:

```dotenv
NPM_IMAGE=ghcr.io/your-org/your-npm-image:latest
NPM_DATA_DIR=/path/to/npm/data
NPM_LETSENCRYPT_DIR=/path/to/npm/letsencrypt
NPM_NETWORK_NAME=your_external_network
NPM_IPV4_ADDRESS=192.0.2.22
```

The remaining values have sensible defaults in `docker-compose.yml` and can
be changed when required.

Start or recreate NPM:

```bash
docker compose pull
docker compose up -d
```

The external Docker network configured by `NPM_NETWORK_NAME` must exist before
starting the stack. Create it once if necessary, using a subnet that matches
your `NPM_IPV4_ADDRESS`:

```bash
docker network create \
  --driver bridge \
  --subnet <network-subnet> \
  <network-name>
```

Use the same network name as `NPM_NETWORK_NAME`, and choose an
`NPM_IPV4_ADDRESS` inside that network's subnet.

If you do not need a fixed IP, remove `ipv4_address` from the service and
`NPM_IPV4_ADDRESS` from the Compose file. If you do not need an external
network, replace the network configuration with a regular Compose-managed
network.

## Request a certificate in the NPM UI

1. Open **SSL Certificates** → **Add Certificate** → **Let's Encrypt**.
2. Enter one or more domain names. For a wildcard certificate, include both
   the apex and wildcard names, for example `example.com` and `*.example.com`.
3. Enable **Use a DNS Challenge**.
4. Select **GoDaddy (PAT)** as the DNS provider.
5. Paste the following into **Credentials File Content**, replacing the value:

   ```ini
   dns_godaddy_pat_pat = YOUR_GODADDY_PRODUCTION_PAT
   ```

6. Choose a propagation delay, accept the Let's Encrypt terms, and save.

NPM stores the submitted credentials internally and writes the Certbot
credentials file with restrictive permissions. The same credentials are used
for automatic renewal; no host-side PAT file is required.

To use the certificate, edit a Proxy Host, open its **SSL** tab, select the
new certificate, and save.

## Troubleshooting

Check that the plugin is installed in the running container:

```bash
docker compose exec npm /opt/certbot/bin/certbot plugins
```

Follow NPM's logs while requesting or renewing a certificate:

```bash
docker compose logs -f npm
```

Common causes of failure:

- a Sandbox PAT was used instead of a Production PAT;
- the PAT cannot read and write DNS records;
- the domain's authoritative DNS is not hosted at GoDaddy;
- DNS propagation requires more time;
- the container is still running an older image. Run `docker compose pull` and
  `docker compose up -d --force-recreate`.

## Local development

Build the image locally instead of using GHCR:

```bash
docker build --pull -t npm-godaddy-pat:local .
```

Run the Python syntax check:

```bash
python3 -m compileall certbot-dns-godaddy-pat/certbot_dns_godaddy_pat
```

The base image can be selected explicitly:

```bash
docker build \
  --build-arg NPM_IMAGE=jc21/nginx-proxy-manager:<tag> \
  -t npm-godaddy-pat:local .
```

## Repository layout

```text
.
├── Dockerfile                         # Custom NPM image
├── docker-compose.yml                 # Example deployment
├── .env.example                       # Deployment configuration template
├── docker/patch-dns-plugins.mjs       # Registers the provider in NPM
└── certbot-dns-godaddy-pat/           # Certbot plugin
```

## License

The project is released under the Apache License 2.0.

import fs from "node:fs";

const provider = {
  credentials: "# GoDaddy Personal Access Token (Production)\n dns_godaddy_pat_pat = YOUR_GODADDY_PAT_HERE",
  dependencies: "",
  full_plugin_name: "dns-godaddy-pat",
  name: "GoDaddy (PAT)",
  package_name: "/opt/certbot-dns-godaddy-pat",
  version: "",
};

const candidates = [
  "/app/certbot/dns-plugins.json",
  "/app/backend/certbot/dns-plugins.json",
  "/app/global/certbot-dns-plugins.json",
];

let patched = 0;
for (const filename of candidates) {
  if (!fs.existsSync(filename)) continue;
  const plugins = JSON.parse(fs.readFileSync(filename, "utf8"));
  plugins["godaddy-pat"] = provider;
  fs.writeFileSync(filename, `${JSON.stringify(plugins, null, 2)}\n`);
  console.log(`Registered GoDaddy PAT provider in ${filename}`);
  patched += 1;
}

if (patched === 0) {
  throw new Error("Could not find NPM's DNS provider registry");
}

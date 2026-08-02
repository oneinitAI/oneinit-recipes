#!/usr/bin/env node
/**
 * Sign INDEX.json with the registry Ed25519 private key.
 *
 * Usage: ONEINIT_SIGN_KEY=<seed-hex> node scripts/sign.js
 * Reads INDEX.json, writes INDEX.json.sig (hex signature).
 * Private key is a 32-byte Ed25519 seed (hex), stored in GitHub secret
 * ONEINIT_SIGN_KEY. Public key is embedded in oneinit (src/core/registry.rs).
 */
"use strict";

const fs = require("fs");
const crypto = require("crypto");

const SEED_HEX = process.env.ONEINIT_SIGN_KEY;
if (!SEED_HEX) {
  console.error("[ERROR] ONEINIT_SIGN_KEY env var required");
  process.exit(1);
}

const seed = Buffer.from(SEED_HEX, "hex");
if (seed.length !== 32) {
  console.error(`[ERROR] key must be 32 bytes, got ${seed.length}`);
  process.exit(1);
}

// RFC 8410 PKCS#8 DER for Ed25519: 302e020100300506032b657004220420 || seed
const pkcs8Der = Buffer.concat([
  Buffer.from("302e020100300506032b657004220420", "hex"),
  seed,
]);

const privateKey = crypto.createPrivateKey({
  key: pkcs8Der,
  format: "der",
  type: "pkcs8",
});

const data = fs.readFileSync("INDEX.json");
// Ed25519 → algorithm null
const sig = crypto.sign(null, data, privateKey);

fs.writeFileSync("INDEX.json.sig", sig.toString("hex") + "\n");
console.log(`[OK] INDEX.json.sig written (${sig.length} bytes)`);

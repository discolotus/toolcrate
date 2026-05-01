#!/usr/bin/env tsx
/**
 * Regenerate src/api/types.ts from the running backend's OpenAPI document.
 *
 * Usage: TOOLCRATE_API_BASE=http://127.0.0.1:48721 npm run gen:api
 */
import openapiTS, { astToString } from "openapi-typescript";
import { writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const base = process.env.TOOLCRATE_API_BASE ?? "http://127.0.0.1:48721";
const url = new URL("/api/openapi.json", base);

const ast = await openapiTS(url);
const out = astToString(ast);
const target = path.join(__dirname, "..", "src", "api", "types.ts");
await writeFile(target, "/* eslint-disable */\n/* prettier-ignore */\n" + out);
console.log(`wrote ${target}`);

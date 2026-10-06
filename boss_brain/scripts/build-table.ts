/**
 * Builds the table tool (DESIGN.md 7) into one self-contained file,
 * table/dist/boss-table.html: the engine, the Placeholder Boss and the screen
 * bundled into an inline script, the stylesheet inline, nothing fetched. It
 * opens from disk and works offline. It is deliberately not part of the
 * public site build (web/build.py): the tool is for the DM.
 *
 * Usage, from boss_brain/:  npm run table:build
 */
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { build } from "esbuild";

const at = (path: string) => new URL(`../${path}`, import.meta.url);

const result = await build({
  entryPoints: [fileURLToPath(at("src/table/main.ts"))],
  bundle: true,
  format: "iife",
  target: "es2022",
  minify: true,
  write: false,
  legalComments: "none",
});
const script = result.outputFiles[0]!.text.replace(/<\/script/gi, "<\\/script");
const style = readFileSync(at("table/style.css"), "utf8");
const page = readFileSync(at("table/index.html"), "utf8").replace("/* STYLE */", () => style).replace("// SCRIPT", () => script);

mkdirSync(at("table/dist/"), { recursive: true });
writeFileSync(at("table/dist/boss-table.html"), page);
console.log(`Wrote table/dist/boss-table.html (${Math.round(page.length / 1024)} KB)`);

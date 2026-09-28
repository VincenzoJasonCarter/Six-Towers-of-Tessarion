import { useEffect } from "react";
import { createFileRoute, Link } from "@tanstack/react-router";
import { Panel } from "@/components/terminal/panel";

export const Route = createFileRoute("/privacy")({
  component: PrivacyPolicy,
});

// Written for the Threadmint deployment, which builds without Google Drive
// sync (no VITE_GDRIVE_CLIENT_ID). Turning sync on means rewriting this page:
// see the upstream version (SonicRay241/charasheet) for the Drive sections.
function PrivacyPolicy() {
  useEffect(() => {
    document.title = "Privacy Policy — The Roster";
  }, []);

  return (
    <div className="mx-auto max-w-2xl p-4">
      <Link
        to="/"
        className="terminal-label inline-block cursor-pointer text-xs"
      >
        ← BACK TO THE ROSTER
      </Link>
      <Panel label="Privacy Policy" className="mt-3">
        <div className="space-y-4 text-sm text-muted-foreground">
          <p>
            <span className="text-foreground">Last updated:</span> September
            28, 2026
          </p>
          <section className="space-y-2">
            <p>
              The Roster is the character sheet of the Six Towers of Tessarion
              campaign site, built on{" "}
              <a
                className="underline"
                href="https://github.com/SonicRay241/charasheet"
                target="_blank"
                rel="noreferrer"
              >
                charasheet
              </a>{" "}
              by SonicRay241. It runs entirely in your browser. We collect
              nothing.
            </p>
          </section>

          <section className="space-y-2">
            <h2 className="text-xs uppercase tracking-widest text-primary">
              Data we do not collect
            </h2>
            <ul className="list-inside list-disc space-y-1">
              <li>
                Character data (names, stats, notes, spells, everything) is
                stored in your browser and never sent to us or anyone else.
              </li>
              <li>
                No accounts. No analytics. No advertising. No tracking
                pixels.
              </li>
              <li>
                No cloud sync. This version doesn't connect to Google Drive or
                any other storage service.
              </li>
            </ul>
          </section>

          <section className="space-y-2">
            <h2 className="text-xs uppercase tracking-widest text-primary">
              Local storage
            </h2>
            <p>
              Characters and preferences are stored in your browser's local
              storage and IndexedDB. Clearing your browser data for this site
              removes all of it, and nothing is kept anywhere else: use Export
              to keep a copy.
            </p>
          </section>

          <section className="space-y-2">
            <h2 className="text-xs uppercase tracking-widest text-primary">
              Traffic and hosting
            </h2>
            <p>
              This site is served by Vercel. Like virtually all websites, the
              hosting infrastructure processes request metadata (IP address,
              user agent, requested URL, timestamps) for security and abuse
              prevention. That is handled under Vercel's own privacy policy,
              not data we collect or control.
            </p>
          </section>

          <section className="space-y-2">
            <h2 className="text-xs uppercase tracking-widest text-primary">
              Contact
            </h2>
            <p>
              Questions about this policy?{" "}
              <a
                className="underline"
                href="https://github.com/VincenzoJasonCarter/Six-Towers-of-Tessarion/issues"
                target="_blank"
                rel="noreferrer"
              >
                Open an issue on GitHub
              </a>
              .
            </p>
          </section>
        </div>
      </Panel>
    </div>
  );
}

import { useEffect } from "react";
import { createFileRoute, Link } from "@tanstack/react-router";
import { Panel } from "@/components/terminal/panel";

export const Route = createFileRoute("/terms")({
  component: TermsOfService,
});

// Written for the Threadmint deployment, which builds without Google Drive
// sync; see the note in privacy.tsx.
function TermsOfService() {
  useEffect(() => {
    document.title = "Terms of Service — The Barracks";
  }, []);

  return (
    <div className="mx-auto max-w-2xl p-4">
      <Link
        to="/"
        className="terminal-label inline-block cursor-pointer text-xs"
      >
        ← BACK TO THE BARRACKS
      </Link>
      <Panel label="Terms of Service" className="mt-3">
        <div className="space-y-4 text-sm text-muted-foreground">
          <p>
            <span className="text-foreground">Last updated:</span> September
            28, 2026
          </p>
          <section className="space-y-2">
            <p>
              By using the Barracks you agree to these terms. If you do not
              agree, do not use it.
            </p>
          </section>

          <section className="space-y-2">
            <h2 className="text-xs uppercase tracking-widest text-primary">
              The service
            </h2>
            <p>
              The Barracks is a free, offline-first D&amp;D 5e character sheet
              for the Six Towers of Tessarion campaign, built on{" "}
              <a
                className="underline"
                href="https://github.com/SonicRay241/charasheet"
                target="_blank"
                rel="noreferrer"
              >
                charasheet
              </a>{" "}
              by SonicRay241. It runs in your browser and stores character
              data on your device only. There is no server holding your data.
            </p>
          </section>

          <section className="space-y-2">
            <h2 className="text-xs uppercase tracking-widest text-primary">
              Your data is your responsibility
            </h2>
            <ul className="list-inside list-disc space-y-1">
              <li>
                Your characters live in this browser's storage. Clearing
                browser data, private browsing modes, or aggressive browser
                settings can erase them.
              </li>
              <li>
                Characters don't follow you to another browser or device. Use
                Export to keep YAML backups, and Import to bring them back.
              </li>
              <li>
                We cannot recover lost characters. There is no server copy to
                restore from.
              </li>
            </ul>
          </section>

          <section className="space-y-2">
            <h2 className="text-xs uppercase tracking-widest text-primary">
              Acceptable use
            </h2>
            <p>
              Don't misuse the service: no attempts to breach, overload, or
              abuse the site or its hosting.
            </p>
          </section>

          <section className="space-y-2">
            <h2 className="text-xs uppercase tracking-widest text-primary">
              No warranty
            </h2>
            <p>
              The app is provided "as is", without warranty of any kind. D&amp;D
              5e content, rules, and terminology are used as references for a
              personal tool; the Barracks is not affiliated with or endorsed by
              Wizards of the Coast.
            </p>
          </section>

          <section className="space-y-2">
            <h2 className="text-xs uppercase tracking-widest text-primary">
              Limitation of liability
            </h2>
            <p>
              To the maximum extent permitted by law, we are not liable for
              any data loss, damages, or losses arising from your use of the
              app. If this term doesn't hold where you live, the app isn't
              intended for use there.
            </p>
          </section>

          <section className="space-y-2">
            <h2 className="text-xs uppercase tracking-widest text-primary">
              Changes
            </h2>
            <p>
              Terms may change; material updates will be reflected on this
              page with a new "last updated" date.
            </p>
          </section>

          <section className="space-y-2">
            <h2 className="text-xs uppercase tracking-widest text-primary">
              Contact
            </h2>
            <p>
              Questions about these terms?{" "}
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

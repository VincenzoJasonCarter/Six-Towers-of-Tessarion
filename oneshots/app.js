// LIVE and VERSION come from the inline script in template.html, which core.py fills in.

// Mark the section being read in the contents rail.
const links = new Map([...document.querySelectorAll("nav.toc a")].map(a => [a.getAttribute("href").slice(1), a]));
if (links.size && "IntersectionObserver" in window) {
  const seen = new Set();
  const io = new IntersectionObserver(entries => {
    for (const e of entries) e.isIntersecting ? seen.add(e.target.id) : seen.delete(e.target.id);
    const first = [...links.keys()].find(id => seen.has(id));
    if (first) links.forEach((a, id) => a.classList.toggle("here", id === first));
  }, { rootMargin: "0px 0px -70% 0px" });
  document.querySelectorAll("article h2[id]").forEach(h => io.observe(h));
}

// Served by serve.py: reload when a module or the page's files change, keeping the scroll position.
if (LIVE) {
  const key = "oneshots-scroll:" + location.pathname;
  try {
    const y = sessionStorage.getItem(key);
    if (y !== null) { window.scrollTo(0, Number(y)); sessionStorage.removeItem(key); }
  } catch (e) { /* storage blocked: start at the top */ }
  setInterval(async () => {
    try {
      const { version } = await (await fetch("/version", { cache: "no-store" })).json();
      if (version === VERSION) return;
      try { sessionStorage.setItem(key, String(window.scrollY)); } catch (e) { /* reload at the top */ }
      location.reload();
    } catch (e) { /* server stopped: keep the page as it is */ }
  }, 1000);
}

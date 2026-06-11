"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const LINKS = [
  { href: "/ledger", label: "Ledger" },
  { href: "/trust", label: "Trust" },
  { href: "/method", label: "Method" },
];

export function SiteNav() {
  const pathname = usePathname();
  return (
    <header className="fixed top-0 inset-x-0 z-50 border-b border-hairline bg-void/80 backdrop-blur-md">
      <nav
        aria-label="Primary"
        className="mx-auto flex max-w-7xl items-center justify-between px-5 py-3 md:px-8"
      >
        <Link
          href="/"
          className="display text-sm font-semibold tracking-[0.18em] text-ink hover:text-phosphor transition-colors"
        >
          PLANET<span className="text-phosphor">_</span>BACKLOG
        </Link>
        <ul className="flex items-center gap-6 md:gap-8">
          {LINKS.map(({ href, label }) => {
            const active = pathname?.startsWith(href);
            return (
              <li key={href}>
                <Link
                  href={href}
                  aria-current={active ? "page" : undefined}
                  className={`readout text-xs uppercase tracking-[0.2em] transition-colors ${
                    active ? "text-phosphor" : "text-ink-dim hover:text-ink"
                  }`}
                >
                  {label}
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>
    </header>
  );
}

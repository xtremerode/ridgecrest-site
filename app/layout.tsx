import "./globals.css";
import Link from "next/link";
import type { Metadata } from "next";
import { site } from "@/data/site";

export const metadata: Metadata = {
  title: "Custom Residential Design Build Firm | Ridgecrest Designs Pleasanton CA",
  description: "Ridgecrest Designs is a full-service residential design-build firm specializing in luxury homes and remodels across the Tri-Valley area. Schedule your custom design consultation today.",
  metadataBase: new URL("https://www.ridgecrestdesigns.com"),
};

const NAV = [
  {
    "label": "Home",
    "href": "/"
  },
  {
    "label": "Portfolio",
    "href": "/portfolio"
  },
  {
    "label": "Services",
    "href": "/services"
  },
  {
    "label": "Process",
    "href": "/california-process"
  },
  {
    "label": "About",
    "href": "/about"
  },
  {
    "label": "Testimonials",
    "href": "/testimonials"
  },
  {
    "label": "Contact",
    "href": "/contact"
  },
  {
    "label": "The RD Edit",
    "href": "/therdedit"
  }
];

function spaced(s: string) {
  return s.replace(/\S/g, (c) => c + " ").trim();
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <header className="topbar">
          <div className="container">
            <div className="nav">
              <Link className="brand" href="/">{spaced(site.brand.name)}</Link>
              <nav className="navlinks" aria-label="Primary">
                {NAV.slice(0,7).map((i) => (
                  <Link key={i.href} className="pill" href={i.href}>{i.label}</Link>
                ))}
                <Link className="btn" href={site.cta.href}>{site.cta.label}</Link>
              </nav>
            </div>
          </div>
        </header>

        <main>{children}</main>

        <footer className="footer">
          <div className="container">
            <div className="footerGrid">
              <div>
                <div className="brand">{spaced(site.brand.name)}</div>
                <div className="hr"></div>
                <div className="small">{site.brand.tagline}</div>
                <div className="small" style={{marginTop:10}}>
                  {site.brand.phone} · {site.brand.email}
                </div>
              </div>
              <div>
                <div className="small"><strong>Locations</strong></div>
                <div className="small" style={{marginTop:8}}>Pleasanton, CA · {site.brand.addressCA}</div>
                <div className="small" style={{marginTop:8}}>Texas · {site.brand.addressTX}</div>
              </div>
            </div>
            <div className="hr"></div>
            <div className="small">© {new Date().getFullYear()} Ridgecrest Designs</div>
          </div>
        </footer>
      </body>
    </html>
  );
}

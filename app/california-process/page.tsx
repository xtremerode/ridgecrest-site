import Section from "@/components/Section";
import { site } from "@/data/site";
import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "California Design-Build Process | Ridgecrest Designs",
  description: "Learn how Ridgecrest Designs guides your luxury home project in California with a transparent, streamlined design-build process tailored to the Tri-Valley market.",
  alternates: { canonical: "/california-process" },
};

export default function Process() {
  return (
    <>
      <Section>
        <div className="kicker">California</div>
        <h1>Design‑Build Process</h1>
        <p>{site.processCA.intro}</p>
        <div style={{marginTop:18}}>
          <Link className="btn" href="/contact">Book a consultation</Link>
        </div>
      </Section>

      <Section>
        <div className="projGrid">
          {site.processCA.steps.map((s) => (
            <div key={s.title} className="card projB">
              <div className="cardPad">
                <div className="kicker">{s.title}</div>
                <ul style={{marginTop:12, color:"var(--muted)", lineHeight:1.7}}>
                  {s.bullets.map((b) => <li key={b}>{b}</li>)}
                </ul>
              </div>
            </div>
          ))}
        </div>
      </Section>
    </>
  );
}

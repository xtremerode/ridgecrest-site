import Section from "@/components/Section";
import { site } from "@/data/site";
import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Testimonials | Ridgecrest Designs",
  description: "Discover client testimonials and reviews for Ridgecrest Designs, a premier residential design-build firm specializing in luxury custom homes, renovations, and high-end interior design in California and Texas.",
  alternates: { canonical: "/testimonials" },
};

export default function Testimonials() {
  return (
    <>
      <Section>
        <div className="kicker">Testimonials</div>
        <h1>What clients say</h1>
        <p>Short highlights from your current testimonials page.</p>
        <div style={{marginTop:18}}>
          <Link className="btn" href="/contact">Get in touch</Link>
        </div>
      </Section>

      <Section>
        <div className="projGrid">
          {site.testimonials.map((t, idx) => (
            <div key={idx} className="card projB">
              <div className="cardPad">
                <p style={{color:"var(--text)"}}>&ldquo;{t.quote}&rdquo;</p>
                <div className="hr"></div>
                <div className="small">— {t.name}</div>
              </div>
            </div>
          ))}
        </div>
      </Section>
    </>
  );
}

import Section from "@/components/Section";
import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "California Business Letter Format Guide | Ridgecrest Designs",
  description: "Explore a clear, professional California business-letter format guide from Ridgecrest Designs—ideal for architects, remodelers and luxury home firms needing polished correspondence.",
  alternates: { canonical: "/business-format-letter" },
};

const steps = [
  "Initial Contact",
  "Discovery Call",
  "“First Date” (In‑Home Consultation — fee applies)",
  "Present & Sign Design Contract",
  "In‑Home Measure and Inspiration Share",
  "Execute Design Package",
  "Present Design Package & Cost to Build",
  "Sign Construction Contract, Schedule Start Date & Provide Deposit",
  "Begin Construction"
];

export default function BusinessFormat() {
  const label = "California";
  return (
    <>
      <Section>
        <div className="kicker">Business format</div>
        <h1>{label}</h1>
        <p>Process overview and typical timelines.</p>
        <div style={{marginTop:18}}>
          <Link className="btn" href="/contact">Contact us</Link>
        </div>
      </Section>

      <Section>
        <div className="projGrid">
          <div className="card projA">
            <div className="cardPad">
              <div className="kicker">Process</div>
              <ol style={{marginTop:12, color:"var(--muted)", lineHeight:1.85}}>
                {steps.map((s) => <li key={s}>{s}</li>)}
              </ol>
            </div>
          </div>
        </div>
      </Section>
    </>
  );
}

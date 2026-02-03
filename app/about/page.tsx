import Section from "@/components/Section";
import { site } from "@/data/site";
import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "About | Ridgecrest Designs",
  description: "Meet the team of designers and craftsmen at Ridgecrest Designs, a luxury home design-build firm. We infuse clean, modern aesthetics with organic materials.",
  alternates: { canonical: "/about" },
};

export default function About() {
  return (
    <>
      <Section>
        <div className="kicker">About</div>
        <h1>{site.about.headline}</h1>
        <p>{site.about.body}</p>
        <div style={{marginTop:18}}>
          <Link className="btn" href="/contact">Contact us</Link>
        </div>
      </Section>

      <Section>
        <div className="kicker">Integrated design + build</div>
        <h2 style={{marginTop:10}}>One team. One vision.</h2>
        <p>{site.about.sub}</p>
      </Section>

      <Section>
        <div className="kicker">Team</div>
        <h2 style={{marginTop:10}}>People behind the work</h2>
        <div className="projGrid" style={{marginTop:18}}>
          {site.about.team.map((m) => (
            <div key={m.email} className="card projB">
              <div className="cardPad">
                <div className="kicker">{m.role}</div>
                <h2 style={{marginTop:10}}>{m.name}</h2>
                <p>{m.email}</p>
              </div>
            </div>
          ))}
        </div>
      </Section>
    </>
  );
}

import Section from "@/components/Section";
import { site } from "@/data/site";
import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Sunol Homestead Luxury Home | Ridgecrest Designs",
  description: "Ridgecrest Designs transformed this Sunol, CA home into the “Sunol Homestead” – a craftsman-inspired luxury residence with hand-placed river-stone exterior, custom timber details, and modern comforts.",
  alternates: { canonical: "/sunolhomestead" },
};

export default function Project() {
  const p = site.projects.find(x => x.slug === "/sunolhomestead")!;
  return (
    <>
      <Section>
        <div className="kicker"><Link href="/allprojects">Projects</Link></div>
        <h1>{p.title}</h1>
        <div className="card" style={{marginTop:18}}>
          <img className="img" src={p.hero} alt={p.title} />
        </div>

        <div className="metaRow" style={{marginTop:18}}>
          <div className="metaBox"><div className="label">Project</div><div className="value">{p.title}</div></div>
          <div className="metaBox"><div className="label">Location</div><div className="value">{p.where}</div></div>
          <div className="metaBox"><div className="label">Type</div><div className="value">{p.what}</div></div>
          <div className="metaBox"><div className="label">Year</div><div className="value">{p.when}</div></div>
        </div>
      </Section>

      <Section>
        <div className="kicker">Overview</div>
        <h2 style={{marginTop:10}}>{p.lead}</h2>
        <p style={{marginTop:12}}>{p.body}</p>
        <div style={{marginTop:18}}>
          <Link className="btn" href="/contact">Start your project</Link>
        </div>
      </Section>
    </>
  );
}

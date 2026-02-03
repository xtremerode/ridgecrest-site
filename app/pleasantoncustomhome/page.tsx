import Section from "@/components/Section";
import { site } from "@/data/site";
import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Pleasanton Custom Home | Ridgecrest Designs",
  description: "Experience bespoke custom home building in Pleasanton with Ridgecrest Designs: tailored architecture, high-end finishes and seamless design-build process.",
  alternates: { canonical: "/pleasantoncustomhome" },
};

export default function Project() {
  const p = site.projects.find(x => x.slug === "/pleasantoncustomhome")!;
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

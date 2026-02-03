import Section from "@/components/Section";
import { site } from "@/data/site";
import { ProjectCard } from "@/components/ProjectCard";
import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Portfolio of Luxury Homes & Remodels | Ridgecrest Designs",
  description: "Discover Ridgecrest Designs’ gallery of luxury home transformations: custom builds, remodels and craftsmanship across the Tri-Valley and East Bay.",
  alternates: { canonical: "/portfolio" },
};

export default function Portfolio() {
  const items = site.home.featuredProjects;
  return (
    <>
      <Section>
        <div className="kicker">Portfolio</div>
        <h1>Featured Projects</h1>
        <p>Luxury custom homes and transformative remodels crafted with architectural excellence and fine craftsmanship.</p>
        <div style={{marginTop:18}}>
          <Link className="pill" href="/allprojects">View all projects</Link>
        </div>
      </Section>

      <Section>
        <div className="projGrid">
          <ProjectCard size="A" title={items[0].title} summary={items[0].summary} image={items[0].image} href={items[0].slug} />
          <ProjectCard title={items[1].title} summary={items[1].summary} image={items[1].image} href={items[1].slug} />
          <ProjectCard title={items[2].title} summary={items[2].summary} image={items[2].image} href={items[2].slug} />
        </div>
      </Section>
    </>
  );
}

import Section from "@/components/Section";
import { site } from "@/data/site";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "The RD Edit Blog | Ridgecrest Designs",
  description: "Explore The RD Edit by Ridgecrest Designs—articles on custom home builds, remodel case studies, design trends and expert tips for homeowners in the Tri-Valley.",
  alternates: { canonical: "/therdedit" },
};

export default function Blog() {
  return (
    <>
      <Section>
        <div className="kicker">The RD Edit</div>
        <h1>Design notes + updates</h1>
        <p>{site.blog.intro}</p>
      </Section>

      <Section>
        <div className="projGrid">
          {site.blog.items.map((b) => (
            <div key={b.title} className="card projB">
              <div className="cardPad">
                <div className="kicker">Article</div>
                <h2 style={{marginTop:10}}>{b.title}</h2>
                <p>{b.excerpt}</p>
              </div>
            </div>
          ))}
        </div>
      </Section>
    </>
  );
}

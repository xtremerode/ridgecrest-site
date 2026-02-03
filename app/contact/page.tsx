import Section from "@/components/Section";
import { site } from "@/data/site";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Contact | Ridgecrest Designs",
  description: "Get in touch with Ridgecrest Designs, a leading luxury residential design-build firm serving California and Texas. Call 925-784-2798 or fill out our contact form to start your custom home or high-end remodel project today.",
  alternates: { canonical: "/contact" },
};

export default function Contact() {
  return (
    <>
      <Section>
        <div className="grid2">
          <div>
            <div className="kicker">Contact</div>
            <h1>Start your project</h1>
            <p>Get in touch with Ridgecrest Designs serving California and Texas.</p>

            <div className="hr"></div>
            <div className="small"><strong>Address</strong><br/>{site.brand.addressCA}</div>
            <div className="small" style={{marginTop:10}}><strong>Email</strong><br/>{site.brand.email}</div>
            <div className="small" style={{marginTop:10}}><strong>Phone</strong><br/>{site.brand.phone}</div>

            <div className="hr"></div>
            <div className="small"><strong>Form fields</strong><br/>First name · Last name · Phone · Email · Project budget · Tell us about your project</div>
          </div>

          <div className="card">
            <img className="img" src={site.images.contactKitchen} alt="Kitchen project" />
          </div>
        </div>
      </Section>
    </>
  );
}

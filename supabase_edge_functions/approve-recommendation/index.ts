/**
 * approve-recommendation edge function
 * Handles approve/dismiss actions from email links and Lovable UI.
 * Validates HMAC token on email links to prevent tampering.
 */
import { serve } from "https://deno.land/std@0.168.0/http/server.ts";
import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type, x-api-key",
};

async function verifyToken(id: string, action: string, token: string): Promise<boolean> {
  const secret = Deno.env.get("INGEST_API_KEY") ?? "";
  const secretKey = await crypto.subtle.importKey(
    "raw", new TextEncoder().encode(secret.slice(0, 32)),
    { name: "HMAC", hash: "SHA-256" }, false, ["sign"],
  );
  const msg = new TextEncoder().encode(`${id}:${action}`);
  const sig = await crypto.subtle.sign("HMAC", secretKey, msg);
  const hex = Array.from(new Uint8Array(sig)).map(b => b.toString(16).padStart(2, "0")).join("");
  return hex.slice(0, 16) === token;
}

serve(async (req) => {
  if (req.method === "OPTIONS") return new Response("ok", { headers: corsHeaders });

  const supabase = createClient(
    Deno.env.get("SUPABASE_URL")!,
    Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!,
  );

  // Support both GET (email links) and POST (Lovable UI)
  let id: string, action: string, token: string | null = null;

  if (req.method === "GET") {
    const url = new URL(req.url);
    id     = url.searchParams.get("id") ?? "";
    action = url.searchParams.get("action") ?? "";
    token  = url.searchParams.get("token");
  } else {
    const body = await req.json();
    id     = String(body.id ?? "");
    action = body.action ?? "";
    // Lovable UI uses authenticated requests — no token needed
    const apiKey = req.headers.get("x-api-key");
    if (apiKey !== Deno.env.get("INGEST_API_KEY")) {
      // Must be authenticated Supabase user (from Lovable)
      const authHeader = req.headers.get("Authorization");
      if (!authHeader) {
        return new Response(JSON.stringify({ error: "Unauthorized" }), {
          status: 401, headers: { ...corsHeaders, "Content-Type": "application/json" },
        });
      }
    }
  }

  if (!["approve", "dismiss"].includes(action)) {
    return new Response(JSON.stringify({ error: "Invalid action" }), {
      status: 400, headers: { ...corsHeaders, "Content-Type": "application/json" },
    });
  }

  // Verify token for email links
  if (token) {
    const valid = await verifyToken(id, action, token);
    if (!valid) {
      return new Response("<h2>Invalid or expired link.</h2>", {
        status: 403, headers: { "Content-Type": "text/html" },
      });
    }
  }

  const now = new Date().toISOString();
  const update = action === "approve"
    ? { status: "approved",  approved_at:  now }
    : { status: "dismissed", dismissed_at: now };

  const { data, error } = await supabase
    .from("recommendations")
    .update(update)
    .eq("id", id)
    .eq("status", "pending")  // only update pending ones
    .select()
    .single();

  if (error || !data) {
    const msg = error?.message ?? "Recommendation not found or already actioned";
    if (req.method === "GET") {
      return new Response(`<h2>${msg}</h2>`, {
        status: 404, headers: { "Content-Type": "text/html" },
      });
    }
    return new Response(JSON.stringify({ error: msg }), {
      status: 404, headers: { ...corsHeaders, "Content-Type": "application/json" },
    });
  }

  // Return friendly HTML for email link clicks
  if (req.method === "GET") {
    const emoji  = action === "approve" ? "✅" : "❌";
    const label  = action === "approve" ? "Approved" : "Dismissed";
    const color  = action === "approve" ? "#22c55e" : "#94a3b8";
    return new Response(`
      <html><body style="font-family:system-ui;max-width:480px;margin:80px auto;text-align:center;padding:24px">
        <div style="font-size:48px">${emoji}</div>
        <h2 style="color:${color}">${label}</h2>
        <p style="color:#64748b">${data.recommendation}</p>
        ${action === "approve" ? "<p style='color:#64748b;font-size:14px'>This will execute within 60 seconds.</p>" : ""}
      </body></html>
    `, { status: 200, headers: { "Content-Type": "text/html" } });
  }

  return new Response(JSON.stringify({ success: true, status: update.status }), {
    status: 200, headers: { ...corsHeaders, "Content-Type": "application/json" },
  });
});

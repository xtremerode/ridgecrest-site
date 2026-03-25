/**
 * save-health-check edge function
 * Receives health check results from health_agent.py and writes to system_health table.
 */
import { serve } from "https://deno.land/std@0.168.0/http/server.ts";
import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type, x-api-key",
};

serve(async (req) => {
  if (req.method === "OPTIONS") return new Response("ok", { headers: corsHeaders });

  const apiKey = req.headers.get("x-api-key");
  if (apiKey !== Deno.env.get("INGEST_API_KEY")) {
    return new Response(JSON.stringify({ error: "Unauthorized" }), {
      status: 401, headers: { ...corsHeaders, "Content-Type": "application/json" },
    });
  }

  const supabase = createClient(
    Deno.env.get("SUPABASE_URL")!,
    Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!,
  );

  const body = await req.json();
  const checks: Array<{ component: string; status: string; detail: string }> = body.checks ?? [];
  const checkedAt: string = body.checked_at ?? new Date().toISOString();

  if (!checks.length) {
    return new Response(JSON.stringify({ error: "No checks provided" }), {
      status: 400, headers: { ...corsHeaders, "Content-Type": "application/json" },
    });
  }

  const rows = checks.map((c) => ({
    component:  c.component,
    status:     c.status,
    detail:     c.detail ?? "",
    checked_at: checkedAt,
  }));

  const { error } = await supabase.from("system_health").insert(rows);

  if (error) {
    return new Response(JSON.stringify({ error: error.message }), {
      status: 500, headers: { ...corsHeaders, "Content-Type": "application/json" },
    });
  }

  return new Response(JSON.stringify({ success: true, rows_written: rows.length }), {
    status: 200, headers: { ...corsHeaders, "Content-Type": "application/json" },
  });
});

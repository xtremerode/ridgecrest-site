/**
 * save-recommendation edge function
 * Receives recommendations from recommendation_agent.py and writes to Supabase.
 * Also handles count_pending, fetch_approved, and mark_executed actions.
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

  // Count pending recommendations
  if (body.action === "count_pending") {
    const { count } = await supabase
      .from("recommendations")
      .select("*", { count: "exact", head: true })
      .eq("status", "pending");
    return new Response(JSON.stringify({ count: count ?? 0 }), {
      status: 200, headers: { ...corsHeaders, "Content-Type": "application/json" },
    });
  }

  // Fetch approved recommendations ready for execution
  if (body.action === "fetch_approved") {
    const { data, error } = await supabase
      .from("recommendations")
      .select("*")
      .eq("status", "approved")
      .is("executed_at", null)
      .order("approved_at", { ascending: true })
      .limit(20);
    if (error) {
      return new Response(JSON.stringify({ error: error.message }), {
        status: 500, headers: { ...corsHeaders, "Content-Type": "application/json" },
      });
    }
    return new Response(JSON.stringify({ recommendations: data ?? [] }), {
      status: 200, headers: { ...corsHeaders, "Content-Type": "application/json" },
    });
  }

  // Mark a recommendation as executed or failed
  if (body.action === "mark_executed") {
    const { id, success, result } = body;
    if (!id) {
      return new Response(JSON.stringify({ error: "id required" }), {
        status: 400, headers: { ...corsHeaders, "Content-Type": "application/json" },
      });
    }
    const now = new Date().toISOString();
    const update = success
      ? { status: "executed", executed_at: now, execution_result: result ?? "ok", updated_at: now }
      : { status: "failed",   executed_at: now, execution_result: result ?? "unknown error", updated_at: now };
    const { error } = await supabase
      .from("recommendations")
      .update(update)
      .eq("id", id);
    if (error) {
      return new Response(JSON.stringify({ error: error.message }), {
        status: 500, headers: { ...corsHeaders, "Content-Type": "application/json" },
      });
    }
    return new Response(JSON.stringify({ success: true }), {
      status: 200, headers: { ...corsHeaders, "Content-Type": "application/json" },
    });
  }

  // Write new recommendation
  const { data, error } = await supabase
    .from("recommendations")
    .insert(body)
    .select()
    .single();

  if (error) {
    return new Response(JSON.stringify({ error: error.message }), {
      status: 500, headers: { ...corsHeaders, "Content-Type": "application/json" },
    });
  }

  return new Response(JSON.stringify({ id: data.id, success: true }), {
    status: 200, headers: { ...corsHeaders, "Content-Type": "application/json" },
  });
});

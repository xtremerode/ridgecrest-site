/**
 * Supabase Edge Function: execute-command
 * ========================================
 * Receives campaign control commands from the Lovable Command Center
 * and writes them to the command_queue table.
 * The local command_executor.py polls this table every 30 seconds and
 * executes the commands against the ad platforms.
 *
 * Deploy:
 *   supabase functions deploy execute-command
 *
 * Request body (JSON):
 *   {
 *     "command_type": "pause_campaign" | "enable_campaign" | "pause_all" | "enable_all",
 *     "platform":     "google_ads" | "meta" | "microsoft_ads" | "all",
 *     "external_id":  "campaign-id-on-platform",   // required for single-campaign commands
 *     "params":       {}                             // optional extra params
 *   }
 *
 * Response:
 *   { "id": 123, "status": "queued", "message": "Command queued successfully" }
 */

import { serve } from "https://deno.land/std@0.168.0/http/server.ts";
import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers":
    "authorization, x-client-info, apikey, content-type",
};

const VALID_COMMANDS = [
  "pause_campaign",
  "enable_campaign",
  "pause_all",
  "enable_all",
];
const VALID_PLATFORMS = [
  "google_ads",
  "meta",
  "microsoft_ads",
  "all",
];

serve(async (req) => {
  // Handle CORS preflight
  if (req.method === "OPTIONS") {
    return new Response("ok", { headers: corsHeaders });
  }

  try {
    const supabase = createClient(
      Deno.env.get("SUPABASE_URL")!,
      Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!,
    );

    const body = await req.json();
    const { command_type, platform = "all", external_id, params = {} } = body;

    // Validate command_type
    if (!command_type || !VALID_COMMANDS.includes(command_type)) {
      return new Response(
        JSON.stringify({
          error: `Invalid command_type. Must be one of: ${VALID_COMMANDS.join(", ")}`,
        }),
        {
          status: 400,
          headers: { ...corsHeaders, "Content-Type": "application/json" },
        },
      );
    }

    // Validate platform
    if (!VALID_PLATFORMS.includes(platform)) {
      return new Response(
        JSON.stringify({
          error: `Invalid platform. Must be one of: ${VALID_PLATFORMS.join(", ")}`,
        }),
        {
          status: 400,
          headers: { ...corsHeaders, "Content-Type": "application/json" },
        },
      );
    }

    // Single-campaign commands require external_id
    if (
      ["pause_campaign", "enable_campaign"].includes(command_type) &&
      !external_id
    ) {
      return new Response(
        JSON.stringify({
          error: "external_id is required for pause_campaign and enable_campaign",
        }),
        {
          status: 400,
          headers: { ...corsHeaders, "Content-Type": "application/json" },
        },
      );
    }

    // Insert into command_queue
    const { data, error } = await supabase
      .from("command_queue")
      .insert({
        command_type,
        platform,
        external_id: external_id ?? null,
        params,
        status: "pending",
      })
      .select()
      .single();

    if (error) {
      console.error("Supabase insert error:", error);
      return new Response(
        JSON.stringify({ error: error.message }),
        {
          status: 500,
          headers: { ...corsHeaders, "Content-Type": "application/json" },
        },
      );
    }

    return new Response(
      JSON.stringify({
        id: data.id,
        status: "queued",
        message: `Command "${command_type}" queued — executes within 30 seconds`,
      }),
      {
        status: 200,
        headers: { ...corsHeaders, "Content-Type": "application/json" },
      },
    );
  } catch (err) {
    console.error("Edge function error:", err);
    return new Response(
      JSON.stringify({ error: err.message }),
      {
        status: 500,
        headers: { ...corsHeaders, "Content-Type": "application/json" },
      },
    );
  }
});

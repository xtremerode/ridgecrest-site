/**
 * Supabase Edge Function: chat-messages
 * =======================================
 * Handles read/write operations on the chat_messages table for the
 * Lovable Command Center chat interface.
 *
 * Actions:
 *   get_pending    — fetch unprocessed user messages (polled by chat_agent.py)
 *   get_history    — fetch full conversation history for a session_id
 *   post_response  — write assistant response and mark user message done
 *   post_message   — write a user message (used by Lovable frontend)
 *   mark_processing — mark a user message as processing
 *
 * Deploy:
 *   supabase functions deploy chat-messages
 */

import { serve } from "https://deno.land/std@0.168.0/http/server.ts";
import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers":
    "authorization, x-client-info, apikey, content-type, x-api-key",
};

serve(async (req) => {
  if (req.method === "OPTIONS") {
    return new Response("ok", { headers: corsHeaders });
  }

  try {
    const supabase = createClient(
      Deno.env.get("SUPABASE_URL")!,
      Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!,
    );

    const body = await req.json();
    const { action } = body;

    // ---- get_pending: chat_agent polls this to find messages to process ----
    if (action === "get_pending") {
      const { data, error } = await supabase
        .from("chat_messages")
        .select("*")
        .eq("role", "user")
        .eq("status", "pending")
        .order("created_at", { ascending: true })
        .limit(10);

      if (error) throw error;

      return new Response(JSON.stringify({ messages: data }), {
        headers: { ...corsHeaders, "Content-Type": "application/json" },
      });
    }

    // ---- get_history: load full conversation for a session ----
    if (action === "get_history") {
      const { session_id } = body;
      if (!session_id) {
        return new Response(JSON.stringify({ error: "session_id required" }), {
          status: 400,
          headers: { ...corsHeaders, "Content-Type": "application/json" },
        });
      }

      const { data, error } = await supabase
        .from("chat_messages")
        .select("*")
        .eq("session_id", session_id)
        .order("created_at", { ascending: true });

      if (error) throw error;

      return new Response(JSON.stringify({ messages: data }), {
        headers: { ...corsHeaders, "Content-Type": "application/json" },
      });
    }

    // ---- mark_processing: chat_agent marks a message as in-flight ----
    if (action === "mark_processing") {
      const { id } = body;
      if (!id) {
        return new Response(JSON.stringify({ error: "id required" }), {
          status: 400,
          headers: { ...corsHeaders, "Content-Type": "application/json" },
        });
      }

      const { error } = await supabase
        .from("chat_messages")
        .update({ status: "processing" })
        .eq("id", id);

      if (error) throw error;

      return new Response(JSON.stringify({ success: true }), {
        headers: { ...corsHeaders, "Content-Type": "application/json" },
      });
    }

    // ---- post_response: chat_agent writes the assistant reply ----
    if (action === "post_response") {
      const { session_id, content, user_message_id, metadata = {} } = body;
      if (!session_id || !content) {
        return new Response(
          JSON.stringify({ error: "session_id and content required" }),
          {
            status: 400,
            headers: { ...corsHeaders, "Content-Type": "application/json" },
          },
        );
      }

      // Insert assistant message
      const { data: inserted, error: insertError } = await supabase
        .from("chat_messages")
        .insert({
          session_id,
          role: "assistant",
          content,
          status: "done",
          metadata,
        })
        .select()
        .single();

      if (insertError) throw insertError;

      // Mark user message as done
      if (user_message_id) {
        await supabase
          .from("chat_messages")
          .update({ status: "done" })
          .eq("id", user_message_id);
      }

      return new Response(JSON.stringify({ success: true, id: inserted.id }), {
        headers: { ...corsHeaders, "Content-Type": "application/json" },
      });
    }

    // ---- post_message: Lovable frontend writes a user message ----
    if (action === "post_message") {
      const { session_id, content, metadata = {} } = body;
      if (!session_id || !content) {
        return new Response(
          JSON.stringify({ error: "session_id and content required" }),
          {
            status: 400,
            headers: { ...corsHeaders, "Content-Type": "application/json" },
          },
        );
      }

      const { data, error } = await supabase
        .from("chat_messages")
        .insert({
          session_id,
          role: "user",
          content,
          status: "pending",
          metadata,
        })
        .select()
        .single();

      if (error) throw error;

      return new Response(JSON.stringify({ success: true, id: data.id }), {
        headers: { ...corsHeaders, "Content-Type": "application/json" },
      });
    }

    return new Response(
      JSON.stringify({
        error: `Unknown action: ${action}. Valid: get_pending, get_history, mark_processing, post_response, post_message`,
      }),
      {
        status: 400,
        headers: { ...corsHeaders, "Content-Type": "application/json" },
      },
    );
  } catch (err) {
    console.error("chat-messages edge function error:", err);
    return new Response(JSON.stringify({ error: err.message }), {
      status: 500,
      headers: { ...corsHeaders, "Content-Type": "application/json" },
    });
  }
});

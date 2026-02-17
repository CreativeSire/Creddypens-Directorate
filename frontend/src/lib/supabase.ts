"use client";

import { createClient } from "@supabase/supabase-js";

import { supabaseAnonKey, supabaseUrl } from "@/lib/env";

export const supabase = createClient(supabaseUrl(), supabaseAnonKey());


export function apiBaseUrl() {
  return process.env.NEXT_PUBLIC_API_URL?.trim() || "http://127.0.0.1:8010";
}

export function supabaseUrl() {
  return process.env.NEXT_PUBLIC_SUPABASE_URL?.trim() || "";
}

export function supabaseAnonKey() {
  return process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY?.trim() || "";
}


import { createContext, useContext, useState, useEffect } from "react";
import { supabase } from "./supabase";
import { api } from "./api";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [session, setSession] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    
    supabase.auth.getSession().then(({ data: { session: s } }) => {
      setSession(s);
      if (s) fetchProfile(s);
      else setLoading(false);
    });

    
    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      (_event, s) => {
        setSession(s);
        if (s) fetchProfile(s);
        else {
          setUser(null);
          setLoading(false);
        }
      }
    );

    return () => subscription.unsubscribe();
  }, []);

  async function fetchProfile(s) {
    try {
      const profile = await api.get("/auth/me");
      setUser(profile);
    } catch (err) {
      console.error("fetchProfile failed:", err);
      
      setUser({
        id: s.user.id,
        email: s.user.email,
        full_name: s.user.user_metadata?.full_name || s.user.email,
        role: s.user.user_metadata?.role || "employee",
        org_id: s.user.user_metadata?.org_id || "",
      });
    } finally {
      setLoading(false);
    }
  }

  async function signUp({ email, password, fullName, orgId, role }) {
    const { data, error } = await supabase.auth.signUp({
      email,
      password,
      options: {
        data: { full_name: fullName, org_id: orgId, role: role || "employee" },
      },
    });
    if (error) throw error;
    return data;
  }

  async function signIn({ email, password }) {
    const { data, error } = await supabase.auth.signInWithPassword({
      email,
      password,
    });
    if (error) throw error;
    return data;
  }

  async function signOut() {
    await supabase.auth.signOut();
    setUser(null);
    setSession(null);
  }

  return (
    <AuthContext.Provider
      value={{ user, session, loading, signUp, signIn, signOut }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}

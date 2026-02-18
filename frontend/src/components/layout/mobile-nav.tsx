"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { AnimatePresence, motion } from "framer-motion";
import { Briefcase, GraduationCap, Home, LogOut, Menu, Users, X } from "lucide-react";

import { supabase } from "@/lib/supabase";
import { toast } from "@/lib/toast";

const navItems = [
  { href: "/dashboard", label: "Dashboard", icon: Home },
  { href: "/dashboard/departments/customer-experience", label: "Departments", icon: Briefcase },
  { href: "/dashboard/my-agents", label: "My Agents", icon: Users },
  { href: "/dashboard/academy", label: "The Academy", icon: GraduationCap },
];

export function MobileNav() {
  const [open, setOpen] = useState(false);
  const pathname = usePathname();
  const router = useRouter();

  const handleLogout = async () => {
    await supabase.auth.signOut();
    toast.success("Logged out successfully");
    setOpen(false);
    router.push("/login");
  };

  return (
    <>
      <button
        onClick={() => setOpen((v) => !v)}
        className="md:hidden text-cyan p-2 hover:text-amber transition-colors touch-target focus-ring"
        aria-label="Toggle menu"
      >
        {open ? <X size={22} /> : <Menu size={22} />}
      </button>

      <AnimatePresence>
        {open ? (
          <>
            <motion.button
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setOpen(false)}
              className="fixed inset-0 bg-black/60 backdrop-blur-sm z-[140] md:hidden"
              aria-label="Close menu"
            />
            <motion.div
              initial={{ x: "100%" }}
              animate={{ x: 0 }}
              exit={{ x: "100%" }}
              transition={{ type: "tween", duration: 0.3, ease: "easeInOut" }}
              className="fixed inset-y-0 right-0 z-[150] w-72 bg-[#0D1520] border-l border-cyan/30 p-6 md:hidden"
            >
              <div className="flex items-center justify-between mb-8">
                <h2 className="text-lg font-bold text-cyan tracking-wide">COMMAND CENTER</h2>
                <button onClick={() => setOpen(false)} className="text-cyan hover:text-amber transition-colors focus-ring">
                  <X size={22} />
                </button>
              </div>

              <nav className="space-y-2">
                {navItems.map((item) => {
                  const Icon = item.icon;
                  const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
                  return (
                    <Link
                      key={item.href}
                      href={item.href}
                      onClick={() => setOpen(false)}
                      className={`flex items-center gap-3 px-4 py-3 rounded transition-all focus-ring ${
                        active
                          ? "bg-cyan/10 text-cyan border border-cyan/30"
                          : "text-white/80 hover:bg-cyan/5 hover:text-cyan"
                      }`}
                    >
                      <Icon size={18} />
                      <span className="font-medium">{item.label}</span>
                    </Link>
                  );
                })}
              </nav>

              <button
                onClick={() => void handleLogout()}
                className="mt-8 w-full flex items-center gap-3 px-4 py-3 rounded text-white/80 hover:bg-red-500/10 hover:text-red-300 transition-all focus-ring"
              >
                <LogOut size={18} />
                <span className="font-medium">Logout</span>
              </button>
            </motion.div>
          </>
        ) : null}
      </AnimatePresence>
    </>
  );
}


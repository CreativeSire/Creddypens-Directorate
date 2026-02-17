import React, { useState } from 'react';
import { Search, Shield, Zap, Users, ChevronRight, Lock } from 'lucide-react';

export default function CreddyPensLanding() {
  const [selectedDept, setSelectedDept] = useState(null);
  const [scanActive, setScanActive] = useState(false);

  const departments = [
    { id: 1, name: 'CUSTOMER EXPERIENCE', code: 'CX-01', agents: 6, icon: '👥' },
    { id: 2, name: 'SALES & BUSINESS DEV', code: 'SD-02', agents: 5, icon: '📈' },
    { id: 3, name: 'MARKETING & CREATIVE', code: 'MC-03', agents: 6, icon: '🎨' },
    { id: 4, name: 'OPERATIONS & ADMIN', code: 'OA-04', agents: 7, icon: '⚙️' },
    { id: 5, name: 'TECHNICAL & IT', code: 'IT-05', agents: 6, icon: '💻' },
    { id: 6, name: 'SPECIALIZED SERVICES', code: 'SP-06', agents: 7, icon: '🎓' }
  ];

  const featuredAgents = [
    {
      code: 'GREETER-01',
      role: 'AI Receptionist',
      dept: 'Customer Experience',
      price: '$149/mo',
      status: 'ACTIVE',
      clearance: 'STANDARD'
    },
    {
      code: 'HUNTER-01',
      role: 'Lead Generator',
      dept: 'Sales & Business Dev',
      price: '$199/mo',
      status: 'ACTIVE',
      clearance: 'STANDARD'
    },
    {
      code: 'AUTHOR-01',
      role: 'Content Writer',
      dept: 'Marketing & Creative',
      price: '$249/mo',
      status: 'ACTIVE',
      clearance: 'PREMIUM'
    }
  ];

  return (
    <div className="min-h-screen bg-[#0A0F14] text-[#00F0FF] font-mono overflow-hidden relative">
      {/* Scanline Effect */}
      <div className="absolute inset-0 pointer-events-none opacity-10">
        <div className="h-full w-full" style={{
          backgroundImage: 'repeating-linear-gradient(0deg, transparent, transparent 2px, #00F0FF 2px, #00F0FF 4px)',
          animation: 'scan 8s linear infinite'
        }}></div>
      </div>

      {/* Grid Background */}
      <div className="absolute inset-0 opacity-5">
        <div className="h-full w-full" style={{
          backgroundImage: 'linear-gradient(#00F0FF 1px, transparent 1px), linear-gradient(90deg, #00F0FF 1px, transparent 1px)',
          backgroundSize: '50px 50px'
        }}></div>
      </div>

      {/* Header */}
      <header className="relative border-b border-[#00F0FF]/30 backdrop-blur-sm">
        <div className="max-w-7xl mx-auto px-6 py-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Shield className="w-8 h-8 text-[#00F0FF]" />
              <div>
                <h1 className="text-2xl font-bold tracking-wider">THE CREDDYPENS DIRECTORATE</h1>
                <p className="text-xs text-[#00F0FF]/60 tracking-widest">CLASSIFIED // LEVEL 5 ACCESS</p>
              </div>
            </div>
            <div className="flex gap-4">
              <button className="px-4 py-2 border border-[#00F0FF]/50 hover:bg-[#00F0FF]/10 transition-all">
                ACCESS PORTAL
              </button>
              <button className="px-4 py-2 bg-[#FFB800] text-[#0A0F14] font-bold hover:bg-[#FFB800]/90 transition-all">
                REQUEST ACCESS
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section className="relative max-w-7xl mx-auto px-6 py-16">
        <div className="text-center mb-12">
          <div className="inline-block mb-4 px-4 py-2 border border-[#FFB800] bg-[#FFB800]/10 backdrop-blur-sm">
            <p className="text-[#FFB800] text-sm tracking-widest">⚠ SYNTHETIC WORKFORCE DEPLOYMENT SYSTEM</p>
          </div>
          <h2 className="text-6xl font-bold mb-6 tracking-tight">
            HIRE <span className="text-[#FFB800]">AI STAFF</span>.<br/>
            PAY MONTHLY.<br/>
            SCALE INSTANTLY.
          </h2>
          <p className="text-xl text-[#00F0FF]/70 max-w-2xl mx-auto mb-8">
            Access our classified directory of 42 autonomous AI agents. Each trained, specialized, and ready for immediate deployment.
          </p>
          
          {/* Search Bar */}
          <div className="max-w-2xl mx-auto relative">
            <div className="relative border-2 border-[#00F0FF]/50 bg-[#0A0F14]/50 backdrop-blur-sm">
              <input 
                type="text"
                placeholder="IDENTIFY YOUR NEED: [e.g., 'Receptionist', 'Sales Agent', 'Bookkeeper']"
                className="w-full px-6 py-4 bg-transparent text-[#00F0FF] placeholder-[#00F0FF]/40 focus:outline-none"
                onFocus={() => setScanActive(true)}
                onBlur={() => setScanActive(false)}
              />
              <Search className="absolute right-4 top-1/2 -translate-y-1/2 w-6 h-6" />
            </div>
            {scanActive && (
              <div className="absolute top-full left-0 right-0 mt-2 border border-[#00F0FF]/30 bg-[#0A0F14]/95 backdrop-blur-md p-4">
                <p className="text-xs text-[#FFB800] mb-2">SCANNING DATABASE...</p>
                <div className="space-y-2">
                  <div className="p-2 hover:bg-[#00F0FF]/10 cursor-pointer">GREETER-01 // AI Receptionist</div>
                  <div className="p-2 hover:bg-[#00F0FF]/10 cursor-pointer">ASSISTANT-01 // Virtual Assistant</div>
                  <div className="p-2 hover:bg-[#00F0FF]/10 cursor-pointer">LEDGER-02 // Bookkeeper</div>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-4 gap-6 max-w-4xl mx-auto mb-16">
          {[
            { label: 'ACTIVE AGENTS', value: '42' },
            { label: 'DEPARTMENTS', value: '06' },
            { label: 'AVG RESPONSE', value: '<3s' },
            { label: 'UPTIME', value: '99.9%' }
          ].map((stat, i) => (
            <div key={i} className="border border-[#00F0FF]/30 bg-[#00F0FF]/5 backdrop-blur-sm p-6 text-center">
              <div className="text-4xl font-bold text-[#FFB800] mb-2">{stat.value}</div>
              <div className="text-xs tracking-wider text-[#00F0FF]/60">{stat.label}</div>
            </div>
          ))}
        </div>
      </section>

      {/* Department Directory */}
      <section className="relative max-w-7xl mx-auto px-6 py-16 border-t border-[#00F0FF]/30">
        <div className="mb-8">
          <div className="flex items-center gap-3 mb-2">
            <Lock className="w-5 h-5" />
            <h3 className="text-3xl font-bold tracking-wider">DEPARTMENT DIRECTORY</h3>
          </div>
          <p className="text-[#00F0FF]/60">Select a division to view available assets</p>
        </div>

        <div className="grid grid-cols-3 gap-6">
          {departments.map((dept) => (
            <button
              key={dept.id}
              onClick={() => setSelectedDept(dept.id)}
              className={`group relative border-2 p-6 text-left transition-all ${
                selectedDept === dept.id 
                  ? 'border-[#FFB800] bg-[#FFB800]/10' 
                  : 'border-[#00F0FF]/30 hover:border-[#00F0FF]/60 bg-[#00F0FF]/5'
              }`}
            >
              <div className="absolute top-2 right-2 text-3xl opacity-20 group-hover:opacity-40 transition-opacity">
                {dept.icon}
              </div>
              <div className="text-xs text-[#FFB800] mb-2 tracking-widest">{dept.code}</div>
              <div className="text-xl font-bold mb-2 tracking-wide">{dept.name}</div>
              <div className="flex items-center justify-between text-sm">
                <span className="text-[#00F0FF]/60">{dept.agents} AGENTS AVAILABLE</span>
                <ChevronRight className="w-4 h-4" />
              </div>
            </button>
          ))}
        </div>
      </section>

      {/* Featured Agents */}
      <section className="relative max-w-7xl mx-auto px-6 py-16 border-t border-[#00F0FF]/30">
        <div className="mb-8">
          <div className="flex items-center gap-3 mb-2">
            <Users className="w-5 h-5" />
            <h3 className="text-3xl font-bold tracking-wider">FEATURED ASSETS</h3>
          </div>
          <p className="text-[#00F0FF]/60">High-demand agents ready for immediate deployment</p>
        </div>

        <div className="grid grid-cols-3 gap-6">
          {featuredAgents.map((agent, i) => (
            <div key={i} className="border border-[#00F0FF]/30 bg-gradient-to-br from-[#00F0FF]/5 to-transparent backdrop-blur-sm overflow-hidden group hover:border-[#FFB800] transition-all">
              {/* Agent Header */}
              <div className="border-b border-[#00F0FF]/30 p-4 bg-[#00F0FF]/5">
                <div className="flex items-start justify-between mb-2">
                  <div>
                    <div className="text-xs text-[#FFB800] tracking-widest mb-1">AGENT FILE</div>
                    <div className="text-2xl font-bold tracking-wide">{agent.code}</div>
                  </div>
                  <div className={`px-3 py-1 text-xs border ${
                    agent.clearance === 'PREMIUM' 
                      ? 'border-[#FFB800] text-[#FFB800]' 
                      : 'border-[#00F0FF] text-[#00F0FF]'
                  }`}>
                    {agent.clearance}
                  </div>
                </div>
              </div>

              {/* Agent Details */}
              <div className="p-4 space-y-3">
                <div>
                  <div className="text-xs text-[#00F0FF]/60 mb-1">DESIGNATION</div>
                  <div className="font-bold">{agent.role}</div>
                </div>
                <div>
                  <div className="text-xs text-[#00F0FF]/60 mb-1">DEPARTMENT</div>
                  <div className="text-sm">{agent.dept}</div>
                </div>
                <div className="flex items-center justify-between pt-3 border-t border-[#00F0FF]/30">
                  <div>
                    <div className="text-xs text-[#00F0FF]/60">STATUS</div>
                    <div className="flex items-center gap-2 mt-1">
                      <div className="w-2 h-2 rounded-full bg-[#00FF00] animate-pulse"></div>
                      <span className="text-sm">{agent.status}</span>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="text-2xl font-bold text-[#FFB800]">{agent.price}</div>
                  </div>
                </div>
              </div>

              {/* Action Button */}
              <div className="p-4 border-t border-[#00F0FF]/30">
                <button className="w-full py-3 bg-[#00F0FF]/10 border border-[#00F0FF]/50 hover:bg-[#00F0FF]/20 transition-all font-bold tracking-wider group-hover:border-[#FFB800] group-hover:text-[#FFB800]">
                  [ VIEW DOSSIER ]
                </button>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* CTA Section */}
      <section className="relative max-w-7xl mx-auto px-6 py-16 border-t border-[#00F0FF]/30">
        <div className="border-2 border-[#FFB800] bg-[#FFB800]/10 backdrop-blur-sm p-12 text-center">
          <Zap className="w-12 h-12 text-[#FFB800] mx-auto mb-4" />
          <h3 className="text-4xl font-bold mb-4 tracking-wide">READY TO DEPLOY YOUR WORKFORCE?</h3>
          <p className="text-xl text-[#00F0FF]/70 mb-8 max-w-2xl mx-auto">
            Request Level 5 clearance to access the full agent catalog. No contracts. Cancel anytime.
          </p>
          <div className="flex gap-4 justify-center">
            <button className="px-8 py-4 bg-[#FFB800] text-[#0A0F14] font-bold text-lg hover:bg-[#FFB800]/90 transition-all">
              REQUEST ACCESS
            </button>
            <button className="px-8 py-4 border-2 border-[#00F0FF] hover:bg-[#00F0FF]/10 transition-all font-bold text-lg">
              VIEW DEMO
            </button>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="relative border-t border-[#00F0FF]/30 backdrop-blur-sm mt-16">
        <div className="max-w-7xl mx-auto px-6 py-8">
          <div className="flex items-center justify-between text-sm">
            <div className="text-[#00F0FF]/60">
              © 2026 THE CREDDYPENS DIRECTORATE // ALL RIGHTS RESERVED
            </div>
            <div className="flex gap-6 text-[#00F0FF]/60">
              <a href="#" className="hover:text-[#00F0FF]">DOCUMENTATION</a>
              <a href="#" className="hover:text-[#00F0FF]">SECURITY</a>
              <a href="#" className="hover:text-[#00F0FF]">CONTACT</a>
            </div>
          </div>
        </div>
      </footer>

      <style jsx>{`
        @keyframes scan {
          0% { transform: translateY(0); }
          100% { transform: translateY(100%); }
        }
      `}</style>
    </div>
  );
}

"use client";

const ORG_KEY = "creddypens_org_id";

export function getOrgId(): string | null {
  try {
    return localStorage.getItem(ORG_KEY);
  } catch {
    return null;
  }
}

export function setOrgId(orgId: string) {
  try {
    localStorage.setItem(ORG_KEY, orgId);
  } catch {
    // ignore
  }
}


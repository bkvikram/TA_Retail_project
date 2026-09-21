// Dev-only credential handling: an API key + user id are kept in memory and sent as headers.
// Production replaces this with an OAuth2/OIDC bearer token from the corporate IdP
// (see docs/ARCHITECTURE.md - Design Decisions - AuthN/AuthZ).
const API_KEY = import.meta.env.VITE_API_KEY || "dev-local-api-key";
const USER_ID = import.meta.env.VITE_USER_ID || "demo-user";

function authHeaders(extra = {}) {
  return { "X-API-Key": API_KEY, "X-User-Id": USER_ID, ...extra };
}

async function handle(response) {
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = await response.json();
      detail = body.detail || JSON.stringify(body);
    } catch {
      // response had no JSON body
    }
    throw new Error(`${response.status}: ${detail}`);
  }
  return response.status === 204 ? null : response.json();
}

export async function uploadFeed(file) {
  const formData = new FormData();
  formData.append("file", file);
  const response = await fetch("/api/uploads", {
    method: "POST",
    headers: authHeaders(),
    body: formData,
  });
  return handle(response);
}

export async function getUploadStatus(jobId) {
  const response = await fetch(`/api/uploads/${jobId}`, { headers: authHeaders() });
  return handle(response);
}

export async function searchPricing(filters, page, pageSize) {
  const params = new URLSearchParams({ page, page_size: pageSize });
  Object.entries(filters).forEach(([key, value]) => {
    if (value !== "" && value !== null && value !== undefined) params.set(key, value);
  });
  const response = await fetch(`/api/pricing?${params.toString()}`, { headers: authHeaders() });
  return handle(response);
}

export async function updatePricingRecord(id, changes) {
  const response = await fetch(`/api/pricing/${id}`, {
    method: "PATCH",
    headers: authHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify(changes),
  });
  return handle(response);
}

export async function getPricingHistory(id) {
  const response = await fetch(`/api/pricing/${id}/history`, { headers: authHeaders() });
  return handle(response);
}

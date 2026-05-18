export type IngestPayload = {
  patient_id: string;
  raw_text: string;
  doctor_id?: string;
  file_url?: string;
};

export type IngestResult = {
  ok: boolean;
  status: number;
  data: unknown;
  error?: string;
};

const API_BASE = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(/\/$/, "");
const API_KEY = process.env.NEXT_PUBLIC_VAULT_API_KEY ?? "vault-test-key-do-not-use-in-production";

export async function ingestRecord(
  payload: IngestPayload,
): Promise<IngestResult> {
  try {
    const response = await fetch(`${API_BASE}/ingest`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-API-Key": API_KEY,
      },
      body: JSON.stringify(payload),
    });

    let data: unknown = null;
    try {
      data = await response.json();
    } catch {
      data = null;
    }

    return {
      ok: response.ok,
      status: response.status,
      data,
    };
  } catch (error) {
    const message = error instanceof Error ? error.message : "Network error";

    return {
      ok: false,
      status: 0,
      data: null,
      error: message,
    };
  }
}

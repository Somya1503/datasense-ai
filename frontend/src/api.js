// All backend communication lives here, separate from the UI.
// Override with a .env file later: VITE_API_URL=https://your-app.onrender.com
const API_BASE = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

export async function checkHealth() {
  try {
    const response = await fetch(`${API_BASE}/health`);
    if (!response.ok) return false;
    const data = await response.json();
    return data.status === "healthy";
  } catch {
    return false;
  }
}

export async function analyzeCsv(file) {
  const formData = new FormData();
  formData.append("file", file); // field name must be "file"

  let response;
  try {
    // No Content-Type header: the browser sets the multipart boundary itself.
    response = await fetch(`${API_BASE}/analyze`, {
      method: "POST",
      body: formData,
    });
  } catch {
    throw new Error(
      "Cannot reach the backend. Make sure uvicorn is running on http://127.0.0.1:8000."
    );
  }

  let data = null;
  try {
    data = await response.json();
  } catch {
    // Response was not JSON; fall through to the generic message.
  }

  if (!response.ok) {
    const detail =
      data && typeof data.detail === "string"
        ? data.detail
        : `The request failed (status ${response.status}).`;
    throw new Error(detail);
  }
  return data;
}
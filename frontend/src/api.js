// Cliente HTTP minimo. O token e o actor vivem so em memoria (nunca em localStorage).

export class ApiError extends Error {
  constructor(status, message) {
    super(message);
    this.status = status;
  }
}

function describeDetail(detail) {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail.map((item) => (item && item.msg ? item.msg : String(item))).join("; ");
  }
  return "erro desconhecido";
}

export async function apiRequest(path, { token, actor, method = "GET", body } = {}) {
  const headers = {};
  if (token) headers.Authorization = `Bearer ${token}`;
  if (actor) headers["X-Actor"] = actor;
  if (body !== undefined) headers["Content-Type"] = "application/json";
  let response;
  try {
    response = await fetch(path, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch {
    throw new ApiError(0, "sem ligação à API");
  }
  let data = null;
  try {
    data = await response.json();
  } catch {
    data = null;
  }
  if (!response.ok) {
    throw new ApiError(response.status, describeDetail(data?.detail) || response.statusText);
  }
  return data;
}

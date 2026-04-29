const API_BASE_URL = "http://47.106.32.222:8001";

async function request(path, options = {}) {
  const res = await fetch(`${API_BASE_URL}${path}`, options);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(data.detail || `Request failed: ${res.status}`);
  }
  return data;
}

export async function uploadExamFiles(files, ruleProfileId, layoutAdjustments = null) {
  const formData = new FormData();
  files.forEach((file) => formData.append("files", file));
  if (ruleProfileId !== undefined && ruleProfileId !== null && ruleProfileId !== "") {
    formData.append("ruleProfileId", String(ruleProfileId));
  }
  if (
    layoutAdjustments &&
    typeof layoutAdjustments === "object" &&
    Object.keys(layoutAdjustments).length > 0
  ) {
    formData.append("layoutAdjustments", JSON.stringify(layoutAdjustments));
  }
  return request("/api/v1/recognitions/upload", {
    method: "POST",
    body: formData,
  });
}

export async function getTaskStatus(taskId) {
  return request(`/api/v1/recognitions/tasks/${taskId}`);
}

export async function getTaskResult(taskId) {
  return request(`/api/v1/recognitions/tasks/${taskId}/result`);
}

export async function getTaskDetails(taskId) {
  return request(`/api/v1/recognitions/tasks/${taskId}/details`);
}

export async function listRecognitionTasks(limit = 100, offset = 0) {
  const safeLimit = Number.isFinite(Number(limit)) ? Number(limit) : 100;
  const safeOffset = Number.isFinite(Number(offset)) ? Number(offset) : 0;
  return request(`/api/v1/recognitions/tasks?limit=${safeLimit}&offset=${safeOffset}`);
}

export async function clearRecognitionTasks() {
  return request("/api/v1/recognitions/tasks", {
    method: "DELETE",
  });
}

export async function listRuleProfiles() {
  return request("/api/v1/rule-profiles");
}

export const apiBaseUrl = API_BASE_URL;

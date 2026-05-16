const AGENTGUARD_DECISION_HEADER = "x-agentguard-decision";
const AGENTGUARD_BLOCK_STATUS = 403;

function headerValue(headers, name) {
  if (!headers) return null;
  const wanted = name.toLowerCase();

  if (typeof headers.get === "function") {
    return headers.get(name) ?? headers.get(wanted);
  }

  if (Array.isArray(headers)) {
    for (const item of headers) {
      if (!Array.isArray(item) || item.length < 2) continue;
      if (String(item[0]).toLowerCase() === wanted) return String(item[1]);
    }
    return null;
  }

  if (typeof headers === "object") {
    for (const [key, value] of Object.entries(headers)) {
      if (String(key).toLowerCase() === wanted) return String(value);
    }
  }

  return null;
}

function statusCode(response) {
  const raw = response?.status ?? response?.statusCode;
  const parsed = Number.parseInt(String(raw), 10);
  return Number.isFinite(parsed) ? parsed : null;
}

function extractBlockReason(response) {
  const body =
    response?.bodyText ??
    response?.text ??
    response?.body ??
    response?.data ??
    "";
  if (typeof body !== "string" || body.trim() === "") return null;

  const reasonMatch = body.match(/(?:^|\n)\s*Reason:\s*(.+)$/is);
  if (reasonMatch) return reasonMatch[1].trim();
  return body.trim();
}

export function isAgentGuardBlockResponse(response) {
  const decision = headerValue(response?.headers, AGENTGUARD_DECISION_HEADER);
  return (
    statusCode(response) === AGENTGUARD_BLOCK_STATUS &&
    typeof decision === "string" &&
    decision.toLowerCase() === "block"
  );
}

export function detectAgentGuardBlock(response) {
  const blocked = isAgentGuardBlockResponse(response);
  return {
    blocked,
    statusCode: statusCode(response),
    decision: headerValue(response?.headers, AGENTGUARD_DECISION_HEADER),
    reason: blocked ? extractBlockReason(response) : null,
  };
}

export { AGENTGUARD_BLOCK_STATUS, AGENTGUARD_DECISION_HEADER };

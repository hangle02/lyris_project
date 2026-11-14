import { test } from "node:test";
import assert from "node:assert/strict";
import { ApiError, api, codeOf, detailToText, errorMessage, errorTechnical, locToText, streamChat, technicalOf } from "./client.ts";
import type { ChatStreamEvent } from "../types.ts";

test("locToText: field path without FastAPI's where-prefix", () => {
  assert.equal(locToText(["body", "handle"]), "handle");
  assert.equal(locToText(["body", "card", "address_terms", "self_term"]), "card.address_terms.self_term");
  assert.equal(locToText(["query", "card_id"]), "card_id");
  assert.equal(locToText(["body", "tags", 0]), "tags.0");
  assert.equal(locToText(["body"]), "");
  assert.equal(locToText(undefined), "");
  assert.equal(locToText("handle"), "");
});

test("detailToText keeps where each 422 error is", () => {
  assert.equal(detailToText("Không tìm thấy story."), "Không tìm thấy story.");
  assert.equal(
    detailToText([{ loc: ["body", "handle"], msg: "String should have at least 3 characters", type: "string_too_short" }]),
    "Dữ liệu không hợp lệ: handle: String should have at least 3 characters",
  );
  assert.equal(
    detailToText([
      { loc: ["body", "display_name"], msg: "Field required" },
      { loc: ["body"], msg: "Invalid JSON" },
      { msg: "" },
      "rác",
    ]),
    "Dữ liệu không hợp lệ: display_name: Field required; Invalid JSON",
  );
  assert.equal(detailToText([]), null);
  assert.equal(detailToText({ x: 1 }), null);
});

test("technicalOf reads the Phase 3b `technical` field", () => {
  assert.equal(technicalOf({ detail: "Nhân vật đang bận.", technical: " stream active " }), "stream active");
  assert.equal(technicalOf({ detail: "x" }), null);
  assert.equal(technicalOf({ technical: 3 }), null);
  assert.equal(technicalOf(null), null);
});

test("errorMessage is plain; errorTechnical keeps the raw text", () => {
  const e = new ApiError(500, "Ollama báo lỗi (HTTP 500): out of memory");
  assert.doesNotMatch(errorMessage(e), /ollama|http/i);
  assert.equal(errorTechnical(e), "Ollama báo lỗi (HTTP 500): out of memory");
  const plain = new ApiError(409, "Nhân vật đang trả lời, đợi một chút.", "busy: stream 12");
  assert.equal(errorMessage(plain), "Nhân vật đang trả lời, đợi một chút.");
  assert.equal(errorTechnical(plain), "busy: stream 12");
  assert.equal(errorTechnical(new Error("Story này không còn.")), null);
});

// ---- Phase 4b (docs/auth.md §7.1, §8.2) ----

interface Sent {
  url: string;
  init: RequestInit;
}

/** Replaces fetch and dispatchEvent for one test; returns what was sent and dispatched. */
function fakeNetwork(respond: (url: string) => Response) {
  const sent: Sent[] = [];
  const events: { type: string; detail: unknown }[] = [];
  const g = globalThis as unknown as Record<string, unknown>;
  const before = { fetch: g.fetch, dispatchEvent: g.dispatchEvent };
  g.fetch = async (url: string, init: RequestInit) => {
    sent.push({ url, init });
    return respond(url);
  };
  g.dispatchEvent = (e: Event) => {
    events.push({ type: e.type, detail: (e as CustomEvent).detail });
    return true;
  };
  return {
    sent,
    events,
    restore: () => {
      g.fetch = before.fetch;
      g.dispatchEvent = before.dispatchEvent;
    },
  };
}

const json = (status: number, body: unknown) =>
  new Response(status === 204 ? null : JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });

function header(init: RequestInit, name: string): string | null {
  return new Headers(init.headers).get(name);
}

test("every request (read, write, upload, stream) sends X-Lyris and the sign-in cookie", async () => {
  const net = fakeNetwork((url) =>
    url.endsWith("/messages")
      ? new Response("event: waiting\ndata: {}\n\nevent: start\ndata: {\"turn_index\": 2, \"variant_index\": 0}\n\n", { status: 200 })
      : json(200, { ok: true }),
  );
  try {
    await api.listStories();
    await api.createPersona({ id: null, name: "Lâm", gender: "female", description: "" });
    await api.deleteStory(3);
    await api.uploadAvatar(4, new Blob(["x"], { type: "image/png" }));
    const seen: ChatStreamEvent["name"][] = [];
    await streamChat("/stories/3/messages", { content: "chào" }, (ev) => seen.push(ev.name), new AbortController().signal);
    assert.deepEqual(seen, ["waiting", "start"]);
    assert.equal(net.sent.length, 5);
    for (const s of net.sent) {
      assert.equal(header(s.init, "X-Lyris"), "1", s.url);
      assert.equal(s.init.credentials, "same-origin", s.url);
    }
  } finally {
    net.restore();
  }
});

test("a 401 anywhere tells the gate (lyris:auth); the sign-in forms do not", async () => {
  const net = fakeNetwork((url) =>
    url.includes("/auth/login")
      ? json(401, { detail: "Tên đăng nhập hoặc mật khẩu không đúng.", technical: null })
      : json(401, { detail: "Bạn đã bị đăng xuất. Hãy đăng nhập lại.", technical: null, code: "auth_required" }),
  );
  try {
    await assert.rejects(api.listStories(), (e: unknown) => e instanceof ApiError && e.status === 401 && e.code === "auth_required");
    assert.deepEqual(net.events, [{ type: "lyris:auth", detail: { status: 401, code: "auth_required" } }]);
    await assert.rejects(api.login({ handle: "ban", password: "sai mật khẩu" }), (e: unknown) => e instanceof ApiError && e.status === 401);
    assert.equal(net.events.length, 1);
  } finally {
    net.restore();
  }
});

test("403 password_change_required tells the gate; owner_only does not, and reads plainly", async () => {
  const net = fakeNetwork((url) =>
    url.includes("/admin/")
      ? json(403, { detail: "Chỉ chủ máy làm được việc này.", technical: null, code: "owner_only" })
      : json(403, { detail: "Hãy đặt mật khẩu mới để tiếp tục.", technical: null, code: "password_change_required" }),
  );
  try {
    await assert.rejects(api.listAdminAccounts(), (e: unknown) => e instanceof ApiError && errorMessage(e) === "Chỉ chủ máy làm được việc này.");
    assert.equal(net.events.length, 0);
    await assert.rejects(api.listCards());
    assert.deepEqual(net.events.map((e) => e.type), ["lyris:auth"]);
  } finally {
    net.restore();
  }
});

test("429 and bodies without a sentence still read in plain Vietnamese", async () => {
  const net = fakeNetwork(() => new Response("", { status: 429 }));
  try {
    await assert.rejects(api.listStories(), (e: unknown) => errorMessage(e) === "Bạn đã thử sai nhiều lần. Hãy đợi 15 phút rồi thử lại.");
  } finally {
    net.restore();
  }
  assert.equal(codeOf({ detail: "x", code: "rate_limited" }), "rate_limited");
  assert.equal(codeOf({ detail: "x" }), null);
  assert.equal(codeOf({ code: 3 }), null);
});

test("createCard says when a picture follows, so character_created.has_avatar is right", async () => {
  const net = fakeNetwork(() => json(200, { id: 9 }));
  try {
    const card = { name: "Lâm" } as unknown as Parameters<typeof api.createCard>[0];
    await api.createCard(card, null, "form", true);
    await api.createCard(card, "tok", "import");
    const [withPicture, imported] = net.sent;
    assert.ok(withPicture && imported);
    assert.match(withPicture.url, /\/cards\?via=form&with_avatar=true$/);
    assert.match(imported.url, /\/cards\?via=import$/);
    assert.equal(JSON.parse(String(imported.init.body)).avatar_token, "tok");
  } finally {
    net.restore();
  }
});

test("reportCard and unpublishCard hit the character report routes", async () => {
  const net = fakeNetwork(() => json(200, { id: 1, reason: "hateful", shared_text: false, status: "open" }));
  try {
    await api.reportCard(12, { reason: "hateful", note: "" });
    await api.unpublishCard(12);
    const [report, hide] = net.sent;
    assert.ok(report && hide);
    assert.match(report.url, /\/api\/cards\/12\/report$/);
    assert.equal(report.init.method, "POST");
    assert.deepEqual(JSON.parse(String(report.init.body)), { reason: "hateful", note: "" });
    assert.match(hide.url, /\/api\/admin\/cards\/12\/unpublish$/);
  } finally {
    net.restore();
  }
});

test("a network failure does not blame 'this machine' (open web: Lyris runs on a server)", async () => {
  const g = globalThis as unknown as Record<string, unknown>;
  const before = g.fetch;
  g.fetch = async () => {
    throw new TypeError("Failed to fetch");
  };
  try {
    await assert.rejects(api.listStories(), (e: unknown) => {
      const text = errorMessage(e);
      return !/máy này|Mac/.test(text) && /kết nối/.test(text);
    });
  } finally {
    g.fetch = before;
  }
});

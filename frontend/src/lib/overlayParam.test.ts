import { test } from "node:test";
import assert from "node:assert/strict";
import { initialOverlayOpen, initialTab, overlayFromSearch, tabFromSearch } from "./overlayParam.ts";

test("overlayFromSearch đọc ?open=", () => {
  assert.equal(overlayFromSearch("?open=system"), "system");
  assert.equal(overlayFromSearch("?theme=light&open=heart"), "heart");
  assert.equal(overlayFromSearch("open=settings"), "settings");
  assert.equal(overlayFromSearch("?open=%20Heart%20"), "heart");
  assert.equal(overlayFromSearch("?open=profile"), "profile");
});

test("overlayFromSearch bỏ qua giá trị lạ", () => {
  assert.equal(overlayFromSearch(""), null);
  assert.equal(overlayFromSearch("?open="), null);
  assert.equal(overlayFromSearch("?open=menu"), null);
  assert.equal(overlayFromSearch("?theme=dark"), null);
});

test("initialOverlayOpen trả false khi không có window", () => {
  assert.equal(initialOverlayOpen("system"), false);
});

test("tabFromSearch chỉ nhận tab cho phép", () => {
  const tabs = ["characters", "personas"] as const;
  assert.equal(tabFromSearch("?tab=personas", tabs), "personas");
  assert.equal(tabFromSearch("?theme=light&tab=%20Personas", tabs), "personas");
  assert.equal(tabFromSearch("?tab=posts", tabs), null);
  assert.equal(tabFromSearch("", tabs), null);
  assert.equal(initialTab(tabs, "characters"), "characters");
});

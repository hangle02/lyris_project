import { test } from "node:test";
import assert from "node:assert/strict";
import { formatGb, machineStatus, memorySearchRow, memoryText, onOff, plainMachineLine } from "./status.ts";

test("machineStatus: connection first, then power", () => {
  assert.equal(machineStatus("checking", null).tone, "checking");
  assert.deepEqual(machineStatus("down", { on_battery: true, low_power_mode: true }), {
    tone: "down",
    short: "Mất kết nối",
    long: "Không kết nối được Ollama",
  });
  assert.equal(machineStatus("warn", null).tone, "warn");
  assert.deepEqual(machineStatus("ok", null), { tone: "ok", short: "M2 sẵn sàng", long: "Hoạt động êm ái" });
  assert.deepEqual(machineStatus("ok", { on_battery: false, low_power_mode: null }).tone, "ok");
  assert.equal(machineStatus("ok", { on_battery: true, low_power_mode: false }).short, "Đang chạy pin");
  assert.equal(machineStatus("ok", { on_battery: true, low_power_mode: false }).long, "Đang chạy pin, sẽ chậm hơn");
  assert.equal(machineStatus("ok", { on_battery: false, low_power_mode: true }).short, "Tiết kiệm pin");
});

test("memoryText and formatGb", () => {
  assert.equal(memoryText(9.42, 24), "9.4 GB / 24 GB");
  assert.equal(memoryText(16, 24.0), "16 GB / 24 GB");
  assert.equal(memoryText(0, 24), "0 GB / 24 GB");
  assert.equal(memoryText(null, 24), null);
  assert.equal(memoryText(3, 0), null);
  assert.equal(formatGb(4.96), "5 GB");
  assert.equal(formatGb(0.35), "0.4 GB");
});

test("onOff", () => {
  assert.equal(onOff(true), "Bật");
  assert.equal(onOff(false), "Tắt");
  assert.equal(onOff(null), null);
  assert.equal(onOff(undefined), null);
});

test("memorySearchRow: keyword with a pull hint, meaning search without", () => {
  assert.deepEqual(memorySearchRow({ memory_search: "keyword", embed_model: "bge-m3", ollama_reachable: true }), {
    value: "Tìm theo từ khoá",
    pull: "ollama pull bge-m3",
  });
  assert.deepEqual(memorySearchRow({ memory_search: "hybrid", embed_model: "bge-m3", ollama_reachable: true }), {
    value: "Tìm theo nghĩa, bge-m3",
    pull: null,
  });
  // Ollama down: pulling cannot help right now.
  assert.equal(memorySearchRow({ memory_search: "keyword", embed_model: "bge-m3", ollama_reachable: false }).pull, null);
  // Older server without the fields.
  assert.deepEqual(memorySearchRow({ ollama_reachable: true }), { value: "Tìm theo từ khoá", pull: null });
});

test("plainMachineLine: only when something is wrong, no technical words", () => {
  assert.equal(plainMachineLine("ok"), null);
  assert.equal(plainMachineLine("checking"), null);
  for (const level of ["down", "warn"] as const) {
    const line = plainMachineLine(level);
    assert.ok(line);
    assert.doesNotMatch(line, /ollama|model/i);
  }
});

// Incremental Server-Sent Events parser (WHATWG "event stream" interpretation),
// for SSE read from a fetch() ReadableStream. Chunks may split anywhere: inside a
// line, between "\r" and "\n", or inside a multi-byte UTF-8 character (the caller
// decodes with TextDecoder({stream: true}), so we only ever see whole code points).

export interface SSEMessage {
  /** Value of the last `event:` field, or "message" when absent. */
  event: string;
  /** All `data:` lines joined with "\n". */
  data: string;
  /** Value of the last `id:` field, if any. */
  id: string | null;
}

export class SSEParser {
  private buffer = "";
  private eventName = "";
  private dataLines: string[] = [];
  private hasData = false;
  private lastId: string | null = null;
  private pendingCR = false;

  /** Feed decoded text; returns every event completed by this chunk. */
  feed(chunk: string): SSEMessage[] {
    const out: SSEMessage[] = [];
    let text = chunk;
    if (this.pendingCR) {
      // A previous chunk ended with "\r": it already terminated a line.
      // Swallow a "\n" that completes a "\r\n" pair.
      this.pendingCR = false;
      if (text.startsWith("\n")) text = text.slice(1);
    }
    this.buffer += text;

    let start = 0;
    for (let i = 0; i < this.buffer.length; i++) {
      const ch = this.buffer.charCodeAt(i);
      if (ch !== 10 /* \n */ && ch !== 13 /* \r */) continue;
      const line = this.buffer.slice(start, i);
      if (ch === 13) {
        if (i + 1 < this.buffer.length) {
          if (this.buffer.charCodeAt(i + 1) === 10) i++;
        } else {
          this.pendingCR = true;
        }
      }
      start = i + 1;
      const ev = this.processLine(line);
      if (ev) out.push(ev);
    }
    this.buffer = this.buffer.slice(start);
    return out;
  }

  /**
   * Call at end of stream. Per spec an unterminated final event is discarded, but
   * servers sometimes omit the trailing blank line, so we dispatch it if it has data.
   */
  flush(): SSEMessage[] {
    const out: SSEMessage[] = [];
    if (this.buffer.length > 0) {
      const ev = this.processLine(this.buffer);
      this.buffer = "";
      if (ev) out.push(ev);
    }
    const ev = this.dispatch();
    if (ev) out.push(ev);
    this.pendingCR = false;
    return out;
  }

  private processLine(line: string): SSEMessage | null {
    if (line === "") return this.dispatch();
    if (line.startsWith(":")) return null; // comment / keep-alive

    const colon = line.indexOf(":");
    let field: string;
    let value: string;
    if (colon === -1) {
      field = line;
      value = "";
    } else {
      field = line.slice(0, colon);
      value = line.slice(colon + 1);
      if (value.startsWith(" ")) value = value.slice(1);
    }

    switch (field) {
      case "event":
        this.eventName = value;
        break;
      case "data":
        this.dataLines.push(value);
        this.hasData = true;
        break;
      case "id":
        if (!value.includes("\u0000")) this.lastId = value;
        break;
      default:
        // "retry" and unknown fields are ignored.
        break;
    }
    return null;
  }

  private dispatch(): SSEMessage | null {
    const hadData = this.hasData;
    const ev: SSEMessage = {
      event: this.eventName || "message",
      data: this.dataLines.join("\n"),
      id: this.lastId,
    };
    this.eventName = "";
    this.dataLines = [];
    this.hasData = false;
    return hadData ? ev : null;
  }
}

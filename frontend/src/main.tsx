import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

// Self-hosted fonts (work offline), only the weights the design uses; each file carries the
// Vietnamese subset. Brand: wordmark only. UI: Plus Jakarta Sans. Story text: Be Vietnam Pro.
import "@fontsource/cormorant-garamond/600-italic.css";
import "@fontsource/cormorant-garamond/700-italic.css";
import "@fontsource/plus-jakarta-sans/400.css";
import "@fontsource/plus-jakarta-sans/500.css";
import "@fontsource/plus-jakarta-sans/600.css";
import "@fontsource/plus-jakarta-sans/700.css";
import "@fontsource/be-vietnam-pro/300.css";
import "@fontsource/be-vietnam-pro/400.css";
import "@fontsource/be-vietnam-pro/400-italic.css";
import "@fontsource/be-vietnam-pro/500.css";

import App from "./App";
import "./index.css";
import { migrateLegacyKeys } from "./lib/legacyStorage";
import { ThemeProvider } from "./theme/ThemeProvider";

try {
  migrateLegacyKeys(window.localStorage);
} catch {
  // storage unavailable (private mode): nothing to move
}

const root = document.getElementById("root");
if (!root) throw new Error("Không tìm thấy phần tử #root");

createRoot(root).render(
  <StrictMode>
    <ThemeProvider>
      <App />
    </ThemeProvider>
  </StrictMode>,
);

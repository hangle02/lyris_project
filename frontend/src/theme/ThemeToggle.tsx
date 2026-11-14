import { IconMoon, IconSun } from "../components/icons";
import { IconButton } from "../components/ui/Button";
import type { ButtonSize } from "../components/ui/Button";
import { useTheme } from "./ThemeProvider";

/**
 * Header button that switches Velvet Nocturne (dark) and Rosewater Parchment (light). Shows the
 * theme it will switch to: a sun in dark, a moon in light.
 */
export function ThemeToggle({ size = "md", className }: { size?: ButtonSize; className?: string }) {
  const { theme, toggleTheme } = useTheme();
  const toLight = theme === "dark";
  return (
    <IconButton
      label={toLight ? "Chuyển sang giao diện sáng" : "Chuyển sang giao diện tối"}
      icon={toLight ? <IconSun /> : <IconMoon />}
      size={size}
      onClick={toggleTheme}
      className={className}
    />
  );
}

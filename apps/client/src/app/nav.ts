// The app's sections, in menu order. Only finished sections are listed: there are no placeholder
// pages. The admin items (technical pages, account) are hidden until the admin mode is unlocked. On a phone the bottom bar shows the `primary` ones and a "More" page lists them all.
import type { Messages } from "../i18n";

export type IconName =
  | "home" | "search" | "book" | "cards" | "grammar" | "tests" | "spell" | "reading" | "calendar" | "user" | "settings" | "info" | "more" | "shield";

export interface NavItem {
  to: string;
  label: (m: Messages) => string;
  icon: IconName;
  primary?: boolean;
  /** Shown only while the admin mode is unlocked (src/stores/admin.ts). */
  admin?: boolean;
}

export const NAV: NavItem[] = [
  { to: "/", label: (m) => m.nav.home, icon: "home", primary: true },
  { to: "/dictionary", label: (m) => m.nav.dictionary, icon: "book", primary: true },
  { to: "/cards", label: (m) => m.nav.cards, icon: "cards", primary: true },
  { to: "/reading", label: (m) => m.nav.reading, icon: "reading" },
  { to: "/tests", label: (m) => m.nav.tests, icon: "tests" },
  { to: "/grammar", label: (m) => m.nav.grammar, icon: "grammar" },
  { to: "/spell", label: (m) => m.nav.spell, icon: "spell" },
  { to: "/calendar", label: (m) => m.nav.calendar, icon: "calendar" },
  { to: "/analyze", label: (m) => m.nav.analyze, icon: "search", primary: true },
  { to: "/account", label: (m) => m.nav.account, icon: "user", admin: true },
  { to: "/settings", label: (m) => m.nav.settings, icon: "settings" },
  { to: "/about", label: (m) => m.nav.about, icon: "info" },
  { to: "/admin", label: (m) => m.nav.admin, icon: "shield", admin: true },
];

/** The menu for the current mode: admin items only while it is unlocked. */
export const visibleNav = (adminUnlocked: boolean): NavItem[] => NAV.filter((item) => adminUnlocked || !item.admin);

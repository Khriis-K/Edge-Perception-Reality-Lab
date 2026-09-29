import { Icon } from "@blueprintjs/core";
import { NavLink } from "react-router";
import { SECTIONS } from "./sections";

/** Icon-only section links. NavLink sets aria-current="page", which the CSS marks with a bar. */
export function Rail() {
  return (
    <nav aria-label="Sections" className="rail">
      <ul>
        {SECTIONS.map((section) => (
          <li key={section.id}>
            <NavLink to={`/${section.id}`} className="rail-link" aria-label={section.label} title={section.label}>
              <Icon icon={section.icon} size={16} aria-hidden />
            </NavLink>
          </li>
        ))}
      </ul>
      <span className="rail-version">v0.1</span>
    </nav>
  );
}

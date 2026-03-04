/**
 * Shared DOM helper utilities.
 *
 * These tiny helpers are used across many page modules to look up
 * elements and read form values by ID. Centralising them here
 * eliminates ~19 duplicate inline declarations.
 */

/** Get an element by its ID. */
export const el = (id: string): HTMLElement | null =>
  document.getElementById(id);

/** Get the string value of an input element by its ID. */
export const val = (id: string): string =>
  (document.getElementById(id) as HTMLInputElement)?.value ?? '';

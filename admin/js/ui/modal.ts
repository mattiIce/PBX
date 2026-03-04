/**
 * Centralized modal management with full accessibility support.
 *
 * Provides focus trapping, Escape key handling, backdrop click-to-close,
 * ARIA attributes (role="dialog", aria-modal, aria-labelledby), and
 * focus restoration on close.
 */

const FOCUSABLE_SELECTOR =
  'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

/** Stack of previously focused elements, one per open modal. */
const focusReturnStack: HTMLElement[] = [];

/** Active keydown handler for the currently open modal (for cleanup). */
let activeTrapHandler: ((e: KeyboardEvent) => void) | null = null;

/**
 * Open a modal by element ID, adding accessibility attributes
 * and trapping focus inside it.
 */
export function openModal(modalId: string): void {
  const modal = document.getElementById(modalId);
  if (!modal) return;

  // Save the element that had focus so we can restore it on close.
  const previouslyFocused = document.activeElement as HTMLElement | null;
  if (previouslyFocused) {
    focusReturnStack.push(previouslyFocused);
  }

  // --- ARIA attributes ---
  modal.setAttribute('role', 'dialog');
  modal.setAttribute('aria-modal', 'true');

  // Point aria-labelledby at the modal heading, generating an id if needed.
  const heading = modal.querySelector('.modal-header h3') as HTMLElement | null;
  if (heading) {
    if (!heading.id) {
      heading.id = `${modalId}-heading`;
    }
    modal.setAttribute('aria-labelledby', heading.id);
  }

  // Show the modal — support both the classList and display-based patterns.
  modal.classList.add('active');
  modal.style.display = 'block';

  // Move focus to the first focusable element inside modal-content.
  requestAnimationFrame(() => {
    const content = modal.querySelector('.modal-content') as HTMLElement | null;
    const target = content ?? modal;
    const firstFocusable = target.querySelector(FOCUSABLE_SELECTOR) as HTMLElement | null;
    if (firstFocusable) {
      firstFocusable.focus();
    }
  });

  // Install focus-trap keydown listener.
  cleanupTrapHandler();

  activeTrapHandler = (e: KeyboardEvent) => {
    if (e.key === 'Escape') {
      e.stopPropagation();
      closeModal(modalId);
      return;
    }
    if (e.key !== 'Tab') return;

    const content = modal.querySelector('.modal-content') as HTMLElement | null;
    const container = content ?? modal;
    const focusables = Array.from(
      container.querySelectorAll(FOCUSABLE_SELECTOR),
    ) as HTMLElement[];
    if (focusables.length === 0) return;

    const first = focusables[0];
    const last = focusables[focusables.length - 1];

    if (e.shiftKey) {
      if (document.activeElement === first && last) {
        e.preventDefault();
        last.focus();
      }
    } else {
      if (document.activeElement === last && first) {
        e.preventDefault();
        first.focus();
      }
    }
  };

  document.addEventListener('keydown', activeTrapHandler, true);

  // Backdrop click-to-close: clicking the .modal overlay itself (not its children).
  modal.addEventListener('click', handleBackdropClick);
}

/**
 * Close a modal by element ID, restoring focus to the previously
 * focused element.
 */
export function closeModal(modalId: string): void {
  const modal = document.getElementById(modalId);
  if (!modal) return;

  modal.classList.remove('active');
  modal.style.display = 'none';

  // Clean up ARIA attributes so they don't linger on hidden elements.
  modal.removeAttribute('aria-modal');

  // Remove listeners.
  cleanupTrapHandler();
  modal.removeEventListener('click', handleBackdropClick);

  // Restore focus.
  const previouslyFocused = focusReturnStack.pop();
  if (previouslyFocused && typeof previouslyFocused.focus === 'function') {
    previouslyFocused.focus();
  }
}

/** Close when user clicks the backdrop (the .modal element itself). */
function handleBackdropClick(e: Event): void {
  const modal = e.currentTarget as HTMLElement;
  if (e.target === modal) {
    closeModal(modal.id);
  }
}

/** Remove the active keydown trap handler if one exists. */
function cleanupTrapHandler(): void {
  if (activeTrapHandler) {
    document.removeEventListener('keydown', activeTrapHandler, true);
    activeTrapHandler = null;
  }
}

/**
 * Initialize all modal close buttons in the document.
 *
 * Finds every `.modal .close` element and wires up a click handler
 * that closes the parent modal, so inline onclick attributes can be
 * removed from the HTML.
 */
export function initializeModalCloseButtons(): void {
  for (const btn of document.querySelectorAll('.modal .close')) {
    const modal = btn.closest('.modal') as HTMLElement | null;
    if (!modal?.id) continue;

    const modalId = modal.id;
    btn.addEventListener('click', () => closeModal(modalId));
  }
}

// Register on window for backward compatibility with non-modular code.
(window as unknown as Record<string, unknown>).openModal = openModal;
(window as unknown as Record<string, unknown>).closeModal = closeModal;

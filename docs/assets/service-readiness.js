/**
 * Public site readiness for CommerceLint paid checkout.
 * Paid Stripe checkout remains unavailable until sandbox acceptance is observed.
 */
(() => {
  'use strict';
  const readiness = Object.freeze({
    paid_checkout_available: false,
    stripe_sandbox_observed: false,
    allowed_public_actions: Object.freeze(['request_plan', 'free_scanner', 'read_guides']),
    message: 'Paid checkout is unavailable. Request a plan or use the free scanner.',
  });
  window.commerceLintServiceReadiness = readiness;

  function annotateUnavailableCheckout() {
    document.querySelectorAll('[data-cl-paid-checkout]').forEach((node) => {
      node.setAttribute('aria-disabled', 'true');
      node.setAttribute('title', readiness.message);
      if (node.tagName === 'A') {
        node.addEventListener('click', (event) => {
          event.preventDefault();
        });
      }
      if (node.tagName === 'BUTTON') {
        node.disabled = true;
      }
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', annotateUnavailableCheckout);
  } else {
    annotateUnavailableCheckout();
  }
})();

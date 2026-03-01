/**
 * content.js - Entry point for the Rent Recon content script.
 *
 * Runs on every Facebook page. Initializes the button injector
 * that adds "Analyze Listing" buttons to posts.
 */

import "./content.css";
import { initInjector } from "./injector.js";

// Wait for page to be ready, then initialize
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initInjector);
} else {
  initInjector();
}

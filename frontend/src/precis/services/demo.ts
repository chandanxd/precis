/**
 * Demo mode swaps real backend calls for bundled fixtures when the backend is
 * unavailable. It must be opted into explicitly (VITE_DEMO_MODE=true); in normal
 * builds, backend failures surface as errors instead of fake data.
 */
export const DEMO_MODE = import.meta.env["VITE_DEMO_MODE"] === "true";

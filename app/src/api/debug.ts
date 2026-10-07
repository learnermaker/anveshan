/**
 * Team-only diagnostic view: add ?debug=1 to the URL.
 *
 * Not a product surface and never linked from the UI. When DEBUG is true the views also render the
 * technical panels (claim ids, confidence, provenance, run class, lineage, raw warnings). Learners,
 * creators and stewards never need it.
 */

function readDebug(): boolean {
  try {
    return new URLSearchParams(window.location.search).get('debug') === '1';
  } catch {
    return false;
  }
}

export const DEBUG: boolean = readDebug();

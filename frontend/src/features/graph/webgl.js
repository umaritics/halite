// The 3D graph needs WebGL. Some browsers (sandboxed panes, machines with hardware
// acceleration off) do not provide it, and the renderer throws when it is missing.
export function hasWebGL() {
  try {
    const canvas = document.createElement('canvas');
    const context = canvas.getContext('webgl') || canvas.getContext('experimental-webgl');
    return Boolean(window.WebGLRenderingContext && context);
  } catch {
    return false;
  }
}

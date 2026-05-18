import type { NextConfig } from 'next';
import path from 'path';

const nextConfig: NextConfig = {
  // Ensure Turbopack resolves the frontend directory as the workspace root
  turbopack: {
    // Use an absolute path to avoid Turbopack warnings and resolution issues
    root: path.resolve('.'),
  },
  // Note: removed legacy `experimental.middleware` flag because
  // it is not a recognized property on Next's `ExperimentalConfig` type.
};

export default nextConfig;

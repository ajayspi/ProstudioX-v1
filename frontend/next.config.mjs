/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Static export: produce a fully static `out/` that FastAPI serves directly,
  // so no Node.js runtime is needed on the server.
  output: "export",
};

export default nextConfig;

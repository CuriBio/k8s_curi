/** @type {import('next').NextConfig} */

const nextConfig = {
  reactStrictMode: true,
  images: {
    loader: "custom",
  },
  compiler: {
    // ssr and displayName are configured by default
    styledComponents: true,
  },
  api: {
    bodyParser: {
      sizeLimit: "4mb", // Set desired value here
    },
  },
  async redirects() {
    return [
      {
        source: "/",
        destination: "/login",
        permanent: true,
      },
    ];
  },
  future: { webpack5: true },
};

module.exports = nextConfig;

module.exports = {
  testMatch: '**/*.spec.js',
  timeout: 30000,
  use: {
    browserName: 'chromium',
    headless: true,
  },
};

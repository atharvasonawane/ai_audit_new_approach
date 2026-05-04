module.exports = {
  extends: [
    'plugin:vue/recommended',
    'plugin:vuejs-accessibility/recommended'
  ],
  parserOptions: {
    ecmaVersion: 2020,
    sourceType: 'module'
  },
  env: {
    browser: true,
    es6: true,
    node: true
  }
};

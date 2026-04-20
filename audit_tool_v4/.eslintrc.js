/**
 * .eslintrc.js — V4 Vue Audit Pipeline
 * ======================================
 * This config is used by the Python orchestrator — it IS NOT meant to
 * be a project-level config for the target repo. The orchestrator calls:
 *
 *   npx eslint <target_base_path> --ext .vue,.js --format json --no-eslintrc --config <path_to_this_file>
 *
 * That --no-eslintrc + --config pattern ensures we always use this file,
 * never accidentally picking up the target project's own ESLint config.
 *
 * Single pass covers THREE tool domains from MASTER_ARCHITECTURE §2:
 *   ✅ Parsing Base    — vue-eslint-parser (natively splits <template>/<script>/<style>)
 *   ✅ Syntax/Quality  — eslint-plugin-vue (vue3-recommended rule set)
 *   ✅ Accessibility   — eslint-plugin-vuejs-accessibility (WCAG ARIA checks)
 */

"use strict";

module.exports = {
  root: true,

  // ── Parser ──────────────────────────────────────────────────────────────────
  // vue-eslint-parser handles .vue SFCs natively, delegates <script> to
  // @babel/eslint-parser for modern JS/TS support.
  parser: "vue-eslint-parser",
  parserOptions: {
    parser: "@babel/eslint-parser",
    requireConfigFile: false,
    babelOptions: {
      plugins: ["@babel/plugin-syntax-import-assertions"],
    },
    ecmaVersion: 2022,
    sourceType: "module",
  },

  // ── Plugins ─────────────────────────────────────────────────────────────────
  plugins: [
    "vue",
    "vuejs-accessibility",
  ],

  // ── Rule Sets ───────────────────────────────────────────────────────────────
  extends: [
    "plugin:vue/vue3-recommended",             // Vue 3 structural + style rules
    "plugin:vuejs-accessibility/recommended",  // WCAG 2.1 aria/role/alt checks
  ],

  // ── Rule Overrides ───────────────────────────────────────────────────────────
  rules: {
    // Complexity heuristics (maps to Category.COMPLEXITY in schema_models)
    "complexity": ["warn", { max: 10 }],

    // Accessibility — escalate critical checks to errors
    "vuejs-accessibility/alt-text":          "error",
    "vuejs-accessibility/aria-role":         "error",
    "vuejs-accessibility/interactive-supports-focus": "warn",
    "vuejs-accessibility/label-has-for":     "warn",

    // Vue quality rules
    "vue/no-mutating-props":                 "error",
    "vue/no-unused-vars":                    "warn",
    "vue/require-v-for-key":                 "error",
    "vue/no-use-v-if-with-v-for":            "error",
    "vue/eqeqeq":                            "warn",

    // Relaxed rules (targets are third-party codebases — avoid false noise)
    "vue/multi-word-component-names":        "off",
    "vue/max-attributes-per-line":           "off",
    "vue/html-self-closing":                 "off",
  },

  // ── Ignore Patterns ──────────────────────────────────────────────────────────
  ignorePatterns: [
    "**/node_modules/**",
    "**/dist/**",
    "**/.nuxt/**",
    "**/.output/**",
    "**/coverage/**",
    "**/*.min.js",
  ],
};

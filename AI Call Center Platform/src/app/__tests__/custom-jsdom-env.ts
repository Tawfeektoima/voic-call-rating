/**
 * Custom JSDOM environment for Vitest.
 * 
 * Why this exists:
 * Node v20.9.0 handles ESM/CJS dual-package resolution differently than browsers. Some of our
 * dependencies (such as `@exodus/bytes` and `parse5`) fail to resolve correctly or cause ESM loaders
 * to crash when imported inside JSDOM tests.
 * 
 * To prevent ESM/CJS dual-package resolution hazards, this custom environment intercepts the
 * module resolution algorithm via Node's `module` API and redirects these packages to their
 * pre-bundled CommonJS (CJS) equivalent bundles.
 */
import { createRequire } from 'module';
import { builtinEnvironments } from 'vitest/environments';
import type { Environment } from 'vitest';

const require = createRequire(import.meta.url);
const Module = require('module');

// Patch node:vm constants for Node versions < 20.12.0
const vm = require('node:vm');
if (!vm.constants) {
  vm.constants = {};
}
if (vm.constants.DONT_CONTEXTIFY === undefined) {
  vm.constants.DONT_CONTEXTIFY = undefined;
}

// Override the module resolution immediately on file execution
const originalResolveFilename = Module._resolveFilename;
Module._resolveFilename = function (request: string, parent: any, isMain: boolean, options: any) {
  if (request === '@exodus/bytes/encoding-lite.js' || request === '@exodus/bytes/encoding-lite') {
    return require.resolve('./exodus-encoding-lite.cjs');
  }
  if (request === '@exodus/bytes/encoding.js' || request === '@exodus/bytes/encoding') {
    return require.resolve('./exodus-encoding.cjs');
  }
  if (request === '@exodus/bytes/whatwg.js' || request === '@exodus/bytes/whatwg') {
    return require.resolve('./exodus-whatwg.cjs');
  }
  if (request === '@exodus/bytes/base64.js' || request === '@exodus/bytes/base64') {
    return require.resolve('./exodus-base64.cjs');
  }
  if (request === 'parse5') {
    return require.resolve('./parse5-bundle.cjs');
  }
  if (request === '@asamuzakjp/css-color') {
    return require.resolve('./css-color-bundle.cjs');
  }
  if (request === '@asamuzakjp/dom-selector') {
    return require.resolve('./dom-selector-bundle.cjs');
  }
  return originalResolveFilename.apply(this, arguments);
};

export default <Environment>{
  name: 'custom-jsdom',
  transformMode: 'web',
  async setup(global, options) {
    // Setup the base jsdom environment
    const jsdom = await builtinEnvironments.jsdom.setup(global, options);

    return {
      async teardown(global) {
        await jsdom.teardown(global);
      },
    };
  },
};

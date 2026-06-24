var __defProp = Object.defineProperty;
var __getOwnPropDesc = Object.getOwnPropertyDescriptor;
var __getOwnPropNames = Object.getOwnPropertyNames;
var __hasOwnProp = Object.prototype.hasOwnProperty;
var __export = (target, all) => {
  for (var name in all)
    __defProp(target, name, { get: all[name], enumerable: true });
};
var __copyProps = (to, from, except, desc) => {
  if (from && typeof from === "object" || typeof from === "function") {
    for (let key of __getOwnPropNames(from))
      if (!__hasOwnProp.call(to, key) && key !== except)
        __defProp(to, key, { get: () => from[key], enumerable: !(desc = __getOwnPropDesc(from, key)) || desc.enumerable });
  }
  return to;
};
var __toCommonJS = (mod) => __copyProps(__defProp({}, "__esModule", { value: true }), mod);

// node_modules/@exodus/bytes/base64.js
var base64_exports2 = {};
__export(base64_exports2, {
  fromBase64: () => fromBase642,
  fromBase64any: () => fromBase64any,
  fromBase64url: () => fromBase64url,
  toBase64: () => toBase642,
  toBase64url: () => toBase64url
});
module.exports = __toCommonJS(base64_exports2);

// node_modules/@exodus/bytes/assert.js
function assertEmptyRest(rest) {
  if (Object.keys(rest).length > 0) throw new TypeError("Unexpected extra options");
}
var TypedArray = Object.getPrototypeOf(Uint8Array);

// node_modules/@exodus/bytes/fallback/platform.native.js
var { Buffer: Buffer2 } = globalThis;
var haveNativeBuffer = Buffer2 && !Buffer2.TYPED_ARRAY_SUPPORT;
var nativeBuffer = haveNativeBuffer ? Buffer2 : null;
var isHermes = /* @__PURE__ */ (() => !!globalThis.HermesInternal)();
var isDeno = /* @__PURE__ */ (() => !!globalThis.Deno)();
var isNative = (x) => x && (haveNativeBuffer || `${x}`.includes("[native code]"));
if (!haveNativeBuffer && isNative(() => {
})) isNative = () => false;
var nativeEncoder = /* @__PURE__ */ (() => isNative(globalThis.TextEncoder) ? new TextEncoder() : null)();
var nativeDecoder = /* @__PURE__ */ (() => isNative(globalThis.TextDecoder) ? new TextDecoder("utf-8", { ignoreBOM: true }) : null)();
var nativeDecoderLatin1 = /* @__PURE__ */ (() => {
  if (nativeDecoder) {
    try {
      return new TextDecoder("latin1", { ignoreBOM: true });
    } catch {
    }
  }
  return null;
})();
function encodeCharcodesHermes(str, arr) {
  const length = str.length;
  if (length > 64) {
    const at = str.charCodeAt.bind(str);
    for (let i = 0; i < length; i++) arr[i] = at(i);
  } else {
    for (let i = 0; i < length; i++) arr[i] = str.charCodeAt(i);
  }
  return arr;
}
function encodeCharcodesPure(str, arr) {
  const length = str.length;
  for (let i = 0; i < length; i++) arr[i] = str.charCodeAt(i);
  return arr;
}
var encodeCharcodes = isHermes ? encodeCharcodesHermes : encodeCharcodesPure;

// node_modules/@exodus/bytes/fallback/_utils.js
var Buffer3 = /* @__PURE__ */ (() => globalThis.Buffer)();
function assertU8(arg) {
  if (arg && arg instanceof Uint8Array) return;
  throw new TypeError("Expected an Uint8Array");
}
var E_STRING = "Input is not a string";
function fromUint8(arr, format) {
  switch (format) {
    case "uint8":
      if (arr.constructor !== Uint8Array) throw new Error("Unexpected");
      return arr;
    case "arraybuffer":
      if (arr.byteLength !== arr.buffer.byteLength) throw new Error("Unexpected");
      return arr.buffer;
    case "buffer":
      if (arr.length <= 64) return Buffer3.from(arr);
      return Buffer3.from(arr.buffer, arr.byteOffset, arr.byteLength);
  }
  throw new TypeError("Unexpected format");
}
function fromBuffer(arr, format) {
  switch (format) {
    case "uint8":
      if (arr.length <= 64 || arr.byteOffset !== 0 || arr.byteLength !== arr.buffer.byteLength) {
        return new Uint8Array(arr);
      }
      return new Uint8Array(arr.buffer, arr.byteOffset, arr.byteLength);
    case "arraybuffer":
      return arr.buffer.byteLength === arr.byteLength ? arr.buffer : arr.buffer.slice(arr.byteOffset, arr.byteOffset + arr.byteLength);
    case "buffer":
      if (arr.constructor !== Buffer3) throw new Error("Unexpected");
      return arr;
  }
  throw new TypeError("Unexpected format");
}

// node_modules/@exodus/bytes/fallback/latin1.js
var atob = /* @__PURE__ */ (() => globalThis.atob)();
var web64 = /* @__PURE__ */ (() => Uint8Array.prototype.toBase64)();
var maxFunctionArgs = 8192;
var useLatin1atob = web64 && atob;
function decodeLatin1(arr, start = 0, stop = arr.length) {
  start |= 0;
  stop |= 0;
  const total = stop - start;
  if (total === 0) return "";
  if (useLatin1atob && total >= 256 && total < 1e8 && arr.toBase64 === web64 && arr.BYTES_PER_ELEMENT === 1) {
    const sliced2 = start === 0 && stop === arr.length ? arr : arr.subarray(start, stop);
    return atob(sliced2.toBase64());
  }
  if (total > maxFunctionArgs) {
    let prefix = "";
    for (let i = start; i < stop; ) {
      const i1 = Math.min(stop, i + maxFunctionArgs);
      prefix += String.fromCharCode.apply(String, arr.subarray(i, i1));
      i = i1;
    }
    return prefix;
  }
  const sliced = start === 0 && stop === arr.length ? arr : arr.subarray(start, stop);
  return String.fromCharCode.apply(String, sliced);
}
var decodeAscii = nativeBuffer ? (a) => (
  // Buffer is faster on Node.js (but only for long enough data), if we know that output is ascii
  a.byteLength >= 768 && !isDeno ? nativeBuffer.from(a.buffer, a.byteOffset, a.byteLength).latin1Slice(0, a.byteLength) : nativeDecoder.decode(a)
) : nativeDecoderLatin1 ? (a) => nativeDecoderLatin1.decode(a) : (a) => decodeLatin1(
  a instanceof Uint8Array ? a : new Uint8Array(a.buffer, a.byteOffset, a.byteLength)
);
var encodeLatin1 = (str) => encodeCharcodes(str, new Uint8Array(str.length));
var useEncodeInto = /* @__PURE__ */ (() => isHermes && nativeEncoder?.encodeInto)();
var encodeAscii = useEncodeInto ? (str, ERR) => {
  const codes = new Uint8Array(str.length + 4);
  const info = nativeEncoder.encodeInto(str, codes);
  if (info.read !== str.length || info.written !== str.length) throw new SyntaxError(ERR);
  return codes.subarray(0, str.length);
} : nativeBuffer ? (str, ERR) => {
  const codes = nativeBuffer.from(str, "utf8");
  if (codes.length !== str.length) throw new SyntaxError(ERR);
  return new Uint8Array(codes.buffer, codes.byteOffset, codes.byteLength);
} : (str, ERR) => {
  const codes = nativeEncoder.encode(str);
  if (codes.length !== str.length) throw new SyntaxError(ERR);
  return codes;
};

// node_modules/@exodus/bytes/fallback/base64.js
var base64_exports = {};
__export(base64_exports, {
  E_CHAR: () => E_CHAR,
  E_LAST: () => E_LAST,
  E_LENGTH: () => E_LENGTH,
  E_PADDING: () => E_PADDING,
  fromBase64: () => fromBase64,
  toBase64: () => toBase64
});
var BASE64 = [..."ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"];
var BASE64URL = [..."ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"];
var BASE64_HELPERS = {};
var BASE64URL_HELPERS = {};
var E_CHAR = "Invalid character in base64 input";
var E_PADDING = "Invalid base64 padding";
var E_LENGTH = "Invalid base64 length";
var E_LAST = "Invalid last chunk";
function toBase64(arr, isURL, padding) {
  const fullChunks = arr.length / 3 | 0;
  const fullChunksBytes = fullChunks * 3;
  let o = "";
  let i = 0;
  const alphabet = isURL ? BASE64URL : BASE64;
  const helpers = isURL ? BASE64URL_HELPERS : BASE64_HELPERS;
  if (!helpers.pairs) {
    helpers.pairs = [];
    if (nativeDecoder) {
      helpers.codepairs = new Uint16Array(64 * 64);
      const u16 = helpers.codepairs;
      const u8 = new Uint8Array(u16.buffer, u16.byteOffset, u16.byteLength);
      for (let i2 = 0; i2 < 64; i2++) {
        const ic = alphabet[i2].charCodeAt(0);
        for (let j = 0; j < 64; j++) u8[i2 << 7 | j << 1] = u8[j << 7 | (i2 << 1) + 1] = ic;
      }
    } else {
      const p = helpers.pairs;
      for (let i2 = 0; i2 < 64; i2++) {
        for (let j = 0; j < 64; j++) p.push(`${alphabet[i2]}${alphabet[j]}`);
      }
    }
  }
  const { pairs, codepairs } = helpers;
  if (nativeDecoder) {
    const oa = new Uint16Array(fullChunks * 2);
    let j = 0;
    for (const last = arr.length - 11; i < last; i += 12, j += 8) {
      const x0 = arr[i];
      const x1 = arr[i + 1];
      const x2 = arr[i + 2];
      const x3 = arr[i + 3];
      const x4 = arr[i + 4];
      const x5 = arr[i + 5];
      const x6 = arr[i + 6];
      const x7 = arr[i + 7];
      const x8 = arr[i + 8];
      const x9 = arr[i + 9];
      const x10 = arr[i + 10];
      const x11 = arr[i + 11];
      oa[j] = codepairs[x0 << 4 | x1 >> 4];
      oa[j + 1] = codepairs[(x1 & 15) << 8 | x2];
      oa[j + 2] = codepairs[x3 << 4 | x4 >> 4];
      oa[j + 3] = codepairs[(x4 & 15) << 8 | x5];
      oa[j + 4] = codepairs[x6 << 4 | x7 >> 4];
      oa[j + 5] = codepairs[(x7 & 15) << 8 | x8];
      oa[j + 6] = codepairs[x9 << 4 | x10 >> 4];
      oa[j + 7] = codepairs[(x10 & 15) << 8 | x11];
    }
    for (const last = arr.length - 2; i < last; i += 3, j += 2) {
      const a = arr[i];
      const b = arr[i + 1];
      const c = arr[i + 2];
      oa[j] = codepairs[a << 4 | b >> 4];
      oa[j + 1] = codepairs[(b & 15) << 8 | c];
    }
    o = decodeAscii(oa);
  } else {
    for (; i < fullChunksBytes; i += 3) {
      const a = arr[i];
      const b = arr[i + 1];
      const c = arr[i + 2];
      o += pairs[a << 4 | b >> 4];
      o += pairs[(b & 15) << 8 | c];
    }
  }
  let carry = 0;
  let shift = 2;
  const length = arr.length;
  for (; i < length; i++) {
    const x = arr[i];
    o += alphabet[carry | x >> shift];
    if (shift === 6) {
      shift = 0;
      o += alphabet[x & 63];
    }
    carry = x << 6 - shift & 63;
    shift += 2;
  }
  if (shift !== 2) o += alphabet[carry];
  if (padding) o += ["", "==", "="][length - fullChunksBytes];
  return o;
}
var mapSize = nativeEncoder ? 128 : 65536;
function fromBase64(str, isURL) {
  let inputLength = str.length;
  while (str[inputLength - 1] === "=") inputLength--;
  const paddingLength = str.length - inputLength;
  const tailLength = inputLength % 4;
  const mainLength = inputLength - tailLength;
  if (tailLength === 1) throw new SyntaxError(E_LENGTH);
  if (paddingLength > 3 || paddingLength !== 0 && str.length % 4 !== 0) {
    throw new SyntaxError(E_PADDING);
  }
  const alphabet = isURL ? BASE64URL : BASE64;
  const helpers = isURL ? BASE64URL_HELPERS : BASE64_HELPERS;
  if (!helpers.fromMap) {
    helpers.fromMap = new Int8Array(mapSize).fill(-1);
    alphabet.forEach((c2, i2) => helpers.fromMap[c2.charCodeAt(0)] = i2);
  }
  const m = helpers.fromMap;
  const arr = new Uint8Array(Math.floor(inputLength * 3 / 4));
  let at = 0;
  let i = 0;
  if (nativeEncoder) {
    const codes = encodeAscii(str, E_CHAR);
    for (; i < mainLength; i += 4) {
      const c0 = codes[i];
      const c1 = codes[i + 1];
      const c2 = codes[i + 2];
      const c3 = codes[i + 3];
      const a = m[c0] << 18 | m[c1] << 12 | m[c2] << 6 | m[c3];
      if (a < 0) throw new SyntaxError(E_CHAR);
      arr[at] = a >> 16;
      arr[at + 1] = a >> 8 & 255;
      arr[at + 2] = a & 255;
      at += 3;
    }
  } else {
    for (; i < mainLength; i += 4) {
      const c0 = str.charCodeAt(i);
      const c1 = str.charCodeAt(i + 1);
      const c2 = str.charCodeAt(i + 2);
      const c3 = str.charCodeAt(i + 3);
      const a = m[c0] << 18 | m[c1] << 12 | m[c2] << 6 | m[c3];
      if (a < 0) throw new SyntaxError(E_CHAR);
      arr[at] = a >> 16;
      arr[at + 1] = a >> 8 & 255;
      arr[at + 2] = a & 255;
      at += 3;
    }
  }
  if (tailLength < 2) return arr;
  const ab = m[str.charCodeAt(i++)] << 6 | m[str.charCodeAt(i++)];
  if (ab < 0) throw new SyntaxError(E_CHAR);
  arr[at++] = ab >> 4;
  if (tailLength < 3) {
    if (ab & 15) throw new SyntaxError(E_LAST);
    return arr;
  }
  const c = m[str.charCodeAt(i++)];
  if (c < 0) throw new SyntaxError(E_CHAR);
  arr[at++] = ab << 4 & 255 | c >> 2;
  if (c & 3) throw new SyntaxError(E_LAST);
  return arr;
}

// node_modules/@exodus/bytes/base64.js
var { Buffer: Buffer4, atob: atob2, btoa } = globalThis;
var haveNativeBuffer2 = Buffer4 && !Buffer4.TYPED_ARRAY_SUPPORT;
var { toBase64: web642 } = Uint8Array.prototype;
var { E_CHAR: E_CHAR2, E_PADDING: E_PADDING2, E_LENGTH: E_LENGTH2, E_LAST: E_LAST2 } = base64_exports;
var shouldUseBtoa = btoa && isHermes;
var shouldUseAtob = atob2 && isHermes;
var isBuffer = (x) => x.constructor === Buffer4 && Buffer4.isBuffer(x);
var toBuffer = (x) => isBuffer(x) ? x : Buffer4.from(x.buffer, x.byteOffset, x.byteLength);
function maybeUnpad(res, padding) {
  if (padding) return res;
  const at = res.indexOf("=", res.length - 3);
  return at === -1 ? res : res.slice(0, at);
}
function maybePad(res, padding) {
  return padding && res.length % 4 !== 0 ? res + "=".repeat(4 - res.length % 4) : res;
}
var toUrl = (x) => x.replaceAll("+", "-").replaceAll("/", "_");
var haveWeb = (x) => web642 && x.toBase64 === web642;
function toBase642(x, { padding = true } = {}) {
  assertU8(x);
  if (haveWeb(x)) return padding ? x.toBase64() : x.toBase64({ omitPadding: !padding });
  if (haveNativeBuffer2) return maybeUnpad(toBuffer(x).base64Slice(0, x.byteLength), padding);
  if (shouldUseBtoa) return maybeUnpad(btoa(decodeLatin1(x)), padding);
  return toBase64(x, false, padding);
}
function toBase64url(x, { padding = false } = {}) {
  assertU8(x);
  if (haveWeb(x)) return x.toBase64({ alphabet: "base64url", omitPadding: !padding });
  if (haveNativeBuffer2) return maybePad(toBuffer(x).base64urlSlice(0, x.byteLength), padding);
  if (shouldUseBtoa) return maybeUnpad(toUrl(btoa(decodeLatin1(x))), padding);
  return toBase64(x, true, padding);
}
function fromBase642(str, options) {
  if (typeof options === "string") options = { format: options };
  if (!options) return fromBase64common(str, false, "both", "uint8", null);
  const { format = "uint8", padding = "both", ...rest } = options;
  return fromBase64common(str, false, padding, format, rest);
}
function fromBase64url(str, options) {
  if (!options) return fromBase64common(str, true, false, "uint8", null);
  const { format = "uint8", padding = false, ...rest } = options;
  return fromBase64common(str, true, padding, format, rest);
}
function fromBase64any(str, { format = "uint8", padding = "both", ...rest } = {}) {
  if (typeof str !== "string") throw new TypeError(E_STRING);
  const isBase64url = !str.includes("+") && !str.includes("/");
  return fromBase64common(str, isBase64url, padding, format, rest);
}
function fromBase64common(str, isBase64url, padding, format, rest) {
  if (typeof str !== "string") throw new TypeError(E_STRING);
  if (rest !== null) assertEmptyRest(rest);
  const auto = padding === "both" ? str.endsWith("=") : void 0;
  if (padding === true || auto === true) {
    if (str.length % 4 !== 0) throw new SyntaxError(E_PADDING2);
    if (str[str.length - 3] === "=") throw new SyntaxError(E_PADDING2);
  } else if (padding === false || auto === false) {
    if (str.length % 4 === 1) throw new SyntaxError(E_LENGTH2);
    if (padding === false && str.endsWith("=")) {
      throw new SyntaxError("Did not expect padding in base64 input");
    }
  } else {
    throw new TypeError("Invalid padding option");
  }
  return fromBase64impl(str, isBase64url, padding, format);
}
var ASCII_WHITESPACE = /[\t\n\f\r ]/;
function noWhitespaceSeen(str, arr) {
  const at = str.indexOf("=", str.length - 3);
  const paddingLength = at >= 0 ? str.length - at : 0;
  const chars = str.length - paddingLength;
  const e = chars % 4;
  const b = arr.length - (chars - e) / 4 * 3;
  return e === 0 && b === 0 || e === 2 && b === 1 || e === 3 && b === 2;
}
var fromBase64impl;
if (Uint8Array.fromBase64) {
  fromBase64impl = (str, isBase64url, padding, format) => {
    const alphabet = isBase64url ? "base64url" : "base64";
    let arr;
    if (padding === true) {
      arr = Uint8Array.fromBase64(str, { alphabet, lastChunkHandling: "strict" });
    } else {
      try {
        const padded = str.length % 4 > 0 ? `${str}${"=".repeat(4 - str.length % 4)}` : str;
        arr = Uint8Array.fromBase64(padded, { alphabet, lastChunkHandling: "strict" });
      } catch (err) {
        throw ASCII_WHITESPACE.test(str) ? new SyntaxError(E_CHAR2) : err;
      }
    }
    if (!noWhitespaceSeen(str, arr)) throw new SyntaxError(E_CHAR2);
    return fromUint8(arr, format);
  };
} else if (haveNativeBuffer2) {
  fromBase64impl = (str, isBase64url, padding, format) => {
    const size = Buffer4.byteLength(str, "base64");
    const arr = Buffer4.allocUnsafeSlow(size);
    if (arr.base64Write(str) !== size) throw new SyntaxError(E_PADDING2);
    const got = isBase64url ? maybeUnpad(str, padding === false) : maybePad(str, padding !== true);
    const valid = isBase64url ? arr.base64urlSlice(0, arr.length) : arr.base64Slice(0, arr.length);
    if (got !== valid) throw new SyntaxError(E_PADDING2);
    return fromBuffer(arr, format);
  };
} else if (shouldUseAtob) {
  fromBase64impl = (str, isBase64url, padding, format) => {
    let arr;
    if (isBase64url) {
      if (/[\t\n\f\r +/]/.test(str)) throw new SyntaxError(E_CHAR2);
      str = str.replaceAll("-", "+").replaceAll("_", "/");
    }
    try {
      arr = encodeLatin1(atob2(str));
    } catch {
      throw new SyntaxError(E_CHAR2);
    }
    if (!isBase64url && !noWhitespaceSeen(str, arr)) throw new SyntaxError(E_CHAR2);
    if (arr.length % 3 !== 0) {
      const expected = toBase642(arr.subarray(-(arr.length % 3)));
      const end = str.length % 4 === 0 ? str.slice(-4) : str.slice(-(str.length % 4)).padEnd(4, "=");
      if (expected !== end) throw new SyntaxError(E_LAST2);
    }
    return fromUint8(arr, format);
  };
} else {
  fromBase64impl = (str, isBase64url, padding, format) => fromUint8(fromBase64(str, isBase64url), format);
}
// Annotate the CommonJS export names for ESM import in node:
0 && (module.exports = {
  fromBase64,
  fromBase64any,
  fromBase64url,
  toBase64,
  toBase64url
});

var __create = Object.create;
var __defProp = Object.defineProperty;
var __getOwnPropDesc = Object.getOwnPropertyDescriptor;
var __getOwnPropNames = Object.getOwnPropertyNames;
var __getProtoOf = Object.getPrototypeOf;
var __hasOwnProp = Object.prototype.hasOwnProperty;
var __commonJS = (cb, mod) => function __require() {
  return mod || (0, cb[__getOwnPropNames(cb)[0]])((mod = { exports: {} }).exports, mod), mod.exports;
};
var __export = (target, all) => {
  for (var name50 in all)
    __defProp(target, name50, { get: all[name50], enumerable: true });
};
var __copyProps = (to, from, except, desc) => {
  if (from && typeof from === "object" || typeof from === "function") {
    for (let key of __getOwnPropNames(from))
      if (!__hasOwnProp.call(to, key) && key !== except)
        __defProp(to, key, { get: () => from[key], enumerable: !(desc = __getOwnPropDesc(from, key)) || desc.enumerable });
  }
  return to;
};
var __toESM = (mod, isNodeMode, target) => (target = mod != null ? __create(__getProtoOf(mod)) : {}, __copyProps(
  // If the importer is in node compatibility mode or this is not an ESM
  // file that has been converted to a CommonJS file using a Babel-
  // compatible transform (i.e. "__esModule" has not been set), then set
  // "default" to the CommonJS "module.exports" for node compatibility.
  isNodeMode || !mod || !mod.__esModule ? __defProp(target, "default", { value: mod, enumerable: true }) : target,
  mod
));
var __toCommonJS = (mod) => __copyProps(__defProp({}, "__esModule", { value: true }), mod);

// node_modules/source-map-js/lib/base64.js
var require_base64 = __commonJS({
  "node_modules/source-map-js/lib/base64.js"(exports2) {
    var intToCharMap = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/".split("");
    exports2.encode = function(number2) {
      if (0 <= number2 && number2 < intToCharMap.length) {
        return intToCharMap[number2];
      }
      throw new TypeError("Must be between 0 and 63: " + number2);
    };
    exports2.decode = function(charCode) {
      var bigA = 65;
      var bigZ = 90;
      var littleA = 97;
      var littleZ = 122;
      var zero2 = 48;
      var nine = 57;
      var plus = 43;
      var slash = 47;
      var littleOffset = 26;
      var numberOffset = 52;
      if (bigA <= charCode && charCode <= bigZ) {
        return charCode - bigA;
      }
      if (littleA <= charCode && charCode <= littleZ) {
        return charCode - littleA + littleOffset;
      }
      if (zero2 <= charCode && charCode <= nine) {
        return charCode - zero2 + numberOffset;
      }
      if (charCode == plus) {
        return 62;
      }
      if (charCode == slash) {
        return 63;
      }
      return -1;
    };
  }
});

// node_modules/source-map-js/lib/base64-vlq.js
var require_base64_vlq = __commonJS({
  "node_modules/source-map-js/lib/base64-vlq.js"(exports2) {
    var base64 = require_base64();
    var VLQ_BASE_SHIFT = 5;
    var VLQ_BASE = 1 << VLQ_BASE_SHIFT;
    var VLQ_BASE_MASK = VLQ_BASE - 1;
    var VLQ_CONTINUATION_BIT = VLQ_BASE;
    function toVLQSigned(aValue) {
      return aValue < 0 ? (-aValue << 1) + 1 : (aValue << 1) + 0;
    }
    function fromVLQSigned(aValue) {
      var isNegative = (aValue & 1) === 1;
      var shifted = aValue >> 1;
      return isNegative ? -shifted : shifted;
    }
    exports2.encode = function base64VLQ_encode(aValue) {
      var encoded = "";
      var digit;
      var vlq = toVLQSigned(aValue);
      do {
        digit = vlq & VLQ_BASE_MASK;
        vlq >>>= VLQ_BASE_SHIFT;
        if (vlq > 0) {
          digit |= VLQ_CONTINUATION_BIT;
        }
        encoded += base64.encode(digit);
      } while (vlq > 0);
      return encoded;
    };
    exports2.decode = function base64VLQ_decode(aStr, aIndex, aOutParam) {
      var strLen = aStr.length;
      var result = 0;
      var shift = 0;
      var continuation, digit;
      do {
        if (aIndex >= strLen) {
          throw new Error("Expected more digits in base 64 VLQ value.");
        }
        digit = base64.decode(aStr.charCodeAt(aIndex++));
        if (digit === -1) {
          throw new Error("Invalid base64 digit: " + aStr.charAt(aIndex - 1));
        }
        continuation = !!(digit & VLQ_CONTINUATION_BIT);
        digit &= VLQ_BASE_MASK;
        result = result + (digit << shift);
        shift += VLQ_BASE_SHIFT;
      } while (continuation);
      aOutParam.value = fromVLQSigned(result);
      aOutParam.rest = aIndex;
    };
  }
});

// node_modules/source-map-js/lib/util.js
var require_util = __commonJS({
  "node_modules/source-map-js/lib/util.js"(exports2) {
    function getArg(aArgs, aName, aDefaultValue) {
      if (aName in aArgs) {
        return aArgs[aName];
      } else if (arguments.length === 3) {
        return aDefaultValue;
      } else {
        throw new Error('"' + aName + '" is a required argument.');
      }
    }
    exports2.getArg = getArg;
    var urlRegexp = /^(?:([\w+\-.]+):)?\/\/(?:(\w+:\w+)@)?([\w.-]*)(?::(\d+))?(.*)$/;
    var dataUrlRegexp = /^data:.+\,.+$/;
    function urlParse(aUrl) {
      var match = aUrl.match(urlRegexp);
      if (!match) {
        return null;
      }
      return {
        scheme: match[1],
        auth: match[2],
        host: match[3],
        port: match[4],
        path: match[5]
      };
    }
    exports2.urlParse = urlParse;
    function urlGenerate(aParsedUrl) {
      var url = "";
      if (aParsedUrl.scheme) {
        url += aParsedUrl.scheme + ":";
      }
      url += "//";
      if (aParsedUrl.auth) {
        url += aParsedUrl.auth + "@";
      }
      if (aParsedUrl.host) {
        url += aParsedUrl.host;
      }
      if (aParsedUrl.port) {
        url += ":" + aParsedUrl.port;
      }
      if (aParsedUrl.path) {
        url += aParsedUrl.path;
      }
      return url;
    }
    exports2.urlGenerate = urlGenerate;
    var MAX_CACHED_INPUTS = 32;
    function lruMemoize(f) {
      var cache = [];
      return function(input) {
        for (var i = 0; i < cache.length; i++) {
          if (cache[i].input === input) {
            var temp = cache[0];
            cache[0] = cache[i];
            cache[i] = temp;
            return cache[0].result;
          }
        }
        var result = f(input);
        cache.unshift({
          input,
          result
        });
        if (cache.length > MAX_CACHED_INPUTS) {
          cache.pop();
        }
        return result;
      };
    }
    var normalize = lruMemoize(function normalize2(aPath) {
      var path = aPath;
      var url = urlParse(aPath);
      if (url) {
        if (!url.path) {
          return aPath;
        }
        path = url.path;
      }
      var isAbsolute = exports2.isAbsolute(path);
      var parts = [];
      var start = 0;
      var i = 0;
      while (true) {
        start = i;
        i = path.indexOf("/", start);
        if (i === -1) {
          parts.push(path.slice(start));
          break;
        } else {
          parts.push(path.slice(start, i));
          while (i < path.length && path[i] === "/") {
            i++;
          }
        }
      }
      for (var part, up = 0, i = parts.length - 1; i >= 0; i--) {
        part = parts[i];
        if (part === ".") {
          parts.splice(i, 1);
        } else if (part === "..") {
          up++;
        } else if (up > 0) {
          if (part === "") {
            parts.splice(i + 1, up);
            up = 0;
          } else {
            parts.splice(i, 2);
            up--;
          }
        }
      }
      path = parts.join("/");
      if (path === "") {
        path = isAbsolute ? "/" : ".";
      }
      if (url) {
        url.path = path;
        return urlGenerate(url);
      }
      return path;
    });
    exports2.normalize = normalize;
    function join(aRoot, aPath) {
      if (aRoot === "") {
        aRoot = ".";
      }
      if (aPath === "") {
        aPath = ".";
      }
      var aPathUrl = urlParse(aPath);
      var aRootUrl = urlParse(aRoot);
      if (aRootUrl) {
        aRoot = aRootUrl.path || "/";
      }
      if (aPathUrl && !aPathUrl.scheme) {
        if (aRootUrl) {
          aPathUrl.scheme = aRootUrl.scheme;
        }
        return urlGenerate(aPathUrl);
      }
      if (aPathUrl || aPath.match(dataUrlRegexp)) {
        return aPath;
      }
      if (aRootUrl && !aRootUrl.host && !aRootUrl.path) {
        aRootUrl.host = aPath;
        return urlGenerate(aRootUrl);
      }
      var joined = aPath.charAt(0) === "/" ? aPath : normalize(aRoot.replace(/\/+$/, "") + "/" + aPath);
      if (aRootUrl) {
        aRootUrl.path = joined;
        return urlGenerate(aRootUrl);
      }
      return joined;
    }
    exports2.join = join;
    exports2.isAbsolute = function(aPath) {
      return aPath.charAt(0) === "/" || urlRegexp.test(aPath);
    };
    function relative(aRoot, aPath) {
      if (aRoot === "") {
        aRoot = ".";
      }
      aRoot = aRoot.replace(/\/$/, "");
      var level = 0;
      while (aPath.indexOf(aRoot + "/") !== 0) {
        var index = aRoot.lastIndexOf("/");
        if (index < 0) {
          return aPath;
        }
        aRoot = aRoot.slice(0, index);
        if (aRoot.match(/^([^\/]+:\/)?\/*$/)) {
          return aPath;
        }
        ++level;
      }
      return Array(level + 1).join("../") + aPath.substr(aRoot.length + 1);
    }
    exports2.relative = relative;
    var supportsNullProto = (function() {
      var obj = /* @__PURE__ */ Object.create(null);
      return !("__proto__" in obj);
    })();
    function identity(s) {
      return s;
    }
    function toSetString(aStr) {
      if (isProtoString(aStr)) {
        return "$" + aStr;
      }
      return aStr;
    }
    exports2.toSetString = supportsNullProto ? identity : toSetString;
    function fromSetString(aStr) {
      if (isProtoString(aStr)) {
        return aStr.slice(1);
      }
      return aStr;
    }
    exports2.fromSetString = supportsNullProto ? identity : fromSetString;
    function isProtoString(s) {
      if (!s) {
        return false;
      }
      var length2 = s.length;
      if (length2 < 9) {
        return false;
      }
      if (s.charCodeAt(length2 - 1) !== 95 || s.charCodeAt(length2 - 2) !== 95 || s.charCodeAt(length2 - 3) !== 111 || s.charCodeAt(length2 - 4) !== 116 || s.charCodeAt(length2 - 5) !== 111 || s.charCodeAt(length2 - 6) !== 114 || s.charCodeAt(length2 - 7) !== 112 || s.charCodeAt(length2 - 8) !== 95 || s.charCodeAt(length2 - 9) !== 95) {
        return false;
      }
      for (var i = length2 - 10; i >= 0; i--) {
        if (s.charCodeAt(i) !== 36) {
          return false;
        }
      }
      return true;
    }
    function compareByOriginalPositions(mappingA, mappingB, onlyCompareOriginal) {
      var cmp = strcmp(mappingA.source, mappingB.source);
      if (cmp !== 0) {
        return cmp;
      }
      cmp = mappingA.originalLine - mappingB.originalLine;
      if (cmp !== 0) {
        return cmp;
      }
      cmp = mappingA.originalColumn - mappingB.originalColumn;
      if (cmp !== 0 || onlyCompareOriginal) {
        return cmp;
      }
      cmp = mappingA.generatedColumn - mappingB.generatedColumn;
      if (cmp !== 0) {
        return cmp;
      }
      cmp = mappingA.generatedLine - mappingB.generatedLine;
      if (cmp !== 0) {
        return cmp;
      }
      return strcmp(mappingA.name, mappingB.name);
    }
    exports2.compareByOriginalPositions = compareByOriginalPositions;
    function compareByOriginalPositionsNoSource(mappingA, mappingB, onlyCompareOriginal) {
      var cmp;
      cmp = mappingA.originalLine - mappingB.originalLine;
      if (cmp !== 0) {
        return cmp;
      }
      cmp = mappingA.originalColumn - mappingB.originalColumn;
      if (cmp !== 0 || onlyCompareOriginal) {
        return cmp;
      }
      cmp = mappingA.generatedColumn - mappingB.generatedColumn;
      if (cmp !== 0) {
        return cmp;
      }
      cmp = mappingA.generatedLine - mappingB.generatedLine;
      if (cmp !== 0) {
        return cmp;
      }
      return strcmp(mappingA.name, mappingB.name);
    }
    exports2.compareByOriginalPositionsNoSource = compareByOriginalPositionsNoSource;
    function compareByGeneratedPositionsDeflated(mappingA, mappingB, onlyCompareGenerated) {
      var cmp = mappingA.generatedLine - mappingB.generatedLine;
      if (cmp !== 0) {
        return cmp;
      }
      cmp = mappingA.generatedColumn - mappingB.generatedColumn;
      if (cmp !== 0 || onlyCompareGenerated) {
        return cmp;
      }
      cmp = strcmp(mappingA.source, mappingB.source);
      if (cmp !== 0) {
        return cmp;
      }
      cmp = mappingA.originalLine - mappingB.originalLine;
      if (cmp !== 0) {
        return cmp;
      }
      cmp = mappingA.originalColumn - mappingB.originalColumn;
      if (cmp !== 0) {
        return cmp;
      }
      return strcmp(mappingA.name, mappingB.name);
    }
    exports2.compareByGeneratedPositionsDeflated = compareByGeneratedPositionsDeflated;
    function compareByGeneratedPositionsDeflatedNoLine(mappingA, mappingB, onlyCompareGenerated) {
      var cmp = mappingA.generatedColumn - mappingB.generatedColumn;
      if (cmp !== 0 || onlyCompareGenerated) {
        return cmp;
      }
      cmp = strcmp(mappingA.source, mappingB.source);
      if (cmp !== 0) {
        return cmp;
      }
      cmp = mappingA.originalLine - mappingB.originalLine;
      if (cmp !== 0) {
        return cmp;
      }
      cmp = mappingA.originalColumn - mappingB.originalColumn;
      if (cmp !== 0) {
        return cmp;
      }
      return strcmp(mappingA.name, mappingB.name);
    }
    exports2.compareByGeneratedPositionsDeflatedNoLine = compareByGeneratedPositionsDeflatedNoLine;
    function strcmp(aStr1, aStr2) {
      if (aStr1 === aStr2) {
        return 0;
      }
      if (aStr1 === null) {
        return 1;
      }
      if (aStr2 === null) {
        return -1;
      }
      if (aStr1 > aStr2) {
        return 1;
      }
      return -1;
    }
    function compareByGeneratedPositionsInflated(mappingA, mappingB) {
      var cmp = mappingA.generatedLine - mappingB.generatedLine;
      if (cmp !== 0) {
        return cmp;
      }
      cmp = mappingA.generatedColumn - mappingB.generatedColumn;
      if (cmp !== 0) {
        return cmp;
      }
      cmp = strcmp(mappingA.source, mappingB.source);
      if (cmp !== 0) {
        return cmp;
      }
      cmp = mappingA.originalLine - mappingB.originalLine;
      if (cmp !== 0) {
        return cmp;
      }
      cmp = mappingA.originalColumn - mappingB.originalColumn;
      if (cmp !== 0) {
        return cmp;
      }
      return strcmp(mappingA.name, mappingB.name);
    }
    exports2.compareByGeneratedPositionsInflated = compareByGeneratedPositionsInflated;
    function parseSourceMapInput(str) {
      return JSON.parse(str.replace(/^\)]}'[^\n]*\n/, ""));
    }
    exports2.parseSourceMapInput = parseSourceMapInput;
    function computeSourceURL(sourceRoot, sourceURL, sourceMapURL) {
      sourceURL = sourceURL || "";
      if (sourceRoot) {
        if (sourceRoot[sourceRoot.length - 1] !== "/" && sourceURL[0] !== "/") {
          sourceRoot += "/";
        }
        sourceURL = sourceRoot + sourceURL;
      }
      if (sourceMapURL) {
        var parsed = urlParse(sourceMapURL);
        if (!parsed) {
          throw new Error("sourceMapURL could not be parsed");
        }
        if (parsed.path) {
          var index = parsed.path.lastIndexOf("/");
          if (index >= 0) {
            parsed.path = parsed.path.substring(0, index + 1);
          }
        }
        sourceURL = join(urlGenerate(parsed), sourceURL);
      }
      return normalize(sourceURL);
    }
    exports2.computeSourceURL = computeSourceURL;
  }
});

// node_modules/source-map-js/lib/array-set.js
var require_array_set = __commonJS({
  "node_modules/source-map-js/lib/array-set.js"(exports2) {
    var util = require_util();
    var has = Object.prototype.hasOwnProperty;
    var hasNativeMap = typeof Map !== "undefined";
    function ArraySet() {
      this._array = [];
      this._set = hasNativeMap ? /* @__PURE__ */ new Map() : /* @__PURE__ */ Object.create(null);
    }
    ArraySet.fromArray = function ArraySet_fromArray(aArray, aAllowDuplicates) {
      var set = new ArraySet();
      for (var i = 0, len = aArray.length; i < len; i++) {
        set.add(aArray[i], aAllowDuplicates);
      }
      return set;
    };
    ArraySet.prototype.size = function ArraySet_size() {
      return hasNativeMap ? this._set.size : Object.getOwnPropertyNames(this._set).length;
    };
    ArraySet.prototype.add = function ArraySet_add(aStr, aAllowDuplicates) {
      var sStr = hasNativeMap ? aStr : util.toSetString(aStr);
      var isDuplicate = hasNativeMap ? this.has(aStr) : has.call(this._set, sStr);
      var idx = this._array.length;
      if (!isDuplicate || aAllowDuplicates) {
        this._array.push(aStr);
      }
      if (!isDuplicate) {
        if (hasNativeMap) {
          this._set.set(aStr, idx);
        } else {
          this._set[sStr] = idx;
        }
      }
    };
    ArraySet.prototype.has = function ArraySet_has(aStr) {
      if (hasNativeMap) {
        return this._set.has(aStr);
      } else {
        var sStr = util.toSetString(aStr);
        return has.call(this._set, sStr);
      }
    };
    ArraySet.prototype.indexOf = function ArraySet_indexOf(aStr) {
      if (hasNativeMap) {
        var idx = this._set.get(aStr);
        if (idx >= 0) {
          return idx;
        }
      } else {
        var sStr = util.toSetString(aStr);
        if (has.call(this._set, sStr)) {
          return this._set[sStr];
        }
      }
      throw new Error('"' + aStr + '" is not in the set.');
    };
    ArraySet.prototype.at = function ArraySet_at(aIdx) {
      if (aIdx >= 0 && aIdx < this._array.length) {
        return this._array[aIdx];
      }
      throw new Error("No element indexed by " + aIdx);
    };
    ArraySet.prototype.toArray = function ArraySet_toArray() {
      return this._array.slice();
    };
    exports2.ArraySet = ArraySet;
  }
});

// node_modules/source-map-js/lib/mapping-list.js
var require_mapping_list = __commonJS({
  "node_modules/source-map-js/lib/mapping-list.js"(exports2) {
    var util = require_util();
    function generatedPositionAfter(mappingA, mappingB) {
      var lineA = mappingA.generatedLine;
      var lineB = mappingB.generatedLine;
      var columnA = mappingA.generatedColumn;
      var columnB = mappingB.generatedColumn;
      return lineB > lineA || lineB == lineA && columnB >= columnA || util.compareByGeneratedPositionsInflated(mappingA, mappingB) <= 0;
    }
    function MappingList() {
      this._array = [];
      this._sorted = true;
      this._last = { generatedLine: -1, generatedColumn: 0 };
    }
    MappingList.prototype.unsortedForEach = function MappingList_forEach(aCallback, aThisArg) {
      this._array.forEach(aCallback, aThisArg);
    };
    MappingList.prototype.add = function MappingList_add(aMapping) {
      if (generatedPositionAfter(this._last, aMapping)) {
        this._last = aMapping;
        this._array.push(aMapping);
      } else {
        this._sorted = false;
        this._array.push(aMapping);
      }
    };
    MappingList.prototype.toArray = function MappingList_toArray() {
      if (!this._sorted) {
        this._array.sort(util.compareByGeneratedPositionsInflated);
        this._sorted = true;
      }
      return this._array;
    };
    exports2.MappingList = MappingList;
  }
});

// node_modules/source-map-js/lib/source-map-generator.js
var require_source_map_generator = __commonJS({
  "node_modules/source-map-js/lib/source-map-generator.js"(exports2) {
    var base64VLQ = require_base64_vlq();
    var util = require_util();
    var ArraySet = require_array_set().ArraySet;
    var MappingList = require_mapping_list().MappingList;
    function SourceMapGenerator2(aArgs) {
      if (!aArgs) {
        aArgs = {};
      }
      this._file = util.getArg(aArgs, "file", null);
      this._sourceRoot = util.getArg(aArgs, "sourceRoot", null);
      this._skipValidation = util.getArg(aArgs, "skipValidation", false);
      this._ignoreInvalidMapping = util.getArg(aArgs, "ignoreInvalidMapping", false);
      this._sources = new ArraySet();
      this._names = new ArraySet();
      this._mappings = new MappingList();
      this._sourcesContents = null;
    }
    SourceMapGenerator2.prototype._version = 3;
    SourceMapGenerator2.fromSourceMap = function SourceMapGenerator_fromSourceMap(aSourceMapConsumer, generatorOps) {
      var sourceRoot = aSourceMapConsumer.sourceRoot;
      var generator = new SourceMapGenerator2(Object.assign(generatorOps || {}, {
        file: aSourceMapConsumer.file,
        sourceRoot
      }));
      aSourceMapConsumer.eachMapping(function(mapping) {
        var newMapping = {
          generated: {
            line: mapping.generatedLine,
            column: mapping.generatedColumn
          }
        };
        if (mapping.source != null) {
          newMapping.source = mapping.source;
          if (sourceRoot != null) {
            newMapping.source = util.relative(sourceRoot, newMapping.source);
          }
          newMapping.original = {
            line: mapping.originalLine,
            column: mapping.originalColumn
          };
          if (mapping.name != null) {
            newMapping.name = mapping.name;
          }
        }
        generator.addMapping(newMapping);
      });
      aSourceMapConsumer.sources.forEach(function(sourceFile) {
        var sourceRelative = sourceFile;
        if (sourceRoot !== null) {
          sourceRelative = util.relative(sourceRoot, sourceFile);
        }
        if (!generator._sources.has(sourceRelative)) {
          generator._sources.add(sourceRelative);
        }
        var content = aSourceMapConsumer.sourceContentFor(sourceFile);
        if (content != null) {
          generator.setSourceContent(sourceFile, content);
        }
      });
      return generator;
    };
    SourceMapGenerator2.prototype.addMapping = function SourceMapGenerator_addMapping(aArgs) {
      var generated = util.getArg(aArgs, "generated");
      var original = util.getArg(aArgs, "original", null);
      var source = util.getArg(aArgs, "source", null);
      var name50 = util.getArg(aArgs, "name", null);
      if (!this._skipValidation) {
        if (this._validateMapping(generated, original, source, name50) === false) {
          return;
        }
      }
      if (source != null) {
        source = String(source);
        if (!this._sources.has(source)) {
          this._sources.add(source);
        }
      }
      if (name50 != null) {
        name50 = String(name50);
        if (!this._names.has(name50)) {
          this._names.add(name50);
        }
      }
      this._mappings.add({
        generatedLine: generated.line,
        generatedColumn: generated.column,
        originalLine: original != null && original.line,
        originalColumn: original != null && original.column,
        source,
        name: name50
      });
    };
    SourceMapGenerator2.prototype.setSourceContent = function SourceMapGenerator_setSourceContent(aSourceFile, aSourceContent) {
      var source = aSourceFile;
      if (this._sourceRoot != null) {
        source = util.relative(this._sourceRoot, source);
      }
      if (aSourceContent != null) {
        if (!this._sourcesContents) {
          this._sourcesContents = /* @__PURE__ */ Object.create(null);
        }
        this._sourcesContents[util.toSetString(source)] = aSourceContent;
      } else if (this._sourcesContents) {
        delete this._sourcesContents[util.toSetString(source)];
        if (Object.keys(this._sourcesContents).length === 0) {
          this._sourcesContents = null;
        }
      }
    };
    SourceMapGenerator2.prototype.applySourceMap = function SourceMapGenerator_applySourceMap(aSourceMapConsumer, aSourceFile, aSourceMapPath) {
      var sourceFile = aSourceFile;
      if (aSourceFile == null) {
        if (aSourceMapConsumer.file == null) {
          throw new Error(
            `SourceMapGenerator.prototype.applySourceMap requires either an explicit source file, or the source map's "file" property. Both were omitted.`
          );
        }
        sourceFile = aSourceMapConsumer.file;
      }
      var sourceRoot = this._sourceRoot;
      if (sourceRoot != null) {
        sourceFile = util.relative(sourceRoot, sourceFile);
      }
      var newSources = new ArraySet();
      var newNames = new ArraySet();
      this._mappings.unsortedForEach(function(mapping) {
        if (mapping.source === sourceFile && mapping.originalLine != null) {
          var original = aSourceMapConsumer.originalPositionFor({
            line: mapping.originalLine,
            column: mapping.originalColumn
          });
          if (original.source != null) {
            mapping.source = original.source;
            if (aSourceMapPath != null) {
              mapping.source = util.join(aSourceMapPath, mapping.source);
            }
            if (sourceRoot != null) {
              mapping.source = util.relative(sourceRoot, mapping.source);
            }
            mapping.originalLine = original.line;
            mapping.originalColumn = original.column;
            if (original.name != null) {
              mapping.name = original.name;
            }
          }
        }
        var source = mapping.source;
        if (source != null && !newSources.has(source)) {
          newSources.add(source);
        }
        var name50 = mapping.name;
        if (name50 != null && !newNames.has(name50)) {
          newNames.add(name50);
        }
      }, this);
      this._sources = newSources;
      this._names = newNames;
      aSourceMapConsumer.sources.forEach(function(sourceFile2) {
        var content = aSourceMapConsumer.sourceContentFor(sourceFile2);
        if (content != null) {
          if (aSourceMapPath != null) {
            sourceFile2 = util.join(aSourceMapPath, sourceFile2);
          }
          if (sourceRoot != null) {
            sourceFile2 = util.relative(sourceRoot, sourceFile2);
          }
          this.setSourceContent(sourceFile2, content);
        }
      }, this);
    };
    SourceMapGenerator2.prototype._validateMapping = function SourceMapGenerator_validateMapping(aGenerated, aOriginal, aSource, aName) {
      if (aOriginal && typeof aOriginal.line !== "number" && typeof aOriginal.column !== "number") {
        var message = "original.line and original.column are not numbers -- you probably meant to omit the original mapping entirely and only map the generated position. If so, pass null for the original mapping instead of an object with empty or null values.";
        if (this._ignoreInvalidMapping) {
          if (typeof console !== "undefined" && console.warn) {
            console.warn(message);
          }
          return false;
        } else {
          throw new Error(message);
        }
      }
      if (aGenerated && "line" in aGenerated && "column" in aGenerated && aGenerated.line > 0 && aGenerated.column >= 0 && !aOriginal && !aSource && !aName) {
        return;
      } else if (aGenerated && "line" in aGenerated && "column" in aGenerated && aOriginal && "line" in aOriginal && "column" in aOriginal && aGenerated.line > 0 && aGenerated.column >= 0 && aOriginal.line > 0 && aOriginal.column >= 0 && aSource) {
        return;
      } else {
        var message = "Invalid mapping: " + JSON.stringify({
          generated: aGenerated,
          source: aSource,
          original: aOriginal,
          name: aName
        });
        if (this._ignoreInvalidMapping) {
          if (typeof console !== "undefined" && console.warn) {
            console.warn(message);
          }
          return false;
        } else {
          throw new Error(message);
        }
      }
    };
    SourceMapGenerator2.prototype._serializeMappings = function SourceMapGenerator_serializeMappings() {
      var previousGeneratedColumn = 0;
      var previousGeneratedLine = 1;
      var previousOriginalColumn = 0;
      var previousOriginalLine = 0;
      var previousName = 0;
      var previousSource = 0;
      var result = "";
      var next;
      var mapping;
      var nameIdx;
      var sourceIdx;
      var mappings = this._mappings.toArray();
      for (var i = 0, len = mappings.length; i < len; i++) {
        mapping = mappings[i];
        next = "";
        if (mapping.generatedLine !== previousGeneratedLine) {
          previousGeneratedColumn = 0;
          while (mapping.generatedLine !== previousGeneratedLine) {
            next += ";";
            previousGeneratedLine++;
          }
        } else {
          if (i > 0) {
            if (!util.compareByGeneratedPositionsInflated(mapping, mappings[i - 1])) {
              continue;
            }
            next += ",";
          }
        }
        next += base64VLQ.encode(mapping.generatedColumn - previousGeneratedColumn);
        previousGeneratedColumn = mapping.generatedColumn;
        if (mapping.source != null) {
          sourceIdx = this._sources.indexOf(mapping.source);
          next += base64VLQ.encode(sourceIdx - previousSource);
          previousSource = sourceIdx;
          next += base64VLQ.encode(mapping.originalLine - 1 - previousOriginalLine);
          previousOriginalLine = mapping.originalLine - 1;
          next += base64VLQ.encode(mapping.originalColumn - previousOriginalColumn);
          previousOriginalColumn = mapping.originalColumn;
          if (mapping.name != null) {
            nameIdx = this._names.indexOf(mapping.name);
            next += base64VLQ.encode(nameIdx - previousName);
            previousName = nameIdx;
          }
        }
        result += next;
      }
      return result;
    };
    SourceMapGenerator2.prototype._generateSourcesContent = function SourceMapGenerator_generateSourcesContent(aSources, aSourceRoot) {
      return aSources.map(function(source) {
        if (!this._sourcesContents) {
          return null;
        }
        if (aSourceRoot != null) {
          source = util.relative(aSourceRoot, source);
        }
        var key = util.toSetString(source);
        return Object.prototype.hasOwnProperty.call(this._sourcesContents, key) ? this._sourcesContents[key] : null;
      }, this);
    };
    SourceMapGenerator2.prototype.toJSON = function SourceMapGenerator_toJSON() {
      var map = {
        version: this._version,
        sources: this._sources.toArray(),
        names: this._names.toArray(),
        mappings: this._serializeMappings()
      };
      if (this._file != null) {
        map.file = this._file;
      }
      if (this._sourceRoot != null) {
        map.sourceRoot = this._sourceRoot;
      }
      if (this._sourcesContents) {
        map.sourcesContent = this._generateSourcesContent(map.sources, map.sourceRoot);
      }
      return map;
    };
    SourceMapGenerator2.prototype.toString = function SourceMapGenerator_toString() {
      return JSON.stringify(this.toJSON());
    };
    exports2.SourceMapGenerator = SourceMapGenerator2;
  }
});

// node_modules/@asamuzakjp/nwsapi/src/nwsapi.js
var require_nwsapi = __commonJS({
  "node_modules/@asamuzakjp/nwsapi/src/nwsapi.js"(exports2, module2) {
    (function Export(global, factory) {
      "use strict";
      module2.exports = factory;
    })(exports2, function Factory(global, Export) {
      const version = "nwsapi-2.2.2";
      let doc = global.document;
      function createMatchingParensRegex(depth = 1) {
        const out = "\\([^)(]*?(?:".repeat(depth) + "\\([^)(]*?\\)" + "[^)(]*?)*?\\)".repeat(depth);
        return out.slice(2, out.length - 2);
      }
      const CFG = {
        // extensions
        operators: "[~*^$|]=|=",
        combinators: "[\\s>+~](?=[^>+~])"
      };
      const NOT = {
        // not enclosed in double/single/parens/square
        doubleEnc: '(?=(?:[^"]*"[^"]*")*[^"]*$)',
        singleEnc: "(?=(?:[^']*'[^']*')*[^']*$)",
        parensEnc: "(?![^\\x28]*\\x29)",
        squareEnc: "(?![^\\x5b]*\\x5d)"
      };
      const REX = {
        // regular expressions
        hasEscapes: /\\/,
        hexNumbers: /^[0-9a-f]/i,
        escOrQuote: /^\\|[\x22\x27]/,
        regExpChar: /(?:(?!\\)[\\^$.*+?()[\]{}|/])/g,
        trimSpaces: /[\r\n\f]|^\s+|\s+$/g,
        commaGroup: RegExp("(\\s{0,255},\\s{0,255})" + NOT.squareEnc + NOT.parensEnc, "g"),
        splitGroup: /((?:\x28[^\x29]{0,255}\x29|\[[^\]]{0,255}\]|\\.|[^,])+)/g,
        fixEscapes: /\\([0-9a-f]{1,6}\s?|.)|([\x22\x27])/gi,
        combineWSP: RegExp("\\s{1,255}" + NOT.singleEnc + NOT.doubleEnc, "g"),
        tabCharWSP: RegExp("(\\s?\\t{1,255}\\s?)" + NOT.singleEnc + NOT.doubleEnc, "g"),
        pseudosWSP: RegExp("\\s{1,255}([-+])\\s{1,255}" + NOT.squareEnc, "g")
      };
      const STD = {
        combinator: /\s?([>+~])\s?/g,
        apimethods: /^(?:[a-z]+|\*)\|/i,
        namespaces: /(\*|[a-z]+)\|[-a-z]+/i
      };
      const GROUPS = {
        // pseudo-classes requiring parameters
        logicalsel: "(is|where|matches|not|has)(?:\\x28\\s?(" + createMatchingParensRegex(3) + ")\\s?\\x29)",
        treestruct: "(nth(?:-last)?(?:-child|-of-type))(?:\\x28\\s?(even|odd|(?:[-+]?\\d*)(?:n\\s?[-+]?\\s?\\d*)?)\\s?(?:\\x29|$))",
        // pseudo-classes not requiring parameters
        locationpc: "(any-link|link|visited|target)\\b",
        structural: "(root|empty|(?:(?:first|last|only)(?:-child|-of-type)))\\b",
        inputstate: "(enabled|disabled|read-(?:only|write)|placeholder-shown|default)\\b",
        inputvalue: "(checked|indeterminate)\\b",
        // pseudo-classes for parsing only selectors
        pseudoNop: "(autofill|-webkit-autofill)\\b",
        // pseudo-elements starting with single colon (:)
        pseudoSng: "(after|before|first-letter|first-line)\\b",
        // pseudo-elements starting with double colon (::)
        pseudoDbl: ":(after|before|first-letter|first-line|selection|part|placeholder|slotted|-webkit-[-a-z0-9]{2,})\\b"
      };
      const Patterns = {
        // pseudo-classes
        treestruct: RegExp("^:(?:" + GROUPS.treestruct + ")(.*)", "i"),
        structural: RegExp("^:(?:" + GROUPS.structural + ")(.*)", "i"),
        inputstate: RegExp("^:(?:" + GROUPS.inputstate + ")(.*)", "i"),
        inputvalue: RegExp("^:(?:" + GROUPS.inputvalue + ")(.*)", "i"),
        locationpc: RegExp("^:(?:" + GROUPS.locationpc + ")(.*)", "i"),
        logicalsel: RegExp("^:(?:" + GROUPS.logicalsel + ")(.*)", "i"),
        pseudoNop: RegExp("^:(?:" + GROUPS.pseudoNop + ")(.*)", "i"),
        pseudoSng: RegExp("^:(?:" + GROUPS.pseudoSng + ")(.*)", "i"),
        pseudoDbl: RegExp("^:(?:" + GROUPS.pseudoDbl + ")(.*)", "i"),
        // combinator symbols
        children: /^\s?>\s?(.*)/,
        adjacent: /^\s?\+\s?(.*)/,
        relative: /^\s?~\s?(.*)/,
        ancestor: /^\s+(.*)/,
        // universal & namespace
        universal: /^\*(.*)/,
        namespace: /^(\w+|\*)?\|(.*)/
      };
      const qsNotArgs = "Not enough arguments";
      const qsInvalid = " is not a valid selector";
      const reNthElem = /(:nth(?:-last)?-child)/i;
      const reNthType = /(:nth(?:-last)?-of-type)/i;
      let reOptimizer;
      let reValidator;
      const Config = {
        IDS_DUPES: true,
        MIXEDCASE: true,
        LOGERRORS: true,
        VERBOSITY: true
      };
      let NAMESPACE;
      let QUIRKS_MODE;
      let HTML_DOCUMENT;
      const ATTR_STD_OPS = {
        "=": 1,
        "^=": 1,
        "$=": 1,
        "|=": 1,
        "*=": 1,
        "~=": 1
      };
      const HTML_TABLE = {
        accept: 1,
        "accept-charset": 1,
        align: 1,
        alink: 1,
        axis: 1,
        bgcolor: 1,
        charset: 1,
        checked: 1,
        clear: 1,
        codetype: 1,
        color: 1,
        compact: 1,
        declare: 1,
        defer: 1,
        dir: 1,
        direction: 1,
        disabled: 1,
        enctype: 1,
        face: 1,
        frame: 1,
        hreflang: 1,
        "http-equiv": 1,
        lang: 1,
        language: 1,
        link: 1,
        media: 1,
        method: 1,
        multiple: 1,
        nohref: 1,
        noresize: 1,
        noshade: 1,
        nowrap: 1,
        readonly: 1,
        rel: 1,
        rev: 1,
        rules: 1,
        scope: 1,
        scrolling: 1,
        selected: 1,
        shape: 1,
        target: 1,
        text: 1,
        type: 1,
        valign: 1,
        valuetype: 1,
        vlink: 1
      };
      const Combinators = {};
      const Selectors = {};
      const Operators = {
        "=": {
          p1: "^",
          p2: "$",
          p3: "true"
        },
        "^=": {
          p1: "^",
          p2: "",
          p3: "true"
        },
        "$=": {
          p1: "",
          p2: "$",
          p3: "true"
        },
        "*=": {
          p1: "",
          p2: "",
          p3: "true"
        },
        "|=": {
          p1: "^",
          p2: "(-|$)",
          p3: "true"
        },
        "~=": {
          p1: "(^|\\s)",
          p2: "(\\s|$)",
          p3: "true"
        }
      };
      const concatCall = function(nodes, callback) {
        let i = 0;
        const l = nodes.length;
        const list = Array(l);
        while (l > i) {
          if (callback(list[i] = nodes[i]) === false) {
            break;
          }
          ++i;
        }
        return list;
      };
      const concatList = function(list, nodes) {
        let i = -1;
        let l = nodes.length;
        while (l--) {
          list[list.length] = nodes[++i];
        }
        return list;
      };
      let hasDupes = false;
      const documentOrder = function(a, b) {
        if (!hasDupes && a === b) {
          hasDupes = true;
          return 0;
        }
        return a.compareDocumentPosition(b) & 4 ? -1 : 1;
      };
      const unique = function(nodes) {
        let i = 0;
        let j = -1;
        let l = nodes.length + 1;
        const list = [];
        while (--l) {
          if (nodes[i++] === nodes[i]) {
            continue;
          }
          list[++j] = nodes[i - 1];
        }
        hasDupes = false;
        return list;
      };
      const hasMixedCaseTagNames = function(context) {
        const api = "getElementsByTagNameNS";
        context = context.ownerDocument || context;
        const ns = context.documentElement && context.documentElement.namespaceURI ? context.documentElement.namespaceURI : "http://www.w3.org/1999/xhtml";
        return context[api]("*", "*").length - context[api](ns, "*").length > 0;
      };
      const isHTML = function(node) {
        const doc2 = node.ownerDocument || node;
        return doc2.nodeType === 9 && doc2.contentType === "text/html";
      };
      const codePointToUTF16 = function(codePoint) {
        if (codePoint < 1 || codePoint > 1114111 || codePoint > 55295 && codePoint < 57344) {
          return "\\ufffd";
        }
        if (codePoint < 65536) {
          const lowHex = "000" + codePoint.toString(16);
          return "\\u" + lowHex.substr(lowHex.length - 4);
        }
        return "\\u" + ((codePoint - 65536 >> 10) + 55296).toString(16) + "\\u" + ((codePoint - 65536) % 1024 + 56320).toString(16);
      };
      const stringFromCodePoint = function(codePoint) {
        if (codePoint < 1 || codePoint > 1114111 || codePoint > 55295 && codePoint < 57344) {
          return "\uFFFD";
        }
        if (codePoint < 65536) {
          return String.fromCharCode(codePoint);
        }
        return String.fromCodePoint(codePoint);
      };
      const convertEscapes = function(str) {
        return REX.hasEscapes.test(str) ? str.replace(REX.fixEscapes, function(substring, p1, p2) {
          return p2 ? "\\" + p2 : REX.hexNumbers.test(p1) ? codePointToUTF16(parseInt(p1, 16)) : REX.escOrQuote.test(p1) ? substring : p1;
        }) : str;
      };
      const unescapeIdentifier = function(str) {
        return REX.hasEscapes.test(str) ? str.replace(REX.fixEscapes, function(substring, p1, p2) {
          return p2 || (REX.hexNumbers.test(p1) ? stringFromCodePoint(parseInt(p1, 16)) : REX.escOrQuote.test(p1) ? substring : p1);
        }) : str;
      };
      const none = [];
      const matchLambdas = {};
      const selectLambdas = {};
      let matchResolvers = {};
      let selectResolvers = {};
      const method = {
        "#": "getElementById",
        "*": "getElementsByTagName",
        "|": "getElementsByTagNameNS",
        ".": "getElementsByClassName"
      };
      const byIdRaw = function(id, context) {
        let node = context;
        const nodes = [];
        let next = node.firstElementChild;
        while (node = next) {
          node.id === id && nodes.push(node);
          if (next = node.firstElementChild || node.nextElementSibling) {
            continue;
          }
          while (!next && (node = node.parentElement) && node !== context) {
            next = node.nextElementSibling;
          }
        }
        return nodes;
      };
      const byId = function(id, context) {
        let e;
        const api = method["#"];
        if (Config.IDS_DUPES === false) {
          if (api in context) {
            e = context[api](id);
            return e ? [e] : none;
          }
        } else if ("all" in context) {
          if (e = context.all[id]) {
            if (e.nodeType === 1) {
              return e.getAttribute("id") !== id ? [] : [e];
            } else if (id === "length") {
              e = context[api](id);
              return e ? [e] : none;
            }
            const nodes = [];
            for (let i = 0, l = e.length; l > i; ++i) {
              if (e[i].id === id) {
                nodes.push(e[i]);
              }
            }
            return nodes.length ? nodes : none;
          } else {
            return none;
          }
        }
        return byIdRaw(id, context);
      };
      const byTag = function(tag, context) {
        let e;
        let nodes;
        const api = method["*"];
        if (api in context) {
          return Array.prototype.slice.call(context[api](tag));
        } else {
          tag = tag.toLowerCase();
          if (e = context.firstElementChild) {
            if (!(e.nextElementSibling || tag === "*" || e.localName === tag)) {
              return Array.prototype.slice.call(e[api](tag));
            } else {
              nodes = [];
              do {
                if (tag === "*" || e.localName === tag) {
                  nodes.push(e);
                }
                concatList(nodes, e[api](tag));
              } while (e = e.nextElementSibling);
            }
          } else {
            nodes = none;
          }
        }
        return nodes;
      };
      const byClass = function(cls, context) {
        let e;
        let nodes;
        const api = method["."];
        let reCls;
        if (api in context) {
          return Array.prototype.slice.call(context[api](cls));
        } else {
          if (e = context.firstElementChild) {
            reCls = RegExp("(^|\\s)" + cls + "(\\s|$)", QUIRKS_MODE ? "i" : "");
            if (!(e.nextElementSibling || reCls.test(e.className))) {
              return Array.prototype.slice.call(e[api](cls));
            } else {
              nodes = [];
              do {
                if (reCls.test(e.className)) {
                  nodes.push(e);
                }
                concatList(nodes, e[api](cls));
              } while (e = e.nextElementSibling);
            }
          } else nodes = none;
        }
        return nodes;
      };
      const compat = {
        "#": function(c, n) {
          REX.hasEscapes.test(n) && (n = unescapeIdentifier(n));
          return function(e, f) {
            return byId(n, c);
          };
        },
        "*": function(c, n) {
          REX.hasEscapes.test(n) && (n = unescapeIdentifier(n));
          return function(e, f) {
            return byTag(n, c);
          };
        },
        "|": function(c, n) {
          REX.hasEscapes.test(n) && (n = unescapeIdentifier(n));
          return function(e, f) {
            return byTag(n, c);
          };
        },
        ".": function(c, n) {
          REX.hasEscapes.test(n) && (n = unescapeIdentifier(n));
          return function(e, f) {
            return byClass(n, c);
          };
        }
      };
      const hasAttributeNS = function(e, name50) {
        let i;
        let l;
        const attr = e.getAttributeNames();
        name50 = RegExp(":?" + name50 + "$", HTML_DOCUMENT ? "i" : "");
        for (i = 0, l = attr.length; l > i; ++i) {
          if (name50.test(attr[i])) {
            return true;
          }
        }
        return false;
      };
      const nthElement = /* @__PURE__ */ (function() {
        let idx = 0;
        let len = 0;
        let set = 0;
        let parent;
        let parents = [];
        let nodes = [];
        return function(element, dir) {
          if (dir === 2) {
            idx = 0;
            len = 0;
            set = 0;
            nodes = [];
            parents = [];
            parent = void 0;
            return -1;
          }
          let e, i, j, k, l;
          if (parent === element.parentElement) {
            i = set;
            j = idx;
            l = len;
          } else {
            l = parents.length;
            parent = element.parentElement;
            for (i = -1, j = 0, k = l - 1; l > j; ++j, --k) {
              if (parents[j] === parent) {
                i = j;
                break;
              }
              if (parents[k] === parent) {
                i = k;
                break;
              }
            }
            if (i < 0) {
              parents[i = l] = parent;
              l = 0;
              nodes[i] = [];
              e = parent && parent.firstElementChild || element;
              while (e) {
                nodes[i][l] = e;
                if (e === element) {
                  j = l;
                }
                e = e.nextElementSibling;
                ++l;
              }
              set = i;
              idx = 0;
              len = l;
              if (l < 2) {
                return l;
              }
            } else {
              l = nodes[i].length;
              set = i;
            }
          }
          if (element !== nodes[i][j] && element !== nodes[i][j = 0]) {
            for (j = 0, e = nodes[i], k = l - 1; l > j; ++j, --k) {
              if (e[j] === element) {
                break;
              }
              if (e[k] === element) {
                j = k;
                break;
              }
            }
          }
          idx = j + 1;
          len = l;
          return dir ? l - j : idx;
        };
      })();
      const nthOfType = /* @__PURE__ */ (function() {
        let idx = 0;
        let len = 0;
        let set = 0;
        let parent;
        let parents = [];
        let nodes = [];
        return function(element, dir) {
          if (dir === 2) {
            idx = 0;
            len = 0;
            set = 0;
            nodes = [];
            parents = [];
            parent = void 0;
            return -1;
          }
          const name50 = element.localName;
          const nsURI = element.namespaceURI;
          if (nsURI !== "http://www.w3.org/1999/xhtml") {
            idx = 0;
            len = 0;
            set = 0;
            nodes = [];
            parents = [];
            parent = void 0;
          }
          let e;
          let i;
          let j;
          let k;
          let l;
          if (nodes[set] && nodes[set][name50] && parent === element.parentElement) {
            i = set;
            j = idx;
            l = len;
          } else {
            l = parents.length;
            parent = element.parentElement;
            for (i = -1, j = 0, k = l - 1; l > j; ++j, --k) {
              if (parents[j] === parent) {
                i = j;
                break;
              }
              if (parents[k] === parent) {
                i = k;
                break;
              }
            }
            if (i < 0 || !nodes[i][name50]) {
              parents[i = l] = parent;
              nodes[i] || (nodes[i] = Object());
              l = 0;
              nodes[i][name50] = [];
              e = parent && parent.firstElementChild || element;
              while (e) {
                if (e === element) {
                  j = l;
                }
                if (e.localName === name50 && e.namespaceURI === nsURI) {
                  nodes[i][name50][l] = e;
                  ++l;
                }
                e = e.nextElementSibling;
              }
              set = i;
              idx = j;
              len = l;
              if (l < 2) {
                return l;
              }
            } else {
              l = nodes[i][name50].length;
              set = i;
            }
          }
          if (element !== nodes[i][name50][j] && element !== nodes[i][name50][j = 0]) {
            for (j = 0, e = nodes[i][name50], k = l - 1; l > j; ++j, --k) {
              if (e[j] === element) {
                break;
              }
              if (e[k] === element) {
                j = k;
                break;
              }
            }
          }
          idx = j + 1;
          len = l;
          return dir ? l - j : idx;
        };
      })();
      const isTarget = function(node) {
        const doc2 = node.ownerDocument || node;
        const { hash } = new URL(doc2.URL);
        if (node.id && hash === `#${node.id}` && doc2.contains(node)) {
          return true;
        }
        return false;
      };
      const isIndeterminate = function(node) {
        if (node.indeterminate && node.localName === "input" && node.type === "checkbox" || node.localName === "progress" && !node.hasAttribute("value")) {
          return true;
        }
        if (node.localName === "input" && node.type === "radio" && !node.hasAttribute("checked")) {
          const nodeName = node.name;
          let parent = node.parentNode;
          while (parent) {
            if (parent.localName === "form") {
              break;
            }
            parent = parent.parentNode;
          }
          if (!parent) {
            const doc2 = node.ownerDocument;
            parent = doc2.documentElement;
          }
          const items = parent.getElementsByTagName("input");
          const l = items.length;
          let checked;
          for (let i = 0; i < l; i++) {
            const item = items[i];
            if (item.getAttribute("type") === "radio") {
              if (nodeName) {
                if (item.getAttribute("name") === nodeName) {
                  checked = !!item.checked;
                }
              } else if (!item.hasAttribute("name")) {
                checked = !!item.checked;
              }
              if (checked) {
                break;
              }
            }
          }
          if (!checked) {
            return true;
          }
        }
        return false;
      };
      const isContentEditable2 = function(node) {
        let attrValue = "inherit";
        if (node.hasAttribute("contenteditable")) {
          attrValue = node.getAttribute("contenteditable");
        }
        switch (attrValue) {
          case "":
          case "plaintext-only":
          case "true":
            return true;
          case "false":
            return false;
          default:
            if (node.parentNode && node.parentNode.nodeType === 1) {
              return isContentEditable2(node.parentNode);
            }
            return false;
        }
      };
      const setIdentifierSyntax = function() {
        const nonascii = "[^\\x00-\\x9f]";
        const esctoken = "\\\\(?:[^\\r\\n\\f\\da-f]|[\\da-f]{1,6}\\s{0,255})";
        const identifier = "(?:--|-?(?:[a-z_]|" + nonascii + "|" + esctoken + "))(?:[\\w-]|" + nonascii + "|" + esctoken + ")*";
        const pseudonames = "[-\\w]+";
        const pseudoparms = "(?:[-+]?\\d*)(?:n\\s?[-+]?\\s?\\d*)";
        const doublequote = '"[^"\\\\]*(?:\\\\.[^"\\\\]*)*(?:"|$)';
        const singlequote = "'[^'\\\\]*(?:\\\\.[^'\\\\]*)*(?:'|$)";
        const attrparser = identifier + "|" + doublequote + "|" + singlequote;
        const attrvalues = "([\\x22\\x27]?)((?!\\3)*|(?:\\\\?.)*?)(?:\\3|$)";
        const attributes = "\\[(?:\\*\\|)?\\s?(" + identifier + "(?::" + identifier + ")?)\\s?(?:(" + CFG.operators + ")\\s?(?:" + attrparser + "))?(?:\\s?\\b(i))?\\s?(?:\\]|$)";
        const attrmatcher = attributes.replace(attrparser, attrvalues);
        const pseudoclass = "(?:\\x28\\s*(?:" + pseudoparms + "?)?|[*|]|(?:(?::" + pseudonames + "(?:\\x28" + pseudoparms + "?(?:\\x29|$))?)|(?:[.#]?" + identifier + ")|(?:" + attributes + "))+|\\s?[>+~]\\s?|\\s?,\\s?|\\s|\\x29|$)*";
        const standardValidator = "(?=\\s?[^>+~(){}<])(?:\\*|\\||(?:[.#]?" + identifier + ")+|(?:" + attributes + ")+|(?:::?" + pseudonames + pseudoclass + ")|(?:\\s?" + CFG.combinators + "\\s?)|\\s?,\\s?|\\s?)+";
        reOptimizer = RegExp(
          "(?:([.:#*]?)(" + identifier + ")(?::[-\\w]+|\\[[^\\]]+(?:\\]|$)|\\x28[^\\x29]+(?:\\x29|$))*)$",
          "i"
        );
        reValidator = RegExp(standardValidator, "gi");
        Patterns.id = RegExp("^#(" + identifier + ")(.*)", "i");
        Patterns.tagName = RegExp("^(" + identifier + ")(.*)", "i");
        Patterns.className = RegExp("^\\.(" + identifier + ")(.*)", "i");
        Patterns.attribute = RegExp("^(?:" + attrmatcher + ")(.*)");
      };
      const configure = function(option, clear) {
        if (typeof option === "string") {
          return !!Config[option];
        }
        if (typeof option !== "object") {
          return Config;
        }
        for (const i in option) {
          Config[i] = !!option[i];
        }
        if (clear) {
          matchResolvers = {};
          selectResolvers = {};
        }
        setIdentifierSyntax();
        return true;
      };
      const emit = function(message, proto) {
        let err;
        if (Config.VERBOSITY) {
          if (global[proto]) {
            err = new global[proto](message);
          } else {
            err = new global.DOMException(message, "SyntaxError");
          }
          throw err;
        }
        if (Config.LOGERRORS && console && console.log) {
          console.log(message);
        }
      };
      const Snapshot = {
        doc: null,
        from: null,
        byTag: null,
        first: null,
        match: null,
        ancestor: null,
        nthOfType: null,
        nthElement: null,
        hasAttributeNS: null,
        isTarget: null,
        isIndeterminate: null,
        isContentEditable: null
      };
      let lastContext;
      const switchContext = function(context, force) {
        const oldDoc = doc;
        doc = context.ownerDocument || context;
        if (force || oldDoc !== doc) {
          HTML_DOCUMENT = isHTML(doc);
          QUIRKS_MODE = HTML_DOCUMENT && doc.compatMode.indexOf("CSS") < 0;
          NAMESPACE = doc.documentElement && doc.documentElement.namespaceURI;
          Snapshot.doc = doc;
        }
        Snapshot.from = context;
        return context;
      };
      let lastMatched;
      let lastSelected;
      const F_INIT = '"use strict";return function Resolver(c,f,x,r)';
      const S_HEAD = "var e,n,o,j=r.length-1,k=-1";
      const M_HEAD = "var e,n,o";
      const S_LOOP = "main:while((e=c[++k]))";
      const N_LOOP = "main:while((e=c.item(++k)))";
      const M_LOOP = "e=c;";
      const S_BODY = "r[++j]=c[k];";
      const N_BODY = "r[++j]=c.item(k);";
      const M_BODY = "";
      const S_TAIL = "continue main;";
      const M_TAIL = "r=true;";
      const S_TEST = "if(f(c[k])){break main;}";
      const N_TEST = "if(f(c.item(k))){break main;}";
      const M_TEST = "f(c);";
      let S_VARS = [];
      let M_VARS = [];
      const compileSelector = function(expression, source, mode, callback) {
        let a;
        let b;
        let n;
        let f;
        let name50;
        let NS;
        const N6 = "";
        const D = "!";
        let compat2;
        let expr;
        let match2;
        let result;
        let status;
        let symbol;
        let test;
        let type;
        let selector2 = expression;
        let vars;
        const selectorString = mode ? lastSelected : lastMatched;
        selector2 = selector2.replace(STD.combinator, "$1");
        let selectorRecursion = true;
        while (selector2) {
          symbol = STD.apimethods.test(selector2) ? "|" : selector2[0];
          switch (symbol) {
            // universal resolver
            case "*":
              match2 = selector2.match(Patterns.universal);
              if (N6 === "!") {
                source = "if(" + N6 + "true){" + source + "}";
              }
              break;
            // id resolver
            case "#":
              match2 = selector2.match(Patterns.id);
              source = "if(" + N6 + "(/^" + match2[1] + '$/.test(e.getAttribute("id")))){' + source + "}";
              break;
            // class name resolver
            case ".":
              match2 = selector2.match(Patterns.className);
              compat2 = (QUIRKS_MODE ? "i" : "") + '.test(e.getAttribute("class"))';
              source = "if(" + N6 + "(/(^|\\s)" + match2[1] + "(\\s|$)/" + compat2 + ")){" + source + "}";
              break;
            // tag name resolver
            case (/[_a-z]/i.test(symbol) ? symbol : void 0):
              match2 = selector2.match(Patterns.tagName);
              source = "if(" + N6 + "(e.localName" + (Config.MIXEDCASE || hasMixedCaseTagNames(doc) ? '=="' + match2[1].toLowerCase() + '"' : '=="' + match2[1].toUpperCase() + '"') + ")){" + source + "}";
              break;
            // namespace resolver
            case "|":
              match2 = selector2.match(Patterns.namespace);
              if (match2[1] === "*") {
                source = "if(" + N6 + "true){" + source + "}";
              } else if (!match2[1]) {
                source = "if(" + N6 + "(!e.namespaceURI)){" + source + "}";
              } else if (typeof match2[1] === "string" && doc.documentElement && doc.documentElement.prefix === match2[1]) {
                source = "if(" + N6 + '(e.namespaceURI=="' + NAMESPACE + '")){' + source + "}";
              } else {
                emit("'" + selectorString + "'" + qsInvalid);
              }
              break;
            // attributes resolver
            case "[":
              match2 = selector2.match(Patterns.attribute);
              NS = match2[0].match(STD.namespaces);
              name50 = match2[1];
              expr = name50.split(":");
              expr = expr.length === 2 ? expr[1] : expr[0];
              if (match2[2] && !(test = Operators[match2[2]])) {
                emit("'" + selectorString + "'" + qsInvalid);
                return "";
              }
              if (match2[4] === "") {
                test = match2[2] === "~=" ? { p1: "^\\s", p2: "+$", p3: "true" } : match2[2] in ATTR_STD_OPS && match2[2] !== "~=" ? { p1: "^", p2: "$", p3: "true" } : test;
              } else if (match2[2] === "~=" && match2[4].includes(" ")) {
                source = "if(" + N6 + "false){" + source + "}";
                break;
              } else if (match2[4]) {
                match2[4] = convertEscapes(match2[4]).replace(REX.regExpChar, "\\$&");
              }
              type = match2[5] === "i" || HTML_DOCUMENT && HTML_TABLE[expr.toLowerCase()] ? "i" : "";
              source = "if(" + N6 + "(" + (!match2[2] ? NS ? 's.hasAttributeNS(e,"' + name50 + '")' : 'e.hasAttribute&&e.hasAttribute("' + name50 + '")' : !match2[4] && ATTR_STD_OPS[match2[2]] && match2[2] !== "~=" ? 'e.getAttribute&&e.getAttribute("' + name50 + '")==""' : "(/" + test.p1 + match2[4] + test.p2 + "/" + type + ').test(e.getAttribute&&e.getAttribute("' + name50 + '"))==' + test.p3) + ")){" + source + "}";
              break;
            // *** General sibling combinator
            // E ~ F (F relative sibling of E)
            case "~":
              match2 = selector2.match(Patterns.relative);
              source = "n=e;while((e=e.previousElementSibling)){" + source + "}e=n;";
              break;
            // *** Adjacent sibling combinator
            // E + F (F adiacent sibling of E)
            case "+":
              match2 = selector2.match(Patterns.adjacent);
              source = "n=e;if((e=e.previousElementSibling)){" + source + "}e=n;";
              break;
            // *** Descendant combinator
            // E F (E ancestor of F)
            case "	":
            case " ":
              match2 = selector2.match(Patterns.ancestor);
              source = "n=e;while((e=e.parentElement)){" + source + "}e=n;";
              break;
            // *** Child combinator
            // E > F (F children of E)
            case ">":
              match2 = selector2.match(Patterns.children);
              source = "n=e;if((e=e.parentElement)){" + source + "}e=n;";
              break;
            // *** user supplied combinators extensions
            case (symbol in Combinators ? symbol : void 0):
              match2[match2.length - 1] = "*";
              source = Combinators[symbol](match2) + source;
              break;
            // *** tree-structural pseudo-classes
            // :root, :empty, :first-child, :last-child, :only-child, :first-of-type, :last-of-type, :only-of-type
            case ":":
              if (match2 = selector2.match(Patterns.structural)) {
                match2[1] = match2[1].toLowerCase();
                switch (match2[1]) {
                  case "root":
                    source = "if(" + N6 + "(e===s.doc.documentElement)){" + source + (mode ? "break main;" : "") + "}";
                    break;
                  case "empty":
                    source = "n=e.firstChild;while(n&&!(/1|3/).test(n.nodeType)){n=n.nextSibling}if(" + D + "n){" + source + "}";
                    break;
                  // *** child-indexed pseudo-classes
                  // :first-child, :last-child, :only-child
                  case "only-child":
                    source = "if(" + N6 + "(!e.nextElementSibling&&!e.previousElementSibling)){" + source + "}";
                    break;
                  case "last-child":
                    source = "if(" + N6 + "(!e.nextElementSibling)){" + source + "}";
                    break;
                  case "first-child":
                    source = "if(" + N6 + "(!e.previousElementSibling)){" + source + "}";
                    break;
                  // *** typed child-indexed pseudo-classes
                  // :only-of-type, :last-of-type, :first-of-type
                  case "only-of-type":
                    source = "o=e.localName;n=e;while((n=n.nextElementSibling)&&n.localName!=o);if(!n){n=e;while((n=n.previousElementSibling)&&n.localName!=o);}if(" + D + "n){" + source + "}";
                    break;
                  case "last-of-type":
                    source = "n=e;o=e.localName;while((n=n.nextElementSibling)&&n.localName!=o);if(" + D + "n){" + source + "}";
                    break;
                  case "first-of-type":
                    source = "n=e;o=e.localName;while((n=n.previousElementSibling)&&n.localName!=o);if(" + D + "n){" + source + "}";
                    break;
                  default:
                    emit("'" + selectorString + "'" + qsInvalid);
                }
              } else if (match2 = selector2.match(Patterns.treestruct)) {
                match2[1] = match2[1].toLowerCase();
                switch (match2[1]) {
                  case "nth-child":
                  case "nth-of-type":
                  case "nth-last-child":
                  case "nth-last-of-type":
                    expr = /-of-type/i.test(match2[1]);
                    if (match2[1] && match2[2]) {
                      type = /last/i.test(match2[1]);
                      if (match2[2] === "n") {
                        source = "if(" + N6 + "true){" + source + "}";
                        break;
                      } else if (match2[2] === "1") {
                        test = type ? "next" : "previous";
                        source = expr ? "n=e;o=e.localName;while((n=n." + test + "ElementSibling)&&n.localName!=o);if(" + D + "n){" + source + "}" : "if(" + N6 + "!e." + test + "ElementSibling){" + source + "}";
                        break;
                      } else if (match2[2] === "even" || match2[2] === "2n0" || match2[2] === "2n+0" || match2[2] === "2n") {
                        test = "n%2==0";
                      } else if (match2[2] === "odd" || match2[2] === "2n1" || match2[2] === "2n+1") {
                        test = "n%2==1";
                      } else {
                        f = /n/i.test(match2[2]);
                        n = match2[2].split("n");
                        a = parseInt(n[0], 10) || 0;
                        b = parseInt(n[1], 10) || 0;
                        if (n[0] === "-") {
                          a = -1;
                        }
                        if (n[0] === "+") {
                          a = 1;
                        }
                        test = (b ? "(n" + (b > 0 ? "-" : "+") + Math.abs(b) + ")" : "n") + "%" + a + "==0";
                        test = a >= 1 ? f ? "n>" + (b - 1) + (Math.abs(a) !== 1 ? "&&" + test : "") : "n==" + a : a <= -1 ? f ? "n<" + (b + 1) + (Math.abs(a) !== 1 ? "&&" + test : "") : "n==" + a : a === 0 ? n[0] ? "n==" + b : "n>" + (b - 1) : "false";
                      }
                      expr = expr ? "OfType" : "Element";
                      type = type ? "true" : "false";
                      source = "n=s.nth" + expr + "(e," + type + ");if(" + N6 + "(" + test + ")){" + source + "}";
                    } else {
                      emit("'" + selectorString + "'" + qsInvalid);
                    }
                    break;
                  default:
                    emit("'" + selectorString + "'" + qsInvalid);
                }
              } else if (match2 = selector2.match(Patterns.logicalsel)) {
                match2[1] = match2[1].toLowerCase();
                expr = match2[2].replace(REX.CommaGroup, ",").replace(REX.TrimSpaces, "");
                switch (match2[1]) {
                  // FIXME:
                  case "is":
                  case "where":
                  case "matches":
                    source = 'if(s.match("' + expr.replace(/\x22/g, '\\"') + '",e)){' + source + "}";
                    break;
                  // FIXME:
                  case "not":
                    source = 'if(!s.match("' + expr.replace(/\x22/g, '\\"') + '",e)){' + source + "}";
                    break;
                  // FIXME:
                  case "has":
                    matchResolvers = {};
                    source = 'if(e.querySelector(":scope ' + expr.replace(/\x22/g, '\\"') + '")){' + source + "}";
                    break;
                  default:
                    emit("'" + selectorString + "'" + qsInvalid);
                }
              } else if (match2 = selector2.match(Patterns.locationpc)) {
                match2[1] = match2[1].toLowerCase();
                switch (match2[1]) {
                  case "any-link":
                    source = "if(" + N6 + '(/^a|area$/i.test(e.localName)&&e.hasAttribute("href")||e.visited)){' + source + "}";
                    break;
                  case "link":
                    source = "if(" + N6 + '(/^a|area$/i.test(e.localName)&&e.hasAttribute("href"))){' + source + "}";
                    break;
                  // FIXME:
                  case "visited":
                    source = "if(" + N6 + '(/^a|area$/i.test(e.localName)&&e.hasAttribute("href")&&e.visited)){' + source + "}";
                    break;
                  case "target":
                    source = "if(s.isTarget(e)){" + source + "}";
                    break;
                  default:
                    emit("'" + selectorString + "'" + qsInvalid);
                }
              } else if (match2 = selector2.match(Patterns.inputstate)) {
                match2[1] = match2[1].toLowerCase();
                switch (match2[1]) {
                  // FIXME: lacks custom element support
                  case "enabled":
                    source = 'if((("form" in e||/^optgroup$/i.test(e.localName))&&"disabled" in e &&e.disabled===false)){' + source + "}";
                    break;
                  // FIXME: lacks custom element support
                  case "disabled":
                    source = 'if((("form" in e||/^optgroup$/i.test(e.localName))&&"disabled" in e)){var x=0,N=[],F=false,L=false;if(!(/^(optgroup|option)$/i.test(e.localName))){n=e.parentElement;while(n){if(n.localName==="fieldset"){N[x++]=n;if(n.disabled===true){F=true;break;}}n=n.parentElement;}for(var x=0;x<N.length;x++){if((n=s.first("legend",N[x]))&&n.contains(e)){L=true;break;}}}if(e.disabled===true||(F&&!L)){' + source + "}}";
                    break;
                  case "read-only":
                    source = 'if((/^textarea$/i.test(e.localName)&&(e.readOnly||e.disabled))||(/^input$/i.test(e.localName)&&("|date|datetime-local|email|month|number|password|search|tel|text|time|url|week|".includes("|"+e.type+"|")?(e.readOnly||e.disabled):true))||(!/^(?:input|textarea)$/i.test(e.localName) && !s.isContentEditable(e))){' + source + "}";
                    break;
                  case "read-write":
                    source = 'if((/^textarea$/i.test(e.localName)&&!e.readOnly&&!e.disabled)||(/^input$/i.test(e.localName)&&"|date|datetime-local|email|month|number|password|search|tel|text|time|url|week|".includes("|"+e.type+"|")&&!e.readOnly&&!e.disabled)||(!/^(?:input|textarea)$/i.test(e.localName) && s.isContentEditable(e))){' + source + "}";
                    break;
                  // FIXME:
                  case "placeholder-shown":
                    source = 'if(((/^input|textarea$/i.test(e.localName))&&e.hasAttribute("placeholder")&&("|textarea|password|number|search|email|text|tel|url|".includes("|"+e.type+"|"))&&(!s.match(":focus",e)))){' + source + "}";
                    break;
                  // FIXME:
                  case "default":
                    source = 'if(("form" in e && e.form)){var x=0;n=[];if(e.type=="image")n=e.form.getElementsByTagName("input");if(e.type=="submit")n=e.form.elements;while(n[x]&&e!==n[x]){if(n[x].type=="image")break;if(n[x].type=="submit")break;x++;}}if((e.form&&(e===n[x]&&"|image|submit|".includes("|"+e.type+"|"))||((/^option$/i.test(e.localName))&&e.defaultSelected)||(("|radio|checkbox|".includes("|"+e.type+"|"))&&e.defaultChecked))){' + source + "}";
                    break;
                  default:
                    emit("'" + selector_string + "'" + qsInvalid);
                    break;
                }
              } else if (match2 = selector2.match(Patterns.inputvalue)) {
                match2[1] = match2[1].toLowerCase();
                switch (match2[1]) {
                  case "checked":
                    source = "if(" + N6 + '(/^input$/i.test(e.localName)&&("|radio|checkbox|".includes("|"+e.type+"|")&&e.checked)||(/^option$/i.test(e.localName)&&(e.selected||e.checked)))){' + source + "}";
                    break;
                  case "indeterminate":
                    source = "if(s.isIndeterminate(e)){" + source + "}";
                    break;
                  // FIXME:
                  case "required":
                    source = "if(" + N6 + "(/^input|select|textarea$/i.test(e.localName)&&e.required)){" + source + "}";
                    break;
                  // FIXME:
                  case "optional":
                    source = "if(" + N6 + "(/^input|select|textarea$/i.test(e.localName)&&!e.required)){" + source + "}";
                    break;
                  // FIXME:
                  case "invalid":
                    source = "if(" + N6 + '(((/^form$/i.test(e.localName)&&!e.noValidate)||(e.willValidate&&!e.formNoValidate))&&!e.checkValidity())||(/^fieldset$/i.test(e.localName)&&s.first(":invalid",e))){' + source + "}";
                    break;
                  // FIXME:
                  case "valid":
                    source = "if(" + N6 + '(((/^form$/i.test(e.localName)&&!e.noValidate)||(e.willValidate&&!e.formNoValidate))&&e.checkValidity())||(/^fieldset$/i.test(e.localName)&&s.first(":valid",e))){' + source + "}";
                    break;
                  // FIXME:
                  case "in-range":
                    source = "if(" + N6 + '(/^input$/i.test(e.localName))&&(e.willValidate&&!e.formNoValidate)&&(!e.validity.rangeUnderflow&&!e.validity.rangeOverflow)&&("|date|datetime-local|month|number|range|time|week|".includes("|"+e.type+"|"))&&("range"==e.type||e.getAttribute("min")||e.getAttribute("max"))){' + source + "}";
                    break;
                  // FIXME:
                  case "out-of-range":
                    source = "if(" + N6 + '(/^input$/i.test(e.localName))&&(e.willValidate&&!e.formNoValidate)&&(e.validity.rangeUnderflow||e.validity.rangeOverflow)&&("|date|datetime-local|month|number|range|time|week|".includes("|"+e.type+"|"))&&("range"==e.type||e.getAttribute("min")||e.getAttribute("max"))){' + source + "}";
                    break;
                  default:
                    emit("'" + selectorString + "'" + qsInvalid);
                }
              } else if (match2 = selector2.match(Patterns.pseudoSng)) {
                source = 'if(e.element&&e.type.toLowerCase()==":' + match2[0].toLowerCase() + '"){e=e.element;' + source + "}";
              } else if (match2 = selector2.match(Patterns.pseudoDbl)) {
                source = 'if(e.element&&e.type.toLowerCase()=="' + match2[0].toLowerCase() + '"){e=e.element;' + source + "}";
              } else if (match2 = selector2.match(Patterns.pseudoNop)) {
                source = "if(" + N6 + "false){" + source + "}";
              } else {
                expr = false;
                status = false;
                for (expr in Selectors) {
                  if (match2 = selector2.match(Selectors[expr].Expression)) {
                    result = Selectors[expr].Callback(match2, source, mode, callback);
                    if ("match" in result) {
                      match2 = result.match;
                    }
                    vars = result.modvar;
                    if (mode) {
                      vars && !S_VARS.includes(vars) && S_VARS.push(vars);
                    } else {
                      vars && M_VARS.includes(vars) && M_VARS.push(vars);
                    }
                    source = result.source;
                    status = result.status;
                    if (status) {
                      break;
                    }
                  }
                }
                if (!status) {
                  emit("unknown pseudo-class selector '" + selector2 + "'");
                  return "";
                }
                if (!expr) {
                  emit("unknown token in selector '" + selector2 + "'");
                  return "";
                }
              }
              break;
            default:
              selectorRecursion = false;
              emit("'" + selectorString + "'" + qsInvalid);
          }
          if (!selectorRecursion) {
            break;
          }
          if (!match2) {
            emit("'" + selectorString + "'" + qsInvalid);
            return "";
          }
          selector2 = match2.pop();
        }
        return source;
      };
      const compile = function(selector2, mode, callback) {
        let head = "";
        let loop = "";
        let macro = "";
        let source = "";
        let vars = "";
        switch (mode) {
          case true:
            if (selectLambdas[selector2]) {
              return selectLambdas[selector2];
            }
            macro = S_BODY + (callback ? S_TEST : "") + S_TAIL;
            head = S_HEAD;
            loop = S_LOOP;
            break;
          case false:
            if (matchLambdas[selector2]) {
              return matchLambdas[selector2];
            }
            macro = M_BODY + (callback ? M_TEST : "") + M_TAIL;
            head = M_HEAD;
            loop = M_LOOP;
            break;
          case null:
            if (selectLambdas[selector2]) {
              return selectLambdas[selector2];
            }
            macro = N_BODY + (callback ? N_TEST : "") + S_TAIL;
            head = S_HEAD;
            loop = N_LOOP;
            break;
          default:
        }
        source = compileSelector(selector2, macro, mode, callback);
        loop += mode || mode === null ? "{" + source + "}" : source;
        if ((mode || mode === null) && selector2.includes(":nth")) {
          loop += reNthElem.test(selector2) ? "s.nthElement(null, 2);" : "";
          loop += reNthType.test(selector2) ? "s.nthOfType(null, 2);" : "";
        }
        if (S_VARS[0] || M_VARS[0]) {
          vars = "," + (S_VARS.join(",") || M_VARS.join(","));
          S_VARS = [];
          M_VARS = [];
        }
        const factory = Function("s", F_INIT + "{" + head + vars + ";" + loop + "return r;}")(Snapshot);
        return mode || mode === null ? selectLambdas[selector2] = factory : matchLambdas[selector2] = factory;
      };
      const optimize = function(selector2, token) {
        const index = token.index;
        const length2 = token[1].length + token[2].length;
        return selector2.slice(0, index) + (" >+~".indexOf(selector2.charAt(index - 1)) > -1 ? ":[".indexOf(selector2.charAt(index + length2 + 1)) > -1 ? "*" : "" : "") + selector2.slice(index + length2 - (token[1] === "*" ? 1 : 0));
      };
      const collect = function(selectors, context, callback) {
        let i;
        let l;
        const seen = {};
        let token = ["", "*", "*"];
        const optimized = selectors;
        const factory = [];
        const htmlset = [];
        const nodeset = [];
        let results = [];
        let type;
        for (i = 0, l = selectors.length; l > i; ++i) {
          if (!seen[selectors[i]] && (seen[selectors[i]] = true)) {
            type = selectors[i].match(reOptimizer);
            if (type && type[1] !== ":" && (token = type)) {
              token[1] || (token[1] = "*");
              optimized[i] = optimize(optimized[i], token);
            } else {
              token = ["", "*", "*"];
            }
          }
          nodeset[i] = token[1] + token[2];
          htmlset[i] = compat[token[1]](context, token[2]);
          factory[i] = compile(optimized[i], true, null);
          factory[i] ? factory[i](htmlset[i](), callback, context, results) : results.concat(htmlset[i]());
        }
        if (l > 1) {
          results.sort(documentOrder);
          hasDupes && (results = unique(results));
        }
        return {
          callback,
          context,
          factory,
          htmlset,
          nodeset,
          results
        };
      };
      const makeref = function(selectors, element) {
        if (element.nodeType === 9) {
          element = element.documentElement;
        }
        return selectors.replace(
          /:scope/gi,
          element.localName + (element.id ? "#" + element.id : "") + (element.className ? "." + element.classList[0] : "")
        );
      };
      const matchAssert = function(f, element, callback) {
        let r = false;
        for (let i = 0, l = f.length; l > i; ++i) {
          f[i](element, callback, null, false) && (r = true);
        }
        return r;
      };
      const matchCollect = function(selectors, callback) {
        const f = [];
        for (let i = 0, l = selectors.length; l > i; ++i) {
          f[i] = compile(selectors[i], false, callback);
        }
        return { factory: f };
      };
      const match = function _matches(selectors, element, callback) {
        let expressions;
        if (element && !/:has\(/.test(selectors) && matchResolvers[selectors]) {
          return matchAssert(matchResolvers[selectors].factory, element, callback);
        }
        lastMatched = selectors;
        if (arguments.length === 0) {
          emit(qsNotArgs, "TypeError");
          return Config.VERBOSITY ? void 0 : false;
        } else if (arguments[0] === "") {
          emit("''" + qsInvalid);
          return Config.VERBOSITY ? void 0 : false;
        }
        if (typeof selectors !== "string") {
          selectors = "" + selectors;
        }
        if (/:scope/i.test(selectors)) {
          selectors = makeref(selectors, element);
        }
        const parsed = selectors.replace(/\0|\\$/g, "\uFFFD").replace(REX.combineWSP, " ").replace(REX.pseudosWSP, "$1").replace(REX.tabCharWSP, "	").replace(REX.commaGroup, ",").replace(REX.trimSpaces, "");
        if ((expressions = parsed.match(reValidator)) && expressions.join("") === parsed) {
          expressions = parsed.match(REX.splitGroup);
          if (parsed[parsed.length - 1] === ",") {
            emit(qsInvalid);
            return Config.VERBOSITY ? void 0 : false;
          }
        } else {
          emit("'" + selectors + "'" + qsInvalid);
          return Config.VERBOSITY ? void 0 : false;
        }
        matchResolvers[selectors] = matchCollect(expressions, callback);
        return matchAssert(matchResolvers[selectors].factory, element, callback);
      };
      const ancestor = function _closest(selectors, element, callback) {
        if (/:scope/i.test(selectors)) {
          selectors = makeref(selectors, element);
        }
        while (element) {
          if (match(selectors, element, callback)) break;
          element = element.parentElement;
        }
        return element;
      };
      const select = function _querySelectorAll(selectors, context, callback) {
        let expressions;
        let nodes = [];
        let resolver;
        context || (context = doc);
        if (selectors) {
          if (resolver = selectResolvers[selectors]) {
            if (resolver.context === context && resolver.callback === callback) {
              const f = resolver.factory;
              const h = resolver.htmlset;
              const n = resolver.nodeset;
              if (n.length > 1) {
                const l = n.length;
                for (let i = 0, l2 = n.length, list; l2 > i; ++i) {
                  list = compat[n[i][0]](context, n[i].slice(1))();
                  if (f[i] !== null) {
                    f[i](list, callback, context, nodes);
                  } else {
                    nodes = nodes.concat(list);
                  }
                }
                if (l > 1 && nodes.length > 1) {
                  nodes.sort(documentOrder);
                  hasDupes && (nodes = unique(nodes));
                }
              } else {
                if (f[0]) {
                  nodes = f[0](h[0](), callback, context, nodes);
                } else {
                  nodes = h[0]();
                }
              }
              return typeof callback === "function" ? concatCall(nodes, callback) : nodes;
            }
          }
        }
        lastSelected = selectors;
        if (arguments.length === 0) {
          emit(qsNotArgs, "TypeError");
          return Config.VERBOSITY ? void 0 : none;
        } else if (arguments[0] === "") {
          emit("''" + qsInvalid);
          return Config.VERBOSITY ? void 0 : none;
        } else if (lastContext !== context) {
          lastContext = switchContext(context);
        }
        if (typeof selectors !== "string") {
          selectors = "" + selectors;
        }
        if (/:scope/i.test(selectors)) {
          selectors = makeref(selectors, context);
        }
        const parsed = selectors.replace(/\0|\\$/g, "\uFFFD").replace(REX.combineWSP, " ").replace(REX.pseudosWSP, "$1").replace(REX.tabCharWSP, "	").replace(REX.commaGroup, ",").replace(REX.trimSpaces, "");
        if ((expressions = parsed.match(reValidator)) && expressions.join("") === parsed) {
          expressions = parsed.match(REX.splitGroup);
          if (parsed[parsed.length - 1] === ",") {
            emit(qsInvalid);
            return Config.VERBOSITY ? void 0 : false;
          }
        } else {
          emit("'" + selectors + "'" + qsInvalid);
          return Config.VERBOSITY ? void 0 : false;
        }
        selectResolvers[selectors] = collect(expressions, context, callback);
        nodes = selectResolvers[selectors].results;
        return typeof callback === "function" ? concatCall(nodes, callback) : nodes;
      };
      const first = function _querySelector(selectors, context, callback) {
        if (arguments.length === 0) {
          emit(qsNotArgs, "TypeError");
        }
        return select(
          selectors,
          context,
          typeof callback === "function" ? function firstMatch(element) {
            callback(element);
            return false;
          } : function firstMatch() {
            return false;
          }
        )[0] || null;
      };
      const initialize = function(d) {
        setIdentifierSyntax();
        lastContext = switchContext(d, true);
        Snapshot.doc = doc;
        Snapshot.from = doc;
        Snapshot.byTag = byTag;
        Snapshot.first = first;
        Snapshot.match = match;
        Snapshot.ancestor = ancestor;
        Snapshot.nthOfType = nthOfType;
        Snapshot.nthElement = nthElement;
        Snapshot.hasAttributeNS = hasAttributeNS;
        Snapshot.isTarget = isTarget;
        Snapshot.isIndeterminate = isIndeterminate;
        Snapshot.isContentEditable = isContentEditable2;
      };
      initialize(doc);
      const Dom = {
        // exported engine methods
        Version: version,
        configure,
        match,
        closest: ancestor,
        first,
        select
      };
      return Dom;
    });
  }
});

// node_modules/bidi-js/dist/bidi.js
var require_bidi = __commonJS({
  "node_modules/bidi-js/dist/bidi.js"(exports2, module2) {
    (function(global, factory) {
      typeof exports2 === "object" && typeof module2 !== "undefined" ? module2.exports = factory() : typeof define === "function" && define.amd ? define(factory) : (global = typeof globalThis !== "undefined" ? globalThis : global || self, global.bidi_js = factory());
    })(exports2, (function() {
      "use strict";
      function bidiFactory2() {
        var bidi = (function(exports3) {
          var DATA = {
            "R": "13k,1a,2,3,3,2+1j,ch+16,a+1,5+2,2+n,5,a,4,6+16,4+3,h+1b,4mo,179q,2+9,2+11,2i9+7y,2+68,4,3+4,5+13,4+3,2+4k,3+29,8+cf,1t+7z,w+17,3+3m,1t+3z,16o1+5r,8+30,8+mc,29+1r,29+4v,75+73",
            "EN": "1c+9,3d+1,6,187+9,513,4+5,7+9,sf+j,175h+9,qw+q,161f+1d,4xt+a,25i+9",
            "ES": "17,2,6dp+1,f+1,av,16vr,mx+1,4o,2",
            "ET": "z+2,3h+3,b+1,ym,3e+1,2o,p4+1,8,6u,7c,g6,1wc,1n9+4,30+1b,2n,6d,qhx+1,h0m,a+1,49+2,63+1,4+1,6bb+3,12jj",
            "AN": "16o+5,2j+9,2+1,35,ed,1ff2+9,87+u",
            "CS": "18,2+1,b,2u,12k,55v,l,17v0,2,3,53,2+1,b",
            "B": "a,3,f+2,2v,690",
            "S": "9,2,k",
            "WS": "c,k,4f4,1vk+a,u,1j,335",
            "ON": "x+1,4+4,h+5,r+5,r+3,z,5+3,2+1,2+1,5,2+2,3+4,o,w,ci+1,8+d,3+d,6+8,2+g,39+1,9,6+1,2,33,b8,3+1,3c+1,7+1,5r,b,7h+3,sa+5,2,3i+6,jg+3,ur+9,2v,ij+1,9g+9,7+a,8m,4+1,49+x,14u,2+2,c+2,e+2,e+2,e+1,i+n,e+e,2+p,u+2,e+2,36+1,2+3,2+1,b,2+2,6+5,2,2,2,h+1,5+4,6+3,3+f,16+2,5+3l,3+81,1y+p,2+40,q+a,m+13,2r+ch,2+9e,75+hf,3+v,2+2w,6e+5,f+6,75+2a,1a+p,2+2g,d+5x,r+b,6+3,4+o,g,6+1,6+2,2k+1,4,2j,5h+z,1m+1,1e+f,t+2,1f+e,d+3,4o+3,2s+1,w,535+1r,h3l+1i,93+2,2s,b+1,3l+x,2v,4g+3,21+3,kz+1,g5v+1,5a,j+9,n+v,2,3,2+8,2+1,3+2,2,3,46+1,4+4,h+5,r+5,r+a,3h+2,4+6,b+4,78,1r+24,4+c,4,1hb,ey+6,103+j,16j+c,1ux+7,5+g,fsh,jdq+1t,4,57+2e,p1,1m,1m,1m,1m,4kt+1,7j+17,5+2r,d+e,3+e,2+e,2+10,m+4,w,1n+5,1q,4z+5,4b+rb,9+c,4+c,4+37,d+2g,8+b,l+b,5+1j,9+9,7+13,9+t,3+1,27+3c,2+29,2+3q,d+d,3+4,4+2,6+6,a+o,8+6,a+2,e+6,16+42,2+1i",
            "BN": "0+8,6+d,2s+5,2+p,e,4m9,1kt+2,2b+5,5+5,17q9+v,7k,6p+8,6+1,119d+3,440+7,96s+1,1ekf+1,1ekf+1,1ekf+1,1ekf+1,1ekf+1,1ekf+1,1ekf+1,1ekf+1,1ekf+1,1ekf+1,1ekf+1,1ekf+75,6p+2rz,1ben+1,1ekf+1,1ekf+1",
            "NSM": "lc+33,7o+6,7c+18,2,2+1,2+1,2,21+a,1d+k,h,2u+6,3+5,3+1,2+3,10,v+q,2k+a,1n+8,a,p+3,2+8,2+2,2+4,18+2,3c+e,2+v,1k,2,5+7,5,4+6,b+1,u,1n,5+3,9,l+1,r,3+1,1m,5+1,5+1,3+2,4,v+1,4,c+1,1m,5+4,2+1,5,l+1,n+5,2,1n,3,2+3,9,8+1,c+1,v,1q,d,1f,4,1m+2,6+2,2+3,8+1,c+1,u,1n,g+1,l+1,t+1,1m+1,5+3,9,l+1,u,21,8+2,2,2j,3+6,d+7,2r,3+8,c+5,23+1,s,2,2,1k+d,2+4,2+1,6+a,2+z,a,2v+3,2+5,2+1,3+1,q+1,5+2,h+3,e,3+1,7,g,jk+2,qb+2,u+2,u+1,v+1,1t+1,2+6,9,3+a,a,1a+2,3c+1,z,3b+2,5+1,a,7+2,64+1,3,1n,2+6,2,2,3+7,7+9,3,1d+g,1s+3,1d,2+4,2,6,15+8,d+1,x+3,3+1,2+2,1l,2+1,4,2+2,1n+7,3+1,49+2,2+c,2+6,5,7,4+1,5j+1l,2+4,k1+w,2db+2,3y,2p+v,ff+3,30+1,n9x+3,2+9,x+1,29+1,7l,4,5,q+1,6,48+1,r+h,e,13+7,q+a,1b+2,1d,3+3,3+1,14,1w+5,3+1,3+1,d,9,1c,1g,2+2,3+1,6+1,2,17+1,9,6n,3,5,fn5,ki+f,h+f,r2,6b,46+4,1af+2,2+1,6+3,15+2,5,4m+1,fy+3,as+1,4a+a,4x,1j+e,1l+2,1e+3,3+1,1y+2,11+4,2+7,1r,d+1,1h+8,b+3,3,2o+2,3,2+1,7,4h,4+7,m+1,1m+1,4,12+6,4+4,5g+7,3+2,2,o,2d+5,2,5+1,2+1,6n+3,7+1,2+1,s+1,2e+7,3,2+1,2z,2,3+5,2,2u+2,3+3,2+4,78+8,2+1,75+1,2,5,41+3,3+1,5,x+5,3+1,15+5,3+3,9,a+5,3+2,1b+c,2+1,bb+6,2+5,2d+l,3+6,2+1,2+1,3f+5,4,2+1,2+6,2,21+1,4,2,9o+1,f0c+4,1o+6,t5,1s+3,2a,f5l+1,43t+2,i+7,3+6,v+3,45+2,1j0+1i,5+1d,9,f,n+4,2+e,11t+6,2+g,3+6,2+1,2+4,7a+6,c6+3,15t+6,32+6,gzhy+6n",
            "AL": "16w,3,2,e+1b,z+2,2+2s,g+1,8+1,b+m,2+t,s+2i,c+e,4h+f,1d+1e,1bwe+dp,3+3z,x+c,2+1,35+3y,2rm+z,5+7,b+5,dt+l,c+u,17nl+27,1t+27,4x+6n,3+d",
            "LRO": "6ct",
            "RLO": "6cu",
            "LRE": "6cq",
            "RLE": "6cr",
            "PDF": "6cs",
            "LRI": "6ee",
            "RLI": "6ef",
            "FSI": "6eg",
            "PDI": "6eh"
          };
          var TYPES = {};
          var TYPES_TO_NAMES = {};
          TYPES.L = 1;
          TYPES_TO_NAMES[1] = "L";
          Object.keys(DATA).forEach(function(type, i) {
            TYPES[type] = 1 << i + 1;
            TYPES_TO_NAMES[TYPES[type]] = type;
          });
          Object.freeze(TYPES);
          var ISOLATE_INIT_TYPES = TYPES.LRI | TYPES.RLI | TYPES.FSI;
          var STRONG_TYPES = TYPES.L | TYPES.R | TYPES.AL;
          var NEUTRAL_ISOLATE_TYPES = TYPES.B | TYPES.S | TYPES.WS | TYPES.ON | TYPES.FSI | TYPES.LRI | TYPES.RLI | TYPES.PDI;
          var BN_LIKE_TYPES = TYPES.BN | TYPES.RLE | TYPES.LRE | TYPES.RLO | TYPES.LRO | TYPES.PDF;
          var TRAILING_TYPES = TYPES.S | TYPES.WS | TYPES.B | ISOLATE_INIT_TYPES | TYPES.PDI | BN_LIKE_TYPES;
          var map = null;
          function parseData() {
            if (!map) {
              map = /* @__PURE__ */ new Map();
              var loop = function(type2) {
                if (DATA.hasOwnProperty(type2)) {
                  var lastCode = 0;
                  DATA[type2].split(",").forEach(function(range) {
                    var ref = range.split("+");
                    var skip = ref[0];
                    var step = ref[1];
                    skip = parseInt(skip, 36);
                    step = step ? parseInt(step, 36) : 0;
                    map.set(lastCode += skip, TYPES[type2]);
                    for (var i = 0; i < step; i++) {
                      map.set(++lastCode, TYPES[type2]);
                    }
                  });
                }
              };
              for (var type in DATA) loop(type);
            }
          }
          function getBidiCharType(char) {
            parseData();
            return map.get(char.codePointAt(0)) || TYPES.L;
          }
          function getBidiCharTypeName(char) {
            return TYPES_TO_NAMES[getBidiCharType(char)];
          }
          var data$1 = {
            "pairs": "14>1,1e>2,u>2,2wt>1,1>1,1ge>1,1wp>1,1j>1,f>1,hm>1,1>1,u>1,u6>1,1>1,+5,28>1,w>1,1>1,+3,b8>1,1>1,+3,1>3,-1>-1,3>1,1>1,+2,1s>1,1>1,x>1,th>1,1>1,+2,db>1,1>1,+3,3>1,1>1,+2,14qm>1,1>1,+1,4q>1,1e>2,u>2,2>1,+1",
            "canonical": "6f1>-6dx,6dy>-6dx,6ec>-6ed,6ee>-6ed,6ww>2jj,-2ji>2jj,14r4>-1e7l,1e7m>-1e7l,1e7m>-1e5c,1e5d>-1e5b,1e5c>-14qx,14qy>-14qx,14vn>-1ecg,1ech>-1ecg,1edu>-1ecg,1eci>-1ecg,1eda>-1ecg,1eci>-1ecg,1eci>-168q,168r>-168q,168s>-14ye,14yf>-14ye"
          };
          function parseCharacterMap(encodedString, includeReverse) {
            var radix = 36;
            var lastCode = 0;
            var map2 = /* @__PURE__ */ new Map();
            var reverseMap = includeReverse && /* @__PURE__ */ new Map();
            var prevPair;
            encodedString.split(",").forEach(function visit(entry) {
              if (entry.indexOf("+") !== -1) {
                for (var i = +entry; i--; ) {
                  visit(prevPair);
                }
              } else {
                prevPair = entry;
                var ref = entry.split(">");
                var a = ref[0];
                var b = ref[1];
                a = String.fromCodePoint(lastCode += parseInt(a, radix));
                b = String.fromCodePoint(lastCode += parseInt(b, radix));
                map2.set(a, b);
                includeReverse && reverseMap.set(b, a);
              }
            });
            return { map: map2, reverseMap };
          }
          var openToClose, closeToOpen, canonical;
          function parse$1() {
            if (!openToClose) {
              var ref = parseCharacterMap(data$1.pairs, true);
              var map2 = ref.map;
              var reverseMap = ref.reverseMap;
              openToClose = map2;
              closeToOpen = reverseMap;
              canonical = parseCharacterMap(data$1.canonical, false).map;
            }
          }
          function openingToClosingBracket(char) {
            parse$1();
            return openToClose.get(char) || null;
          }
          function closingToOpeningBracket(char) {
            parse$1();
            return closeToOpen.get(char) || null;
          }
          function getCanonicalBracket(char) {
            parse$1();
            return canonical.get(char) || null;
          }
          var TYPE_L = TYPES.L;
          var TYPE_R = TYPES.R;
          var TYPE_EN = TYPES.EN;
          var TYPE_ES = TYPES.ES;
          var TYPE_ET = TYPES.ET;
          var TYPE_AN = TYPES.AN;
          var TYPE_CS = TYPES.CS;
          var TYPE_B = TYPES.B;
          var TYPE_S = TYPES.S;
          var TYPE_ON = TYPES.ON;
          var TYPE_BN = TYPES.BN;
          var TYPE_NSM = TYPES.NSM;
          var TYPE_AL = TYPES.AL;
          var TYPE_LRO = TYPES.LRO;
          var TYPE_RLO = TYPES.RLO;
          var TYPE_LRE = TYPES.LRE;
          var TYPE_RLE = TYPES.RLE;
          var TYPE_PDF = TYPES.PDF;
          var TYPE_LRI = TYPES.LRI;
          var TYPE_RLI = TYPES.RLI;
          var TYPE_FSI = TYPES.FSI;
          var TYPE_PDI = TYPES.PDI;
          function getEmbeddingLevels(string, baseDirection) {
            var MAX_DEPTH = 125;
            var charTypes = new Uint32Array(string.length);
            for (var i = 0; i < string.length; i++) {
              charTypes[i] = getBidiCharType(string[i]);
            }
            var charTypeCounts = /* @__PURE__ */ new Map();
            function changeCharType(i2, type2) {
              var oldType = charTypes[i2];
              charTypes[i2] = type2;
              charTypeCounts.set(oldType, charTypeCounts.get(oldType) - 1);
              if (oldType & NEUTRAL_ISOLATE_TYPES) {
                charTypeCounts.set(NEUTRAL_ISOLATE_TYPES, charTypeCounts.get(NEUTRAL_ISOLATE_TYPES) - 1);
              }
              charTypeCounts.set(type2, (charTypeCounts.get(type2) || 0) + 1);
              if (type2 & NEUTRAL_ISOLATE_TYPES) {
                charTypeCounts.set(NEUTRAL_ISOLATE_TYPES, (charTypeCounts.get(NEUTRAL_ISOLATE_TYPES) || 0) + 1);
              }
            }
            var embedLevels = new Uint8Array(string.length);
            var isolationPairs = /* @__PURE__ */ new Map();
            var paragraphs = [];
            var paragraph = null;
            for (var i$1 = 0; i$1 < string.length; i$1++) {
              if (!paragraph) {
                paragraphs.push(paragraph = {
                  start: i$1,
                  end: string.length - 1,
                  // 3.3.1 P2-P3: Determine the paragraph level
                  level: baseDirection === "rtl" ? 1 : baseDirection === "ltr" ? 0 : determineAutoEmbedLevel(i$1, false)
                });
              }
              if (charTypes[i$1] & TYPE_B) {
                paragraph.end = i$1;
                paragraph = null;
              }
            }
            var FORMATTING_TYPES = TYPE_RLE | TYPE_LRE | TYPE_RLO | TYPE_LRO | ISOLATE_INIT_TYPES | TYPE_PDI | TYPE_PDF | TYPE_B;
            var nextEven = function(n) {
              return n + (n & 1 ? 1 : 2);
            };
            var nextOdd = function(n) {
              return n + (n & 1 ? 2 : 1);
            };
            for (var paraIdx = 0; paraIdx < paragraphs.length; paraIdx++) {
              paragraph = paragraphs[paraIdx];
              var statusStack = [{
                _level: paragraph.level,
                _override: 0,
                //0=neutral, 1=L, 2=R
                _isolate: 0
                //bool
              }];
              var stackTop = void 0;
              var overflowIsolateCount = 0;
              var overflowEmbeddingCount = 0;
              var validIsolateCount = 0;
              charTypeCounts.clear();
              for (var i$2 = paragraph.start; i$2 <= paragraph.end; i$2++) {
                var charType = charTypes[i$2];
                stackTop = statusStack[statusStack.length - 1];
                charTypeCounts.set(charType, (charTypeCounts.get(charType) || 0) + 1);
                if (charType & NEUTRAL_ISOLATE_TYPES) {
                  charTypeCounts.set(NEUTRAL_ISOLATE_TYPES, (charTypeCounts.get(NEUTRAL_ISOLATE_TYPES) || 0) + 1);
                }
                if (charType & FORMATTING_TYPES) {
                  if (charType & (TYPE_RLE | TYPE_LRE)) {
                    embedLevels[i$2] = stackTop._level;
                    var level = (charType === TYPE_RLE ? nextOdd : nextEven)(stackTop._level);
                    if (level <= MAX_DEPTH && !overflowIsolateCount && !overflowEmbeddingCount) {
                      statusStack.push({
                        _level: level,
                        _override: 0,
                        _isolate: 0
                      });
                    } else if (!overflowIsolateCount) {
                      overflowEmbeddingCount++;
                    }
                  } else if (charType & (TYPE_RLO | TYPE_LRO)) {
                    embedLevels[i$2] = stackTop._level;
                    var level$1 = (charType === TYPE_RLO ? nextOdd : nextEven)(stackTop._level);
                    if (level$1 <= MAX_DEPTH && !overflowIsolateCount && !overflowEmbeddingCount) {
                      statusStack.push({
                        _level: level$1,
                        _override: charType & TYPE_RLO ? TYPE_R : TYPE_L,
                        _isolate: 0
                      });
                    } else if (!overflowIsolateCount) {
                      overflowEmbeddingCount++;
                    }
                  } else if (charType & ISOLATE_INIT_TYPES) {
                    if (charType & TYPE_FSI) {
                      charType = determineAutoEmbedLevel(i$2 + 1, true) === 1 ? TYPE_RLI : TYPE_LRI;
                    }
                    embedLevels[i$2] = stackTop._level;
                    if (stackTop._override) {
                      changeCharType(i$2, stackTop._override);
                    }
                    var level$2 = (charType === TYPE_RLI ? nextOdd : nextEven)(stackTop._level);
                    if (level$2 <= MAX_DEPTH && overflowIsolateCount === 0 && overflowEmbeddingCount === 0) {
                      validIsolateCount++;
                      statusStack.push({
                        _level: level$2,
                        _override: 0,
                        _isolate: 1,
                        _isolInitIndex: i$2
                      });
                    } else {
                      overflowIsolateCount++;
                    }
                  } else if (charType & TYPE_PDI) {
                    if (overflowIsolateCount > 0) {
                      overflowIsolateCount--;
                    } else if (validIsolateCount > 0) {
                      overflowEmbeddingCount = 0;
                      while (!statusStack[statusStack.length - 1]._isolate) {
                        statusStack.pop();
                      }
                      var isolInitIndex = statusStack[statusStack.length - 1]._isolInitIndex;
                      if (isolInitIndex != null) {
                        isolationPairs.set(isolInitIndex, i$2);
                        isolationPairs.set(i$2, isolInitIndex);
                      }
                      statusStack.pop();
                      validIsolateCount--;
                    }
                    stackTop = statusStack[statusStack.length - 1];
                    embedLevels[i$2] = stackTop._level;
                    if (stackTop._override) {
                      changeCharType(i$2, stackTop._override);
                    }
                  } else if (charType & TYPE_PDF) {
                    if (overflowIsolateCount === 0) {
                      if (overflowEmbeddingCount > 0) {
                        overflowEmbeddingCount--;
                      } else if (!stackTop._isolate && statusStack.length > 1) {
                        statusStack.pop();
                        stackTop = statusStack[statusStack.length - 1];
                      }
                    }
                    embedLevels[i$2] = stackTop._level;
                  } else if (charType & TYPE_B) {
                    embedLevels[i$2] = paragraph.level;
                  }
                } else {
                  embedLevels[i$2] = stackTop._level;
                  if (stackTop._override && charType !== TYPE_BN) {
                    changeCharType(i$2, stackTop._override);
                  }
                }
              }
              var levelRuns = [];
              var currentRun = null;
              for (var i$3 = paragraph.start; i$3 <= paragraph.end; i$3++) {
                var charType$1 = charTypes[i$3];
                if (!(charType$1 & BN_LIKE_TYPES)) {
                  var lvl = embedLevels[i$3];
                  var isIsolInit = charType$1 & ISOLATE_INIT_TYPES;
                  var isPDI = charType$1 === TYPE_PDI;
                  if (currentRun && lvl === currentRun._level) {
                    currentRun._end = i$3;
                    currentRun._endsWithIsolInit = isIsolInit;
                  } else {
                    levelRuns.push(currentRun = {
                      _start: i$3,
                      _end: i$3,
                      _level: lvl,
                      _startsWithPDI: isPDI,
                      _endsWithIsolInit: isIsolInit
                    });
                  }
                }
              }
              var isolatingRunSeqs = [];
              for (var runIdx = 0; runIdx < levelRuns.length; runIdx++) {
                var run = levelRuns[runIdx];
                if (!run._startsWithPDI || run._startsWithPDI && !isolationPairs.has(run._start)) {
                  var seqRuns = [currentRun = run];
                  for (var pdiIndex = void 0; currentRun && currentRun._endsWithIsolInit && (pdiIndex = isolationPairs.get(currentRun._end)) != null; ) {
                    for (var i$4 = runIdx + 1; i$4 < levelRuns.length; i$4++) {
                      if (levelRuns[i$4]._start === pdiIndex) {
                        seqRuns.push(currentRun = levelRuns[i$4]);
                        break;
                      }
                    }
                  }
                  var seqIndices = [];
                  for (var i$5 = 0; i$5 < seqRuns.length; i$5++) {
                    var run$1 = seqRuns[i$5];
                    for (var j = run$1._start; j <= run$1._end; j++) {
                      seqIndices.push(j);
                    }
                  }
                  var firstLevel = embedLevels[seqIndices[0]];
                  var prevLevel = paragraph.level;
                  for (var i$6 = seqIndices[0] - 1; i$6 >= 0; i$6--) {
                    if (!(charTypes[i$6] & BN_LIKE_TYPES)) {
                      prevLevel = embedLevels[i$6];
                      break;
                    }
                  }
                  var lastIndex = seqIndices[seqIndices.length - 1];
                  var lastLevel = embedLevels[lastIndex];
                  var nextLevel = paragraph.level;
                  if (!(charTypes[lastIndex] & ISOLATE_INIT_TYPES)) {
                    for (var i$7 = lastIndex + 1; i$7 <= paragraph.end; i$7++) {
                      if (!(charTypes[i$7] & BN_LIKE_TYPES)) {
                        nextLevel = embedLevels[i$7];
                        break;
                      }
                    }
                  }
                  isolatingRunSeqs.push({
                    _seqIndices: seqIndices,
                    _sosType: Math.max(prevLevel, firstLevel) % 2 ? TYPE_R : TYPE_L,
                    _eosType: Math.max(nextLevel, lastLevel) % 2 ? TYPE_R : TYPE_L
                  });
                }
              }
              for (var seqIdx = 0; seqIdx < isolatingRunSeqs.length; seqIdx++) {
                var ref = isolatingRunSeqs[seqIdx];
                var seqIndices$1 = ref._seqIndices;
                var sosType = ref._sosType;
                var eosType = ref._eosType;
                var embedDirection = embedLevels[seqIndices$1[0]] & 1 ? TYPE_R : TYPE_L;
                if (charTypeCounts.get(TYPE_NSM)) {
                  for (var si = 0; si < seqIndices$1.length; si++) {
                    var i$8 = seqIndices$1[si];
                    if (charTypes[i$8] & TYPE_NSM) {
                      var prevType = sosType;
                      for (var sj = si - 1; sj >= 0; sj--) {
                        if (!(charTypes[seqIndices$1[sj]] & BN_LIKE_TYPES)) {
                          prevType = charTypes[seqIndices$1[sj]];
                          break;
                        }
                      }
                      changeCharType(i$8, prevType & (ISOLATE_INIT_TYPES | TYPE_PDI) ? TYPE_ON : prevType);
                    }
                  }
                }
                if (charTypeCounts.get(TYPE_EN)) {
                  for (var si$1 = 0; si$1 < seqIndices$1.length; si$1++) {
                    var i$9 = seqIndices$1[si$1];
                    if (charTypes[i$9] & TYPE_EN) {
                      for (var sj$1 = si$1 - 1; sj$1 >= -1; sj$1--) {
                        var prevCharType = sj$1 === -1 ? sosType : charTypes[seqIndices$1[sj$1]];
                        if (prevCharType & STRONG_TYPES) {
                          if (prevCharType === TYPE_AL) {
                            changeCharType(i$9, TYPE_AN);
                          }
                          break;
                        }
                      }
                    }
                  }
                }
                if (charTypeCounts.get(TYPE_AL)) {
                  for (var si$2 = 0; si$2 < seqIndices$1.length; si$2++) {
                    var i$10 = seqIndices$1[si$2];
                    if (charTypes[i$10] & TYPE_AL) {
                      changeCharType(i$10, TYPE_R);
                    }
                  }
                }
                if (charTypeCounts.get(TYPE_ES) || charTypeCounts.get(TYPE_CS)) {
                  for (var si$3 = 1; si$3 < seqIndices$1.length - 1; si$3++) {
                    var i$11 = seqIndices$1[si$3];
                    if (charTypes[i$11] & (TYPE_ES | TYPE_CS)) {
                      var prevType$1 = 0, nextType = 0;
                      for (var sj$2 = si$3 - 1; sj$2 >= 0; sj$2--) {
                        prevType$1 = charTypes[seqIndices$1[sj$2]];
                        if (!(prevType$1 & BN_LIKE_TYPES)) {
                          break;
                        }
                      }
                      for (var sj$3 = si$3 + 1; sj$3 < seqIndices$1.length; sj$3++) {
                        nextType = charTypes[seqIndices$1[sj$3]];
                        if (!(nextType & BN_LIKE_TYPES)) {
                          break;
                        }
                      }
                      if (prevType$1 === nextType && (charTypes[i$11] === TYPE_ES ? prevType$1 === TYPE_EN : prevType$1 & (TYPE_EN | TYPE_AN))) {
                        changeCharType(i$11, prevType$1);
                      }
                    }
                  }
                }
                if (charTypeCounts.get(TYPE_EN)) {
                  for (var si$4 = 0; si$4 < seqIndices$1.length; si$4++) {
                    var i$12 = seqIndices$1[si$4];
                    if (charTypes[i$12] & TYPE_EN) {
                      for (var sj$4 = si$4 - 1; sj$4 >= 0 && charTypes[seqIndices$1[sj$4]] & (TYPE_ET | BN_LIKE_TYPES); sj$4--) {
                        changeCharType(seqIndices$1[sj$4], TYPE_EN);
                      }
                      for (si$4++; si$4 < seqIndices$1.length && charTypes[seqIndices$1[si$4]] & (TYPE_ET | BN_LIKE_TYPES | TYPE_EN); si$4++) {
                        if (charTypes[seqIndices$1[si$4]] !== TYPE_EN) {
                          changeCharType(seqIndices$1[si$4], TYPE_EN);
                        }
                      }
                    }
                  }
                }
                if (charTypeCounts.get(TYPE_ET) || charTypeCounts.get(TYPE_ES) || charTypeCounts.get(TYPE_CS)) {
                  for (var si$5 = 0; si$5 < seqIndices$1.length; si$5++) {
                    var i$13 = seqIndices$1[si$5];
                    if (charTypes[i$13] & (TYPE_ET | TYPE_ES | TYPE_CS)) {
                      changeCharType(i$13, TYPE_ON);
                      for (var sj$5 = si$5 - 1; sj$5 >= 0 && charTypes[seqIndices$1[sj$5]] & BN_LIKE_TYPES; sj$5--) {
                        changeCharType(seqIndices$1[sj$5], TYPE_ON);
                      }
                      for (var sj$6 = si$5 + 1; sj$6 < seqIndices$1.length && charTypes[seqIndices$1[sj$6]] & BN_LIKE_TYPES; sj$6++) {
                        changeCharType(seqIndices$1[sj$6], TYPE_ON);
                      }
                    }
                  }
                }
                if (charTypeCounts.get(TYPE_EN)) {
                  for (var si$6 = 0, prevStrongType = sosType; si$6 < seqIndices$1.length; si$6++) {
                    var i$14 = seqIndices$1[si$6];
                    var type = charTypes[i$14];
                    if (type & TYPE_EN) {
                      if (prevStrongType === TYPE_L) {
                        changeCharType(i$14, TYPE_L);
                      }
                    } else if (type & STRONG_TYPES) {
                      prevStrongType = type;
                    }
                  }
                }
                if (charTypeCounts.get(NEUTRAL_ISOLATE_TYPES)) {
                  var R_TYPES_FOR_N_STEPS = TYPE_R | TYPE_EN | TYPE_AN;
                  var STRONG_TYPES_FOR_N_STEPS = R_TYPES_FOR_N_STEPS | TYPE_L;
                  var bracketPairs = [];
                  {
                    var openerStack = [];
                    for (var si$7 = 0; si$7 < seqIndices$1.length; si$7++) {
                      if (charTypes[seqIndices$1[si$7]] & NEUTRAL_ISOLATE_TYPES) {
                        var char = string[seqIndices$1[si$7]];
                        var oppositeBracket = void 0;
                        if (openingToClosingBracket(char) !== null) {
                          if (openerStack.length < 63) {
                            openerStack.push({ char, seqIndex: si$7 });
                          } else {
                            break;
                          }
                        } else if ((oppositeBracket = closingToOpeningBracket(char)) !== null) {
                          for (var stackIdx = openerStack.length - 1; stackIdx >= 0; stackIdx--) {
                            var stackChar = openerStack[stackIdx].char;
                            if (stackChar === oppositeBracket || stackChar === closingToOpeningBracket(getCanonicalBracket(char)) || openingToClosingBracket(getCanonicalBracket(stackChar)) === char) {
                              bracketPairs.push([openerStack[stackIdx].seqIndex, si$7]);
                              openerStack.length = stackIdx;
                              break;
                            }
                          }
                        }
                      }
                    }
                    bracketPairs.sort(function(a, b) {
                      return a[0] - b[0];
                    });
                  }
                  for (var pairIdx = 0; pairIdx < bracketPairs.length; pairIdx++) {
                    var ref$1 = bracketPairs[pairIdx];
                    var openSeqIdx = ref$1[0];
                    var closeSeqIdx = ref$1[1];
                    var foundStrongType = false;
                    var useStrongType = 0;
                    for (var si$8 = openSeqIdx + 1; si$8 < closeSeqIdx; si$8++) {
                      var i$15 = seqIndices$1[si$8];
                      if (charTypes[i$15] & STRONG_TYPES_FOR_N_STEPS) {
                        foundStrongType = true;
                        var lr = charTypes[i$15] & R_TYPES_FOR_N_STEPS ? TYPE_R : TYPE_L;
                        if (lr === embedDirection) {
                          useStrongType = lr;
                          break;
                        }
                      }
                    }
                    if (foundStrongType && !useStrongType) {
                      useStrongType = sosType;
                      for (var si$9 = openSeqIdx - 1; si$9 >= 0; si$9--) {
                        var i$16 = seqIndices$1[si$9];
                        if (charTypes[i$16] & STRONG_TYPES_FOR_N_STEPS) {
                          var lr$1 = charTypes[i$16] & R_TYPES_FOR_N_STEPS ? TYPE_R : TYPE_L;
                          if (lr$1 !== embedDirection) {
                            useStrongType = lr$1;
                          } else {
                            useStrongType = embedDirection;
                          }
                          break;
                        }
                      }
                    }
                    if (useStrongType) {
                      charTypes[seqIndices$1[openSeqIdx]] = charTypes[seqIndices$1[closeSeqIdx]] = useStrongType;
                      if (useStrongType !== embedDirection) {
                        for (var si$10 = openSeqIdx + 1; si$10 < seqIndices$1.length; si$10++) {
                          if (!(charTypes[seqIndices$1[si$10]] & BN_LIKE_TYPES)) {
                            if (getBidiCharType(string[seqIndices$1[si$10]]) & TYPE_NSM) {
                              charTypes[seqIndices$1[si$10]] = useStrongType;
                            }
                            break;
                          }
                        }
                      }
                      if (useStrongType !== embedDirection) {
                        for (var si$11 = closeSeqIdx + 1; si$11 < seqIndices$1.length; si$11++) {
                          if (!(charTypes[seqIndices$1[si$11]] & BN_LIKE_TYPES)) {
                            if (getBidiCharType(string[seqIndices$1[si$11]]) & TYPE_NSM) {
                              charTypes[seqIndices$1[si$11]] = useStrongType;
                            }
                            break;
                          }
                        }
                      }
                    }
                  }
                  for (var si$12 = 0; si$12 < seqIndices$1.length; si$12++) {
                    if (charTypes[seqIndices$1[si$12]] & NEUTRAL_ISOLATE_TYPES) {
                      var niRunStart = si$12, niRunEnd = si$12;
                      var prevType$2 = sosType;
                      for (var si2 = si$12 - 1; si2 >= 0; si2--) {
                        if (charTypes[seqIndices$1[si2]] & BN_LIKE_TYPES) {
                          niRunStart = si2;
                        } else {
                          prevType$2 = charTypes[seqIndices$1[si2]] & R_TYPES_FOR_N_STEPS ? TYPE_R : TYPE_L;
                          break;
                        }
                      }
                      var nextType$1 = eosType;
                      for (var si2$1 = si$12 + 1; si2$1 < seqIndices$1.length; si2$1++) {
                        if (charTypes[seqIndices$1[si2$1]] & (NEUTRAL_ISOLATE_TYPES | BN_LIKE_TYPES)) {
                          niRunEnd = si2$1;
                        } else {
                          nextType$1 = charTypes[seqIndices$1[si2$1]] & R_TYPES_FOR_N_STEPS ? TYPE_R : TYPE_L;
                          break;
                        }
                      }
                      for (var sj$7 = niRunStart; sj$7 <= niRunEnd; sj$7++) {
                        charTypes[seqIndices$1[sj$7]] = prevType$2 === nextType$1 ? prevType$2 : embedDirection;
                      }
                      si$12 = niRunEnd;
                    }
                  }
                }
              }
              for (var i$17 = paragraph.start; i$17 <= paragraph.end; i$17++) {
                var level$3 = embedLevels[i$17];
                var type$1 = charTypes[i$17];
                if (level$3 & 1) {
                  if (type$1 & (TYPE_L | TYPE_EN | TYPE_AN)) {
                    embedLevels[i$17]++;
                  }
                } else {
                  if (type$1 & TYPE_R) {
                    embedLevels[i$17]++;
                  } else if (type$1 & (TYPE_AN | TYPE_EN)) {
                    embedLevels[i$17] += 2;
                  }
                }
                if (type$1 & BN_LIKE_TYPES) {
                  embedLevels[i$17] = i$17 === 0 ? paragraph.level : embedLevels[i$17 - 1];
                }
                if (i$17 === paragraph.end || getBidiCharType(string[i$17]) & (TYPE_S | TYPE_B)) {
                  for (var j$1 = i$17; j$1 >= 0 && getBidiCharType(string[j$1]) & TRAILING_TYPES; j$1--) {
                    embedLevels[j$1] = paragraph.level;
                  }
                }
              }
            }
            return {
              levels: embedLevels,
              paragraphs
            };
            function determineAutoEmbedLevel(start, isFSI) {
              for (var i2 = start; i2 < string.length; i2++) {
                var charType2 = charTypes[i2];
                if (charType2 & (TYPE_R | TYPE_AL)) {
                  return 1;
                }
                if (charType2 & (TYPE_B | TYPE_L) || isFSI && charType2 === TYPE_PDI) {
                  return 0;
                }
                if (charType2 & ISOLATE_INIT_TYPES) {
                  var pdi = indexOfMatchingPDI(i2);
                  i2 = pdi === -1 ? string.length : pdi;
                }
              }
              return 0;
            }
            function indexOfMatchingPDI(isolateStart) {
              var isolationLevel = 1;
              for (var i2 = isolateStart + 1; i2 < string.length; i2++) {
                var charType2 = charTypes[i2];
                if (charType2 & TYPE_B) {
                  break;
                }
                if (charType2 & TYPE_PDI) {
                  if (--isolationLevel === 0) {
                    return i2;
                  }
                } else if (charType2 & ISOLATE_INIT_TYPES) {
                  isolationLevel++;
                }
              }
              return -1;
            }
          }
          var data = "14>1,j>2,t>2,u>2,1a>g,2v3>1,1>1,1ge>1,1wd>1,b>1,1j>1,f>1,ai>3,-2>3,+1,8>1k0,-1jq>1y7,-1y6>1hf,-1he>1h6,-1h5>1ha,-1h8>1qi,-1pu>1,6>3u,-3s>7,6>1,1>1,f>1,1>1,+2,3>1,1>1,+13,4>1,1>1,6>1eo,-1ee>1,3>1mg,-1me>1mk,-1mj>1mi,-1mg>1mi,-1md>1,1>1,+2,1>10k,-103>1,1>1,4>1,5>1,1>1,+10,3>1,1>8,-7>8,+1,-6>7,+1,a>1,1>1,u>1,u6>1,1>1,+5,26>1,1>1,2>1,2>2,8>1,7>1,4>1,1>1,+5,b8>1,1>1,+3,1>3,-2>1,2>1,1>1,+2,c>1,3>1,1>1,+2,h>1,3>1,a>1,1>1,2>1,3>1,1>1,d>1,f>1,3>1,1a>1,1>1,6>1,7>1,13>1,k>1,1>1,+19,4>1,1>1,+2,2>1,1>1,+18,m>1,a>1,1>1,lk>1,1>1,4>1,2>1,f>1,3>1,1>1,+3,db>1,1>1,+3,3>1,1>1,+2,14qm>1,1>1,+1,6>1,4j>1,j>2,t>2,u>2,2>1,+1";
          var mirrorMap;
          function parse52() {
            if (!mirrorMap) {
              var ref = parseCharacterMap(data, true);
              var map2 = ref.map;
              var reverseMap = ref.reverseMap;
              reverseMap.forEach(function(value, key) {
                map2.set(key, value);
              });
              mirrorMap = map2;
            }
          }
          function getMirroredCharacter(char) {
            parse52();
            return mirrorMap.get(char) || null;
          }
          function getMirroredCharactersMap(string, embeddingLevels, start, end) {
            var strLen = string.length;
            start = Math.max(0, start == null ? 0 : +start);
            end = Math.min(strLen - 1, end == null ? strLen - 1 : +end);
            var map2 = /* @__PURE__ */ new Map();
            for (var i = start; i <= end; i++) {
              if (embeddingLevels[i] & 1) {
                var mirror = getMirroredCharacter(string[i]);
                if (mirror !== null) {
                  map2.set(i, mirror);
                }
              }
            }
            return map2;
          }
          function getReorderSegments(string, embeddingLevelsResult, start, end) {
            var strLen = string.length;
            start = Math.max(0, start == null ? 0 : +start);
            end = Math.min(strLen - 1, end == null ? strLen - 1 : +end);
            var segments = [];
            embeddingLevelsResult.paragraphs.forEach(function(paragraph) {
              var lineStart = Math.max(start, paragraph.start);
              var lineEnd = Math.min(end, paragraph.end);
              if (lineStart < lineEnd) {
                var lineLevels = embeddingLevelsResult.levels.slice(lineStart, lineEnd + 1);
                for (var i = lineEnd; i >= lineStart && getBidiCharType(string[i]) & TRAILING_TYPES; i--) {
                  lineLevels[i] = paragraph.level;
                }
                var maxLevel = paragraph.level;
                var minOddLevel = Infinity;
                for (var i$1 = 0; i$1 < lineLevels.length; i$1++) {
                  var level = lineLevels[i$1];
                  if (level > maxLevel) {
                    maxLevel = level;
                  }
                  if (level < minOddLevel) {
                    minOddLevel = level | 1;
                  }
                }
                for (var lvl = maxLevel; lvl >= minOddLevel; lvl--) {
                  for (var i$2 = 0; i$2 < lineLevels.length; i$2++) {
                    if (lineLevels[i$2] >= lvl) {
                      var segStart = i$2;
                      while (i$2 + 1 < lineLevels.length && lineLevels[i$2 + 1] >= lvl) {
                        i$2++;
                      }
                      if (i$2 > segStart) {
                        segments.push([segStart + lineStart, i$2 + lineStart]);
                      }
                    }
                  }
                }
              }
            });
            return segments;
          }
          function getReorderedString(string, embedLevelsResult, start, end) {
            var indices = getReorderedIndices(string, embedLevelsResult, start, end);
            var chars = [].concat(string);
            indices.forEach(function(charIndex, i) {
              chars[i] = (embedLevelsResult.levels[charIndex] & 1 ? getMirroredCharacter(string[charIndex]) : null) || string[charIndex];
            });
            return chars.join("");
          }
          function getReorderedIndices(string, embedLevelsResult, start, end) {
            var segments = getReorderSegments(string, embedLevelsResult, start, end);
            var indices = [];
            for (var i = 0; i < string.length; i++) {
              indices[i] = i;
            }
            segments.forEach(function(ref) {
              var start2 = ref[0];
              var end2 = ref[1];
              var slice = indices.slice(start2, end2 + 1);
              for (var i2 = slice.length; i2--; ) {
                indices[end2 - i2] = slice[i2];
              }
            });
            return indices;
          }
          exports3.closingToOpeningBracket = closingToOpeningBracket;
          exports3.getBidiCharType = getBidiCharType;
          exports3.getBidiCharTypeName = getBidiCharTypeName;
          exports3.getCanonicalBracket = getCanonicalBracket;
          exports3.getEmbeddingLevels = getEmbeddingLevels;
          exports3.getMirroredCharacter = getMirroredCharacter;
          exports3.getMirroredCharactersMap = getMirroredCharactersMap;
          exports3.getReorderSegments = getReorderSegments;
          exports3.getReorderedIndices = getReorderedIndices;
          exports3.getReorderedString = getReorderedString;
          exports3.openingToClosingBracket = openingToClosingBracket;
          Object.defineProperty(exports3, "__esModule", { value: true });
          return exports3;
        })({});
        return bidi;
      }
      return bidiFactory2;
    }));
  }
});

// node_modules/is-potential-custom-element-name/index.js
var require_is_potential_custom_element_name = __commonJS({
  "node_modules/is-potential-custom-element-name/index.js"(exports2, module2) {
    var regex = /^[a-z](?:[\.0-9_a-z\xB7\xC0-\xD6\xD8-\xF6\xF8-\u037D\u037F-\u1FFF\u200C\u200D\u203F\u2040\u2070-\u218F\u2C00-\u2FEF\u3001-\uD7FF\uF900-\uFDCF\uFDF0-\uFFFD]|[\uD800-\uDB7F][\uDC00-\uDFFF])*-(?:[\x2D\.0-9_a-z\xB7\xC0-\xD6\xD8-\xF6\xF8-\u037D\u037F-\u1FFF\u200C\u200D\u203F\u2040\u2070-\u218F\u2C00-\u2FEF\u3001-\uD7FF\uF900-\uFDCF\uFDF0-\uFFFD]|[\uD800-\uDB7F][\uDC00-\uDFFF])*$/;
    var isPotentialCustomElementName = function(string) {
      return regex.test(string);
    };
    module2.exports = isPotentialCustomElementName;
  }
});

// node_modules/@asamuzakjp/dom-selector/src/index.js
var index_exports = {};
__export(index_exports, {
  DOMSelector: () => DOMSelector
});
module.exports = __toCommonJS(index_exports);

// node_modules/@asamuzakjp/generational-cache/src/index.js
var GenerationalCache = class {
  #max;
  #boundary;
  #current = /* @__PURE__ */ new Map();
  #old = /* @__PURE__ */ new Map();
  /**
   * Initializes a new instance of the GenerationalCache class.
   * @param {number} max - The maximum number of items the cache can hold.
   */
  constructor(max) {
    this.max = max;
  }
  /**
   * Returns the total number of `entries` currently in the cache.
   * @note To optimize for write speed, this library allows temporary key
   * duplication between generations. Therefore, this value may not always
   * reflect the exact count of unique `keys`.
   * @returns {number} The total entry count.
   */
  get size() {
    return this.#current.size + this.#old.size;
  }
  /**
   * Returns the maximum capacity of the cache.
   * @returns {number} The maximum size limit.
   */
  get max() {
    return this.#max;
  }
  /**
   * Sets the maximum capacity of the cache and recalculates the boundary.
   * Clears the cache when updated.
   * @param {number} value - The new maximum capacity to set.
   */
  set max(value) {
    if (Number.isFinite(value) && value > 4) {
      this.#max = value;
      this.#boundary = Math.ceil(value / 2);
    } else {
      this.#max = 4;
      this.#boundary = 2;
    }
    this.clear();
  }
  /**
   * Retrieves an item from the cache.
   * If the item is in the older generation, it gets promoted to the current
   * generation.
   * @param {K} key - The key of the element to return.
   * @returns {V | undefined} The element associated with the specified key, or
   * undefined if the key cannot be found.
   */
  get(key) {
    let value = this.#current.get(key);
    if (value !== void 0) {
      return value;
    }
    value = this.#old.get(key);
    if (value !== void 0) {
      this.set(key, value);
      return value;
    }
    return void 0;
  }
  /**
   * Adds or updates an element with a specified key and a value to the cache.
   * @param {K} key - The key of the element to add.
   * @param {V} value - The value of the element to add.
   * @returns {GenerationalCache} The cache object itself.
   */
  set(key, value) {
    this.#current.set(key, value);
    if (this.#current.size >= this.#boundary) {
      this.#old = this.#current;
      this.#current = /* @__PURE__ */ new Map();
    }
    return this;
  }
  /**
   * Returns a boolean indicating whether an element with the specified key
   * exists or not.
   * @param {K} key - The key of the element to test for presence.
   * @returns {boolean} true if an element with the specified key exists in the
   * cache; otherwise false.
   */
  has(key) {
    return this.#current.has(key) || this.#old.has(key);
  }
  /**
   * Removes the specified element from the cache.
   * @param {K} key - The key of the element to remove.
   * @returns {boolean} true if an element in the cache existed and has been
   * removed, or false if the element does not exist.
   */
  delete(key) {
    const deletedFromCurrent = this.#current.delete(key);
    const deletedFromOld = this.#old.delete(key);
    return deletedFromCurrent || deletedFromOld;
  }
  /**
   * Removes all elements from the cache.
   */
  clear() {
    this.#current.clear();
    this.#old.clear();
  }
};

// node_modules/css-tree/lib/tokenizer/types.js
var EOF = 0;
var Ident = 1;
var Function2 = 2;
var AtKeyword = 3;
var Hash = 4;
var String2 = 5;
var BadString = 6;
var Url = 7;
var BadUrl = 8;
var Delim = 9;
var Number2 = 10;
var Percentage = 11;
var Dimension = 12;
var WhiteSpace = 13;
var CDO = 14;
var CDC = 15;
var Colon = 16;
var Semicolon = 17;
var Comma = 18;
var LeftSquareBracket = 19;
var RightSquareBracket = 20;
var LeftParenthesis = 21;
var RightParenthesis = 22;
var LeftCurlyBracket = 23;
var RightCurlyBracket = 24;
var Comment = 25;

// node_modules/css-tree/lib/tokenizer/char-code-definitions.js
var EOF2 = 0;
function isDigit(code2) {
  return code2 >= 48 && code2 <= 57;
}
function isHexDigit(code2) {
  return isDigit(code2) || // 0 .. 9
  code2 >= 65 && code2 <= 70 || // A .. F
  code2 >= 97 && code2 <= 102;
}
function isUppercaseLetter(code2) {
  return code2 >= 65 && code2 <= 90;
}
function isLowercaseLetter(code2) {
  return code2 >= 97 && code2 <= 122;
}
function isLetter(code2) {
  return isUppercaseLetter(code2) || isLowercaseLetter(code2);
}
function isNonAscii(code2) {
  return code2 >= 128;
}
function isNameStart(code2) {
  return isLetter(code2) || isNonAscii(code2) || code2 === 95;
}
function isName(code2) {
  return isNameStart(code2) || isDigit(code2) || code2 === 45;
}
function isNonPrintable(code2) {
  return code2 >= 0 && code2 <= 8 || code2 === 11 || code2 >= 14 && code2 <= 31 || code2 === 127;
}
function isNewline(code2) {
  return code2 === 10 || code2 === 13 || code2 === 12;
}
function isWhiteSpace(code2) {
  return isNewline(code2) || code2 === 32 || code2 === 9;
}
function isValidEscape(first, second) {
  if (first !== 92) {
    return false;
  }
  if (isNewline(second) || second === EOF2) {
    return false;
  }
  return true;
}
function isIdentifierStart(first, second, third) {
  if (first === 45) {
    return isNameStart(second) || second === 45 || isValidEscape(second, third);
  }
  if (isNameStart(first)) {
    return true;
  }
  if (first === 92) {
    return isValidEscape(first, second);
  }
  return false;
}
function isNumberStart(first, second, third) {
  if (first === 43 || first === 45) {
    if (isDigit(second)) {
      return 2;
    }
    return second === 46 && isDigit(third) ? 3 : 0;
  }
  if (first === 46) {
    return isDigit(second) ? 2 : 0;
  }
  if (isDigit(first)) {
    return 1;
  }
  return 0;
}
function isBOM(code2) {
  if (code2 === 65279) {
    return 1;
  }
  if (code2 === 65534) {
    return 1;
  }
  return 0;
}
var CATEGORY = new Array(128);
var EofCategory = 128;
var WhiteSpaceCategory = 130;
var DigitCategory = 131;
var NameStartCategory = 132;
var NonPrintableCategory = 133;
for (let i = 0; i < CATEGORY.length; i++) {
  CATEGORY[i] = isWhiteSpace(i) && WhiteSpaceCategory || isDigit(i) && DigitCategory || isNameStart(i) && NameStartCategory || isNonPrintable(i) && NonPrintableCategory || i || EofCategory;
}
function charCodeCategory(code2) {
  return code2 < 128 ? CATEGORY[code2] : NameStartCategory;
}

// node_modules/css-tree/lib/tokenizer/utils.js
function getCharCode(source, offset) {
  return offset < source.length ? source.charCodeAt(offset) : 0;
}
function getNewlineLength(source, offset, code2) {
  if (code2 === 13 && getCharCode(source, offset + 1) === 10) {
    return 2;
  }
  return 1;
}
function cmpChar(testStr, offset, referenceCode) {
  let code2 = testStr.charCodeAt(offset);
  if (isUppercaseLetter(code2)) {
    code2 = code2 | 32;
  }
  return code2 === referenceCode;
}
function cmpStr(testStr, start, end, referenceStr) {
  if (end - start !== referenceStr.length) {
    return false;
  }
  if (start < 0 || end > testStr.length) {
    return false;
  }
  for (let i = start; i < end; i++) {
    const referenceCode = referenceStr.charCodeAt(i - start);
    let testCode = testStr.charCodeAt(i);
    if (isUppercaseLetter(testCode)) {
      testCode = testCode | 32;
    }
    if (testCode !== referenceCode) {
      return false;
    }
  }
  return true;
}
function findWhiteSpaceStart(source, offset) {
  for (; offset >= 0; offset--) {
    if (!isWhiteSpace(source.charCodeAt(offset))) {
      break;
    }
  }
  return offset + 1;
}
function findWhiteSpaceEnd(source, offset) {
  for (; offset < source.length; offset++) {
    if (!isWhiteSpace(source.charCodeAt(offset))) {
      break;
    }
  }
  return offset;
}
function findDecimalNumberEnd(source, offset) {
  for (; offset < source.length; offset++) {
    if (!isDigit(source.charCodeAt(offset))) {
      break;
    }
  }
  return offset;
}
function consumeEscaped(source, offset) {
  offset += 2;
  if (isHexDigit(getCharCode(source, offset - 1))) {
    for (const maxOffset = Math.min(source.length, offset + 5); offset < maxOffset; offset++) {
      if (!isHexDigit(getCharCode(source, offset))) {
        break;
      }
    }
    const code2 = getCharCode(source, offset);
    if (isWhiteSpace(code2)) {
      offset += getNewlineLength(source, offset, code2);
    }
  }
  return offset;
}
function consumeName(source, offset) {
  for (; offset < source.length; offset++) {
    const code2 = source.charCodeAt(offset);
    if (isName(code2)) {
      continue;
    }
    if (isValidEscape(code2, getCharCode(source, offset + 1))) {
      offset = consumeEscaped(source, offset) - 1;
      continue;
    }
    break;
  }
  return offset;
}
function consumeNumber(source, offset) {
  let code2 = source.charCodeAt(offset);
  if (code2 === 43 || code2 === 45) {
    code2 = source.charCodeAt(offset += 1);
  }
  if (isDigit(code2)) {
    offset = findDecimalNumberEnd(source, offset + 1);
    code2 = source.charCodeAt(offset);
  }
  if (code2 === 46 && isDigit(source.charCodeAt(offset + 1))) {
    offset += 2;
    offset = findDecimalNumberEnd(source, offset);
  }
  if (cmpChar(
    source,
    offset,
    101
    /* e */
  )) {
    let sign = 0;
    code2 = source.charCodeAt(offset + 1);
    if (code2 === 45 || code2 === 43) {
      sign = 1;
      code2 = source.charCodeAt(offset + 2);
    }
    if (isDigit(code2)) {
      offset = findDecimalNumberEnd(source, offset + 1 + sign + 1);
    }
  }
  return offset;
}
function consumeBadUrlRemnants(source, offset) {
  for (; offset < source.length; offset++) {
    const code2 = source.charCodeAt(offset);
    if (code2 === 41) {
      offset++;
      break;
    }
    if (isValidEscape(code2, getCharCode(source, offset + 1))) {
      offset = consumeEscaped(source, offset);
    }
  }
  return offset;
}
function decodeEscaped(escaped) {
  if (escaped.length === 1 && !isHexDigit(escaped.charCodeAt(0))) {
    return escaped[0];
  }
  let code2 = parseInt(escaped, 16);
  if (code2 === 0 || // If this number is zero,
  code2 >= 55296 && code2 <= 57343 || // or is for a surrogate,
  code2 > 1114111) {
    code2 = 65533;
  }
  return String.fromCodePoint(code2);
}

// node_modules/css-tree/lib/tokenizer/names.js
var names_default = [
  "EOF-token",
  "ident-token",
  "function-token",
  "at-keyword-token",
  "hash-token",
  "string-token",
  "bad-string-token",
  "url-token",
  "bad-url-token",
  "delim-token",
  "number-token",
  "percentage-token",
  "dimension-token",
  "whitespace-token",
  "CDO-token",
  "CDC-token",
  "colon-token",
  "semicolon-token",
  "comma-token",
  "[-token",
  "]-token",
  "(-token",
  ")-token",
  "{-token",
  "}-token",
  "comment-token"
];

// node_modules/css-tree/lib/tokenizer/adopt-buffer.js
var MIN_SIZE = 16 * 1024;
function adoptBuffer(buffer = null, size) {
  if (buffer === null || buffer.length < size) {
    return new Uint32Array(Math.max(size + 1024, MIN_SIZE));
  }
  return buffer;
}

// node_modules/css-tree/lib/tokenizer/OffsetToLocation.js
var N = 10;
var F = 12;
var R = 13;
function computeLinesAndColumns(host) {
  const source = host.source;
  const sourceLength = source.length;
  const startOffset = source.length > 0 ? isBOM(source.charCodeAt(0)) : 0;
  const lines = adoptBuffer(host.lines, sourceLength);
  const columns = adoptBuffer(host.columns, sourceLength);
  let line = host.startLine;
  let column = host.startColumn;
  for (let i = startOffset; i < sourceLength; i++) {
    const code2 = source.charCodeAt(i);
    lines[i] = line;
    columns[i] = column++;
    if (code2 === N || code2 === R || code2 === F) {
      if (code2 === R && i + 1 < sourceLength && source.charCodeAt(i + 1) === N) {
        i++;
        lines[i] = line;
        columns[i] = column;
      }
      line++;
      column = 1;
    }
  }
  lines[sourceLength] = line;
  columns[sourceLength] = column;
  host.lines = lines;
  host.columns = columns;
  host.computed = true;
}
var OffsetToLocation = class {
  constructor(source, startOffset, startLine, startColumn) {
    this.setSource(source, startOffset, startLine, startColumn);
    this.lines = null;
    this.columns = null;
  }
  setSource(source = "", startOffset = 0, startLine = 1, startColumn = 1) {
    this.source = source;
    this.startOffset = startOffset;
    this.startLine = startLine;
    this.startColumn = startColumn;
    this.computed = false;
  }
  getLocation(offset, filename) {
    if (!this.computed) {
      computeLinesAndColumns(this);
    }
    return {
      source: filename,
      offset: this.startOffset + offset,
      line: this.lines[offset],
      column: this.columns[offset]
    };
  }
  getLocationRange(start, end, filename) {
    if (!this.computed) {
      computeLinesAndColumns(this);
    }
    return {
      source: filename,
      start: {
        offset: this.startOffset + start,
        line: this.lines[start],
        column: this.columns[start]
      },
      end: {
        offset: this.startOffset + end,
        line: this.lines[end],
        column: this.columns[end]
      }
    };
  }
};

// node_modules/css-tree/lib/tokenizer/TokenStream.js
var OFFSET_MASK = 16777215;
var TYPE_SHIFT = 24;
var BLOCK_OPEN_TOKEN = 1;
var BLOCK_CLOSE_TOKEN = 2;
var balancePair = new Uint8Array(32);
balancePair[Function2] = RightParenthesis;
balancePair[LeftParenthesis] = RightParenthesis;
balancePair[LeftSquareBracket] = RightSquareBracket;
balancePair[LeftCurlyBracket] = RightCurlyBracket;
var blockTokens = new Uint8Array(32);
blockTokens[Function2] = BLOCK_OPEN_TOKEN;
blockTokens[LeftParenthesis] = BLOCK_OPEN_TOKEN;
blockTokens[LeftSquareBracket] = BLOCK_OPEN_TOKEN;
blockTokens[LeftCurlyBracket] = BLOCK_OPEN_TOKEN;
blockTokens[RightParenthesis] = BLOCK_CLOSE_TOKEN;
blockTokens[RightSquareBracket] = BLOCK_CLOSE_TOKEN;
blockTokens[RightCurlyBracket] = BLOCK_CLOSE_TOKEN;
function boundIndex(index, min, max) {
  return index < min ? min : index > max ? max : index;
}
var TokenStream = class {
  constructor(source, tokenize3) {
    this.setSource(source, tokenize3);
  }
  reset() {
    this.eof = false;
    this.tokenIndex = -1;
    this.tokenType = 0;
    this.tokenStart = this.firstCharOffset;
    this.tokenEnd = this.firstCharOffset;
  }
  setSource(source = "", tokenize3 = () => {
  }) {
    source = String(source || "");
    const sourceLength = source.length;
    const offsetAndType = adoptBuffer(this.offsetAndType, source.length + 1);
    const balance = adoptBuffer(this.balance, source.length + 1);
    let tokenCount = 0;
    let firstCharOffset = -1;
    let balanceCloseType = 0;
    let balanceStart = source.length;
    this.offsetAndType = null;
    this.balance = null;
    balance.fill(0);
    tokenize3(source, (type, start, end) => {
      const index = tokenCount++;
      offsetAndType[index] = type << TYPE_SHIFT | end;
      if (firstCharOffset === -1) {
        firstCharOffset = start;
      }
      balance[index] = balanceStart;
      if (type === balanceCloseType) {
        const prevBalanceStart = balance[balanceStart];
        balance[balanceStart] = index;
        balanceStart = prevBalanceStart;
        balanceCloseType = balancePair[offsetAndType[prevBalanceStart] >> TYPE_SHIFT];
      } else if (this.isBlockOpenerTokenType(type)) {
        balanceStart = index;
        balanceCloseType = balancePair[type];
      }
    });
    offsetAndType[tokenCount] = EOF << TYPE_SHIFT | sourceLength;
    balance[tokenCount] = tokenCount;
    for (let i = 0; i < tokenCount; i++) {
      const balanceStart2 = balance[i];
      if (balanceStart2 <= i) {
        const balanceEnd = balance[balanceStart2];
        if (balanceEnd !== i) {
          balance[i] = balanceEnd;
        }
      } else if (balanceStart2 > tokenCount) {
        balance[i] = tokenCount;
      }
    }
    this.source = source;
    this.firstCharOffset = firstCharOffset === -1 ? 0 : firstCharOffset;
    this.tokenCount = tokenCount;
    this.offsetAndType = offsetAndType;
    this.balance = balance;
    this.reset();
    this.next();
  }
  lookupType(offset) {
    offset += this.tokenIndex;
    if (offset < this.tokenCount) {
      return this.offsetAndType[offset] >> TYPE_SHIFT;
    }
    return EOF;
  }
  lookupTypeNonSC(idx) {
    for (let offset = this.tokenIndex; offset < this.tokenCount; offset++) {
      const tokenType2 = this.offsetAndType[offset] >> TYPE_SHIFT;
      if (tokenType2 !== WhiteSpace && tokenType2 !== Comment) {
        if (idx-- === 0) {
          return tokenType2;
        }
      }
    }
    return EOF;
  }
  lookupOffset(offset) {
    offset += this.tokenIndex;
    if (offset < this.tokenCount) {
      return this.offsetAndType[offset - 1] & OFFSET_MASK;
    }
    return this.source.length;
  }
  lookupOffsetNonSC(idx) {
    for (let offset = this.tokenIndex; offset < this.tokenCount; offset++) {
      const tokenType2 = this.offsetAndType[offset] >> TYPE_SHIFT;
      if (tokenType2 !== WhiteSpace && tokenType2 !== Comment) {
        if (idx-- === 0) {
          return offset - this.tokenIndex;
        }
      }
    }
    return EOF;
  }
  lookupValue(offset, referenceStr) {
    offset += this.tokenIndex;
    if (offset < this.tokenCount) {
      return cmpStr(
        this.source,
        this.offsetAndType[offset - 1] & OFFSET_MASK,
        this.offsetAndType[offset] & OFFSET_MASK,
        referenceStr
      );
    }
    return false;
  }
  getTokenStart(tokenIndex) {
    if (tokenIndex === this.tokenIndex) {
      return this.tokenStart;
    }
    if (tokenIndex > 0) {
      return tokenIndex < this.tokenCount ? this.offsetAndType[tokenIndex - 1] & OFFSET_MASK : this.offsetAndType[this.tokenCount] & OFFSET_MASK;
    }
    return this.firstCharOffset;
  }
  getTokenEnd(tokenIndex) {
    if (tokenIndex === this.tokenIndex) {
      return this.tokenEnd;
    }
    return this.offsetAndType[boundIndex(tokenIndex, 0, this.tokenCount)] & OFFSET_MASK;
  }
  getTokenType(tokenIndex) {
    if (tokenIndex === this.tokenIndex) {
      return this.tokenType;
    }
    return this.offsetAndType[boundIndex(tokenIndex, 0, this.tokenCount)] >> TYPE_SHIFT;
  }
  substrToCursor(start) {
    return this.source.substring(start, this.tokenStart);
  }
  isBlockOpenerTokenType(tokenType2) {
    return blockTokens[tokenType2] === BLOCK_OPEN_TOKEN;
  }
  isBlockCloserTokenType(tokenType2) {
    return blockTokens[tokenType2] === BLOCK_CLOSE_TOKEN;
  }
  getBlockTokenPairIndex(tokenIndex) {
    const type = this.getTokenType(tokenIndex);
    if (blockTokens[type] === 1) {
      const pairIndex = this.balance[tokenIndex];
      const closeType = this.getTokenType(pairIndex);
      return balancePair[type] === closeType ? pairIndex : -1;
    } else if (blockTokens[type] === 2) {
      const pairIndex = this.balance[tokenIndex];
      const openType = this.getTokenType(pairIndex);
      return balancePair[openType] === type ? pairIndex : -1;
    }
    return -1;
  }
  isBalanceEdge(tokenIndex) {
    return this.balance[this.tokenIndex] < tokenIndex;
  }
  isDelim(code2, offset) {
    if (offset) {
      return this.lookupType(offset) === Delim && this.source.charCodeAt(this.lookupOffset(offset)) === code2;
    }
    return this.tokenType === Delim && this.source.charCodeAt(this.tokenStart) === code2;
  }
  skip(tokenCount) {
    let next = this.tokenIndex + tokenCount;
    if (next < this.tokenCount) {
      this.tokenIndex = next;
      this.tokenStart = this.offsetAndType[next - 1] & OFFSET_MASK;
      next = this.offsetAndType[next];
      this.tokenType = next >> TYPE_SHIFT;
      this.tokenEnd = next & OFFSET_MASK;
    } else {
      this.tokenIndex = this.tokenCount;
      this.next();
    }
  }
  next() {
    let next = this.tokenIndex + 1;
    if (next < this.tokenCount) {
      this.tokenIndex = next;
      this.tokenStart = this.tokenEnd;
      next = this.offsetAndType[next];
      this.tokenType = next >> TYPE_SHIFT;
      this.tokenEnd = next & OFFSET_MASK;
    } else {
      this.eof = true;
      this.tokenIndex = this.tokenCount;
      this.tokenType = EOF;
      this.tokenStart = this.tokenEnd = this.source.length;
    }
  }
  skipSC() {
    while (this.tokenType === WhiteSpace || this.tokenType === Comment) {
      this.next();
    }
  }
  skipUntilBalanced(startToken, stopConsume) {
    let cursor = startToken;
    let balanceEnd = 0;
    let offset = 0;
    loop:
      for (; cursor < this.tokenCount; cursor++) {
        balanceEnd = this.balance[cursor];
        if (balanceEnd < startToken) {
          break loop;
        }
        offset = cursor > 0 ? this.offsetAndType[cursor - 1] & OFFSET_MASK : this.firstCharOffset;
        switch (stopConsume(this.source.charCodeAt(offset))) {
          case 1:
            break loop;
          case 2:
            cursor++;
            break loop;
          default:
            if (this.isBlockOpenerTokenType(this.offsetAndType[cursor] >> TYPE_SHIFT)) {
              cursor = balanceEnd;
            }
        }
      }
    this.skip(cursor - this.tokenIndex);
  }
  forEachToken(fn) {
    for (let i = 0, offset = this.firstCharOffset; i < this.tokenCount; i++) {
      const start = offset;
      const item = this.offsetAndType[i];
      const end = item & OFFSET_MASK;
      const type = item >> TYPE_SHIFT;
      offset = end;
      fn(type, start, end, i);
    }
  }
  dump() {
    const tokens = new Array(this.tokenCount);
    this.forEachToken((type, start, end, index) => {
      tokens[index] = {
        idx: index,
        type: names_default[type],
        chunk: this.source.substring(start, end),
        balance: this.balance[index]
      };
    });
    return tokens;
  }
};

// node_modules/css-tree/lib/tokenizer/index.js
function tokenize(source, onToken) {
  function getCharCode2(offset2) {
    return offset2 < sourceLength ? source.charCodeAt(offset2) : 0;
  }
  function consumeNumericToken() {
    offset = consumeNumber(source, offset);
    if (isIdentifierStart(getCharCode2(offset), getCharCode2(offset + 1), getCharCode2(offset + 2))) {
      type = Dimension;
      offset = consumeName(source, offset);
      return;
    }
    if (getCharCode2(offset) === 37) {
      type = Percentage;
      offset++;
      return;
    }
    type = Number2;
  }
  function consumeIdentLikeToken() {
    const nameStartOffset = offset;
    offset = consumeName(source, offset);
    if (cmpStr(source, nameStartOffset, offset, "url") && getCharCode2(offset) === 40) {
      offset = findWhiteSpaceEnd(source, offset + 1);
      if (getCharCode2(offset) === 34 || getCharCode2(offset) === 39) {
        type = Function2;
        offset = nameStartOffset + 4;
        return;
      }
      consumeUrlToken();
      return;
    }
    if (getCharCode2(offset) === 40) {
      type = Function2;
      offset++;
      return;
    }
    type = Ident;
  }
  function consumeStringToken(endingCodePoint) {
    if (!endingCodePoint) {
      endingCodePoint = getCharCode2(offset++);
    }
    type = String2;
    for (; offset < source.length; offset++) {
      const code2 = source.charCodeAt(offset);
      switch (charCodeCategory(code2)) {
        // ending code point
        case endingCodePoint:
          offset++;
          return;
        // EOF
        // case EofCategory:
        // This is a parse error. Return the <string-token>.
        // return;
        // newline
        case WhiteSpaceCategory:
          if (isNewline(code2)) {
            offset += getNewlineLength(source, offset, code2);
            type = BadString;
            return;
          }
          break;
        // U+005C REVERSE SOLIDUS (\)
        case 92:
          if (offset === source.length - 1) {
            break;
          }
          const nextCode = getCharCode2(offset + 1);
          if (isNewline(nextCode)) {
            offset += getNewlineLength(source, offset + 1, nextCode);
          } else if (isValidEscape(code2, nextCode)) {
            offset = consumeEscaped(source, offset) - 1;
          }
          break;
      }
    }
  }
  function consumeUrlToken() {
    type = Url;
    offset = findWhiteSpaceEnd(source, offset);
    for (; offset < source.length; offset++) {
      const code2 = source.charCodeAt(offset);
      switch (charCodeCategory(code2)) {
        // U+0029 RIGHT PARENTHESIS ())
        case 41:
          offset++;
          return;
        // EOF
        // case EofCategory:
        // This is a parse error. Return the <url-token>.
        // return;
        // whitespace
        case WhiteSpaceCategory:
          offset = findWhiteSpaceEnd(source, offset);
          if (getCharCode2(offset) === 41 || offset >= source.length) {
            if (offset < source.length) {
              offset++;
            }
            return;
          }
          offset = consumeBadUrlRemnants(source, offset);
          type = BadUrl;
          return;
        // U+0022 QUOTATION MARK (")
        // U+0027 APOSTROPHE (')
        // U+0028 LEFT PARENTHESIS (()
        // non-printable code point
        case 34:
        case 39:
        case 40:
        case NonPrintableCategory:
          offset = consumeBadUrlRemnants(source, offset);
          type = BadUrl;
          return;
        // U+005C REVERSE SOLIDUS (\)
        case 92:
          if (isValidEscape(code2, getCharCode2(offset + 1))) {
            offset = consumeEscaped(source, offset) - 1;
            break;
          }
          offset = consumeBadUrlRemnants(source, offset);
          type = BadUrl;
          return;
      }
    }
  }
  source = String(source || "");
  const sourceLength = source.length;
  let start = isBOM(getCharCode2(0));
  let offset = start;
  let type;
  while (offset < sourceLength) {
    const code2 = source.charCodeAt(offset);
    switch (charCodeCategory(code2)) {
      // whitespace
      case WhiteSpaceCategory:
        type = WhiteSpace;
        offset = findWhiteSpaceEnd(source, offset + 1);
        break;
      // U+0022 QUOTATION MARK (")
      case 34:
        consumeStringToken();
        break;
      // U+0023 NUMBER SIGN (#)
      case 35:
        if (isName(getCharCode2(offset + 1)) || isValidEscape(getCharCode2(offset + 1), getCharCode2(offset + 2))) {
          type = Hash;
          offset = consumeName(source, offset + 1);
        } else {
          type = Delim;
          offset++;
        }
        break;
      // U+0027 APOSTROPHE (')
      case 39:
        consumeStringToken();
        break;
      // U+0028 LEFT PARENTHESIS (()
      case 40:
        type = LeftParenthesis;
        offset++;
        break;
      // U+0029 RIGHT PARENTHESIS ())
      case 41:
        type = RightParenthesis;
        offset++;
        break;
      // U+002B PLUS SIGN (+)
      case 43:
        if (isNumberStart(code2, getCharCode2(offset + 1), getCharCode2(offset + 2))) {
          consumeNumericToken();
        } else {
          type = Delim;
          offset++;
        }
        break;
      // U+002C COMMA (,)
      case 44:
        type = Comma;
        offset++;
        break;
      // U+002D HYPHEN-MINUS (-)
      case 45:
        if (isNumberStart(code2, getCharCode2(offset + 1), getCharCode2(offset + 2))) {
          consumeNumericToken();
        } else {
          if (getCharCode2(offset + 1) === 45 && getCharCode2(offset + 2) === 62) {
            type = CDC;
            offset = offset + 3;
          } else {
            if (isIdentifierStart(code2, getCharCode2(offset + 1), getCharCode2(offset + 2))) {
              consumeIdentLikeToken();
            } else {
              type = Delim;
              offset++;
            }
          }
        }
        break;
      // U+002E FULL STOP (.)
      case 46:
        if (isNumberStart(code2, getCharCode2(offset + 1), getCharCode2(offset + 2))) {
          consumeNumericToken();
        } else {
          type = Delim;
          offset++;
        }
        break;
      // U+002F SOLIDUS (/)
      case 47:
        if (getCharCode2(offset + 1) === 42) {
          type = Comment;
          offset = source.indexOf("*/", offset + 2);
          offset = offset === -1 ? source.length : offset + 2;
        } else {
          type = Delim;
          offset++;
        }
        break;
      // U+003A COLON (:)
      case 58:
        type = Colon;
        offset++;
        break;
      // U+003B SEMICOLON (;)
      case 59:
        type = Semicolon;
        offset++;
        break;
      // U+003C LESS-THAN SIGN (<)
      case 60:
        if (getCharCode2(offset + 1) === 33 && getCharCode2(offset + 2) === 45 && getCharCode2(offset + 3) === 45) {
          type = CDO;
          offset = offset + 4;
        } else {
          type = Delim;
          offset++;
        }
        break;
      // U+0040 COMMERCIAL AT (@)
      case 64:
        if (isIdentifierStart(getCharCode2(offset + 1), getCharCode2(offset + 2), getCharCode2(offset + 3))) {
          type = AtKeyword;
          offset = consumeName(source, offset + 1);
        } else {
          type = Delim;
          offset++;
        }
        break;
      // U+005B LEFT SQUARE BRACKET ([)
      case 91:
        type = LeftSquareBracket;
        offset++;
        break;
      // U+005C REVERSE SOLIDUS (\)
      case 92:
        if (isValidEscape(code2, getCharCode2(offset + 1))) {
          consumeIdentLikeToken();
        } else {
          type = Delim;
          offset++;
        }
        break;
      // U+005D RIGHT SQUARE BRACKET (])
      case 93:
        type = RightSquareBracket;
        offset++;
        break;
      // U+007B LEFT CURLY BRACKET ({)
      case 123:
        type = LeftCurlyBracket;
        offset++;
        break;
      // U+007D RIGHT CURLY BRACKET (})
      case 125:
        type = RightCurlyBracket;
        offset++;
        break;
      // digit
      case DigitCategory:
        consumeNumericToken();
        break;
      // name-start code point
      case NameStartCategory:
        consumeIdentLikeToken();
        break;
      // EOF
      // case EofCategory:
      // Return an <EOF-token>.
      // break;
      // anything else
      default:
        type = Delim;
        offset++;
    }
    onToken(type, start, start = offset);
  }
}

// node_modules/css-tree/lib/utils/List.js
var releasedCursors = null;
var List = class _List {
  static createItem(data) {
    return {
      prev: null,
      next: null,
      data
    };
  }
  constructor() {
    this.head = null;
    this.tail = null;
    this.cursor = null;
  }
  createItem(data) {
    return _List.createItem(data);
  }
  // cursor helpers
  allocateCursor(prev, next) {
    let cursor;
    if (releasedCursors !== null) {
      cursor = releasedCursors;
      releasedCursors = releasedCursors.cursor;
      cursor.prev = prev;
      cursor.next = next;
      cursor.cursor = this.cursor;
    } else {
      cursor = {
        prev,
        next,
        cursor: this.cursor
      };
    }
    this.cursor = cursor;
    return cursor;
  }
  releaseCursor() {
    const { cursor } = this;
    this.cursor = cursor.cursor;
    cursor.prev = null;
    cursor.next = null;
    cursor.cursor = releasedCursors;
    releasedCursors = cursor;
  }
  updateCursors(prevOld, prevNew, nextOld, nextNew) {
    let { cursor } = this;
    while (cursor !== null) {
      if (cursor.prev === prevOld) {
        cursor.prev = prevNew;
      }
      if (cursor.next === nextOld) {
        cursor.next = nextNew;
      }
      cursor = cursor.cursor;
    }
  }
  *[Symbol.iterator]() {
    for (let cursor = this.head; cursor !== null; cursor = cursor.next) {
      yield cursor.data;
    }
  }
  // getters
  get size() {
    let size = 0;
    for (let cursor = this.head; cursor !== null; cursor = cursor.next) {
      size++;
    }
    return size;
  }
  get isEmpty() {
    return this.head === null;
  }
  get first() {
    return this.head && this.head.data;
  }
  get last() {
    return this.tail && this.tail.data;
  }
  // convertors
  fromArray(array) {
    let cursor = null;
    this.head = null;
    for (let data of array) {
      const item = _List.createItem(data);
      if (cursor !== null) {
        cursor.next = item;
      } else {
        this.head = item;
      }
      item.prev = cursor;
      cursor = item;
    }
    this.tail = cursor;
    return this;
  }
  toArray() {
    return [...this];
  }
  toJSON() {
    return [...this];
  }
  // array-like methods
  forEach(fn, thisArg = this) {
    const cursor = this.allocateCursor(null, this.head);
    while (cursor.next !== null) {
      const item = cursor.next;
      cursor.next = item.next;
      fn.call(thisArg, item.data, item, this);
    }
    this.releaseCursor();
  }
  forEachRight(fn, thisArg = this) {
    const cursor = this.allocateCursor(this.tail, null);
    while (cursor.prev !== null) {
      const item = cursor.prev;
      cursor.prev = item.prev;
      fn.call(thisArg, item.data, item, this);
    }
    this.releaseCursor();
  }
  reduce(fn, initialValue, thisArg = this) {
    let cursor = this.allocateCursor(null, this.head);
    let acc = initialValue;
    let item;
    while (cursor.next !== null) {
      item = cursor.next;
      cursor.next = item.next;
      acc = fn.call(thisArg, acc, item.data, item, this);
    }
    this.releaseCursor();
    return acc;
  }
  reduceRight(fn, initialValue, thisArg = this) {
    let cursor = this.allocateCursor(this.tail, null);
    let acc = initialValue;
    let item;
    while (cursor.prev !== null) {
      item = cursor.prev;
      cursor.prev = item.prev;
      acc = fn.call(thisArg, acc, item.data, item, this);
    }
    this.releaseCursor();
    return acc;
  }
  some(fn, thisArg = this) {
    for (let cursor = this.head; cursor !== null; cursor = cursor.next) {
      if (fn.call(thisArg, cursor.data, cursor, this)) {
        return true;
      }
    }
    return false;
  }
  map(fn, thisArg = this) {
    const result = new _List();
    for (let cursor = this.head; cursor !== null; cursor = cursor.next) {
      result.appendData(fn.call(thisArg, cursor.data, cursor, this));
    }
    return result;
  }
  filter(fn, thisArg = this) {
    const result = new _List();
    for (let cursor = this.head; cursor !== null; cursor = cursor.next) {
      if (fn.call(thisArg, cursor.data, cursor, this)) {
        result.appendData(cursor.data);
      }
    }
    return result;
  }
  nextUntil(start, fn, thisArg = this) {
    if (start === null) {
      return;
    }
    const cursor = this.allocateCursor(null, start);
    while (cursor.next !== null) {
      const item = cursor.next;
      cursor.next = item.next;
      if (fn.call(thisArg, item.data, item, this)) {
        break;
      }
    }
    this.releaseCursor();
  }
  prevUntil(start, fn, thisArg = this) {
    if (start === null) {
      return;
    }
    const cursor = this.allocateCursor(start, null);
    while (cursor.prev !== null) {
      const item = cursor.prev;
      cursor.prev = item.prev;
      if (fn.call(thisArg, item.data, item, this)) {
        break;
      }
    }
    this.releaseCursor();
  }
  // mutation
  clear() {
    this.head = null;
    this.tail = null;
  }
  copy() {
    const result = new _List();
    for (let data of this) {
      result.appendData(data);
    }
    return result;
  }
  prepend(item) {
    this.updateCursors(null, item, this.head, item);
    if (this.head !== null) {
      this.head.prev = item;
      item.next = this.head;
    } else {
      this.tail = item;
    }
    this.head = item;
    return this;
  }
  prependData(data) {
    return this.prepend(_List.createItem(data));
  }
  append(item) {
    return this.insert(item);
  }
  appendData(data) {
    return this.insert(_List.createItem(data));
  }
  insert(item, before = null) {
    if (before !== null) {
      this.updateCursors(before.prev, item, before, item);
      if (before.prev === null) {
        if (this.head !== before) {
          throw new Error("before doesn't belong to list");
        }
        this.head = item;
        before.prev = item;
        item.next = before;
        this.updateCursors(null, item);
      } else {
        before.prev.next = item;
        item.prev = before.prev;
        before.prev = item;
        item.next = before;
      }
    } else {
      this.updateCursors(this.tail, item, null, item);
      if (this.tail !== null) {
        this.tail.next = item;
        item.prev = this.tail;
      } else {
        this.head = item;
      }
      this.tail = item;
    }
    return this;
  }
  insertData(data, before) {
    return this.insert(_List.createItem(data), before);
  }
  remove(item) {
    this.updateCursors(item, item.prev, item, item.next);
    if (item.prev !== null) {
      item.prev.next = item.next;
    } else {
      if (this.head !== item) {
        throw new Error("item doesn't belong to list");
      }
      this.head = item.next;
    }
    if (item.next !== null) {
      item.next.prev = item.prev;
    } else {
      if (this.tail !== item) {
        throw new Error("item doesn't belong to list");
      }
      this.tail = item.prev;
    }
    item.prev = null;
    item.next = null;
    return item;
  }
  push(data) {
    this.insert(_List.createItem(data));
  }
  pop() {
    return this.tail !== null ? this.remove(this.tail) : null;
  }
  unshift(data) {
    this.prepend(_List.createItem(data));
  }
  shift() {
    return this.head !== null ? this.remove(this.head) : null;
  }
  prependList(list) {
    return this.insertList(list, this.head);
  }
  appendList(list) {
    return this.insertList(list);
  }
  insertList(list, before) {
    if (list.head === null) {
      return this;
    }
    if (before !== void 0 && before !== null) {
      this.updateCursors(before.prev, list.tail, before, list.head);
      if (before.prev !== null) {
        before.prev.next = list.head;
        list.head.prev = before.prev;
      } else {
        this.head = list.head;
      }
      before.prev = list.tail;
      list.tail.next = before;
    } else {
      this.updateCursors(this.tail, list.tail, null, list.head);
      if (this.tail !== null) {
        this.tail.next = list.head;
        list.head.prev = this.tail;
      } else {
        this.head = list.head;
      }
      this.tail = list.tail;
    }
    list.head = null;
    list.tail = null;
    return this;
  }
  replace(oldItem, newItemOrList) {
    if ("head" in newItemOrList) {
      this.insertList(newItemOrList, oldItem);
    } else {
      this.insert(newItemOrList, oldItem);
    }
    this.remove(oldItem);
  }
};

// node_modules/css-tree/lib/utils/create-custom-error.js
function createCustomError(name50, message) {
  const error = Object.create(SyntaxError.prototype);
  const errorStack = new Error();
  return Object.assign(error, {
    name: name50,
    message,
    get stack() {
      return (errorStack.stack || "").replace(/^(.+\n){1,3}/, `${name50}: ${message}
`);
    }
  });
}

// node_modules/css-tree/lib/parser/SyntaxError.js
var MAX_LINE_LENGTH = 100;
var OFFSET_CORRECTION = 60;
var TAB_REPLACEMENT = "    ";
function sourceFragment({ source, line, column, baseLine, baseColumn }, extraLines) {
  function processLines(start, end) {
    return lines.slice(start, end).map(
      (line2, idx) => String(start + idx + 1).padStart(maxNumLength) + " |" + line2
    ).join("\n");
  }
  const prelines = "\n".repeat(Math.max(baseLine - 1, 0));
  const precolumns = " ".repeat(Math.max(baseColumn - 1, 0));
  const lines = (prelines + precolumns + source).split(/\r\n?|\n|\f/);
  const startLine = Math.max(1, line - extraLines) - 1;
  const endLine = Math.min(line + extraLines, lines.length + 1);
  const maxNumLength = Math.max(4, String(endLine).length) + 1;
  let cutLeft = 0;
  column += (TAB_REPLACEMENT.length - 1) * (lines[line - 1].substr(0, column - 1).match(/\t/g) || []).length;
  if (column > MAX_LINE_LENGTH) {
    cutLeft = column - OFFSET_CORRECTION + 3;
    column = OFFSET_CORRECTION - 2;
  }
  for (let i = startLine; i <= endLine; i++) {
    if (i >= 0 && i < lines.length) {
      lines[i] = lines[i].replace(/\t/g, TAB_REPLACEMENT);
      lines[i] = (cutLeft > 0 && lines[i].length > cutLeft ? "\u2026" : "") + lines[i].substr(cutLeft, MAX_LINE_LENGTH - 2) + (lines[i].length > cutLeft + MAX_LINE_LENGTH - 1 ? "\u2026" : "");
    }
  }
  return [
    processLines(startLine, line),
    new Array(column + maxNumLength + 2).join("-") + "^",
    processLines(line, endLine)
  ].filter(Boolean).join("\n").replace(/^(\s+\d+\s+\|\n)+/, "").replace(/\n(\s+\d+\s+\|)+$/, "");
}
function SyntaxError2(message, source, offset, line, column, baseLine = 1, baseColumn = 1) {
  const error = Object.assign(createCustomError("SyntaxError", message), {
    source,
    offset,
    line,
    column,
    sourceFragment(extraLines) {
      return sourceFragment({ source, line, column, baseLine, baseColumn }, isNaN(extraLines) ? 0 : extraLines);
    },
    get formattedMessage() {
      return `Parse error: ${message}
` + sourceFragment({ source, line, column, baseLine, baseColumn }, 2);
    }
  });
  return error;
}

// node_modules/css-tree/lib/parser/sequence.js
function readSequence(recognizer) {
  const children = this.createList();
  let space = false;
  const context = {
    recognizer
  };
  while (!this.eof) {
    switch (this.tokenType) {
      case Comment:
        this.next();
        continue;
      case WhiteSpace:
        space = true;
        this.next();
        continue;
    }
    let child = recognizer.getNode.call(this, context);
    if (child === void 0) {
      break;
    }
    if (space) {
      if (recognizer.onWhiteSpace) {
        recognizer.onWhiteSpace.call(this, child, children, context);
      }
      space = false;
    }
    children.push(child);
  }
  if (space && recognizer.onWhiteSpace) {
    recognizer.onWhiteSpace.call(this, null, children, context);
  }
  return children;
}

// node_modules/css-tree/lib/parser/create.js
var NOOP = () => {
};
var EXCLAMATIONMARK = 33;
var NUMBERSIGN = 35;
var SEMICOLON = 59;
var LEFTCURLYBRACKET = 123;
var NULL = 0;
var arrayMethods = {
  createList() {
    return [];
  },
  createSingleNodeList(node) {
    return [node];
  },
  getFirstListNode(list) {
    return list && list[0] || null;
  },
  getLastListNode(list) {
    return list && list.length > 0 ? list[list.length - 1] : null;
  }
};
var listMethods = {
  createList() {
    return new List();
  },
  createSingleNodeList(node) {
    return new List().appendData(node);
  },
  getFirstListNode(list) {
    return list && list.first;
  },
  getLastListNode(list) {
    return list && list.last;
  }
};
function createParseContext(name50) {
  return function() {
    return this[name50]();
  };
}
function fetchParseValues(dict) {
  const result = /* @__PURE__ */ Object.create(null);
  for (const name50 of Object.keys(dict)) {
    const item = dict[name50];
    const fn = item.parse || item;
    if (fn) {
      result[name50] = fn;
    }
  }
  return result;
}
function processConfig(config) {
  const parseConfig = {
    context: /* @__PURE__ */ Object.create(null),
    features: Object.assign(/* @__PURE__ */ Object.create(null), config.features),
    scope: Object.assign(/* @__PURE__ */ Object.create(null), config.scope),
    atrule: fetchParseValues(config.atrule),
    pseudo: fetchParseValues(config.pseudo),
    node: fetchParseValues(config.node)
  };
  for (const [name50, context] of Object.entries(config.parseContext)) {
    switch (typeof context) {
      case "function":
        parseConfig.context[name50] = context;
        break;
      case "string":
        parseConfig.context[name50] = createParseContext(context);
        break;
    }
  }
  return {
    config: parseConfig,
    ...parseConfig,
    ...parseConfig.node
  };
}
function createParser(config) {
  let source = "";
  let filename = "<unknown>";
  let needPositions = false;
  let onParseError = NOOP;
  let onParseErrorThrow = false;
  const locationMap = new OffsetToLocation();
  const parser = Object.assign(new TokenStream(), processConfig(config || {}), {
    parseAtrulePrelude: true,
    parseRulePrelude: true,
    parseValue: true,
    parseCustomProperty: false,
    readSequence,
    consumeUntilBalanceEnd: () => 0,
    consumeUntilLeftCurlyBracket(code2) {
      return code2 === LEFTCURLYBRACKET ? 1 : 0;
    },
    consumeUntilLeftCurlyBracketOrSemicolon(code2) {
      return code2 === LEFTCURLYBRACKET || code2 === SEMICOLON ? 1 : 0;
    },
    consumeUntilExclamationMarkOrSemicolon(code2) {
      return code2 === EXCLAMATIONMARK || code2 === SEMICOLON ? 1 : 0;
    },
    consumeUntilSemicolonIncluded(code2) {
      return code2 === SEMICOLON ? 2 : 0;
    },
    createList: NOOP,
    createSingleNodeList: NOOP,
    getFirstListNode: NOOP,
    getLastListNode: NOOP,
    parseWithFallback(consumer, fallback) {
      const startIndex = this.tokenIndex;
      try {
        return consumer.call(this);
      } catch (e) {
        if (onParseErrorThrow) {
          throw e;
        }
        this.skip(startIndex - this.tokenIndex);
        const fallbackNode = fallback.call(this);
        onParseErrorThrow = true;
        onParseError(e, fallbackNode);
        onParseErrorThrow = false;
        return fallbackNode;
      }
    },
    lookupNonWSType(offset) {
      let type;
      do {
        type = this.lookupType(offset++);
        if (type !== WhiteSpace && type !== Comment) {
          return type;
        }
      } while (type !== NULL);
      return NULL;
    },
    charCodeAt(offset) {
      return offset >= 0 && offset < source.length ? source.charCodeAt(offset) : 0;
    },
    substring(offsetStart, offsetEnd) {
      return source.substring(offsetStart, offsetEnd);
    },
    substrToCursor(start) {
      return this.source.substring(start, this.tokenStart);
    },
    cmpChar(offset, charCode) {
      return cmpChar(source, offset, charCode);
    },
    cmpStr(offsetStart, offsetEnd, str) {
      return cmpStr(source, offsetStart, offsetEnd, str);
    },
    consume(tokenType2) {
      const start = this.tokenStart;
      this.eat(tokenType2);
      return this.substrToCursor(start);
    },
    consumeFunctionName() {
      const name50 = source.substring(this.tokenStart, this.tokenEnd - 1);
      this.eat(Function2);
      return name50;
    },
    consumeNumber(type) {
      const number2 = source.substring(this.tokenStart, consumeNumber(source, this.tokenStart));
      this.eat(type);
      return number2;
    },
    eat(tokenType2) {
      if (this.tokenType !== tokenType2) {
        const tokenName = names_default[tokenType2].slice(0, -6).replace(/-/g, " ").replace(/^./, (m) => m.toUpperCase());
        let message = `${/[[\](){}]/.test(tokenName) ? `"${tokenName}"` : tokenName} is expected`;
        let offset = this.tokenStart;
        switch (tokenType2) {
          case Ident:
            if (this.tokenType === Function2 || this.tokenType === Url) {
              offset = this.tokenEnd - 1;
              message = "Identifier is expected but function found";
            } else {
              message = "Identifier is expected";
            }
            break;
          case Hash:
            if (this.isDelim(NUMBERSIGN)) {
              this.next();
              offset++;
              message = "Name is expected";
            }
            break;
          case Percentage:
            if (this.tokenType === Number2) {
              offset = this.tokenEnd;
              message = "Percent sign is expected";
            }
            break;
        }
        this.error(message, offset);
      }
      this.next();
    },
    eatIdent(name50) {
      if (this.tokenType !== Ident || this.lookupValue(0, name50) === false) {
        this.error(`Identifier "${name50}" is expected`);
      }
      this.next();
    },
    eatDelim(code2) {
      if (!this.isDelim(code2)) {
        this.error(`Delim "${String.fromCharCode(code2)}" is expected`);
      }
      this.next();
    },
    getLocation(start, end) {
      if (needPositions) {
        return locationMap.getLocationRange(
          start,
          end,
          filename
        );
      }
      return null;
    },
    getLocationFromList(list) {
      if (needPositions) {
        const head = this.getFirstListNode(list);
        const tail = this.getLastListNode(list);
        return locationMap.getLocationRange(
          head !== null ? head.loc.start.offset - locationMap.startOffset : this.tokenStart,
          tail !== null ? tail.loc.end.offset - locationMap.startOffset : this.tokenStart,
          filename
        );
      }
      return null;
    },
    error(message, offset) {
      const location = typeof offset !== "undefined" && offset < source.length ? locationMap.getLocation(offset) : this.eof ? locationMap.getLocation(findWhiteSpaceStart(source, source.length - 1)) : locationMap.getLocation(this.tokenStart);
      throw new SyntaxError2(
        message || "Unexpected input",
        source,
        location.offset,
        location.line,
        location.column,
        locationMap.startLine,
        locationMap.startColumn
      );
    }
  });
  const createTokenIterateAPI = () => ({
    filename,
    source,
    tokenCount: parser.tokenCount,
    getTokenType: (index) => parser.getTokenType(index),
    getTokenTypeName: (index) => names_default[parser.getTokenType(index)],
    getTokenStart: (index) => parser.getTokenStart(index),
    getTokenEnd: (index) => parser.getTokenEnd(index),
    getTokenValue: (index) => parser.source.substring(parser.getTokenStart(index), parser.getTokenEnd(index)),
    substring: (start, end) => parser.source.substring(start, end),
    balance: parser.balance.subarray(0, parser.tokenCount + 1),
    isBlockOpenerTokenType: parser.isBlockOpenerTokenType,
    isBlockCloserTokenType: parser.isBlockCloserTokenType,
    getBlockTokenPairIndex: (index) => parser.getBlockTokenPairIndex(index),
    getLocation: (offset) => locationMap.getLocation(offset, filename),
    getRangeLocation: (start, end) => locationMap.getLocationRange(start, end, filename)
  });
  const parse52 = function(source_, options) {
    source = source_;
    options = options || {};
    parser.setSource(source, tokenize);
    locationMap.setSource(
      source,
      options.offset,
      options.line,
      options.column
    );
    filename = options.filename || "<unknown>";
    needPositions = Boolean(options.positions);
    onParseError = typeof options.onParseError === "function" ? options.onParseError : NOOP;
    onParseErrorThrow = false;
    parser.parseAtrulePrelude = "parseAtrulePrelude" in options ? Boolean(options.parseAtrulePrelude) : true;
    parser.parseRulePrelude = "parseRulePrelude" in options ? Boolean(options.parseRulePrelude) : true;
    parser.parseValue = "parseValue" in options ? Boolean(options.parseValue) : true;
    parser.parseCustomProperty = "parseCustomProperty" in options ? Boolean(options.parseCustomProperty) : false;
    const { context = "default", list = true, onComment, onToken } = options;
    if (context in parser.context === false) {
      throw new Error("Unknown context `" + context + "`");
    }
    Object.assign(parser, list ? listMethods : arrayMethods);
    if (Array.isArray(onToken)) {
      parser.forEachToken((type, start, end) => {
        onToken.push({ type, start, end });
      });
    } else if (typeof onToken === "function") {
      parser.forEachToken(onToken.bind(createTokenIterateAPI()));
    }
    if (typeof onComment === "function") {
      parser.forEachToken((type, start, end) => {
        if (type === Comment) {
          const loc = parser.getLocation(start, end);
          const value = cmpStr(source, end - 2, end, "*/") ? source.slice(start + 2, end - 2) : source.slice(start + 2, end);
          onComment(value, loc);
        }
      });
    }
    const ast = parser.context[context].call(parser, options);
    if (!parser.eof) {
      parser.error();
    }
    return ast;
  };
  return Object.assign(parse52, {
    SyntaxError: SyntaxError2,
    config: parser.config
  });
}

// node_modules/css-tree/lib/generator/sourceMap.js
var import_source_map_generator = __toESM(require_source_map_generator(), 1);
var trackNodes = /* @__PURE__ */ new Set(["Atrule", "Selector", "Declaration"]);
function generateSourceMap(handlers) {
  const map = new import_source_map_generator.SourceMapGenerator();
  const generated = {
    line: 1,
    column: 0
  };
  const original = {
    line: 0,
    // should be zero to add first mapping
    column: 0
  };
  const activatedGenerated = {
    line: 1,
    column: 0
  };
  const activatedMapping = {
    generated: activatedGenerated
  };
  let line = 1;
  let column = 0;
  let sourceMappingActive = false;
  const origHandlersNode = handlers.node;
  handlers.node = function(node) {
    if (node.loc && node.loc.start && trackNodes.has(node.type)) {
      const nodeLine = node.loc.start.line;
      const nodeColumn = node.loc.start.column - 1;
      if (original.line !== nodeLine || original.column !== nodeColumn) {
        original.line = nodeLine;
        original.column = nodeColumn;
        generated.line = line;
        generated.column = column;
        if (sourceMappingActive) {
          sourceMappingActive = false;
          if (generated.line !== activatedGenerated.line || generated.column !== activatedGenerated.column) {
            map.addMapping(activatedMapping);
          }
        }
        sourceMappingActive = true;
        map.addMapping({
          source: node.loc.source,
          original,
          generated
        });
      }
    }
    origHandlersNode.call(this, node);
    if (sourceMappingActive && trackNodes.has(node.type)) {
      activatedGenerated.line = line;
      activatedGenerated.column = column;
    }
  };
  const origHandlersEmit = handlers.emit;
  handlers.emit = function(value, type, auto) {
    for (let i = 0; i < value.length; i++) {
      if (value.charCodeAt(i) === 10) {
        line++;
        column = 0;
      } else {
        column++;
      }
    }
    origHandlersEmit(value, type, auto);
  };
  const origHandlersResult = handlers.result;
  handlers.result = function() {
    if (sourceMappingActive) {
      map.addMapping(activatedMapping);
    }
    return {
      css: origHandlersResult(),
      map
    };
  };
  return handlers;
}

// node_modules/css-tree/lib/generator/token-before.js
var token_before_exports = {};
__export(token_before_exports, {
  safe: () => safe,
  spec: () => spec
});
var PLUSSIGN = 43;
var HYPHENMINUS = 45;
var code = (type, value) => {
  if (type === Delim) {
    type = value;
  }
  if (typeof type === "string") {
    type = Math.min(type.charCodeAt(0), 128) << 6;
  }
  return type << 1;
};
var specPairs = [
  [Ident, Ident],
  [Ident, Function2],
  [Ident, Url],
  [Ident, BadUrl],
  [Ident, "-"],
  [Ident, Number2],
  [Ident, Percentage],
  [Ident, Dimension],
  [Ident, CDC],
  [Ident, LeftParenthesis],
  [AtKeyword, Ident],
  [AtKeyword, Function2],
  [AtKeyword, Url],
  [AtKeyword, BadUrl],
  [AtKeyword, "-"],
  [AtKeyword, Number2],
  [AtKeyword, Percentage],
  [AtKeyword, Dimension],
  [AtKeyword, CDC],
  [Hash, Ident],
  [Hash, Function2],
  [Hash, Url],
  [Hash, BadUrl],
  [Hash, "-"],
  [Hash, Number2],
  [Hash, Percentage],
  [Hash, Dimension],
  [Hash, CDC],
  [Dimension, Ident],
  [Dimension, Function2],
  [Dimension, Url],
  [Dimension, BadUrl],
  [Dimension, "-"],
  [Dimension, Number2],
  [Dimension, Percentage],
  [Dimension, Dimension],
  [Dimension, CDC],
  ["#", Ident],
  ["#", Function2],
  ["#", Url],
  ["#", BadUrl],
  ["#", "-"],
  ["#", Number2],
  ["#", Percentage],
  ["#", Dimension],
  ["#", CDC],
  // https://github.com/w3c/csswg-drafts/pull/6874
  ["-", Ident],
  ["-", Function2],
  ["-", Url],
  ["-", BadUrl],
  ["-", "-"],
  ["-", Number2],
  ["-", Percentage],
  ["-", Dimension],
  ["-", CDC],
  // https://github.com/w3c/csswg-drafts/pull/6874
  [Number2, Ident],
  [Number2, Function2],
  [Number2, Url],
  [Number2, BadUrl],
  [Number2, Number2],
  [Number2, Percentage],
  [Number2, Dimension],
  [Number2, "%"],
  [Number2, CDC],
  // https://github.com/w3c/csswg-drafts/pull/6874
  ["@", Ident],
  ["@", Function2],
  ["@", Url],
  ["@", BadUrl],
  ["@", "-"],
  ["@", CDC],
  // https://github.com/w3c/csswg-drafts/pull/6874
  [".", Number2],
  [".", Percentage],
  [".", Dimension],
  ["+", Number2],
  ["+", Percentage],
  ["+", Dimension],
  ["/", "*"]
];
var safePairs = specPairs.concat([
  [Ident, Hash],
  [Dimension, Hash],
  [Hash, Hash],
  [AtKeyword, LeftParenthesis],
  [AtKeyword, String2],
  [AtKeyword, Colon],
  [Percentage, Percentage],
  [Percentage, Dimension],
  [Percentage, Function2],
  [Percentage, "-"],
  [RightParenthesis, Ident],
  [RightParenthesis, Function2],
  [RightParenthesis, Percentage],
  [RightParenthesis, Dimension],
  [RightParenthesis, Hash],
  [RightParenthesis, "-"]
]);
function createMap(pairs) {
  const isWhiteSpaceRequired = new Set(
    pairs.map(([prev, next]) => code(prev) << 16 | code(next))
  );
  return function(prevCode, type, value) {
    const nextCode = code(type, value);
    const nextCharCode = value.charCodeAt(0);
    const emitWs = nextCharCode === HYPHENMINUS && type !== Ident && type !== Function2 && type !== CDC || nextCharCode === PLUSSIGN ? isWhiteSpaceRequired.has((prevCode & 65534) << 16 | nextCharCode << 7) : isWhiteSpaceRequired.has((prevCode & 65534) << 16 | nextCode);
    return nextCode | emitWs;
  };
}
var spec = createMap(specPairs);
var safe = createMap(safePairs);

// node_modules/css-tree/lib/generator/create.js
var REVERSESOLIDUS = 92;
function processChildren(node, delimeter) {
  if (typeof delimeter === "function") {
    let prev = null;
    node.children.forEach((node2) => {
      if (prev !== null) {
        delimeter.call(this, prev);
      }
      this.node(node2);
      prev = node2;
    });
    return;
  }
  node.children.forEach(this.node, this);
}
function createGenerator(config) {
  const types = /* @__PURE__ */ new Map();
  for (let [name50, item] of Object.entries(config.node)) {
    const fn = item.generate || item;
    if (typeof fn === "function") {
      types.set(name50, item.generate || item);
    }
  }
  return function(node, options) {
    let buffer = "";
    let prevCode = 0;
    let handlers = {
      node(node2) {
        if (types.has(node2.type)) {
          types.get(node2.type).call(publicApi, node2);
        } else {
          throw new Error("Unknown node type: " + node2.type);
        }
      },
      tokenBefore: safe,
      token(type, value, suppressAutoWhiteSpace) {
        prevCode = this.tokenBefore(prevCode, type, value);
        if (!suppressAutoWhiteSpace && prevCode & 1) {
          this.emit(" ", WhiteSpace, true);
        }
        this.emit(value, type, false);
        if (type === Delim && value.charCodeAt(0) === REVERSESOLIDUS) {
          this.emit("\n", WhiteSpace, true);
        }
      },
      emit(value) {
        buffer += value;
      },
      result() {
        return buffer;
      }
    };
    if (options) {
      if (typeof options.decorator === "function") {
        handlers = options.decorator(handlers);
      }
      if (options.sourceMap) {
        handlers = generateSourceMap(handlers);
      }
      if (options.mode in token_before_exports) {
        handlers.tokenBefore = token_before_exports[options.mode];
      }
    }
    const publicApi = {
      node: (node2) => handlers.node(node2),
      children: processChildren,
      token: (type, value) => handlers.token(type, value),
      tokenize: (raw) => tokenize(raw, (type, start, end) => {
        handlers.token(
          type,
          raw.slice(start, end),
          start !== 0
          // suppress auto whitespace for internal value tokens
        );
      })
    };
    handlers.node(node);
    return handlers.result();
  };
}

// node_modules/css-tree/lib/convertor/create.js
function createConvertor(walk3) {
  return {
    fromPlainObject(ast) {
      walk3(ast, {
        enter(node) {
          if (node.children && node.children instanceof List === false) {
            node.children = new List().fromArray(node.children);
          }
        }
      });
      return ast;
    },
    toPlainObject(ast) {
      walk3(ast, {
        leave(node) {
          if (node.children && node.children instanceof List) {
            node.children = node.children.toArray();
          }
        }
      });
      return ast;
    }
  };
}

// node_modules/css-tree/lib/walker/create.js
var { hasOwnProperty: hasOwnProperty2 } = Object.prototype;
var noop = function() {
};
function ensureFunction(value) {
  return typeof value === "function" ? value : noop;
}
function invokeForType(fn, type) {
  return function(node, item, list) {
    if (node.type === type) {
      fn.call(this, node, item, list);
    }
  };
}
function getWalkersFromStructure(name50, nodeType) {
  const structure50 = nodeType.structure;
  const walkers = [];
  for (const key in structure50) {
    if (hasOwnProperty2.call(structure50, key) === false) {
      continue;
    }
    let fieldTypes = structure50[key];
    const walker = {
      name: key,
      type: false,
      nullable: false
    };
    if (!Array.isArray(fieldTypes)) {
      fieldTypes = [fieldTypes];
    }
    for (const fieldType of fieldTypes) {
      if (fieldType === null) {
        walker.nullable = true;
      } else if (typeof fieldType === "string") {
        walker.type = "node";
      } else if (Array.isArray(fieldType)) {
        walker.type = "list";
      }
    }
    if (walker.type) {
      walkers.push(walker);
    }
  }
  if (walkers.length) {
    return {
      context: nodeType.walkContext,
      fields: walkers
    };
  }
  return null;
}
function getTypesFromConfig(config) {
  const types = {};
  for (const name50 in config.node) {
    if (hasOwnProperty2.call(config.node, name50)) {
      const nodeType = config.node[name50];
      if (!nodeType.structure) {
        throw new Error("Missed `structure` field in `" + name50 + "` node type definition");
      }
      types[name50] = getWalkersFromStructure(name50, nodeType);
    }
  }
  return types;
}
function createTypeIterator(config, reverse) {
  const fields = config.fields.slice();
  const contextName = config.context;
  const useContext = typeof contextName === "string";
  if (reverse) {
    fields.reverse();
  }
  return function(node, context, walk3, walkReducer) {
    let prevContextValue;
    if (useContext) {
      prevContextValue = context[contextName];
      context[contextName] = node;
    }
    for (const field of fields) {
      const ref = node[field.name];
      if (!field.nullable || ref) {
        if (field.type === "list") {
          const breakWalk = reverse ? ref.reduceRight(walkReducer, false) : ref.reduce(walkReducer, false);
          if (breakWalk) {
            return true;
          }
        } else if (walk3(ref)) {
          return true;
        }
      }
    }
    if (useContext) {
      context[contextName] = prevContextValue;
    }
  };
}
function createFastTraveralMap({
  StyleSheet,
  Atrule,
  Rule,
  Block,
  DeclarationList
}) {
  return {
    Atrule: {
      StyleSheet,
      Atrule,
      Rule,
      Block
    },
    Rule: {
      StyleSheet,
      Atrule,
      Rule,
      Block
    },
    Declaration: {
      StyleSheet,
      Atrule,
      Rule,
      Block,
      DeclarationList
    }
  };
}
function createWalker(config) {
  const types = getTypesFromConfig(config);
  const iteratorsNatural = {};
  const iteratorsReverse = {};
  const breakWalk = Symbol("break-walk");
  const skipNode = Symbol("skip-node");
  for (const name50 in types) {
    if (hasOwnProperty2.call(types, name50) && types[name50] !== null) {
      iteratorsNatural[name50] = createTypeIterator(types[name50], false);
      iteratorsReverse[name50] = createTypeIterator(types[name50], true);
    }
  }
  const fastTraversalIteratorsNatural = createFastTraveralMap(iteratorsNatural);
  const fastTraversalIteratorsReverse = createFastTraveralMap(iteratorsReverse);
  const walk3 = function(root, options) {
    function walkNode(node, item, list) {
      const enterRet = enter.call(context, node, item, list);
      if (enterRet === breakWalk) {
        return true;
      }
      if (enterRet === skipNode) {
        return false;
      }
      if (iterators.hasOwnProperty(node.type)) {
        if (iterators[node.type](node, context, walkNode, walkReducer)) {
          return true;
        }
      }
      if (leave.call(context, node, item, list) === breakWalk) {
        return true;
      }
      return false;
    }
    let enter = noop;
    let leave = noop;
    let iterators = iteratorsNatural;
    let walkReducer = (ret, data, item, list) => ret || walkNode(data, item, list);
    const context = {
      break: breakWalk,
      skip: skipNode,
      root,
      stylesheet: null,
      atrule: null,
      atrulePrelude: null,
      rule: null,
      selector: null,
      block: null,
      declaration: null,
      function: null
    };
    if (typeof options === "function") {
      enter = options;
    } else if (options) {
      enter = ensureFunction(options.enter);
      leave = ensureFunction(options.leave);
      if (options.reverse) {
        iterators = iteratorsReverse;
      }
      if (options.visit) {
        if (fastTraversalIteratorsNatural.hasOwnProperty(options.visit)) {
          iterators = options.reverse ? fastTraversalIteratorsReverse[options.visit] : fastTraversalIteratorsNatural[options.visit];
        } else if (!types.hasOwnProperty(options.visit)) {
          throw new Error("Bad value `" + options.visit + "` for `visit` option (should be: " + Object.keys(types).sort().join(", ") + ")");
        }
        enter = invokeForType(enter, options.visit);
        leave = invokeForType(leave, options.visit);
      }
    }
    if (enter === noop && leave === noop) {
      throw new Error("Neither `enter` nor `leave` walker handler is set or both aren't a function");
    }
    walkNode(root);
  };
  walk3.break = breakWalk;
  walk3.skip = skipNode;
  walk3.find = function(ast, fn) {
    let found = null;
    walk3(ast, function(node, item, list) {
      if (fn.call(this, node, item, list)) {
        found = node;
        return breakWalk;
      }
    });
    return found;
  };
  walk3.findLast = function(ast, fn) {
    let found = null;
    walk3(ast, {
      reverse: true,
      enter(node, item, list) {
        if (fn.call(this, node, item, list)) {
          found = node;
          return breakWalk;
        }
      }
    });
    return found;
  };
  walk3.findAll = function(ast, fn) {
    const found = [];
    walk3(ast, function(node, item, list) {
      if (fn.call(this, node, item, list)) {
        found.push(node);
      }
    });
    return found;
  };
  return walk3;
}

// node_modules/css-tree/lib/definition-syntax/generate.js
function noop2(value) {
  return value;
}
function generateMultiplier(multiplier) {
  const { min, max, comma } = multiplier;
  if (min === 0 && max === 0) {
    return comma ? "#?" : "*";
  }
  if (min === 0 && max === 1) {
    return "?";
  }
  if (min === 1 && max === 0) {
    return comma ? "#" : "+";
  }
  if (min === 1 && max === 1) {
    return "";
  }
  return (comma ? "#" : "") + (min === max ? "{" + min + "}" : "{" + min + "," + (max !== 0 ? max : "") + "}");
}
function generateTypeOpts(node) {
  switch (node.type) {
    case "Range":
      return " [" + (node.min === null ? "-\u221E" : node.min) + "," + (node.max === null ? "\u221E" : node.max) + "]";
    default:
      throw new Error("Unknown node type `" + node.type + "`");
  }
}
function generateSequence(node, decorate, forceBraces, compact) {
  const combinator = node.combinator === " " || compact ? node.combinator : " " + node.combinator + " ";
  const result = node.terms.map((term) => internalGenerate(term, decorate, forceBraces, compact)).join(combinator);
  if (node.explicit || forceBraces) {
    return (compact || result[0] === "," ? "[" : "[ ") + result + (compact ? "]" : " ]");
  }
  return result;
}
function internalGenerate(node, decorate, forceBraces, compact) {
  let result;
  switch (node.type) {
    case "Group":
      result = generateSequence(node, decorate, forceBraces, compact) + (node.disallowEmpty ? "!" : "");
      break;
    case "Multiplier":
      return internalGenerate(node.term, decorate, forceBraces, compact) + decorate(generateMultiplier(node), node);
    case "Boolean":
      result = "<boolean-expr[" + internalGenerate(node.term, decorate, forceBraces, compact) + "]>";
      break;
    case "Type":
      result = "<" + node.name + (node.opts ? decorate(generateTypeOpts(node.opts), node.opts) : "") + ">";
      break;
    case "Property":
      result = "<'" + node.name + "'>";
      break;
    case "Keyword":
      result = node.name;
      break;
    case "AtKeyword":
      result = "@" + node.name;
      break;
    case "Function":
      result = node.name + "(";
      break;
    case "String":
    case "Token":
      result = node.value;
      break;
    case "Comma":
      result = ",";
      break;
    default:
      throw new Error("Unknown node type `" + node.type + "`");
  }
  return decorate(result, node);
}
function generate(node, options) {
  let decorate = noop2;
  let forceBraces = false;
  let compact = false;
  if (typeof options === "function") {
    decorate = options;
  } else if (options) {
    forceBraces = Boolean(options.forceBraces);
    compact = Boolean(options.compact);
    if (typeof options.decorate === "function") {
      decorate = options.decorate;
    }
  }
  return internalGenerate(node, decorate, forceBraces, compact);
}

// node_modules/css-tree/lib/lexer/error.js
var defaultLoc = { offset: 0, line: 1, column: 1 };
function locateMismatch(matchResult, node) {
  const tokens = matchResult.tokens;
  const longestMatch = matchResult.longestMatch;
  const mismatchNode = longestMatch < tokens.length ? tokens[longestMatch].node || null : null;
  const badNode = mismatchNode !== node ? mismatchNode : null;
  let mismatchOffset = 0;
  let mismatchLength = 0;
  let entries = 0;
  let css = "";
  let start;
  let end;
  for (let i = 0; i < tokens.length; i++) {
    const token = tokens[i].value;
    if (i === longestMatch) {
      mismatchLength = token.length;
      mismatchOffset = css.length;
    }
    if (badNode !== null && tokens[i].node === badNode) {
      if (i <= longestMatch) {
        entries++;
      } else {
        entries = 0;
      }
    }
    css += token;
  }
  if (longestMatch === tokens.length || entries > 1) {
    start = fromLoc(badNode || node, "end") || buildLoc(defaultLoc, css);
    end = buildLoc(start);
  } else {
    start = fromLoc(badNode, "start") || buildLoc(fromLoc(node, "start") || defaultLoc, css.slice(0, mismatchOffset));
    end = fromLoc(badNode, "end") || buildLoc(start, css.substr(mismatchOffset, mismatchLength));
  }
  return {
    css,
    mismatchOffset,
    mismatchLength,
    start,
    end
  };
}
function fromLoc(node, point) {
  const value = node && node.loc && node.loc[point];
  if (value) {
    return "line" in value ? buildLoc(value) : value;
  }
  return null;
}
function buildLoc({ offset, line, column }, extra) {
  const loc = {
    offset,
    line,
    column
  };
  if (extra) {
    const lines = extra.split(/\n|\r\n?|\f/);
    loc.offset += extra.length;
    loc.line += lines.length - 1;
    loc.column = lines.length === 1 ? loc.column + extra.length : lines.pop().length + 1;
  }
  return loc;
}
var SyntaxReferenceError = function(type, referenceName) {
  const error = createCustomError(
    "SyntaxReferenceError",
    type + (referenceName ? " `" + referenceName + "`" : "")
  );
  error.reference = referenceName;
  return error;
};
var SyntaxMatchError = function(message, syntax, node, matchResult) {
  const error = createCustomError("SyntaxMatchError", message);
  const {
    css,
    mismatchOffset,
    mismatchLength,
    start,
    end
  } = locateMismatch(matchResult, node);
  error.rawMessage = message;
  error.syntax = syntax ? generate(syntax) : "<generic>";
  error.css = css;
  error.mismatchOffset = mismatchOffset;
  error.mismatchLength = mismatchLength;
  error.message = message + "\n  syntax: " + error.syntax + "\n   value: " + (css || "<empty string>") + "\n  --------" + new Array(error.mismatchOffset + 1).join("-") + "^";
  Object.assign(error, start);
  error.loc = {
    source: node && node.loc && node.loc.source || "<unknown>",
    start,
    end
  };
  return error;
};

// node_modules/css-tree/lib/utils/names.js
var keywords = /* @__PURE__ */ new Map();
var properties = /* @__PURE__ */ new Map();
var HYPHENMINUS2 = 45;
var keyword = getKeywordDescriptor;
var property = getPropertyDescriptor;
function isCustomProperty(str, offset) {
  offset = offset || 0;
  return str.length - offset >= 2 && str.charCodeAt(offset) === HYPHENMINUS2 && str.charCodeAt(offset + 1) === HYPHENMINUS2;
}
function getVendorPrefix(str, offset) {
  offset = offset || 0;
  if (str.length - offset >= 3) {
    if (str.charCodeAt(offset) === HYPHENMINUS2 && str.charCodeAt(offset + 1) !== HYPHENMINUS2) {
      const secondDashIndex = str.indexOf("-", offset + 2);
      if (secondDashIndex !== -1) {
        return str.substring(offset, secondDashIndex + 1);
      }
    }
  }
  return "";
}
function getKeywordDescriptor(keyword2) {
  if (keywords.has(keyword2)) {
    return keywords.get(keyword2);
  }
  const name50 = keyword2.toLowerCase();
  let descriptor = keywords.get(name50);
  if (descriptor === void 0) {
    const custom = isCustomProperty(name50, 0);
    const vendor = !custom ? getVendorPrefix(name50, 0) : "";
    descriptor = Object.freeze({
      basename: name50.substr(vendor.length),
      name: name50,
      prefix: vendor,
      vendor,
      custom
    });
  }
  keywords.set(keyword2, descriptor);
  return descriptor;
}
function getPropertyDescriptor(property2) {
  if (properties.has(property2)) {
    return properties.get(property2);
  }
  let name50 = property2;
  let hack = property2[0];
  if (hack === "/") {
    hack = property2[1] === "/" ? "//" : "/";
  } else if (hack !== "_" && hack !== "*" && hack !== "$" && hack !== "#" && hack !== "+" && hack !== "&") {
    hack = "";
  }
  const custom = isCustomProperty(name50, hack.length);
  if (!custom) {
    name50 = name50.toLowerCase();
    if (properties.has(name50)) {
      const descriptor2 = properties.get(name50);
      properties.set(property2, descriptor2);
      return descriptor2;
    }
  }
  const vendor = !custom ? getVendorPrefix(name50, hack.length) : "";
  const prefix = name50.substr(0, hack.length + vendor.length);
  const descriptor = Object.freeze({
    basename: name50.substr(prefix.length),
    name: name50.substr(hack.length),
    hack,
    vendor,
    prefix,
    custom
  });
  properties.set(property2, descriptor);
  return descriptor;
}

// node_modules/css-tree/lib/lexer/generic-const.js
var cssWideKeywords = [
  "initial",
  "inherit",
  "unset",
  "revert",
  "revert-layer"
];

// node_modules/css-tree/lib/lexer/generic-an-plus-b.js
var PLUSSIGN2 = 43;
var HYPHENMINUS3 = 45;
var N2 = 110;
var DISALLOW_SIGN = true;
var ALLOW_SIGN = false;
function isDelim(token, code2) {
  return token !== null && token.type === Delim && token.value.charCodeAt(0) === code2;
}
function skipSC(token, offset, getNextToken) {
  while (token !== null && (token.type === WhiteSpace || token.type === Comment)) {
    token = getNextToken(++offset);
  }
  return offset;
}
function checkInteger(token, valueOffset, disallowSign, offset) {
  if (!token) {
    return 0;
  }
  const code2 = token.value.charCodeAt(valueOffset);
  if (code2 === PLUSSIGN2 || code2 === HYPHENMINUS3) {
    if (disallowSign) {
      return 0;
    }
    valueOffset++;
  }
  for (; valueOffset < token.value.length; valueOffset++) {
    if (!isDigit(token.value.charCodeAt(valueOffset))) {
      return 0;
    }
  }
  return offset + 1;
}
function consumeB(token, offset_, getNextToken) {
  let sign = false;
  let offset = skipSC(token, offset_, getNextToken);
  token = getNextToken(offset);
  if (token === null) {
    return offset_;
  }
  if (token.type !== Number2) {
    if (isDelim(token, PLUSSIGN2) || isDelim(token, HYPHENMINUS3)) {
      sign = true;
      offset = skipSC(getNextToken(++offset), offset, getNextToken);
      token = getNextToken(offset);
      if (token === null || token.type !== Number2) {
        return 0;
      }
    } else {
      return offset_;
    }
  }
  if (!sign) {
    const code2 = token.value.charCodeAt(0);
    if (code2 !== PLUSSIGN2 && code2 !== HYPHENMINUS3) {
      return 0;
    }
  }
  return checkInteger(token, sign ? 0 : 1, sign, offset);
}
function anPlusB(token, getNextToken) {
  let offset = 0;
  if (!token) {
    return 0;
  }
  if (token.type === Number2) {
    return checkInteger(token, 0, ALLOW_SIGN, offset);
  } else if (token.type === Ident && token.value.charCodeAt(0) === HYPHENMINUS3) {
    if (!cmpChar(token.value, 1, N2)) {
      return 0;
    }
    switch (token.value.length) {
      // -n
      // -n <signed-integer>
      // -n ['+' | '-'] <signless-integer>
      case 2:
        return consumeB(getNextToken(++offset), offset, getNextToken);
      // -n- <signless-integer>
      case 3:
        if (token.value.charCodeAt(2) !== HYPHENMINUS3) {
          return 0;
        }
        offset = skipSC(getNextToken(++offset), offset, getNextToken);
        token = getNextToken(offset);
        return checkInteger(token, 0, DISALLOW_SIGN, offset);
      // <dashndashdigit-ident>
      default:
        if (token.value.charCodeAt(2) !== HYPHENMINUS3) {
          return 0;
        }
        return checkInteger(token, 3, DISALLOW_SIGN, offset);
    }
  } else if (token.type === Ident || isDelim(token, PLUSSIGN2) && getNextToken(offset + 1).type === Ident) {
    if (token.type !== Ident) {
      token = getNextToken(++offset);
    }
    if (token === null || !cmpChar(token.value, 0, N2)) {
      return 0;
    }
    switch (token.value.length) {
      // '+'? n
      // '+'? n <signed-integer>
      // '+'? n ['+' | '-'] <signless-integer>
      case 1:
        return consumeB(getNextToken(++offset), offset, getNextToken);
      // '+'? n- <signless-integer>
      case 2:
        if (token.value.charCodeAt(1) !== HYPHENMINUS3) {
          return 0;
        }
        offset = skipSC(getNextToken(++offset), offset, getNextToken);
        token = getNextToken(offset);
        return checkInteger(token, 0, DISALLOW_SIGN, offset);
      // '+'? <ndashdigit-ident>
      default:
        if (token.value.charCodeAt(1) !== HYPHENMINUS3) {
          return 0;
        }
        return checkInteger(token, 2, DISALLOW_SIGN, offset);
    }
  } else if (token.type === Dimension) {
    let code2 = token.value.charCodeAt(0);
    let sign = code2 === PLUSSIGN2 || code2 === HYPHENMINUS3 ? 1 : 0;
    let i = sign;
    for (; i < token.value.length; i++) {
      if (!isDigit(token.value.charCodeAt(i))) {
        break;
      }
    }
    if (i === sign) {
      return 0;
    }
    if (!cmpChar(token.value, i, N2)) {
      return 0;
    }
    if (i + 1 === token.value.length) {
      return consumeB(getNextToken(++offset), offset, getNextToken);
    } else {
      if (token.value.charCodeAt(i + 1) !== HYPHENMINUS3) {
        return 0;
      }
      if (i + 2 === token.value.length) {
        offset = skipSC(getNextToken(++offset), offset, getNextToken);
        token = getNextToken(offset);
        return checkInteger(token, 0, DISALLOW_SIGN, offset);
      } else {
        return checkInteger(token, i + 2, DISALLOW_SIGN, offset);
      }
    }
  }
  return 0;
}

// node_modules/css-tree/lib/lexer/generic-urange.js
var PLUSSIGN3 = 43;
var HYPHENMINUS4 = 45;
var QUESTIONMARK = 63;
var U = 117;
function isDelim2(token, code2) {
  return token !== null && token.type === Delim && token.value.charCodeAt(0) === code2;
}
function startsWith(token, code2) {
  return token.value.charCodeAt(0) === code2;
}
function hexSequence(token, offset, allowDash) {
  let hexlen = 0;
  for (let pos = offset; pos < token.value.length; pos++) {
    const code2 = token.value.charCodeAt(pos);
    if (code2 === HYPHENMINUS4 && allowDash && hexlen !== 0) {
      hexSequence(token, offset + hexlen + 1, false);
      return 6;
    }
    if (!isHexDigit(code2)) {
      return 0;
    }
    if (++hexlen > 6) {
      return 0;
    }
    ;
  }
  return hexlen;
}
function withQuestionMarkSequence(consumed, length2, getNextToken) {
  if (!consumed) {
    return 0;
  }
  while (isDelim2(getNextToken(length2), QUESTIONMARK)) {
    if (++consumed > 6) {
      return 0;
    }
    length2++;
  }
  return length2;
}
function urange(token, getNextToken) {
  let length2 = 0;
  if (token === null || token.type !== Ident || !cmpChar(token.value, 0, U)) {
    return 0;
  }
  token = getNextToken(++length2);
  if (token === null) {
    return 0;
  }
  if (isDelim2(token, PLUSSIGN3)) {
    token = getNextToken(++length2);
    if (token === null) {
      return 0;
    }
    if (token.type === Ident) {
      return withQuestionMarkSequence(hexSequence(token, 0, true), ++length2, getNextToken);
    }
    if (isDelim2(token, QUESTIONMARK)) {
      return withQuestionMarkSequence(1, ++length2, getNextToken);
    }
    return 0;
  }
  if (token.type === Number2) {
    const consumedHexLength = hexSequence(token, 1, true);
    if (consumedHexLength === 0) {
      return 0;
    }
    token = getNextToken(++length2);
    if (token === null) {
      return length2;
    }
    if (token.type === Dimension || token.type === Number2) {
      if (!startsWith(token, HYPHENMINUS4) || !hexSequence(token, 1, false)) {
        return 0;
      }
      return length2 + 1;
    }
    return withQuestionMarkSequence(consumedHexLength, length2, getNextToken);
  }
  if (token.type === Dimension) {
    return withQuestionMarkSequence(hexSequence(token, 1, true), ++length2, getNextToken);
  }
  return 0;
}

// node_modules/css-tree/lib/lexer/generic.js
var calcFunctionNames = [
  "calc(",
  "-moz-calc(",
  "-webkit-calc("
];
var comparisonFunctionNames = [
  "min(",
  "max(",
  "clamp("
];
var steppedValueFunctionNames = [
  "round(",
  "mod(",
  "rem("
];
var trigNumberFunctionNames = [
  "sin(",
  "cos(",
  "tan("
];
var trigAngleFunctionNames = [
  "asin(",
  "acos(",
  "atan(",
  "atan2("
];
var otherNumberFunctionNames = [
  "pow(",
  "sqrt(",
  "log(",
  "exp(",
  "sign("
];
var expNumberDimensionPercentageFunctionNames = [
  "hypot("
];
var signFunctionNames = [
  "abs("
];
var numberFunctionNames = [
  ...calcFunctionNames,
  ...comparisonFunctionNames,
  ...steppedValueFunctionNames,
  ...trigNumberFunctionNames,
  ...otherNumberFunctionNames,
  ...expNumberDimensionPercentageFunctionNames,
  ...signFunctionNames
];
var percentageFunctionNames = [
  ...calcFunctionNames,
  ...comparisonFunctionNames,
  ...steppedValueFunctionNames,
  ...expNumberDimensionPercentageFunctionNames,
  ...signFunctionNames
];
var dimensionFunctionNames = [
  ...calcFunctionNames,
  ...comparisonFunctionNames,
  ...steppedValueFunctionNames,
  ...trigAngleFunctionNames,
  ...expNumberDimensionPercentageFunctionNames,
  ...signFunctionNames
];
var balancePair2 = /* @__PURE__ */ new Map([
  [Function2, RightParenthesis],
  [LeftParenthesis, RightParenthesis],
  [LeftSquareBracket, RightSquareBracket],
  [LeftCurlyBracket, RightCurlyBracket]
]);
function charCodeAt(str, index) {
  return index < str.length ? str.charCodeAt(index) : 0;
}
function eqStr(actual, expected) {
  return cmpStr(actual, 0, actual.length, expected);
}
function eqStrAny(actual, expected) {
  for (let i = 0; i < expected.length; i++) {
    if (eqStr(actual, expected[i])) {
      return true;
    }
  }
  return false;
}
function isPostfixIeHack(str, offset) {
  if (offset !== str.length - 2) {
    return false;
  }
  return charCodeAt(str, offset) === 92 && // U+005C REVERSE SOLIDUS (\)
  isDigit(charCodeAt(str, offset + 1));
}
function outOfRange(opts, value, numEnd) {
  if (opts && opts.type === "Range") {
    const num = Number(
      numEnd !== void 0 && numEnd !== value.length ? value.substr(0, numEnd) : value
    );
    if (isNaN(num)) {
      return true;
    }
    if (opts.min !== null && num < opts.min && typeof opts.min !== "string") {
      return true;
    }
    if (opts.max !== null && num > opts.max && typeof opts.max !== "string") {
      return true;
    }
  }
  return false;
}
function consumeFunction(token, getNextToken) {
  let balanceCloseType = 0;
  let balanceStash = [];
  let length2 = 0;
  scan:
    do {
      switch (token.type) {
        case RightCurlyBracket:
        case RightParenthesis:
        case RightSquareBracket:
          if (token.type !== balanceCloseType) {
            break scan;
          }
          balanceCloseType = balanceStash.pop();
          if (balanceStash.length === 0) {
            length2++;
            break scan;
          }
          break;
        case Function2:
        case LeftParenthesis:
        case LeftSquareBracket:
        case LeftCurlyBracket:
          balanceStash.push(balanceCloseType);
          balanceCloseType = balancePair2.get(token.type);
          break;
      }
      length2++;
    } while (token = getNextToken(length2));
  return length2;
}
function math(next, functionNames) {
  return function(token, getNextToken, opts) {
    if (token === null) {
      return 0;
    }
    if (token.type === Function2 && eqStrAny(token.value, functionNames)) {
      return consumeFunction(token, getNextToken);
    }
    return next(token, getNextToken, opts);
  };
}
function tokenType(expectedTokenType) {
  return function(token) {
    if (token === null || token.type !== expectedTokenType) {
      return 0;
    }
    return 1;
  };
}
function customIdent(token) {
  if (token === null || token.type !== Ident) {
    return 0;
  }
  const name50 = token.value.toLowerCase();
  if (eqStrAny(name50, cssWideKeywords)) {
    return 0;
  }
  if (eqStr(name50, "default")) {
    return 0;
  }
  return 1;
}
function dashedIdent(token) {
  if (token === null || token.type !== Ident) {
    return 0;
  }
  if (charCodeAt(token.value, 0) !== 45 || charCodeAt(token.value, 1) !== 45) {
    return 0;
  }
  return 1;
}
function customPropertyName(token) {
  if (!dashedIdent(token)) {
    return 0;
  }
  if (token.value === "--") {
    return 0;
  }
  return 1;
}
function hexColor(token) {
  if (token === null || token.type !== Hash) {
    return 0;
  }
  const length2 = token.value.length;
  if (length2 !== 4 && length2 !== 5 && length2 !== 7 && length2 !== 9) {
    return 0;
  }
  for (let i = 1; i < length2; i++) {
    if (!isHexDigit(charCodeAt(token.value, i))) {
      return 0;
    }
  }
  return 1;
}
function idSelector(token) {
  if (token === null || token.type !== Hash) {
    return 0;
  }
  if (!isIdentifierStart(charCodeAt(token.value, 1), charCodeAt(token.value, 2), charCodeAt(token.value, 3))) {
    return 0;
  }
  return 1;
}
function declarationValue(token, getNextToken) {
  if (!token) {
    return 0;
  }
  let balanceCloseType = 0;
  let balanceStash = [];
  let length2 = 0;
  scan:
    do {
      switch (token.type) {
        // ... <bad-string-token>, <bad-url-token>,
        case BadString:
        case BadUrl:
          break scan;
        // ... unmatched <)-token>, <]-token>, or <}-token>,
        case RightCurlyBracket:
        case RightParenthesis:
        case RightSquareBracket:
          if (token.type !== balanceCloseType) {
            break scan;
          }
          balanceCloseType = balanceStash.pop();
          break;
        // ... or top-level <semicolon-token> tokens
        case Semicolon:
          if (balanceCloseType === 0) {
            break scan;
          }
          break;
        // ... or <delim-token> tokens with a value of "!"
        case Delim:
          if (balanceCloseType === 0 && token.value === "!") {
            break scan;
          }
          break;
        case Function2:
        case LeftParenthesis:
        case LeftSquareBracket:
        case LeftCurlyBracket:
          balanceStash.push(balanceCloseType);
          balanceCloseType = balancePair2.get(token.type);
          break;
      }
      length2++;
    } while (token = getNextToken(length2));
  return length2;
}
function anyValue(token, getNextToken) {
  if (!token) {
    return 0;
  }
  let balanceCloseType = 0;
  let balanceStash = [];
  let length2 = 0;
  scan:
    do {
      switch (token.type) {
        // ... does not contain <bad-string-token>, <bad-url-token>,
        case BadString:
        case BadUrl:
          break scan;
        // ... unmatched <)-token>, <]-token>, or <}-token>,
        case RightCurlyBracket:
        case RightParenthesis:
        case RightSquareBracket:
          if (token.type !== balanceCloseType) {
            break scan;
          }
          balanceCloseType = balanceStash.pop();
          break;
        case Function2:
        case LeftParenthesis:
        case LeftSquareBracket:
        case LeftCurlyBracket:
          balanceStash.push(balanceCloseType);
          balanceCloseType = balancePair2.get(token.type);
          break;
      }
      length2++;
    } while (token = getNextToken(length2));
  return length2;
}
function dimension(type) {
  if (type) {
    type = new Set(type);
  }
  return function(token, getNextToken, opts) {
    if (token === null || token.type !== Dimension) {
      return 0;
    }
    const numberEnd = consumeNumber(token.value, 0);
    if (type !== null) {
      const reverseSolidusOffset = token.value.indexOf("\\", numberEnd);
      const unit = reverseSolidusOffset === -1 || !isPostfixIeHack(token.value, reverseSolidusOffset) ? token.value.substr(numberEnd) : token.value.substring(numberEnd, reverseSolidusOffset);
      if (type.has(unit.toLowerCase()) === false) {
        return 0;
      }
    }
    if (outOfRange(opts, token.value, numberEnd)) {
      return 0;
    }
    return 1;
  };
}
function percentage(token, getNextToken, opts) {
  if (token === null || token.type !== Percentage) {
    return 0;
  }
  if (outOfRange(opts, token.value, token.value.length - 1)) {
    return 0;
  }
  return 1;
}
function zero(next) {
  if (typeof next !== "function") {
    next = function() {
      return 0;
    };
  }
  return function(token, getNextToken, opts) {
    if (token !== null && token.type === Number2) {
      if (Number(token.value) === 0) {
        return 1;
      }
    }
    return next(token, getNextToken, opts);
  };
}
function number(token, getNextToken, opts) {
  if (token === null) {
    return 0;
  }
  const numberEnd = consumeNumber(token.value, 0);
  const isNumber = numberEnd === token.value.length;
  if (!isNumber && !isPostfixIeHack(token.value, numberEnd)) {
    return 0;
  }
  if (outOfRange(opts, token.value, numberEnd)) {
    return 0;
  }
  return 1;
}
function integer(token, getNextToken, opts) {
  if (token === null || token.type !== Number2) {
    return 0;
  }
  let i = charCodeAt(token.value, 0) === 43 || // U+002B PLUS SIGN (+)
  charCodeAt(token.value, 0) === 45 ? 1 : 0;
  for (; i < token.value.length; i++) {
    if (!isDigit(charCodeAt(token.value, i))) {
      return 0;
    }
  }
  if (outOfRange(opts, token.value, i)) {
    return 0;
  }
  return 1;
}
var tokenTypes = {
  "ident-token": tokenType(Ident),
  "function-token": tokenType(Function2),
  "at-keyword-token": tokenType(AtKeyword),
  "hash-token": tokenType(Hash),
  "string-token": tokenType(String2),
  "bad-string-token": tokenType(BadString),
  "url-token": tokenType(Url),
  "bad-url-token": tokenType(BadUrl),
  "delim-token": tokenType(Delim),
  "number-token": tokenType(Number2),
  "percentage-token": tokenType(Percentage),
  "dimension-token": tokenType(Dimension),
  "whitespace-token": tokenType(WhiteSpace),
  "CDO-token": tokenType(CDO),
  "CDC-token": tokenType(CDC),
  "colon-token": tokenType(Colon),
  "semicolon-token": tokenType(Semicolon),
  "comma-token": tokenType(Comma),
  "[-token": tokenType(LeftSquareBracket),
  "]-token": tokenType(RightSquareBracket),
  "(-token": tokenType(LeftParenthesis),
  ")-token": tokenType(RightParenthesis),
  "{-token": tokenType(LeftCurlyBracket),
  "}-token": tokenType(RightCurlyBracket)
};
var productionTypes = {
  // token type aliases
  "string": tokenType(String2),
  "ident": tokenType(Ident),
  // percentage
  "percentage": math(percentage, percentageFunctionNames),
  // numeric
  "zero": zero(),
  "number": math(number, numberFunctionNames),
  "integer": math(integer, numberFunctionNames),
  // complex types
  "custom-ident": customIdent,
  "dashed-ident": dashedIdent,
  "custom-property-name": customPropertyName,
  "hex-color": hexColor,
  "id-selector": idSelector,
  // element( <id-selector> )
  "an-plus-b": anPlusB,
  "urange": urange,
  "declaration-value": declarationValue,
  "any-value": anyValue
};
var unitGroups = [
  "length",
  "angle",
  "time",
  "frequency",
  "resolution",
  "flex",
  "decibel",
  "semitones"
];
function createDemensionTypes(units) {
  const {
    angle: angle2,
    decibel: decibel2,
    frequency: frequency2,
    flex: flex2,
    length: length2,
    resolution: resolution2,
    semitones: semitones2,
    time: time2
  } = units || {};
  return {
    "dimension": math(dimension(null), dimensionFunctionNames),
    "angle": math(dimension(angle2), dimensionFunctionNames),
    "decibel": math(dimension(decibel2), dimensionFunctionNames),
    "frequency": math(dimension(frequency2), dimensionFunctionNames),
    "flex": math(dimension(flex2), dimensionFunctionNames),
    "length": math(zero(dimension(length2)), dimensionFunctionNames),
    "resolution": math(dimension(resolution2), dimensionFunctionNames),
    "semitones": math(dimension(semitones2), dimensionFunctionNames),
    "time": math(dimension(time2), dimensionFunctionNames)
  };
}
function createAttrUnit(units) {
  const unitSet = /* @__PURE__ */ new Set();
  for (const group of unitGroups) {
    if (Array.isArray(units[group])) {
      for (const unit of units[group]) {
        unitSet.add(unit.toLowerCase());
      }
    }
  }
  return function attrUnit(token) {
    if (token === null) {
      return 0;
    }
    if (token.type === Delim && token.value === "%") {
      return 1;
    }
    if (token.type === Ident && unitSet.has(token.value.toLowerCase())) {
      return 1;
    }
    return 0;
  };
}
function createGenericTypes(units) {
  return {
    ...tokenTypes,
    ...productionTypes,
    ...createDemensionTypes(units),
    "attr-unit": createAttrUnit(units)
  };
}

// node_modules/css-tree/lib/lexer/units.js
var units_exports = {};
__export(units_exports, {
  angle: () => angle,
  decibel: () => decibel,
  flex: () => flex,
  frequency: () => frequency,
  length: () => length,
  resolution: () => resolution,
  semitones: () => semitones,
  time: () => time
});
var length = [
  // absolute length units https://www.w3.org/TR/css-values-3/#lengths
  "cm",
  "mm",
  "q",
  "in",
  "pt",
  "pc",
  "px",
  // font-relative length units https://drafts.csswg.org/css-values-4/#font-relative-lengths
  "em",
  "rem",
  "ex",
  "rex",
  "cap",
  "rcap",
  "ch",
  "rch",
  "ic",
  "ric",
  "lh",
  "rlh",
  // viewport-percentage lengths https://drafts.csswg.org/css-values-4/#viewport-relative-lengths
  "vw",
  "svw",
  "lvw",
  "dvw",
  "vh",
  "svh",
  "lvh",
  "dvh",
  "vi",
  "svi",
  "lvi",
  "dvi",
  "vb",
  "svb",
  "lvb",
  "dvb",
  "vmin",
  "svmin",
  "lvmin",
  "dvmin",
  "vmax",
  "svmax",
  "lvmax",
  "dvmax",
  // container relative lengths https://drafts.csswg.org/css-contain-3/#container-lengths
  "cqw",
  "cqh",
  "cqi",
  "cqb",
  "cqmin",
  "cqmax"
];
var angle = ["deg", "grad", "rad", "turn"];
var time = ["s", "ms"];
var frequency = ["hz", "khz"];
var resolution = ["dpi", "dpcm", "dppx", "x"];
var flex = ["fr"];
var decibel = ["db"];
var semitones = ["st"];

// node_modules/css-tree/lib/definition-syntax/SyntaxError.js
function SyntaxError3(message, input, offset) {
  return Object.assign(createCustomError("SyntaxError", message), {
    input,
    offset,
    rawMessage: message,
    message: message + "\n  " + input + "\n--" + new Array((offset || input.length) + 1).join("-") + "^"
  });
}

// node_modules/css-tree/lib/definition-syntax/scanner.js
var TAB = 9;
var N3 = 10;
var F2 = 12;
var R2 = 13;
var SPACE = 32;
var NAME_CHAR = new Uint8Array(128).map(
  (_, idx) => /[a-zA-Z0-9\-]/.test(String.fromCharCode(idx)) ? 1 : 0
);
var Scanner = class {
  constructor(str) {
    this.str = str;
    this.pos = 0;
  }
  charCodeAt(pos) {
    return pos < this.str.length ? this.str.charCodeAt(pos) : 0;
  }
  charCode() {
    return this.charCodeAt(this.pos);
  }
  isNameCharCode(code2 = this.charCode()) {
    return code2 < 128 && NAME_CHAR[code2] === 1;
  }
  nextCharCode() {
    return this.charCodeAt(this.pos + 1);
  }
  nextNonWsCode(pos) {
    return this.charCodeAt(this.findWsEnd(pos));
  }
  skipWs() {
    this.pos = this.findWsEnd(this.pos);
  }
  findWsEnd(pos) {
    for (; pos < this.str.length; pos++) {
      const code2 = this.str.charCodeAt(pos);
      if (code2 !== R2 && code2 !== N3 && code2 !== F2 && code2 !== SPACE && code2 !== TAB) {
        break;
      }
    }
    return pos;
  }
  substringToPos(end) {
    return this.str.substring(this.pos, this.pos = end);
  }
  eat(code2) {
    if (this.charCode() !== code2) {
      this.error("Expect `" + String.fromCharCode(code2) + "`");
    }
    this.pos++;
  }
  peek() {
    return this.pos < this.str.length ? this.str.charAt(this.pos++) : "";
  }
  error(message) {
    throw new SyntaxError3(message, this.str, this.pos);
  }
  scanSpaces() {
    return this.substringToPos(this.findWsEnd(this.pos));
  }
  scanWord() {
    let end = this.pos;
    for (; end < this.str.length; end++) {
      const code2 = this.str.charCodeAt(end);
      if (code2 >= 128 || NAME_CHAR[code2] === 0) {
        break;
      }
    }
    if (this.pos === end) {
      this.error("Expect a keyword");
    }
    return this.substringToPos(end);
  }
  scanNumber() {
    let end = this.pos;
    for (; end < this.str.length; end++) {
      const code2 = this.str.charCodeAt(end);
      if (code2 < 48 || code2 > 57) {
        break;
      }
    }
    if (this.pos === end) {
      this.error("Expect a number");
    }
    return this.substringToPos(end);
  }
  scanString() {
    const end = this.str.indexOf("'", this.pos + 1);
    if (end === -1) {
      this.pos = this.str.length;
      this.error("Expect an apostrophe");
    }
    return this.substringToPos(end + 1);
  }
};

// node_modules/css-tree/lib/definition-syntax/parse.js
var TAB2 = 9;
var N4 = 10;
var F3 = 12;
var R3 = 13;
var SPACE2 = 32;
var EXCLAMATIONMARK2 = 33;
var NUMBERSIGN2 = 35;
var AMPERSAND = 38;
var APOSTROPHE = 39;
var LEFTPARENTHESIS = 40;
var RIGHTPARENTHESIS = 41;
var ASTERISK = 42;
var PLUSSIGN4 = 43;
var COMMA = 44;
var HYPERMINUS = 45;
var LESSTHANSIGN = 60;
var GREATERTHANSIGN = 62;
var QUESTIONMARK2 = 63;
var COMMERCIALAT = 64;
var LEFTSQUAREBRACKET = 91;
var RIGHTSQUAREBRACKET = 93;
var LEFTCURLYBRACKET2 = 123;
var VERTICALLINE = 124;
var RIGHTCURLYBRACKET = 125;
var INFINITY = 8734;
var COMBINATOR_PRECEDENCE = {
  " ": 1,
  "&&": 2,
  "||": 3,
  "|": 4
};
function readMultiplierRange(scanner) {
  let min = null;
  let max = null;
  scanner.eat(LEFTCURLYBRACKET2);
  scanner.skipWs();
  min = scanner.scanNumber(scanner);
  scanner.skipWs();
  if (scanner.charCode() === COMMA) {
    scanner.pos++;
    scanner.skipWs();
    if (scanner.charCode() !== RIGHTCURLYBRACKET) {
      max = scanner.scanNumber(scanner);
      scanner.skipWs();
    }
  } else {
    max = min;
  }
  scanner.eat(RIGHTCURLYBRACKET);
  return {
    min: Number(min),
    max: max ? Number(max) : 0
  };
}
function readMultiplier(scanner) {
  let range = null;
  let comma = false;
  switch (scanner.charCode()) {
    case ASTERISK:
      scanner.pos++;
      range = {
        min: 0,
        max: 0
      };
      break;
    case PLUSSIGN4:
      scanner.pos++;
      range = {
        min: 1,
        max: 0
      };
      break;
    case QUESTIONMARK2:
      scanner.pos++;
      range = {
        min: 0,
        max: 1
      };
      break;
    case NUMBERSIGN2:
      scanner.pos++;
      comma = true;
      if (scanner.charCode() === LEFTCURLYBRACKET2) {
        range = readMultiplierRange(scanner);
      } else if (scanner.charCode() === QUESTIONMARK2) {
        scanner.pos++;
        range = {
          min: 0,
          max: 0
        };
      } else {
        range = {
          min: 1,
          max: 0
        };
      }
      break;
    case LEFTCURLYBRACKET2:
      range = readMultiplierRange(scanner);
      break;
    default:
      return null;
  }
  return {
    type: "Multiplier",
    comma,
    min: range.min,
    max: range.max,
    term: null
  };
}
function maybeMultiplied(scanner, node) {
  const multiplier = readMultiplier(scanner);
  if (multiplier !== null) {
    multiplier.term = node;
    if (scanner.charCode() === NUMBERSIGN2 && scanner.charCodeAt(scanner.pos - 1) === PLUSSIGN4) {
      return maybeMultiplied(scanner, multiplier);
    }
    if (scanner.charCode() === QUESTIONMARK2 && scanner.charCodeAt(scanner.pos - 1) === RIGHTCURLYBRACKET) {
      return maybeMultiplied(scanner, multiplier);
    }
    return multiplier;
  }
  return node;
}
function maybeToken(scanner) {
  const ch = scanner.peek();
  if (ch === "") {
    return null;
  }
  return maybeMultiplied(scanner, {
    type: "Token",
    value: ch
  });
}
function readProperty(scanner) {
  let name50;
  scanner.eat(LESSTHANSIGN);
  scanner.eat(APOSTROPHE);
  name50 = scanner.scanWord();
  scanner.eat(APOSTROPHE);
  scanner.eat(GREATERTHANSIGN);
  return maybeMultiplied(scanner, {
    type: "Property",
    name: name50
  });
}
function readTypeRange(scanner) {
  let min = null;
  let max = null;
  let sign = 1;
  scanner.eat(LEFTSQUAREBRACKET);
  if (scanner.charCode() === HYPERMINUS) {
    scanner.peek();
    sign = -1;
  }
  if (sign == -1 && scanner.charCode() === INFINITY) {
    scanner.peek();
  } else {
    min = sign * Number(scanner.scanNumber(scanner));
    if (scanner.isNameCharCode()) {
      min += scanner.scanWord();
    }
  }
  scanner.skipWs();
  scanner.eat(COMMA);
  scanner.skipWs();
  if (scanner.charCode() === INFINITY) {
    scanner.peek();
  } else {
    sign = 1;
    if (scanner.charCode() === HYPERMINUS) {
      scanner.peek();
      sign = -1;
    }
    max = sign * Number(scanner.scanNumber(scanner));
    if (scanner.isNameCharCode()) {
      max += scanner.scanWord();
    }
  }
  scanner.eat(RIGHTSQUAREBRACKET);
  return {
    type: "Range",
    min,
    max
  };
}
function readType(scanner) {
  let name50;
  let opts = null;
  scanner.eat(LESSTHANSIGN);
  name50 = scanner.scanWord();
  if (name50 === "boolean-expr") {
    scanner.eat(LEFTSQUAREBRACKET);
    const implicitGroup = readImplicitGroup(scanner, RIGHTSQUAREBRACKET);
    scanner.eat(RIGHTSQUAREBRACKET);
    scanner.eat(GREATERTHANSIGN);
    return maybeMultiplied(scanner, {
      type: "Boolean",
      term: implicitGroup.terms.length === 1 ? implicitGroup.terms[0] : implicitGroup
    });
  }
  if (scanner.charCode() === LEFTPARENTHESIS && scanner.nextCharCode() === RIGHTPARENTHESIS) {
    scanner.pos += 2;
    name50 += "()";
  }
  if (scanner.charCodeAt(scanner.findWsEnd(scanner.pos)) === LEFTSQUAREBRACKET) {
    scanner.skipWs();
    opts = readTypeRange(scanner);
  }
  scanner.eat(GREATERTHANSIGN);
  return maybeMultiplied(scanner, {
    type: "Type",
    name: name50,
    opts
  });
}
function readKeywordOrFunction(scanner) {
  const name50 = scanner.scanWord();
  if (scanner.charCode() === LEFTPARENTHESIS) {
    scanner.pos++;
    return {
      type: "Function",
      name: name50
    };
  }
  return maybeMultiplied(scanner, {
    type: "Keyword",
    name: name50
  });
}
function regroupTerms(terms, combinators) {
  function createGroup(terms2, combinator2) {
    return {
      type: "Group",
      terms: terms2,
      combinator: combinator2,
      disallowEmpty: false,
      explicit: false
    };
  }
  let combinator;
  combinators = Object.keys(combinators).sort((a, b) => COMBINATOR_PRECEDENCE[a] - COMBINATOR_PRECEDENCE[b]);
  while (combinators.length > 0) {
    combinator = combinators.shift();
    let i = 0;
    let subgroupStart = 0;
    for (; i < terms.length; i++) {
      const term = terms[i];
      if (term.type === "Combinator") {
        if (term.value === combinator) {
          if (subgroupStart === -1) {
            subgroupStart = i - 1;
          }
          terms.splice(i, 1);
          i--;
        } else {
          if (subgroupStart !== -1 && i - subgroupStart > 1) {
            terms.splice(
              subgroupStart,
              i - subgroupStart,
              createGroup(terms.slice(subgroupStart, i), combinator)
            );
            i = subgroupStart + 1;
          }
          subgroupStart = -1;
        }
      }
    }
    if (subgroupStart !== -1 && combinators.length) {
      terms.splice(
        subgroupStart,
        i - subgroupStart,
        createGroup(terms.slice(subgroupStart, i), combinator)
      );
    }
  }
  return combinator;
}
function readImplicitGroup(scanner, stopCharCode = -1) {
  const combinators = /* @__PURE__ */ Object.create(null);
  const terms = [];
  let prevToken = null;
  let prevTokenPos = scanner.pos;
  let prevTokenIsFunction = false;
  while (scanner.charCode() !== stopCharCode) {
    let token = prevTokenIsFunction ? readImplicitGroup(scanner, RIGHTPARENTHESIS) : peek(scanner);
    if (!token) {
      break;
    }
    if (token.type === "Spaces") {
      continue;
    }
    if (prevTokenIsFunction) {
      if (token.terms.length === 0) {
        prevTokenIsFunction = false;
        continue;
      }
      if (token.combinator === " ") {
        while (token.terms.length > 1) {
          combinators[" "] = true;
          terms.push({
            type: "Combinator",
            value: " "
          }, token.terms.shift());
        }
        token = token.terms[0];
      }
    }
    if (token.type === "Combinator") {
      if (prevToken === null || prevToken.type === "Combinator") {
        scanner.pos = prevTokenPos;
        scanner.error("Unexpected combinator");
      }
      combinators[token.value] = true;
    } else if (prevToken !== null && prevToken.type !== "Combinator") {
      combinators[" "] = true;
      terms.push({
        type: "Combinator",
        value: " "
      });
    }
    terms.push(token);
    prevToken = token;
    prevTokenPos = scanner.pos;
    prevTokenIsFunction = token.type === "Function";
  }
  if (prevToken !== null && prevToken.type === "Combinator") {
    scanner.pos -= prevTokenPos;
    scanner.error("Unexpected combinator");
  }
  return {
    type: "Group",
    terms,
    combinator: regroupTerms(terms, combinators) || " ",
    disallowEmpty: false,
    explicit: false
  };
}
function readGroup(scanner) {
  let result;
  scanner.eat(LEFTSQUAREBRACKET);
  result = readImplicitGroup(scanner, RIGHTSQUAREBRACKET);
  scanner.eat(RIGHTSQUAREBRACKET);
  result.explicit = true;
  if (scanner.charCode() === EXCLAMATIONMARK2) {
    scanner.pos++;
    result.disallowEmpty = true;
  }
  return result;
}
function peek(scanner) {
  let code2 = scanner.charCode();
  switch (code2) {
    case RIGHTSQUAREBRACKET:
      break;
    case LEFTSQUAREBRACKET:
      return maybeMultiplied(scanner, readGroup(scanner));
    case LESSTHANSIGN:
      return scanner.nextCharCode() === APOSTROPHE ? readProperty(scanner) : readType(scanner);
    case VERTICALLINE:
      return {
        type: "Combinator",
        value: scanner.substringToPos(
          scanner.pos + (scanner.nextCharCode() === VERTICALLINE ? 2 : 1)
        )
      };
    case AMPERSAND:
      scanner.pos++;
      scanner.eat(AMPERSAND);
      return {
        type: "Combinator",
        value: "&&"
      };
    case COMMA:
      scanner.pos++;
      return {
        type: "Comma"
      };
    case APOSTROPHE:
      return maybeMultiplied(scanner, {
        type: "String",
        value: scanner.scanString()
      });
    case SPACE2:
    case TAB2:
    case N4:
    case R3:
    case F3:
      return {
        type: "Spaces",
        value: scanner.scanSpaces()
      };
    case COMMERCIALAT:
      code2 = scanner.nextCharCode();
      if (scanner.isNameCharCode(code2)) {
        scanner.pos++;
        return {
          type: "AtKeyword",
          name: scanner.scanWord()
        };
      }
      return maybeToken(scanner);
    case ASTERISK:
    case PLUSSIGN4:
    case QUESTIONMARK2:
    case NUMBERSIGN2:
    case EXCLAMATIONMARK2:
      break;
    case LEFTCURLYBRACKET2:
      code2 = scanner.nextCharCode();
      if (code2 < 48 || code2 > 57) {
        return maybeToken(scanner);
      }
      break;
    default:
      if (scanner.isNameCharCode(code2)) {
        return readKeywordOrFunction(scanner);
      }
      return maybeToken(scanner);
  }
}
function parse(source) {
  const scanner = new Scanner(source);
  const result = readImplicitGroup(scanner);
  if (scanner.pos !== source.length) {
    scanner.error("Unexpected input");
  }
  if (result.terms.length === 1 && result.terms[0].type === "Group") {
    return result.terms[0];
  }
  return result;
}

// node_modules/css-tree/lib/definition-syntax/walk.js
var noop3 = function() {
};
function ensureFunction2(value) {
  return typeof value === "function" ? value : noop3;
}
function walk(node, options, context) {
  function walk3(node2) {
    enter.call(context, node2);
    switch (node2.type) {
      case "Group":
        node2.terms.forEach(walk3);
        break;
      case "Multiplier":
      case "Boolean":
        walk3(node2.term);
        break;
      case "Type":
      case "Property":
      case "Keyword":
      case "AtKeyword":
      case "Function":
      case "String":
      case "Token":
      case "Comma":
        break;
      default:
        throw new Error("Unknown type: " + node2.type);
    }
    leave.call(context, node2);
  }
  let enter = noop3;
  let leave = noop3;
  if (typeof options === "function") {
    enter = options;
  } else if (options) {
    enter = ensureFunction2(options.enter);
    leave = ensureFunction2(options.leave);
  }
  if (enter === noop3 && leave === noop3) {
    throw new Error("Neither `enter` nor `leave` walker handler is set or both aren't a function");
  }
  walk3(node, context);
}

// node_modules/css-tree/lib/lexer/prepare-tokens.js
var astToTokens = {
  decorator(handlers) {
    const tokens = [];
    let curNode = null;
    return {
      ...handlers,
      node(node) {
        const tmp = curNode;
        curNode = node;
        handlers.node.call(this, node);
        curNode = tmp;
      },
      emit(value, type, auto) {
        tokens.push({
          type,
          value,
          node: auto ? null : curNode
        });
      },
      result() {
        return tokens;
      }
    };
  }
};
function stringToTokens(str) {
  const tokens = [];
  tokenize(
    str,
    (type, start, end) => tokens.push({
      type,
      value: str.slice(start, end),
      node: null
    })
  );
  return tokens;
}
function prepare_tokens_default(value, syntax) {
  if (typeof value === "string") {
    return stringToTokens(value);
  }
  return syntax.generate(value, astToTokens);
}

// node_modules/css-tree/lib/lexer/match-graph.js
var MATCH = { type: "Match" };
var MISMATCH = { type: "Mismatch" };
var DISALLOW_EMPTY = { type: "DisallowEmpty" };
var LEFTPARENTHESIS2 = 40;
var RIGHTPARENTHESIS2 = 41;
function createCondition(match, thenBranch, elseBranch) {
  if (thenBranch === MATCH && elseBranch === MISMATCH) {
    return match;
  }
  if (match === MATCH && thenBranch === MATCH && elseBranch === MATCH) {
    return match;
  }
  if (match.type === "If" && match.else === MISMATCH && thenBranch === MATCH) {
    thenBranch = match.then;
    match = match.match;
  }
  return {
    type: "If",
    match,
    then: thenBranch,
    else: elseBranch
  };
}
function isFunctionType(name50) {
  return name50.length > 2 && name50.charCodeAt(name50.length - 2) === LEFTPARENTHESIS2 && name50.charCodeAt(name50.length - 1) === RIGHTPARENTHESIS2;
}
function isEnumCapatible(term) {
  return term.type === "Keyword" || term.type === "AtKeyword" || term.type === "Function" || term.type === "Type" && isFunctionType(term.name);
}
function groupNode(terms, combinator = " ", explicit = false) {
  return {
    type: "Group",
    terms,
    combinator,
    disallowEmpty: false,
    explicit
  };
}
function replaceTypeInGraph(node, replacements, visited = /* @__PURE__ */ new Set()) {
  if (!visited.has(node)) {
    visited.add(node);
    switch (node.type) {
      case "If":
        node.match = replaceTypeInGraph(node.match, replacements, visited);
        node.then = replaceTypeInGraph(node.then, replacements, visited);
        node.else = replaceTypeInGraph(node.else, replacements, visited);
        break;
      case "Type":
        return replacements[node.name] || node;
    }
  }
  return node;
}
function buildGroupMatchGraph(combinator, terms, atLeastOneTermMatched) {
  switch (combinator) {
    case " ": {
      let result = MATCH;
      for (let i = terms.length - 1; i >= 0; i--) {
        const term = terms[i];
        result = createCondition(
          term,
          result,
          MISMATCH
        );
      }
      ;
      return result;
    }
    case "|": {
      let result = MISMATCH;
      let map = null;
      for (let i = terms.length - 1; i >= 0; i--) {
        let term = terms[i];
        if (isEnumCapatible(term)) {
          if (map === null && i > 0 && isEnumCapatible(terms[i - 1])) {
            map = /* @__PURE__ */ Object.create(null);
            result = createCondition(
              {
                type: "Enum",
                map
              },
              MATCH,
              result
            );
          }
          if (map !== null) {
            const key = (isFunctionType(term.name) ? term.name.slice(0, -1) : term.name).toLowerCase();
            if (key in map === false) {
              map[key] = term;
              continue;
            }
          }
        }
        map = null;
        result = createCondition(
          term,
          MATCH,
          result
        );
      }
      ;
      return result;
    }
    case "&&": {
      if (terms.length > 5) {
        return {
          type: "MatchOnce",
          terms,
          all: true
        };
      }
      let result = MISMATCH;
      for (let i = terms.length - 1; i >= 0; i--) {
        const term = terms[i];
        let thenClause;
        if (terms.length > 1) {
          thenClause = buildGroupMatchGraph(
            combinator,
            terms.filter(function(newGroupTerm) {
              return newGroupTerm !== term;
            }),
            false
          );
        } else {
          thenClause = MATCH;
        }
        result = createCondition(
          term,
          thenClause,
          result
        );
      }
      ;
      return result;
    }
    case "||": {
      if (terms.length > 5) {
        return {
          type: "MatchOnce",
          terms,
          all: false
        };
      }
      let result = atLeastOneTermMatched ? MATCH : MISMATCH;
      for (let i = terms.length - 1; i >= 0; i--) {
        const term = terms[i];
        let thenClause;
        if (terms.length > 1) {
          thenClause = buildGroupMatchGraph(
            combinator,
            terms.filter(function(newGroupTerm) {
              return newGroupTerm !== term;
            }),
            true
          );
        } else {
          thenClause = MATCH;
        }
        result = createCondition(
          term,
          thenClause,
          result
        );
      }
      ;
      return result;
    }
  }
}
function buildMultiplierMatchGraph(node) {
  let result = MATCH;
  let matchTerm = buildMatchGraphInternal(node.term);
  if (node.max === 0) {
    matchTerm = createCondition(
      matchTerm,
      DISALLOW_EMPTY,
      MISMATCH
    );
    result = createCondition(
      matchTerm,
      null,
      // will be a loop
      MISMATCH
    );
    result.then = createCondition(
      MATCH,
      MATCH,
      result
      // make a loop
    );
    if (node.comma) {
      result.then.else = createCondition(
        { type: "Comma", syntax: node },
        result,
        MISMATCH
      );
    }
  } else {
    for (let i = node.min || 1; i <= node.max; i++) {
      if (node.comma && result !== MATCH) {
        result = createCondition(
          { type: "Comma", syntax: node },
          result,
          MISMATCH
        );
      }
      result = createCondition(
        matchTerm,
        createCondition(
          MATCH,
          MATCH,
          result
        ),
        MISMATCH
      );
    }
  }
  if (node.min === 0) {
    result = createCondition(
      MATCH,
      MATCH,
      result
    );
  } else {
    for (let i = 0; i < node.min - 1; i++) {
      if (node.comma && result !== MATCH) {
        result = createCondition(
          { type: "Comma", syntax: node },
          result,
          MISMATCH
        );
      }
      result = createCondition(
        matchTerm,
        result,
        MISMATCH
      );
    }
  }
  return result;
}
function buildMatchGraphInternal(node) {
  if (typeof node === "function") {
    return {
      type: "Generic",
      fn: node
    };
  }
  switch (node.type) {
    case "Group": {
      let result = buildGroupMatchGraph(
        node.combinator,
        node.terms.map(buildMatchGraphInternal),
        false
      );
      if (node.disallowEmpty) {
        result = createCondition(
          result,
          DISALLOW_EMPTY,
          MISMATCH
        );
      }
      return result;
    }
    case "Multiplier":
      return buildMultiplierMatchGraph(node);
    // https://drafts.csswg.org/css-values-5/#boolean
    case "Boolean": {
      const term = buildMatchGraphInternal(node.term);
      const matchNode = buildMatchGraphInternal(groupNode([
        groupNode([
          { type: "Keyword", name: "not" },
          { type: "Type", name: "!boolean-group" }
        ]),
        groupNode([
          { type: "Type", name: "!boolean-group" },
          groupNode([
            { type: "Multiplier", comma: false, min: 0, max: 0, term: groupNode([
              { type: "Keyword", name: "and" },
              { type: "Type", name: "!boolean-group" }
            ]) },
            { type: "Multiplier", comma: false, min: 0, max: 0, term: groupNode([
              { type: "Keyword", name: "or" },
              { type: "Type", name: "!boolean-group" }
            ]) }
          ], "|")
        ])
      ], "|"));
      const booleanGroup = buildMatchGraphInternal(
        groupNode([
          { type: "Type", name: "!term" },
          groupNode([
            { type: "Token", value: "(" },
            { type: "Type", name: "!self" },
            { type: "Token", value: ")" }
          ]),
          { type: "Type", name: "general-enclosed" }
        ], "|")
      );
      replaceTypeInGraph(booleanGroup, { "!term": term, "!self": matchNode });
      replaceTypeInGraph(matchNode, { "!boolean-group": booleanGroup });
      return matchNode;
    }
    case "Type":
    case "Property":
      return {
        type: node.type,
        name: node.name,
        syntax: node
      };
    case "Keyword":
      return {
        type: node.type,
        name: node.name.toLowerCase(),
        syntax: node
      };
    case "AtKeyword":
      return {
        type: node.type,
        name: "@" + node.name.toLowerCase(),
        syntax: node
      };
    case "Function":
      return {
        type: node.type,
        name: node.name.toLowerCase() + "(",
        syntax: node
      };
    case "String":
      if (node.value.length === 3) {
        return {
          type: "Token",
          value: node.value.charAt(1),
          syntax: node
        };
      }
      return {
        type: node.type,
        value: node.value.substr(1, node.value.length - 2).replace(/\\'/g, "'"),
        syntax: node
      };
    case "Token":
      return {
        type: node.type,
        value: node.value,
        syntax: node
      };
    case "Comma":
      return {
        type: node.type,
        syntax: node
      };
    default:
      throw new Error("Unknown node type:", node.type);
  }
}
function buildMatchGraph(syntaxTree, ref) {
  if (typeof syntaxTree === "string") {
    syntaxTree = parse(syntaxTree);
  }
  return {
    type: "MatchGraph",
    match: buildMatchGraphInternal(syntaxTree),
    syntax: ref || null,
    source: syntaxTree
  };
}

// node_modules/css-tree/lib/lexer/match.js
var { hasOwnProperty: hasOwnProperty3 } = Object.prototype;
var STUB = 0;
var TOKEN = 1;
var OPEN_SYNTAX = 2;
var CLOSE_SYNTAX = 3;
var EXIT_REASON_MATCH = "Match";
var EXIT_REASON_MISMATCH = "Mismatch";
var EXIT_REASON_ITERATION_LIMIT = "Maximum iteration number exceeded (please fill an issue on https://github.com/csstree/csstree/issues)";
var ITERATION_LIMIT = 15e3;
var totalIterationCount = 0;
function reverseList(list) {
  let prev = null;
  let next = null;
  let item = list;
  while (item !== null) {
    next = item.prev;
    item.prev = prev;
    prev = item;
    item = next;
  }
  return prev;
}
function areStringsEqualCaseInsensitive(testStr, referenceStr) {
  if (testStr.length !== referenceStr.length) {
    return false;
  }
  for (let i = 0; i < testStr.length; i++) {
    const referenceCode = referenceStr.charCodeAt(i);
    let testCode = testStr.charCodeAt(i);
    if (testCode >= 65 && testCode <= 90) {
      testCode = testCode | 32;
    }
    if (testCode !== referenceCode) {
      return false;
    }
  }
  return true;
}
function isContextEdgeDelim(token) {
  if (token.type !== Delim) {
    return false;
  }
  return token.value !== "?";
}
function isCommaContextStart(token) {
  if (token === null) {
    return true;
  }
  return token.type === Comma || token.type === Function2 || token.type === LeftParenthesis || token.type === LeftSquareBracket || token.type === LeftCurlyBracket || isContextEdgeDelim(token);
}
function isCommaContextEnd(token) {
  if (token === null) {
    return true;
  }
  return token.type === RightParenthesis || token.type === RightSquareBracket || token.type === RightCurlyBracket || token.type === Delim && token.value === "/";
}
function internalMatch(tokens, state, syntaxes) {
  function moveToNextToken() {
    do {
      tokenIndex++;
      token = tokenIndex < tokens.length ? tokens[tokenIndex] : null;
    } while (token !== null && (token.type === WhiteSpace || token.type === Comment));
  }
  function getNextToken(offset) {
    const nextIndex = tokenIndex + offset;
    return nextIndex < tokens.length ? tokens[nextIndex] : null;
  }
  function stateSnapshotFromSyntax(nextState, prev) {
    return {
      nextState,
      matchStack,
      syntaxStack,
      thenStack,
      tokenIndex,
      prev
    };
  }
  function pushThenStack(nextState) {
    thenStack = {
      nextState,
      matchStack,
      syntaxStack,
      prev: thenStack
    };
  }
  function pushElseStack(nextState) {
    elseStack = stateSnapshotFromSyntax(nextState, elseStack);
  }
  function addTokenToMatch() {
    matchStack = {
      type: TOKEN,
      syntax: state.syntax,
      token,
      prev: matchStack
    };
    moveToNextToken();
    syntaxStash = null;
    if (tokenIndex > longestMatch) {
      longestMatch = tokenIndex;
    }
  }
  function openSyntax() {
    syntaxStack = {
      syntax: state.syntax,
      opts: state.syntax.opts || syntaxStack !== null && syntaxStack.opts || null,
      prev: syntaxStack
    };
    matchStack = {
      type: OPEN_SYNTAX,
      syntax: state.syntax,
      token: matchStack.token,
      prev: matchStack
    };
  }
  function closeSyntax() {
    if (matchStack.type === OPEN_SYNTAX) {
      matchStack = matchStack.prev;
    } else {
      matchStack = {
        type: CLOSE_SYNTAX,
        syntax: syntaxStack.syntax,
        token: matchStack.token,
        prev: matchStack
      };
    }
    syntaxStack = syntaxStack.prev;
  }
  let syntaxStack = null;
  let thenStack = null;
  let elseStack = null;
  let syntaxStash = null;
  let iterationCount = 0;
  let exitReason = null;
  let token = null;
  let tokenIndex = -1;
  let longestMatch = 0;
  let matchStack = {
    type: STUB,
    syntax: null,
    token: null,
    prev: null
  };
  moveToNextToken();
  while (exitReason === null && ++iterationCount < ITERATION_LIMIT) {
    switch (state.type) {
      case "Match":
        if (thenStack === null) {
          if (token !== null) {
            if (tokenIndex !== tokens.length - 1 || token.value !== "\\0" && token.value !== "\\9") {
              state = MISMATCH;
              break;
            }
          }
          exitReason = EXIT_REASON_MATCH;
          break;
        }
        state = thenStack.nextState;
        if (state === DISALLOW_EMPTY) {
          if (thenStack.matchStack === matchStack) {
            state = MISMATCH;
            break;
          } else {
            state = MATCH;
          }
        }
        while (thenStack.syntaxStack !== syntaxStack) {
          closeSyntax();
        }
        thenStack = thenStack.prev;
        break;
      case "Mismatch":
        if (syntaxStash !== null && syntaxStash !== false) {
          if (elseStack === null || tokenIndex > elseStack.tokenIndex) {
            elseStack = syntaxStash;
            syntaxStash = false;
          }
        } else if (elseStack === null) {
          exitReason = EXIT_REASON_MISMATCH;
          break;
        }
        state = elseStack.nextState;
        thenStack = elseStack.thenStack;
        syntaxStack = elseStack.syntaxStack;
        matchStack = elseStack.matchStack;
        tokenIndex = elseStack.tokenIndex;
        token = tokenIndex < tokens.length ? tokens[tokenIndex] : null;
        elseStack = elseStack.prev;
        break;
      case "MatchGraph":
        state = state.match;
        break;
      case "If":
        if (state.else !== MISMATCH) {
          pushElseStack(state.else);
        }
        if (state.then !== MATCH) {
          pushThenStack(state.then);
        }
        state = state.match;
        break;
      case "MatchOnce":
        state = {
          type: "MatchOnceBuffer",
          syntax: state,
          index: 0,
          mask: 0
        };
        break;
      case "MatchOnceBuffer": {
        const terms = state.syntax.terms;
        if (state.index === terms.length) {
          if (state.mask === 0 || state.syntax.all) {
            state = MISMATCH;
            break;
          }
          state = MATCH;
          break;
        }
        if (state.mask === (1 << terms.length) - 1) {
          state = MATCH;
          break;
        }
        for (; state.index < terms.length; state.index++) {
          const matchFlag = 1 << state.index;
          if ((state.mask & matchFlag) === 0) {
            pushElseStack(state);
            pushThenStack({
              type: "AddMatchOnce",
              syntax: state.syntax,
              mask: state.mask | matchFlag
            });
            state = terms[state.index++];
            break;
          }
        }
        break;
      }
      case "AddMatchOnce":
        state = {
          type: "MatchOnceBuffer",
          syntax: state.syntax,
          index: 0,
          mask: state.mask
        };
        break;
      case "Enum":
        if (token !== null) {
          let name50 = token.value.toLowerCase();
          if (name50.indexOf("\\") !== -1) {
            name50 = name50.replace(/\\[09].*$/, "");
          }
          if (hasOwnProperty3.call(state.map, name50)) {
            state = state.map[name50];
            break;
          }
        }
        state = MISMATCH;
        break;
      case "Generic": {
        const opts = syntaxStack !== null ? syntaxStack.opts : null;
        const lastTokenIndex2 = tokenIndex + Math.floor(state.fn(token, getNextToken, opts));
        if (!isNaN(lastTokenIndex2) && lastTokenIndex2 > tokenIndex) {
          while (tokenIndex < lastTokenIndex2) {
            addTokenToMatch();
          }
          state = MATCH;
        } else {
          state = MISMATCH;
        }
        break;
      }
      case "Type":
      case "Property": {
        const syntaxDict = state.type === "Type" ? "types" : "properties";
        const dictSyntax = hasOwnProperty3.call(syntaxes, syntaxDict) ? syntaxes[syntaxDict][state.name] : null;
        if (!dictSyntax || !dictSyntax.match) {
          throw new Error(
            "Bad syntax reference: " + (state.type === "Type" ? "<" + state.name + ">" : "<'" + state.name + "'>")
          );
        }
        if (syntaxStash !== false && token !== null && state.type === "Type") {
          const lowPriorityMatching = (
            // https://drafts.csswg.org/css-values-4/#custom-idents
            // When parsing positionally-ambiguous keywords in a property value, a <custom-ident> production
            // can only claim the keyword if no other unfulfilled production can claim it.
            state.name === "custom-ident" && token.type === Ident || // https://drafts.csswg.org/css-values-4/#lengths
            // ... if a `0` could be parsed as either a <number> or a <length> in a property (such as line-height),
            // it must parse as a <number>
            state.name === "length" && token.value === "0"
          );
          if (lowPriorityMatching) {
            if (syntaxStash === null) {
              syntaxStash = stateSnapshotFromSyntax(state, elseStack);
            }
            state = MISMATCH;
            break;
          }
        }
        openSyntax();
        state = dictSyntax.matchRef || dictSyntax.match;
        break;
      }
      case "Keyword": {
        const name50 = state.name;
        if (token !== null) {
          let keywordName = token.value;
          if (keywordName.indexOf("\\") !== -1) {
            keywordName = keywordName.replace(/\\[09].*$/, "");
          }
          if (areStringsEqualCaseInsensitive(keywordName, name50)) {
            addTokenToMatch();
            state = MATCH;
            break;
          }
        }
        state = MISMATCH;
        break;
      }
      case "AtKeyword":
      case "Function":
        if (token !== null && areStringsEqualCaseInsensitive(token.value, state.name)) {
          addTokenToMatch();
          state = MATCH;
          break;
        }
        state = MISMATCH;
        break;
      case "Token":
        if (token !== null && token.value === state.value) {
          addTokenToMatch();
          state = MATCH;
          break;
        }
        state = MISMATCH;
        break;
      case "Comma":
        if (token !== null && token.type === Comma) {
          if (isCommaContextStart(matchStack.token)) {
            state = MISMATCH;
          } else {
            addTokenToMatch();
            state = isCommaContextEnd(token) ? MISMATCH : MATCH;
          }
        } else {
          state = isCommaContextStart(matchStack.token) || isCommaContextEnd(token) ? MATCH : MISMATCH;
        }
        break;
      case "String":
        let string = "";
        let lastTokenIndex = tokenIndex;
        for (; lastTokenIndex < tokens.length && string.length < state.value.length; lastTokenIndex++) {
          string += tokens[lastTokenIndex].value;
        }
        if (areStringsEqualCaseInsensitive(string, state.value)) {
          while (tokenIndex < lastTokenIndex) {
            addTokenToMatch();
          }
          state = MATCH;
        } else {
          state = MISMATCH;
        }
        break;
      default:
        throw new Error("Unknown node type: " + state.type);
    }
  }
  totalIterationCount += iterationCount;
  switch (exitReason) {
    case null:
      console.warn("[csstree-match] BREAK after " + ITERATION_LIMIT + " iterations");
      exitReason = EXIT_REASON_ITERATION_LIMIT;
      matchStack = null;
      break;
    case EXIT_REASON_MATCH:
      while (syntaxStack !== null) {
        closeSyntax();
      }
      break;
    default:
      matchStack = null;
  }
  return {
    tokens,
    reason: exitReason,
    iterations: iterationCount,
    match: matchStack,
    longestMatch
  };
}
function matchAsTree(tokens, matchGraph, syntaxes) {
  const matchResult = internalMatch(tokens, matchGraph, syntaxes || {});
  if (matchResult.match === null) {
    return matchResult;
  }
  let item = matchResult.match;
  let host = matchResult.match = {
    syntax: matchGraph.syntax || null,
    match: []
  };
  const hostStack = [host];
  item = reverseList(item).prev;
  while (item !== null) {
    switch (item.type) {
      case OPEN_SYNTAX:
        host.match.push(host = {
          syntax: item.syntax,
          match: []
        });
        hostStack.push(host);
        break;
      case CLOSE_SYNTAX:
        hostStack.pop();
        host = hostStack[hostStack.length - 1];
        break;
      default:
        host.match.push({
          syntax: item.syntax || null,
          token: item.token.value,
          node: item.token.node
        });
    }
    item = item.prev;
  }
  return matchResult;
}

// node_modules/css-tree/lib/lexer/trace.js
var trace_exports = {};
__export(trace_exports, {
  getTrace: () => getTrace,
  isKeyword: () => isKeyword,
  isProperty: () => isProperty,
  isType: () => isType
});
function getTrace(node) {
  function shouldPutToTrace(syntax) {
    if (syntax === null) {
      return false;
    }
    return syntax.type === "Type" || syntax.type === "Property" || syntax.type === "Keyword";
  }
  function hasMatch(matchNode) {
    if (Array.isArray(matchNode.match)) {
      for (let i = 0; i < matchNode.match.length; i++) {
        if (hasMatch(matchNode.match[i])) {
          if (shouldPutToTrace(matchNode.syntax)) {
            result.unshift(matchNode.syntax);
          }
          return true;
        }
      }
    } else if (matchNode.node === node) {
      result = shouldPutToTrace(matchNode.syntax) ? [matchNode.syntax] : [];
      return true;
    }
    return false;
  }
  let result = null;
  if (this.matched !== null) {
    hasMatch(this.matched);
  }
  return result;
}
function isType(node, type) {
  return testNode(this, node, (match) => match.type === "Type" && match.name === type);
}
function isProperty(node, property2) {
  return testNode(this, node, (match) => match.type === "Property" && match.name === property2);
}
function isKeyword(node) {
  return testNode(this, node, (match) => match.type === "Keyword");
}
function testNode(match, node, fn) {
  const trace = getTrace.call(match, node);
  if (trace === null) {
    return false;
  }
  return trace.some(fn);
}

// node_modules/css-tree/lib/lexer/search.js
function getFirstMatchNode(matchNode) {
  if ("node" in matchNode) {
    return matchNode.node;
  }
  return getFirstMatchNode(matchNode.match[0]);
}
function getLastMatchNode(matchNode) {
  if ("node" in matchNode) {
    return matchNode.node;
  }
  return getLastMatchNode(matchNode.match[matchNode.match.length - 1]);
}
function matchFragments(lexer2, ast, match, type, name50) {
  function findFragments(matchNode) {
    if (matchNode.syntax !== null && matchNode.syntax.type === type && matchNode.syntax.name === name50) {
      const start = getFirstMatchNode(matchNode);
      const end = getLastMatchNode(matchNode);
      lexer2.syntax.walk(ast, function(node, item, list) {
        if (node === start) {
          const nodes = new List();
          do {
            nodes.appendData(item.data);
            if (item.data === end) {
              break;
            }
            item = item.next;
          } while (item !== null);
          fragments.push({
            parent: list,
            nodes
          });
        }
      });
    }
    if (Array.isArray(matchNode.match)) {
      matchNode.match.forEach(findFragments);
    }
  }
  const fragments = [];
  if (match.matched !== null) {
    findFragments(match.matched);
  }
  return fragments;
}

// node_modules/css-tree/lib/lexer/structure.js
var { hasOwnProperty: hasOwnProperty4 } = Object.prototype;
function isValidNumber(value) {
  return typeof value === "number" && isFinite(value) && Math.floor(value) === value && value >= 0;
}
function isValidLocation(loc) {
  return Boolean(loc) && isValidNumber(loc.offset) && isValidNumber(loc.line) && isValidNumber(loc.column);
}
function createNodeStructureChecker(type, fields) {
  return function checkNode(node, warn) {
    if (!node || node.constructor !== Object) {
      return warn(node, "Type of node should be an Object");
    }
    for (let key in node) {
      let valid = true;
      if (hasOwnProperty4.call(node, key) === false) {
        continue;
      }
      if (key === "type") {
        if (node.type !== type) {
          warn(node, "Wrong node type `" + node.type + "`, expected `" + type + "`");
        }
      } else if (key === "loc") {
        if (node.loc === null) {
          continue;
        } else if (node.loc && node.loc.constructor === Object) {
          if (typeof node.loc.source !== "string") {
            key += ".source";
          } else if (!isValidLocation(node.loc.start)) {
            key += ".start";
          } else if (!isValidLocation(node.loc.end)) {
            key += ".end";
          } else {
            continue;
          }
        }
        valid = false;
      } else if (fields.hasOwnProperty(key)) {
        valid = false;
        for (let i = 0; !valid && i < fields[key].length; i++) {
          const fieldType = fields[key][i];
          switch (fieldType) {
            case String:
              valid = typeof node[key] === "string";
              break;
            case Boolean:
              valid = typeof node[key] === "boolean";
              break;
            case null:
              valid = node[key] === null;
              break;
            default:
              if (typeof fieldType === "string") {
                valid = node[key] && node[key].type === fieldType;
              } else if (Array.isArray(fieldType)) {
                valid = node[key] instanceof List;
              }
          }
        }
      } else {
        warn(node, "Unknown field `" + key + "` for " + type + " node type");
      }
      if (!valid) {
        warn(node, "Bad value for `" + type + "." + key + "`");
      }
    }
    for (const key in fields) {
      if (hasOwnProperty4.call(fields, key) && hasOwnProperty4.call(node, key) === false) {
        warn(node, "Field `" + type + "." + key + "` is missed");
      }
    }
  };
}
function genTypesList(fieldTypes, path) {
  const docsTypes = [];
  for (let i = 0; i < fieldTypes.length; i++) {
    const fieldType = fieldTypes[i];
    if (fieldType === String || fieldType === Boolean) {
      docsTypes.push(fieldType.name.toLowerCase());
    } else if (fieldType === null) {
      docsTypes.push("null");
    } else if (typeof fieldType === "string") {
      docsTypes.push(fieldType);
    } else if (Array.isArray(fieldType)) {
      docsTypes.push("List<" + (genTypesList(fieldType, path) || "any") + ">");
    } else {
      throw new Error("Wrong value `" + fieldType + "` in `" + path + "` structure definition");
    }
  }
  return docsTypes.join(" | ");
}
function processStructure(name50, nodeType) {
  const structure50 = nodeType.structure;
  const fields = {
    type: String,
    loc: true
  };
  const docs = {
    type: '"' + name50 + '"'
  };
  for (const key in structure50) {
    if (hasOwnProperty4.call(structure50, key) === false) {
      continue;
    }
    const fieldTypes = fields[key] = Array.isArray(structure50[key]) ? structure50[key].slice() : [structure50[key]];
    docs[key] = genTypesList(fieldTypes, name50 + "." + key);
  }
  return {
    docs,
    check: createNodeStructureChecker(name50, fields)
  };
}
function getStructureFromConfig(config) {
  const structure50 = {};
  if (config.node) {
    for (const name50 in config.node) {
      if (hasOwnProperty4.call(config.node, name50)) {
        const nodeType = config.node[name50];
        if (nodeType.structure) {
          structure50[name50] = processStructure(name50, nodeType);
        } else {
          throw new Error("Missed `structure` field in `" + name50 + "` node type definition");
        }
      }
    }
  }
  return structure50;
}

// node_modules/css-tree/lib/lexer/Lexer.js
function dumpMapSyntax(map, compact, syntaxAsAst) {
  const result = {};
  for (const name50 in map) {
    if (map[name50].syntax) {
      result[name50] = syntaxAsAst ? map[name50].syntax : generate(map[name50].syntax, { compact });
    }
  }
  return result;
}
function dumpAtruleMapSyntax(map, compact, syntaxAsAst) {
  const result = {};
  for (const [name50, atrule] of Object.entries(map)) {
    result[name50] = {
      prelude: atrule.prelude && (syntaxAsAst ? atrule.prelude.syntax : generate(atrule.prelude.syntax, { compact })),
      descriptors: atrule.descriptors && dumpMapSyntax(atrule.descriptors, compact, syntaxAsAst)
    };
  }
  return result;
}
function valueHasVar(tokens) {
  for (let i = 0; i < tokens.length; i++) {
    if (tokens[i].value.toLowerCase() === "var(") {
      return true;
    }
  }
  return false;
}
function syntaxHasTopLevelCommaMultiplier(syntax) {
  const singleTerm = syntax.terms[0];
  return syntax.explicit === false && syntax.terms.length === 1 && singleTerm.type === "Multiplier" && singleTerm.comma === true;
}
function buildMatchResult(matched, error, iterations) {
  return {
    matched,
    iterations,
    error,
    ...trace_exports
  };
}
function matchSyntax(lexer2, syntax, value, useCssWideKeywords) {
  const tokens = prepare_tokens_default(value, lexer2.syntax);
  let result;
  if (valueHasVar(tokens)) {
    return buildMatchResult(null, new Error("Matching for a tree with var() is not supported"));
  }
  if (useCssWideKeywords) {
    result = matchAsTree(tokens, lexer2.cssWideKeywordsSyntax, lexer2);
  }
  if (!useCssWideKeywords || !result.match) {
    result = matchAsTree(tokens, syntax.match, lexer2);
    if (!result.match) {
      return buildMatchResult(
        null,
        new SyntaxMatchError(result.reason, syntax.syntax, value, result),
        result.iterations
      );
    }
  }
  return buildMatchResult(result.match, null, result.iterations);
}
var Lexer = class {
  constructor(config, syntax, structure50) {
    this.cssWideKeywords = cssWideKeywords;
    this.syntax = syntax;
    this.generic = false;
    this.units = { ...units_exports };
    this.atrules = /* @__PURE__ */ Object.create(null);
    this.properties = /* @__PURE__ */ Object.create(null);
    this.types = /* @__PURE__ */ Object.create(null);
    this.structure = structure50 || getStructureFromConfig(config);
    if (config) {
      if (config.cssWideKeywords) {
        this.cssWideKeywords = config.cssWideKeywords;
      }
      if (config.units) {
        for (const group of Object.keys(units_exports)) {
          if (Array.isArray(config.units[group])) {
            this.units[group] = config.units[group];
          }
        }
      }
      if (config.types) {
        for (const [name50, type] of Object.entries(config.types)) {
          this.addType_(name50, type);
        }
      }
      if (config.generic) {
        this.generic = true;
        for (const [name50, value] of Object.entries(createGenericTypes(this.units))) {
          this.addType_(name50, value);
        }
      }
      if (config.atrules) {
        for (const [name50, atrule] of Object.entries(config.atrules)) {
          this.addAtrule_(name50, atrule);
        }
      }
      if (config.properties) {
        for (const [name50, property2] of Object.entries(config.properties)) {
          this.addProperty_(name50, property2);
        }
      }
    }
    this.cssWideKeywordsSyntax = buildMatchGraph(this.cssWideKeywords.join(" |  "));
  }
  checkStructure(ast) {
    function collectWarning(node, message) {
      warns.push({ node, message });
    }
    const structure50 = this.structure;
    const warns = [];
    this.syntax.walk(ast, function(node) {
      if (structure50.hasOwnProperty(node.type)) {
        structure50[node.type].check(node, collectWarning);
      } else {
        collectWarning(node, "Unknown node type `" + node.type + "`");
      }
    });
    return warns.length ? warns : false;
  }
  createDescriptor(syntax, type, name50, parent = null) {
    const ref = {
      type,
      name: name50
    };
    const descriptor = {
      type,
      name: name50,
      parent,
      serializable: typeof syntax === "string" || syntax && typeof syntax.type === "string",
      syntax: null,
      match: null,
      matchRef: null
      // used for properties when a syntax referenced as <'property'> in other syntax definitions
    };
    if (typeof syntax === "function") {
      descriptor.match = buildMatchGraph(syntax, ref);
    } else {
      if (typeof syntax === "string") {
        Object.defineProperty(descriptor, "syntax", {
          get() {
            Object.defineProperty(descriptor, "syntax", {
              value: parse(syntax)
            });
            return descriptor.syntax;
          }
        });
      } else {
        descriptor.syntax = syntax;
      }
      Object.defineProperty(descriptor, "match", {
        get() {
          Object.defineProperty(descriptor, "match", {
            value: buildMatchGraph(descriptor.syntax, ref)
          });
          return descriptor.match;
        }
      });
      if (type === "Property") {
        Object.defineProperty(descriptor, "matchRef", {
          get() {
            const syntax2 = descriptor.syntax;
            const value = syntaxHasTopLevelCommaMultiplier(syntax2) ? buildMatchGraph({
              ...syntax2,
              terms: [syntax2.terms[0].term]
            }, ref) : null;
            Object.defineProperty(descriptor, "matchRef", {
              value
            });
            return value;
          }
        });
      }
    }
    return descriptor;
  }
  addAtrule_(name50, syntax) {
    if (!syntax) {
      return;
    }
    this.atrules[name50] = {
      type: "Atrule",
      name: name50,
      prelude: syntax.prelude ? this.createDescriptor(syntax.prelude, "AtrulePrelude", name50) : null,
      descriptors: syntax.descriptors ? Object.keys(syntax.descriptors).reduce(
        (map, descName) => {
          map[descName] = this.createDescriptor(syntax.descriptors[descName], "AtruleDescriptor", descName, name50);
          return map;
        },
        /* @__PURE__ */ Object.create(null)
      ) : null
    };
  }
  addProperty_(name50, syntax) {
    if (!syntax) {
      return;
    }
    this.properties[name50] = this.createDescriptor(syntax, "Property", name50);
  }
  addType_(name50, syntax) {
    if (!syntax) {
      return;
    }
    this.types[name50] = this.createDescriptor(syntax, "Type", name50);
  }
  checkAtruleName(atruleName) {
    if (!this.getAtrule(atruleName)) {
      return new SyntaxReferenceError("Unknown at-rule", "@" + atruleName);
    }
  }
  checkAtrulePrelude(atruleName, prelude) {
    const error = this.checkAtruleName(atruleName);
    if (error) {
      return error;
    }
    const atrule = this.getAtrule(atruleName);
    if (!atrule.prelude && prelude) {
      return new SyntaxError("At-rule `@" + atruleName + "` should not contain a prelude");
    }
    if (atrule.prelude && !prelude) {
      if (!matchSyntax(this, atrule.prelude, "", false).matched) {
        return new SyntaxError("At-rule `@" + atruleName + "` should contain a prelude");
      }
    }
  }
  checkAtruleDescriptorName(atruleName, descriptorName) {
    const error = this.checkAtruleName(atruleName);
    if (error) {
      return error;
    }
    const atrule = this.getAtrule(atruleName);
    const descriptor = keyword(descriptorName);
    if (!atrule.descriptors) {
      return new SyntaxError("At-rule `@" + atruleName + "` has no known descriptors");
    }
    if (!atrule.descriptors[descriptor.name] && !atrule.descriptors[descriptor.basename]) {
      return new SyntaxReferenceError("Unknown at-rule descriptor", descriptorName);
    }
  }
  checkPropertyName(propertyName) {
    if (!this.getProperty(propertyName)) {
      return new SyntaxReferenceError("Unknown property", propertyName);
    }
  }
  matchAtrulePrelude(atruleName, prelude) {
    const error = this.checkAtrulePrelude(atruleName, prelude);
    if (error) {
      return buildMatchResult(null, error);
    }
    const atrule = this.getAtrule(atruleName);
    if (!atrule.prelude) {
      return buildMatchResult(null, null);
    }
    return matchSyntax(this, atrule.prelude, prelude || "", false);
  }
  matchAtruleDescriptor(atruleName, descriptorName, value) {
    const error = this.checkAtruleDescriptorName(atruleName, descriptorName);
    if (error) {
      return buildMatchResult(null, error);
    }
    const atrule = this.getAtrule(atruleName);
    const descriptor = keyword(descriptorName);
    return matchSyntax(this, atrule.descriptors[descriptor.name] || atrule.descriptors[descriptor.basename], value, false);
  }
  matchDeclaration(node) {
    if (node.type !== "Declaration") {
      return buildMatchResult(null, new Error("Not a Declaration node"));
    }
    return this.matchProperty(node.property, node.value);
  }
  matchProperty(propertyName, value) {
    if (property(propertyName).custom) {
      return buildMatchResult(null, new Error("Lexer matching doesn't applicable for custom properties"));
    }
    const error = this.checkPropertyName(propertyName);
    if (error) {
      return buildMatchResult(null, error);
    }
    return matchSyntax(this, this.getProperty(propertyName), value, true);
  }
  matchType(typeName, value) {
    const typeSyntax = this.getType(typeName);
    if (!typeSyntax) {
      return buildMatchResult(null, new SyntaxReferenceError("Unknown type", typeName));
    }
    return matchSyntax(this, typeSyntax, value, false);
  }
  match(syntax, value) {
    if (typeof syntax !== "string" && (!syntax || !syntax.type)) {
      return buildMatchResult(null, new SyntaxReferenceError("Bad syntax"));
    }
    if (typeof syntax === "string" || !syntax.match) {
      syntax = this.createDescriptor(syntax, "Type", "anonymous");
    }
    return matchSyntax(this, syntax, value, false);
  }
  findValueFragments(propertyName, value, type, name50) {
    return matchFragments(this, value, this.matchProperty(propertyName, value), type, name50);
  }
  findDeclarationValueFragments(declaration, type, name50) {
    return matchFragments(this, declaration.value, this.matchDeclaration(declaration), type, name50);
  }
  findAllFragments(ast, type, name50) {
    const result = [];
    this.syntax.walk(ast, {
      visit: "Declaration",
      enter: (declaration) => {
        result.push.apply(result, this.findDeclarationValueFragments(declaration, type, name50));
      }
    });
    return result;
  }
  getAtrule(atruleName, fallbackBasename = true) {
    const atrule = keyword(atruleName);
    const atruleEntry = atrule.vendor && fallbackBasename ? this.atrules[atrule.name] || this.atrules[atrule.basename] : this.atrules[atrule.name];
    return atruleEntry || null;
  }
  getAtrulePrelude(atruleName, fallbackBasename = true) {
    const atrule = this.getAtrule(atruleName, fallbackBasename);
    return atrule && atrule.prelude || null;
  }
  getAtruleDescriptor(atruleName, name50) {
    return this.atrules.hasOwnProperty(atruleName) && this.atrules.declarators ? this.atrules[atruleName].declarators[name50] || null : null;
  }
  getProperty(propertyName, fallbackBasename = true) {
    const property2 = property(propertyName);
    const propertyEntry = property2.vendor && fallbackBasename ? this.properties[property2.name] || this.properties[property2.basename] : this.properties[property2.name];
    return propertyEntry || null;
  }
  getType(name50) {
    return hasOwnProperty.call(this.types, name50) ? this.types[name50] : null;
  }
  validate() {
    function syntaxRef(name50, isType2) {
      return isType2 ? `<${name50}>` : `<'${name50}'>`;
    }
    function validate(syntax, name50, broken, descriptor) {
      if (broken.has(name50)) {
        return broken.get(name50);
      }
      broken.set(name50, false);
      if (descriptor.syntax !== null) {
        walk(descriptor.syntax, function(node) {
          if (node.type !== "Type" && node.type !== "Property") {
            return;
          }
          const map = node.type === "Type" ? syntax.types : syntax.properties;
          const brokenMap = node.type === "Type" ? brokenTypes : brokenProperties;
          if (!hasOwnProperty.call(map, node.name)) {
            errors.push(`${syntaxRef(name50, broken === brokenTypes)} used missed syntax definition ${syntaxRef(node.name, node.type === "Type")}`);
            broken.set(name50, true);
          } else if (validate(syntax, node.name, brokenMap, map[node.name])) {
            errors.push(`${syntaxRef(name50, broken === brokenTypes)} used broken syntax definition ${syntaxRef(node.name, node.type === "Type")}`);
            broken.set(name50, true);
          }
        }, this);
      }
    }
    const errors = [];
    let brokenTypes = /* @__PURE__ */ new Map();
    let brokenProperties = /* @__PURE__ */ new Map();
    for (const key in this.types) {
      validate(this, key, brokenTypes, this.types[key]);
    }
    for (const key in this.properties) {
      validate(this, key, brokenProperties, this.properties[key]);
    }
    const brokenTypesArray = [...brokenTypes.keys()].filter((name50) => brokenTypes.get(name50));
    const brokenPropertiesArray = [...brokenProperties.keys()].filter((name50) => brokenProperties.get(name50));
    if (brokenTypesArray.length || brokenPropertiesArray.length) {
      return {
        errors,
        types: brokenTypesArray,
        properties: brokenPropertiesArray
      };
    }
    return null;
  }
  dump(syntaxAsAst, pretty) {
    return {
      generic: this.generic,
      cssWideKeywords: this.cssWideKeywords,
      units: this.units,
      types: dumpMapSyntax(this.types, !pretty, syntaxAsAst),
      properties: dumpMapSyntax(this.properties, !pretty, syntaxAsAst),
      atrules: dumpAtruleMapSyntax(this.atrules, !pretty, syntaxAsAst)
    };
  }
  toString() {
    return JSON.stringify(this.dump());
  }
};

// node_modules/css-tree/lib/syntax/config/mix.js
function appendOrSet(a, b) {
  if (typeof b === "string" && /^\s*\|/.test(b)) {
    return typeof a === "string" ? a + b : b.replace(/^\s*\|\s*/, "");
  }
  return b || null;
}
function extractProps(obj, props) {
  const result = /* @__PURE__ */ Object.create(null);
  for (const prop of Object.keys(obj)) {
    if (props.includes(prop)) {
      result[prop] = obj[prop];
    }
  }
  return result;
}
function mergeDicts(base, ext, fields) {
  const result = { ...base };
  for (const [key, props] of Object.entries(ext)) {
    result[key] = {
      ...result[key],
      ...fields ? extractProps(props, fields) : props
    };
  }
  return result;
}
function mix(dest, src) {
  const result = { ...dest };
  for (const [prop, value] of Object.entries(src)) {
    switch (prop) {
      case "generic":
        result[prop] = Boolean(value);
        break;
      case "cssWideKeywords":
        result[prop] = dest[prop] ? [...dest[prop], ...value] : value || [];
        break;
      case "units":
        result[prop] = { ...dest[prop] };
        for (const [name50, patch2] of Object.entries(value)) {
          result[prop][name50] = Array.isArray(patch2) ? patch2 : [];
        }
        break;
      case "atrules":
        result[prop] = { ...dest[prop] };
        for (const [name50, atrule] of Object.entries(value)) {
          const exists = result[prop][name50] || {};
          const current = result[prop][name50] = {
            prelude: exists.prelude || null,
            descriptors: {
              ...exists.descriptors
            }
          };
          if (!atrule) {
            continue;
          }
          current.prelude = atrule.prelude ? appendOrSet(current.prelude, atrule.prelude) : current.prelude || null;
          for (const [descriptorName, descriptorValue] of Object.entries(atrule.descriptors || {})) {
            current.descriptors[descriptorName] = descriptorValue ? appendOrSet(current.descriptors[descriptorName], descriptorValue) : null;
          }
          if (!Object.keys(current.descriptors).length) {
            current.descriptors = null;
          }
        }
        break;
      case "types":
      case "properties":
        result[prop] = { ...dest[prop] };
        for (const [name50, syntax] of Object.entries(value)) {
          result[prop][name50] = appendOrSet(result[prop][name50], syntax);
        }
        break;
      case "parseContext":
        result[prop] = {
          ...dest[prop],
          ...value
        };
        break;
      case "scope":
      case "features":
        result[prop] = mergeDicts(dest[prop], value);
        break;
      case "atrule":
      case "pseudo":
        result[prop] = mergeDicts(dest[prop], value, ["parse"]);
        break;
      case "node":
        result[prop] = mergeDicts(dest[prop], value, ["name", "structure", "parse", "generate", "walkContext"]);
        break;
    }
  }
  return result;
}

// node_modules/css-tree/lib/syntax/create.js
function createSyntax(config) {
  const parse52 = createParser(config);
  const walk3 = createWalker(config);
  const generate52 = createGenerator(config);
  const { fromPlainObject: fromPlainObject2, toPlainObject: toPlainObject2 } = createConvertor(walk3);
  const syntax = {
    lexer: null,
    createLexer: (config2) => new Lexer(config2, syntax, syntax.lexer.structure),
    tokenize,
    parse: parse52,
    generate: generate52,
    walk: walk3,
    find: walk3.find,
    findLast: walk3.findLast,
    findAll: walk3.findAll,
    fromPlainObject: fromPlainObject2,
    toPlainObject: toPlainObject2,
    fork(extension) {
      const base = mix({}, config);
      return createSyntax(
        typeof extension === "function" ? extension(base) : mix(base, extension)
      );
    }
  };
  syntax.lexer = new Lexer({
    generic: config.generic,
    cssWideKeywords: config.cssWideKeywords,
    units: config.units,
    types: config.types,
    atrules: config.atrules,
    properties: config.properties,
    node: config.node
  }, syntax);
  return syntax;
}
var create_default = (config) => createSyntax(mix({}, config));

// node_modules/css-tree/lib/data.js
var import_module2 = require("module");

// node_modules/css-tree/lib/data-patch.js
var import_module = require("module");
var import_meta = { url: require('url').pathToFileURL(require('path').resolve(require('path').dirname(require.resolve("css-tree/package.json")), "./lib/data-patch.js")).href };
var require2 = (0, import_module.createRequire)(import_meta.url);
var patch = require2("../data/patch.json");
var data_patch_default = patch;

// node_modules/css-tree/lib/data.js
var import_meta2 = { url: require('url').pathToFileURL(require('path').resolve(require('path').dirname(require.resolve("css-tree/package.json")), "./lib/data.js")).href };
var require3 = (0, import_module2.createRequire)(import_meta2.url);
var mdnAtrules = require3("mdn-data/css/at-rules.json");
var mdnProperties = require3("mdn-data/css/properties.json");
var mdnSyntaxes = require3("mdn-data/css/syntaxes.json");
var hasOwn = Object.hasOwn || ((object, property2) => Object.prototype.hasOwnProperty.call(object, property2));
var extendSyntax = /^\s*\|\s*/;
function preprocessAtrules(dict) {
  const result = /* @__PURE__ */ Object.create(null);
  for (const [atruleName, atrule] of Object.entries(dict)) {
    let descriptors = null;
    if (atrule.descriptors) {
      descriptors = /* @__PURE__ */ Object.create(null);
      for (const [name50, descriptor] of Object.entries(atrule.descriptors)) {
        descriptors[name50] = descriptor.syntax;
      }
    }
    result[atruleName.substr(1)] = {
      prelude: atrule.syntax.trim().replace(/\{(.|\s)+\}/, "").match(/^@\S+\s+([^;\{]*)/)[1].trim() || null,
      descriptors
    };
  }
  return result;
}
function patchDictionary(dict, patchDict) {
  const result = /* @__PURE__ */ Object.create(null);
  for (const [key, value] of Object.entries(dict)) {
    if (value) {
      result[key] = value.syntax || value;
    }
  }
  for (const key of Object.keys(patchDict)) {
    if (hasOwn(dict, key)) {
      if (patchDict[key].syntax) {
        result[key] = extendSyntax.test(patchDict[key].syntax) ? result[key] + " " + patchDict[key].syntax.trim() : patchDict[key].syntax;
      } else {
        delete result[key];
      }
    } else {
      if (patchDict[key].syntax) {
        result[key] = patchDict[key].syntax.replace(extendSyntax, "");
      }
    }
  }
  return result;
}
function preprocessPatchAtrulesDescritors(declarations) {
  const result = {};
  for (const [key, value] of Object.entries(declarations || {})) {
    result[key] = typeof value === "string" ? { syntax: value } : value;
  }
  return result;
}
function patchAtrules(dict, patchDict) {
  const result = {};
  for (const key in dict) {
    if (patchDict[key] === null) {
      continue;
    }
    const atrulePatch = patchDict[key] || {};
    result[key] = {
      prelude: key in patchDict && "prelude" in atrulePatch ? atrulePatch.prelude : dict[key].prelude || null,
      descriptors: patchDictionary(
        dict[key].descriptors || {},
        preprocessPatchAtrulesDescritors(atrulePatch.descriptors)
      )
    };
  }
  for (const [key, atrulePatch] of Object.entries(patchDict)) {
    if (atrulePatch && !hasOwn(dict, key)) {
      result[key] = {
        prelude: atrulePatch.prelude || null,
        descriptors: atrulePatch.descriptors ? patchDictionary({}, preprocessPatchAtrulesDescritors(atrulePatch.descriptors)) : null
      };
    }
  }
  return result;
}
var data_default = {
  types: patchDictionary(mdnSyntaxes, data_patch_default.types),
  atrules: patchAtrules(preprocessAtrules(mdnAtrules), data_patch_default.atrules),
  properties: patchDictionary(mdnProperties, data_patch_default.properties)
};

// node_modules/css-tree/lib/syntax/node/index.js
var node_exports = {};
__export(node_exports, {
  AnPlusB: () => AnPlusB_exports,
  Atrule: () => Atrule_exports,
  AtrulePrelude: () => AtrulePrelude_exports,
  AttributeSelector: () => AttributeSelector_exports,
  Block: () => Block_exports,
  Brackets: () => Brackets_exports,
  CDC: () => CDC_exports,
  CDO: () => CDO_exports,
  ClassSelector: () => ClassSelector_exports,
  Combinator: () => Combinator_exports,
  Comment: () => Comment_exports,
  Condition: () => Condition_exports,
  Declaration: () => Declaration_exports,
  DeclarationList: () => DeclarationList_exports,
  Dimension: () => Dimension_exports,
  Feature: () => Feature_exports,
  FeatureFunction: () => FeatureFunction_exports,
  FeatureRange: () => FeatureRange_exports,
  Function: () => Function_exports,
  GeneralEnclosed: () => GeneralEnclosed_exports,
  Hash: () => Hash_exports,
  IdSelector: () => IdSelector_exports,
  Identifier: () => Identifier_exports,
  Layer: () => Layer_exports,
  LayerList: () => LayerList_exports,
  MediaQuery: () => MediaQuery_exports,
  MediaQueryList: () => MediaQueryList_exports,
  NestingSelector: () => NestingSelector_exports,
  Nth: () => Nth_exports,
  Number: () => Number_exports,
  Operator: () => Operator_exports,
  Parentheses: () => Parentheses_exports,
  Percentage: () => Percentage_exports,
  PseudoClassSelector: () => PseudoClassSelector_exports,
  PseudoElementSelector: () => PseudoElementSelector_exports,
  Ratio: () => Ratio_exports,
  Raw: () => Raw_exports,
  Rule: () => Rule_exports,
  Scope: () => Scope_exports,
  Selector: () => Selector_exports,
  SelectorList: () => SelectorList_exports,
  String: () => String_exports,
  StyleSheet: () => StyleSheet_exports,
  SupportsDeclaration: () => SupportsDeclaration_exports,
  TypeSelector: () => TypeSelector_exports,
  UnicodeRange: () => UnicodeRange_exports,
  Url: () => Url_exports,
  Value: () => Value_exports,
  WhiteSpace: () => WhiteSpace_exports
});

// node_modules/css-tree/lib/syntax/node/AnPlusB.js
var AnPlusB_exports = {};
__export(AnPlusB_exports, {
  generate: () => generate2,
  name: () => name,
  parse: () => parse2,
  structure: () => structure
});
var PLUSSIGN5 = 43;
var HYPHENMINUS5 = 45;
var N5 = 110;
var DISALLOW_SIGN2 = true;
var ALLOW_SIGN2 = false;
function checkInteger2(offset, disallowSign) {
  let pos = this.tokenStart + offset;
  const code2 = this.charCodeAt(pos);
  if (code2 === PLUSSIGN5 || code2 === HYPHENMINUS5) {
    if (disallowSign) {
      this.error("Number sign is not allowed");
    }
    pos++;
  }
  for (; pos < this.tokenEnd; pos++) {
    if (!isDigit(this.charCodeAt(pos))) {
      this.error("Integer is expected", pos);
    }
  }
}
function checkTokenIsInteger(disallowSign) {
  return checkInteger2.call(this, 0, disallowSign);
}
function expectCharCode(offset, code2) {
  if (!this.cmpChar(this.tokenStart + offset, code2)) {
    let msg = "";
    switch (code2) {
      case N5:
        msg = "N is expected";
        break;
      case HYPHENMINUS5:
        msg = "HyphenMinus is expected";
        break;
    }
    this.error(msg, this.tokenStart + offset);
  }
}
function consumeB2() {
  let offset = 0;
  let sign = 0;
  let type = this.tokenType;
  while (type === WhiteSpace || type === Comment) {
    type = this.lookupType(++offset);
  }
  if (type !== Number2) {
    if (this.isDelim(PLUSSIGN5, offset) || this.isDelim(HYPHENMINUS5, offset)) {
      sign = this.isDelim(PLUSSIGN5, offset) ? PLUSSIGN5 : HYPHENMINUS5;
      do {
        type = this.lookupType(++offset);
      } while (type === WhiteSpace || type === Comment);
      if (type !== Number2) {
        this.skip(offset);
        checkTokenIsInteger.call(this, DISALLOW_SIGN2);
      }
    } else {
      return null;
    }
  }
  if (offset > 0) {
    this.skip(offset);
  }
  if (sign === 0) {
    type = this.charCodeAt(this.tokenStart);
    if (type !== PLUSSIGN5 && type !== HYPHENMINUS5) {
      this.error("Number sign is expected");
    }
  }
  checkTokenIsInteger.call(this, sign !== 0);
  return sign === HYPHENMINUS5 ? "-" + this.consume(Number2) : this.consume(Number2);
}
var name = "AnPlusB";
var structure = {
  a: [String, null],
  b: [String, null]
};
function parse2() {
  const start = this.tokenStart;
  let a = null;
  let b = null;
  if (this.tokenType === Number2) {
    checkTokenIsInteger.call(this, ALLOW_SIGN2);
    b = this.consume(Number2);
  } else if (this.tokenType === Ident && this.cmpChar(this.tokenStart, HYPHENMINUS5)) {
    a = "-1";
    expectCharCode.call(this, 1, N5);
    switch (this.tokenEnd - this.tokenStart) {
      // -n
      // -n <signed-integer>
      // -n ['+' | '-'] <signless-integer>
      case 2:
        this.next();
        b = consumeB2.call(this);
        break;
      // -n- <signless-integer>
      case 3:
        expectCharCode.call(this, 2, HYPHENMINUS5);
        this.next();
        this.skipSC();
        checkTokenIsInteger.call(this, DISALLOW_SIGN2);
        b = "-" + this.consume(Number2);
        break;
      // <dashndashdigit-ident>
      default:
        expectCharCode.call(this, 2, HYPHENMINUS5);
        checkInteger2.call(this, 3, DISALLOW_SIGN2);
        this.next();
        b = this.substrToCursor(start + 2);
    }
  } else if (this.tokenType === Ident || this.isDelim(PLUSSIGN5) && this.lookupType(1) === Ident) {
    let sign = 0;
    a = "1";
    if (this.isDelim(PLUSSIGN5)) {
      sign = 1;
      this.next();
    }
    expectCharCode.call(this, 0, N5);
    switch (this.tokenEnd - this.tokenStart) {
      // '+'? n
      // '+'? n <signed-integer>
      // '+'? n ['+' | '-'] <signless-integer>
      case 1:
        this.next();
        b = consumeB2.call(this);
        break;
      // '+'? n- <signless-integer>
      case 2:
        expectCharCode.call(this, 1, HYPHENMINUS5);
        this.next();
        this.skipSC();
        checkTokenIsInteger.call(this, DISALLOW_SIGN2);
        b = "-" + this.consume(Number2);
        break;
      // '+'? <ndashdigit-ident>
      default:
        expectCharCode.call(this, 1, HYPHENMINUS5);
        checkInteger2.call(this, 2, DISALLOW_SIGN2);
        this.next();
        b = this.substrToCursor(start + sign + 1);
    }
  } else if (this.tokenType === Dimension) {
    const code2 = this.charCodeAt(this.tokenStart);
    const sign = code2 === PLUSSIGN5 || code2 === HYPHENMINUS5;
    let i = this.tokenStart + sign;
    for (; i < this.tokenEnd; i++) {
      if (!isDigit(this.charCodeAt(i))) {
        break;
      }
    }
    if (i === this.tokenStart + sign) {
      this.error("Integer is expected", this.tokenStart + sign);
    }
    expectCharCode.call(this, i - this.tokenStart, N5);
    a = this.substring(start, i);
    if (i + 1 === this.tokenEnd) {
      this.next();
      b = consumeB2.call(this);
    } else {
      expectCharCode.call(this, i - this.tokenStart + 1, HYPHENMINUS5);
      if (i + 2 === this.tokenEnd) {
        this.next();
        this.skipSC();
        checkTokenIsInteger.call(this, DISALLOW_SIGN2);
        b = "-" + this.consume(Number2);
      } else {
        checkInteger2.call(this, i - this.tokenStart + 2, DISALLOW_SIGN2);
        this.next();
        b = this.substrToCursor(i + 1);
      }
    }
  } else {
    this.error();
  }
  if (a !== null && a.charCodeAt(0) === PLUSSIGN5) {
    a = a.substr(1);
  }
  if (b !== null && b.charCodeAt(0) === PLUSSIGN5) {
    b = b.substr(1);
  }
  return {
    type: "AnPlusB",
    loc: this.getLocation(start, this.tokenStart),
    a,
    b
  };
}
function generate2(node) {
  if (node.a) {
    const a = node.a === "+1" && "n" || node.a === "1" && "n" || node.a === "-1" && "-n" || node.a + "n";
    if (node.b) {
      const b = node.b[0] === "-" || node.b[0] === "+" ? node.b : "+" + node.b;
      this.tokenize(a + b);
    } else {
      this.tokenize(a);
    }
  } else {
    this.tokenize(node.b);
  }
}

// node_modules/css-tree/lib/syntax/node/Atrule.js
var Atrule_exports = {};
__export(Atrule_exports, {
  generate: () => generate3,
  name: () => name2,
  parse: () => parse3,
  structure: () => structure2,
  walkContext: () => walkContext
});
function consumeRaw() {
  return this.Raw(this.consumeUntilLeftCurlyBracketOrSemicolon, true);
}
function isDeclarationBlockAtrule() {
  for (let offset = 1, type; type = this.lookupType(offset); offset++) {
    if (type === RightCurlyBracket) {
      return true;
    }
    if (type === LeftCurlyBracket || type === AtKeyword) {
      return false;
    }
  }
  return false;
}
var name2 = "Atrule";
var walkContext = "atrule";
var structure2 = {
  name: String,
  prelude: ["AtrulePrelude", "Raw", null],
  block: ["Block", null]
};
function parse3(isDeclaration = false) {
  const start = this.tokenStart;
  let name50;
  let nameLowerCase;
  let prelude = null;
  let block = null;
  this.eat(AtKeyword);
  name50 = this.substrToCursor(start + 1);
  nameLowerCase = name50.toLowerCase();
  this.skipSC();
  if (this.eof === false && this.tokenType !== LeftCurlyBracket && this.tokenType !== Semicolon) {
    if (this.parseAtrulePrelude) {
      prelude = this.parseWithFallback(this.AtrulePrelude.bind(this, name50, isDeclaration), consumeRaw);
    } else {
      prelude = consumeRaw.call(this, this.tokenIndex);
    }
    this.skipSC();
  }
  switch (this.tokenType) {
    case Semicolon:
      this.next();
      break;
    case LeftCurlyBracket:
      if (hasOwnProperty.call(this.atrule, nameLowerCase) && typeof this.atrule[nameLowerCase].block === "function") {
        block = this.atrule[nameLowerCase].block.call(this, isDeclaration);
      } else {
        block = this.Block(isDeclarationBlockAtrule.call(this));
      }
      break;
  }
  return {
    type: "Atrule",
    loc: this.getLocation(start, this.tokenStart),
    name: name50,
    prelude,
    block
  };
}
function generate3(node) {
  this.token(AtKeyword, "@" + node.name);
  if (node.prelude !== null) {
    this.node(node.prelude);
  }
  if (node.block) {
    this.node(node.block);
  } else {
    this.token(Semicolon, ";");
  }
}

// node_modules/css-tree/lib/syntax/node/AtrulePrelude.js
var AtrulePrelude_exports = {};
__export(AtrulePrelude_exports, {
  generate: () => generate4,
  name: () => name3,
  parse: () => parse4,
  structure: () => structure3,
  walkContext: () => walkContext2
});
var name3 = "AtrulePrelude";
var walkContext2 = "atrulePrelude";
var structure3 = {
  children: [[]]
};
function parse4(name50) {
  let children = null;
  if (name50 !== null) {
    name50 = name50.toLowerCase();
  }
  this.skipSC();
  if (hasOwnProperty.call(this.atrule, name50) && typeof this.atrule[name50].prelude === "function") {
    children = this.atrule[name50].prelude.call(this);
  } else {
    children = this.readSequence(this.scope.AtrulePrelude);
  }
  this.skipSC();
  if (this.eof !== true && this.tokenType !== LeftCurlyBracket && this.tokenType !== Semicolon) {
    this.error("Semicolon or block is expected");
  }
  return {
    type: "AtrulePrelude",
    loc: this.getLocationFromList(children),
    children
  };
}
function generate4(node) {
  this.children(node);
}

// node_modules/css-tree/lib/syntax/node/AttributeSelector.js
var AttributeSelector_exports = {};
__export(AttributeSelector_exports, {
  generate: () => generate5,
  name: () => name4,
  parse: () => parse5,
  structure: () => structure4
});
var DOLLARSIGN = 36;
var ASTERISK2 = 42;
var EQUALSSIGN = 61;
var CIRCUMFLEXACCENT = 94;
var VERTICALLINE2 = 124;
var TILDE = 126;
function getAttributeName() {
  if (this.eof) {
    this.error("Unexpected end of input");
  }
  const start = this.tokenStart;
  let expectIdent = false;
  if (this.isDelim(ASTERISK2)) {
    expectIdent = true;
    this.next();
  } else if (!this.isDelim(VERTICALLINE2)) {
    this.eat(Ident);
  }
  if (this.isDelim(VERTICALLINE2)) {
    if (this.charCodeAt(this.tokenStart + 1) !== EQUALSSIGN) {
      this.next();
      this.eat(Ident);
    } else if (expectIdent) {
      this.error("Identifier is expected", this.tokenEnd);
    }
  } else if (expectIdent) {
    this.error("Vertical line is expected");
  }
  return {
    type: "Identifier",
    loc: this.getLocation(start, this.tokenStart),
    name: this.substrToCursor(start)
  };
}
function getOperator() {
  const start = this.tokenStart;
  const code2 = this.charCodeAt(start);
  if (code2 !== EQUALSSIGN && // =
  code2 !== TILDE && // ~=
  code2 !== CIRCUMFLEXACCENT && // ^=
  code2 !== DOLLARSIGN && // $=
  code2 !== ASTERISK2 && // *=
  code2 !== VERTICALLINE2) {
    this.error("Attribute selector (=, ~=, ^=, $=, *=, |=) is expected");
  }
  this.next();
  if (code2 !== EQUALSSIGN) {
    if (!this.isDelim(EQUALSSIGN)) {
      this.error("Equal sign is expected");
    }
    this.next();
  }
  return this.substrToCursor(start);
}
var name4 = "AttributeSelector";
var structure4 = {
  name: "Identifier",
  matcher: [String, null],
  value: ["String", "Identifier", null],
  flags: [String, null]
};
function parse5() {
  const start = this.tokenStart;
  let name50;
  let matcher = null;
  let value = null;
  let flags = null;
  this.eat(LeftSquareBracket);
  this.skipSC();
  name50 = getAttributeName.call(this);
  this.skipSC();
  if (this.tokenType !== RightSquareBracket) {
    if (this.tokenType !== Ident) {
      matcher = getOperator.call(this);
      this.skipSC();
      value = this.tokenType === String2 ? this.String() : this.Identifier();
      this.skipSC();
    }
    if (this.tokenType === Ident) {
      flags = this.consume(Ident);
      this.skipSC();
    }
  }
  this.eat(RightSquareBracket);
  return {
    type: "AttributeSelector",
    loc: this.getLocation(start, this.tokenStart),
    name: name50,
    matcher,
    value,
    flags
  };
}
function generate5(node) {
  this.token(Delim, "[");
  this.node(node.name);
  if (node.matcher !== null) {
    this.tokenize(node.matcher);
    this.node(node.value);
  }
  if (node.flags !== null) {
    this.token(Ident, node.flags);
  }
  this.token(Delim, "]");
}

// node_modules/css-tree/lib/syntax/node/Block.js
var Block_exports = {};
__export(Block_exports, {
  generate: () => generate6,
  name: () => name5,
  parse: () => parse6,
  structure: () => structure5,
  walkContext: () => walkContext3
});
var AMPERSAND2 = 38;
function consumeRaw2() {
  return this.Raw(null, true);
}
function consumeRule() {
  return this.parseWithFallback(this.Rule, consumeRaw2);
}
function consumeRawDeclaration() {
  return this.Raw(this.consumeUntilSemicolonIncluded, true);
}
function consumeDeclaration() {
  if (this.tokenType === Semicolon) {
    return consumeRawDeclaration.call(this, this.tokenIndex);
  }
  const node = this.parseWithFallback(this.Declaration, consumeRawDeclaration);
  if (this.tokenType === Semicolon) {
    this.next();
  }
  return node;
}
var name5 = "Block";
var walkContext3 = "block";
var structure5 = {
  children: [[
    "Atrule",
    "Rule",
    "Declaration"
  ]]
};
function parse6(isStyleBlock) {
  const consumer = isStyleBlock ? consumeDeclaration : consumeRule;
  const start = this.tokenStart;
  let children = this.createList();
  this.eat(LeftCurlyBracket);
  scan:
    while (!this.eof) {
      switch (this.tokenType) {
        case RightCurlyBracket:
          break scan;
        case WhiteSpace:
        case Comment:
          this.next();
          break;
        case AtKeyword:
          children.push(this.parseWithFallback(this.Atrule.bind(this, isStyleBlock), consumeRaw2));
          break;
        default:
          if (isStyleBlock && this.isDelim(AMPERSAND2)) {
            children.push(consumeRule.call(this));
          } else {
            children.push(consumer.call(this));
          }
      }
    }
  if (!this.eof) {
    this.eat(RightCurlyBracket);
  }
  return {
    type: "Block",
    loc: this.getLocation(start, this.tokenStart),
    children
  };
}
function generate6(node) {
  this.token(LeftCurlyBracket, "{");
  this.children(node, (prev) => {
    if (prev.type === "Declaration") {
      this.token(Semicolon, ";");
    }
  });
  this.token(RightCurlyBracket, "}");
}

// node_modules/css-tree/lib/syntax/node/Brackets.js
var Brackets_exports = {};
__export(Brackets_exports, {
  generate: () => generate7,
  name: () => name6,
  parse: () => parse7,
  structure: () => structure6
});
var name6 = "Brackets";
var structure6 = {
  children: [[]]
};
function parse7(readSequence2, recognizer) {
  const start = this.tokenStart;
  let children = null;
  this.eat(LeftSquareBracket);
  children = readSequence2.call(this, recognizer);
  if (!this.eof) {
    this.eat(RightSquareBracket);
  }
  return {
    type: "Brackets",
    loc: this.getLocation(start, this.tokenStart),
    children
  };
}
function generate7(node) {
  this.token(Delim, "[");
  this.children(node);
  this.token(Delim, "]");
}

// node_modules/css-tree/lib/syntax/node/CDC.js
var CDC_exports = {};
__export(CDC_exports, {
  generate: () => generate8,
  name: () => name7,
  parse: () => parse8,
  structure: () => structure7
});
var name7 = "CDC";
var structure7 = [];
function parse8() {
  const start = this.tokenStart;
  this.eat(CDC);
  return {
    type: "CDC",
    loc: this.getLocation(start, this.tokenStart)
  };
}
function generate8() {
  this.token(CDC, "-->");
}

// node_modules/css-tree/lib/syntax/node/CDO.js
var CDO_exports = {};
__export(CDO_exports, {
  generate: () => generate9,
  name: () => name8,
  parse: () => parse9,
  structure: () => structure8
});
var name8 = "CDO";
var structure8 = [];
function parse9() {
  const start = this.tokenStart;
  this.eat(CDO);
  return {
    type: "CDO",
    loc: this.getLocation(start, this.tokenStart)
  };
}
function generate9() {
  this.token(CDO, "<!--");
}

// node_modules/css-tree/lib/syntax/node/ClassSelector.js
var ClassSelector_exports = {};
__export(ClassSelector_exports, {
  generate: () => generate10,
  name: () => name9,
  parse: () => parse10,
  structure: () => structure9
});
var FULLSTOP = 46;
var name9 = "ClassSelector";
var structure9 = {
  name: String
};
function parse10() {
  this.eatDelim(FULLSTOP);
  return {
    type: "ClassSelector",
    loc: this.getLocation(this.tokenStart - 1, this.tokenEnd),
    name: this.consume(Ident)
  };
}
function generate10(node) {
  this.token(Delim, ".");
  this.token(Ident, node.name);
}

// node_modules/css-tree/lib/syntax/node/Combinator.js
var Combinator_exports = {};
__export(Combinator_exports, {
  generate: () => generate11,
  name: () => name10,
  parse: () => parse11,
  structure: () => structure10
});
var PLUSSIGN6 = 43;
var SOLIDUS = 47;
var GREATERTHANSIGN2 = 62;
var TILDE2 = 126;
var name10 = "Combinator";
var structure10 = {
  name: String
};
function parse11() {
  const start = this.tokenStart;
  let name50;
  switch (this.tokenType) {
    case WhiteSpace:
      name50 = " ";
      break;
    case Delim:
      switch (this.charCodeAt(this.tokenStart)) {
        case GREATERTHANSIGN2:
        case PLUSSIGN6:
        case TILDE2:
          this.next();
          break;
        case SOLIDUS:
          this.next();
          this.eatIdent("deep");
          this.eatDelim(SOLIDUS);
          break;
        default:
          this.error("Combinator is expected");
      }
      name50 = this.substrToCursor(start);
      break;
  }
  return {
    type: "Combinator",
    loc: this.getLocation(start, this.tokenStart),
    name: name50
  };
}
function generate11(node) {
  this.tokenize(node.name);
}

// node_modules/css-tree/lib/syntax/node/Comment.js
var Comment_exports = {};
__export(Comment_exports, {
  generate: () => generate12,
  name: () => name11,
  parse: () => parse12,
  structure: () => structure11
});
var ASTERISK3 = 42;
var SOLIDUS2 = 47;
var name11 = "Comment";
var structure11 = {
  value: String
};
function parse12() {
  const start = this.tokenStart;
  let end = this.tokenEnd;
  this.eat(Comment);
  if (end - start + 2 >= 2 && this.charCodeAt(end - 2) === ASTERISK3 && this.charCodeAt(end - 1) === SOLIDUS2) {
    end -= 2;
  }
  return {
    type: "Comment",
    loc: this.getLocation(start, this.tokenStart),
    value: this.substring(start + 2, end)
  };
}
function generate12(node) {
  this.token(Comment, "/*" + node.value + "*/");
}

// node_modules/css-tree/lib/syntax/node/Condition.js
var Condition_exports = {};
__export(Condition_exports, {
  generate: () => generate13,
  name: () => name12,
  parse: () => parse13,
  structure: () => structure12
});
var likelyFeatureToken = /* @__PURE__ */ new Set([Colon, RightParenthesis, EOF]);
var name12 = "Condition";
var structure12 = {
  kind: String,
  children: [[
    "Identifier",
    "Feature",
    "FeatureFunction",
    "FeatureRange",
    "SupportsDeclaration"
  ]]
};
function featureOrRange(kind) {
  if (this.lookupTypeNonSC(1) === Ident && likelyFeatureToken.has(this.lookupTypeNonSC(2))) {
    return this.Feature(kind);
  }
  return this.FeatureRange(kind);
}
var parentheses = {
  media: featureOrRange,
  container: featureOrRange,
  supports() {
    return this.SupportsDeclaration();
  }
};
function parse13(kind = "media") {
  const children = this.createList();
  scan: while (!this.eof) {
    switch (this.tokenType) {
      case Comment:
      case WhiteSpace:
        this.next();
        continue;
      case Ident:
        children.push(this.Identifier());
        break;
      case LeftParenthesis: {
        let term = this.parseWithFallback(
          () => parentheses[kind].call(this, kind),
          () => null
        );
        if (!term) {
          term = this.parseWithFallback(
            () => {
              this.eat(LeftParenthesis);
              const res = this.Condition(kind);
              this.eat(RightParenthesis);
              return res;
            },
            () => {
              return this.GeneralEnclosed(kind);
            }
          );
        }
        children.push(term);
        break;
      }
      case Function2: {
        let term = this.parseWithFallback(
          () => this.FeatureFunction(kind),
          () => null
        );
        if (!term) {
          term = this.GeneralEnclosed(kind);
        }
        children.push(term);
        break;
      }
      default:
        break scan;
    }
  }
  if (children.isEmpty) {
    this.error("Condition is expected");
  }
  return {
    type: "Condition",
    loc: this.getLocationFromList(children),
    kind,
    children
  };
}
function generate13(node) {
  node.children.forEach((child) => {
    if (child.type === "Condition") {
      this.token(LeftParenthesis, "(");
      this.node(child);
      this.token(RightParenthesis, ")");
    } else {
      this.node(child);
    }
  });
}

// node_modules/css-tree/lib/syntax/node/Declaration.js
var Declaration_exports = {};
__export(Declaration_exports, {
  generate: () => generate14,
  name: () => name13,
  parse: () => parse14,
  structure: () => structure13,
  walkContext: () => walkContext4
});
var EXCLAMATIONMARK3 = 33;
var NUMBERSIGN3 = 35;
var DOLLARSIGN2 = 36;
var AMPERSAND3 = 38;
var ASTERISK4 = 42;
var PLUSSIGN7 = 43;
var SOLIDUS3 = 47;
function consumeValueRaw() {
  return this.Raw(this.consumeUntilExclamationMarkOrSemicolon, true);
}
function consumeCustomPropertyRaw() {
  return this.Raw(this.consumeUntilExclamationMarkOrSemicolon, false);
}
function consumeValue() {
  const startValueToken = this.tokenIndex;
  const value = this.Value();
  if (value.type !== "Raw" && this.eof === false && this.tokenType !== Semicolon && this.isDelim(EXCLAMATIONMARK3) === false && this.isBalanceEdge(startValueToken) === false) {
    this.error();
  }
  return value;
}
var name13 = "Declaration";
var walkContext4 = "declaration";
var structure13 = {
  important: [Boolean, String],
  property: String,
  value: ["Value", "Raw"]
};
function parse14() {
  const start = this.tokenStart;
  const startToken = this.tokenIndex;
  const property2 = readProperty2.call(this);
  const customProperty = isCustomProperty(property2);
  const parseValue = customProperty ? this.parseCustomProperty : this.parseValue;
  const consumeRaw6 = customProperty ? consumeCustomPropertyRaw : consumeValueRaw;
  let important = false;
  let value;
  this.skipSC();
  this.eat(Colon);
  const valueStart = this.tokenIndex;
  if (!customProperty) {
    this.skipSC();
  }
  if (parseValue) {
    value = this.parseWithFallback(consumeValue, consumeRaw6);
  } else {
    value = consumeRaw6.call(this, this.tokenIndex);
  }
  if (customProperty && value.type === "Value" && value.children.isEmpty) {
    for (let offset = valueStart - this.tokenIndex; offset <= 0; offset++) {
      if (this.lookupType(offset) === WhiteSpace) {
        value.children.appendData({
          type: "WhiteSpace",
          loc: null,
          value: " "
        });
        break;
      }
    }
  }
  if (this.isDelim(EXCLAMATIONMARK3)) {
    important = getImportant.call(this);
    this.skipSC();
  }
  if (this.eof === false && this.tokenType !== Semicolon && this.isBalanceEdge(startToken) === false) {
    this.error();
  }
  return {
    type: "Declaration",
    loc: this.getLocation(start, this.tokenStart),
    important,
    property: property2,
    value
  };
}
function generate14(node) {
  this.token(Ident, node.property);
  this.token(Colon, ":");
  this.node(node.value);
  if (node.important) {
    this.token(Delim, "!");
    this.token(Ident, node.important === true ? "important" : node.important);
  }
}
function readProperty2() {
  const start = this.tokenStart;
  if (this.tokenType === Delim) {
    switch (this.charCodeAt(this.tokenStart)) {
      case ASTERISK4:
      case DOLLARSIGN2:
      case PLUSSIGN7:
      case NUMBERSIGN3:
      case AMPERSAND3:
        this.next();
        break;
      // TODO: not sure we should support this hack
      case SOLIDUS3:
        this.next();
        if (this.isDelim(SOLIDUS3)) {
          this.next();
        }
        break;
    }
  }
  if (this.tokenType === Hash) {
    this.eat(Hash);
  } else {
    this.eat(Ident);
  }
  return this.substrToCursor(start);
}
function getImportant() {
  this.eat(Delim);
  this.skipSC();
  const important = this.consume(Ident);
  return important === "important" ? true : important;
}

// node_modules/css-tree/lib/syntax/node/DeclarationList.js
var DeclarationList_exports = {};
__export(DeclarationList_exports, {
  generate: () => generate15,
  name: () => name14,
  parse: () => parse15,
  structure: () => structure14
});
var AMPERSAND4 = 38;
function consumeRaw3() {
  return this.Raw(this.consumeUntilSemicolonIncluded, true);
}
var name14 = "DeclarationList";
var structure14 = {
  children: [[
    "Declaration",
    "Atrule",
    "Rule"
  ]]
};
function parse15() {
  const children = this.createList();
  scan:
    while (!this.eof) {
      switch (this.tokenType) {
        case WhiteSpace:
        case Comment:
        case Semicolon:
          this.next();
          break;
        case AtKeyword:
          children.push(this.parseWithFallback(this.Atrule.bind(this, true), consumeRaw3));
          break;
        default:
          if (this.isDelim(AMPERSAND4)) {
            children.push(this.parseWithFallback(this.Rule, consumeRaw3));
          } else {
            children.push(this.parseWithFallback(this.Declaration, consumeRaw3));
          }
      }
    }
  return {
    type: "DeclarationList",
    loc: this.getLocationFromList(children),
    children
  };
}
function generate15(node) {
  this.children(node, (prev) => {
    if (prev.type === "Declaration") {
      this.token(Semicolon, ";");
    }
  });
}

// node_modules/css-tree/lib/syntax/node/Dimension.js
var Dimension_exports = {};
__export(Dimension_exports, {
  generate: () => generate16,
  name: () => name15,
  parse: () => parse16,
  structure: () => structure15
});
var name15 = "Dimension";
var structure15 = {
  value: String,
  unit: String
};
function parse16() {
  const start = this.tokenStart;
  const value = this.consumeNumber(Dimension);
  return {
    type: "Dimension",
    loc: this.getLocation(start, this.tokenStart),
    value,
    unit: this.substring(start + value.length, this.tokenStart)
  };
}
function generate16(node) {
  this.token(Dimension, node.value + node.unit);
}

// node_modules/css-tree/lib/syntax/node/Feature.js
var Feature_exports = {};
__export(Feature_exports, {
  generate: () => generate17,
  name: () => name16,
  parse: () => parse17,
  structure: () => structure16
});
var SOLIDUS4 = 47;
var name16 = "Feature";
var structure16 = {
  kind: String,
  name: String,
  value: ["Identifier", "Number", "Dimension", "Ratio", "Function", null]
};
function parse17(kind) {
  const start = this.tokenStart;
  let name50;
  let value = null;
  this.eat(LeftParenthesis);
  this.skipSC();
  name50 = this.consume(Ident);
  this.skipSC();
  if (this.tokenType !== RightParenthesis) {
    this.eat(Colon);
    this.skipSC();
    switch (this.tokenType) {
      case Number2:
        if (this.lookupNonWSType(1) === Delim) {
          value = this.Ratio();
        } else {
          value = this.Number();
        }
        break;
      case Dimension:
        value = this.Dimension();
        break;
      case Ident:
        value = this.Identifier();
        break;
      case Function2:
        value = this.parseWithFallback(
          () => {
            const res = this.Function(this.readSequence, this.scope.Value);
            this.skipSC();
            if (this.isDelim(SOLIDUS4)) {
              this.error();
            }
            return res;
          },
          () => {
            return this.Ratio();
          }
        );
        break;
      default:
        this.error("Number, dimension, ratio or identifier is expected");
    }
    this.skipSC();
  }
  if (!this.eof) {
    this.eat(RightParenthesis);
  }
  return {
    type: "Feature",
    loc: this.getLocation(start, this.tokenStart),
    kind,
    name: name50,
    value
  };
}
function generate17(node) {
  this.token(LeftParenthesis, "(");
  this.token(Ident, node.name);
  if (node.value !== null) {
    this.token(Colon, ":");
    this.node(node.value);
  }
  this.token(RightParenthesis, ")");
}

// node_modules/css-tree/lib/syntax/node/FeatureFunction.js
var FeatureFunction_exports = {};
__export(FeatureFunction_exports, {
  generate: () => generate18,
  name: () => name17,
  parse: () => parse18,
  structure: () => structure17
});
var name17 = "FeatureFunction";
var structure17 = {
  kind: String,
  feature: String,
  value: ["Declaration", "Selector"]
};
function getFeatureParser(kind, name50) {
  const featuresOfKind = this.features[kind] || {};
  const parser = featuresOfKind[name50];
  if (typeof parser !== "function") {
    this.error(`Unknown feature ${name50}()`);
  }
  return parser;
}
function parse18(kind = "unknown") {
  const start = this.tokenStart;
  const functionName = this.consumeFunctionName();
  const valueParser = getFeatureParser.call(this, kind, functionName.toLowerCase());
  this.skipSC();
  const value = this.parseWithFallback(
    () => {
      const startValueToken = this.tokenIndex;
      const value2 = valueParser.call(this);
      if (this.eof === false && this.isBalanceEdge(startValueToken) === false) {
        this.error();
      }
      return value2;
    },
    () => this.Raw(null, false)
  );
  if (!this.eof) {
    this.eat(RightParenthesis);
  }
  return {
    type: "FeatureFunction",
    loc: this.getLocation(start, this.tokenStart),
    kind,
    feature: functionName,
    value
  };
}
function generate18(node) {
  this.token(Function2, node.feature + "(");
  this.node(node.value);
  this.token(RightParenthesis, ")");
}

// node_modules/css-tree/lib/syntax/node/FeatureRange.js
var FeatureRange_exports = {};
__export(FeatureRange_exports, {
  generate: () => generate19,
  name: () => name18,
  parse: () => parse19,
  structure: () => structure18
});
var SOLIDUS5 = 47;
var LESSTHANSIGN2 = 60;
var EQUALSSIGN2 = 61;
var GREATERTHANSIGN3 = 62;
var name18 = "FeatureRange";
var structure18 = {
  kind: String,
  left: ["Identifier", "Number", "Dimension", "Ratio", "Function"],
  leftComparison: String,
  middle: ["Identifier", "Number", "Dimension", "Ratio", "Function"],
  rightComparison: [String, null],
  right: ["Identifier", "Number", "Dimension", "Ratio", "Function", null]
};
function readTerm() {
  this.skipSC();
  switch (this.tokenType) {
    case Number2:
      if (this.isDelim(SOLIDUS5, this.lookupOffsetNonSC(1))) {
        return this.Ratio();
      } else {
        return this.Number();
      }
    case Dimension:
      return this.Dimension();
    case Ident:
      return this.Identifier();
    case Function2:
      return this.parseWithFallback(
        () => {
          const res = this.Function(this.readSequence, this.scope.Value);
          this.skipSC();
          if (this.isDelim(SOLIDUS5)) {
            this.error();
          }
          return res;
        },
        () => {
          return this.Ratio();
        }
      );
    default:
      this.error("Number, dimension, ratio or identifier is expected");
  }
}
function readComparison(expectColon) {
  this.skipSC();
  if (this.isDelim(LESSTHANSIGN2) || this.isDelim(GREATERTHANSIGN3)) {
    const value = this.source[this.tokenStart];
    this.next();
    if (this.isDelim(EQUALSSIGN2)) {
      this.next();
      return value + "=";
    }
    return value;
  }
  if (this.isDelim(EQUALSSIGN2)) {
    return "=";
  }
  this.error(`Expected ${expectColon ? '":", ' : ""}"<", ">", "=" or ")"`);
}
function parse19(kind = "unknown") {
  const start = this.tokenStart;
  this.skipSC();
  this.eat(LeftParenthesis);
  const left = readTerm.call(this);
  const leftComparison = readComparison.call(this, left.type === "Identifier");
  const middle = readTerm.call(this);
  let rightComparison = null;
  let right = null;
  if (this.lookupNonWSType(0) !== RightParenthesis) {
    rightComparison = readComparison.call(this);
    right = readTerm.call(this);
  }
  this.skipSC();
  this.eat(RightParenthesis);
  return {
    type: "FeatureRange",
    loc: this.getLocation(start, this.tokenStart),
    kind,
    left,
    leftComparison,
    middle,
    rightComparison,
    right
  };
}
function generate19(node) {
  this.token(LeftParenthesis, "(");
  this.node(node.left);
  this.tokenize(node.leftComparison);
  this.node(node.middle);
  if (node.right) {
    this.tokenize(node.rightComparison);
    this.node(node.right);
  }
  this.token(RightParenthesis, ")");
}

// node_modules/css-tree/lib/syntax/node/Function.js
var Function_exports = {};
__export(Function_exports, {
  generate: () => generate20,
  name: () => name19,
  parse: () => parse20,
  structure: () => structure19,
  walkContext: () => walkContext5
});
var name19 = "Function";
var walkContext5 = "function";
var structure19 = {
  name: String,
  children: [[]]
};
function parse20(readSequence2, recognizer) {
  const start = this.tokenStart;
  const name50 = this.consumeFunctionName();
  const nameLowerCase = name50.toLowerCase();
  let children;
  children = recognizer.hasOwnProperty(nameLowerCase) ? recognizer[nameLowerCase].call(this, recognizer) : readSequence2.call(this, recognizer);
  if (!this.eof) {
    this.eat(RightParenthesis);
  }
  return {
    type: "Function",
    loc: this.getLocation(start, this.tokenStart),
    name: name50,
    children
  };
}
function generate20(node) {
  this.token(Function2, node.name + "(");
  this.children(node);
  this.token(RightParenthesis, ")");
}

// node_modules/css-tree/lib/syntax/node/GeneralEnclosed.js
var GeneralEnclosed_exports = {};
__export(GeneralEnclosed_exports, {
  generate: () => generate21,
  name: () => name20,
  parse: () => parse21,
  structure: () => structure20
});
var name20 = "GeneralEnclosed";
var structure20 = {
  kind: String,
  function: [String, null],
  children: [[]]
};
function parse21(kind) {
  const start = this.tokenStart;
  let functionName = null;
  if (this.tokenType === Function2) {
    functionName = this.consumeFunctionName();
  } else {
    this.eat(LeftParenthesis);
  }
  const children = this.parseWithFallback(
    () => {
      const startValueToken = this.tokenIndex;
      const children2 = this.readSequence(this.scope.Value);
      if (this.eof === false && this.isBalanceEdge(startValueToken) === false) {
        this.error();
      }
      return children2;
    },
    () => this.createSingleNodeList(
      this.Raw(null, false)
    )
  );
  if (!this.eof) {
    this.eat(RightParenthesis);
  }
  return {
    type: "GeneralEnclosed",
    loc: this.getLocation(start, this.tokenStart),
    kind,
    function: functionName,
    children
  };
}
function generate21(node) {
  if (node.function) {
    this.token(Function2, node.function + "(");
  } else {
    this.token(LeftParenthesis, "(");
  }
  this.children(node);
  this.token(RightParenthesis, ")");
}

// node_modules/css-tree/lib/syntax/node/Hash.js
var Hash_exports = {};
__export(Hash_exports, {
  generate: () => generate22,
  name: () => name21,
  parse: () => parse22,
  structure: () => structure21,
  xxx: () => xxx
});
var xxx = "XXX";
var name21 = "Hash";
var structure21 = {
  value: String
};
function parse22() {
  const start = this.tokenStart;
  this.eat(Hash);
  return {
    type: "Hash",
    loc: this.getLocation(start, this.tokenStart),
    value: this.substrToCursor(start + 1)
  };
}
function generate22(node) {
  this.token(Hash, "#" + node.value);
}

// node_modules/css-tree/lib/syntax/node/Identifier.js
var Identifier_exports = {};
__export(Identifier_exports, {
  generate: () => generate23,
  name: () => name22,
  parse: () => parse23,
  structure: () => structure22
});
var name22 = "Identifier";
var structure22 = {
  name: String
};
function parse23() {
  return {
    type: "Identifier",
    loc: this.getLocation(this.tokenStart, this.tokenEnd),
    name: this.consume(Ident)
  };
}
function generate23(node) {
  this.token(Ident, node.name);
}

// node_modules/css-tree/lib/syntax/node/IdSelector.js
var IdSelector_exports = {};
__export(IdSelector_exports, {
  generate: () => generate24,
  name: () => name23,
  parse: () => parse24,
  structure: () => structure23
});
var name23 = "IdSelector";
var structure23 = {
  name: String
};
function parse24() {
  const start = this.tokenStart;
  this.eat(Hash);
  return {
    type: "IdSelector",
    loc: this.getLocation(start, this.tokenStart),
    name: this.substrToCursor(start + 1)
  };
}
function generate24(node) {
  this.token(Delim, "#" + node.name);
}

// node_modules/css-tree/lib/syntax/node/Layer.js
var Layer_exports = {};
__export(Layer_exports, {
  generate: () => generate25,
  name: () => name24,
  parse: () => parse25,
  structure: () => structure24
});
var FULLSTOP2 = 46;
var name24 = "Layer";
var structure24 = {
  name: String
};
function parse25() {
  let tokenStart = this.tokenStart;
  let name50 = this.consume(Ident);
  while (this.isDelim(FULLSTOP2)) {
    this.eat(Delim);
    name50 += "." + this.consume(Ident);
  }
  return {
    type: "Layer",
    loc: this.getLocation(tokenStart, this.tokenStart),
    name: name50
  };
}
function generate25(node) {
  this.tokenize(node.name);
}

// node_modules/css-tree/lib/syntax/node/LayerList.js
var LayerList_exports = {};
__export(LayerList_exports, {
  generate: () => generate26,
  name: () => name25,
  parse: () => parse26,
  structure: () => structure25
});
var name25 = "LayerList";
var structure25 = {
  children: [[
    "Layer"
  ]]
};
function parse26() {
  const children = this.createList();
  this.skipSC();
  while (!this.eof) {
    children.push(this.Layer());
    if (this.lookupTypeNonSC(0) !== Comma) {
      break;
    }
    this.skipSC();
    this.next();
    this.skipSC();
  }
  return {
    type: "LayerList",
    loc: this.getLocationFromList(children),
    children
  };
}
function generate26(node) {
  this.children(node, () => this.token(Comma, ","));
}

// node_modules/css-tree/lib/syntax/node/MediaQuery.js
var MediaQuery_exports = {};
__export(MediaQuery_exports, {
  generate: () => generate27,
  name: () => name26,
  parse: () => parse27,
  structure: () => structure26
});
var name26 = "MediaQuery";
var structure26 = {
  modifier: [String, null],
  mediaType: [String, null],
  condition: ["Condition", null]
};
function parse27() {
  const start = this.tokenStart;
  let modifier = null;
  let mediaType = null;
  let condition = null;
  this.skipSC();
  if (this.tokenType === Ident && this.lookupTypeNonSC(1) !== LeftParenthesis) {
    const ident = this.consume(Ident);
    const identLowerCase = ident.toLowerCase();
    if (identLowerCase === "not" || identLowerCase === "only") {
      this.skipSC();
      modifier = identLowerCase;
      mediaType = this.consume(Ident);
    } else {
      mediaType = ident;
    }
    switch (this.lookupTypeNonSC(0)) {
      case Ident: {
        this.skipSC();
        this.eatIdent("and");
        condition = this.Condition("media");
        break;
      }
      case LeftCurlyBracket:
      case Semicolon:
      case Comma:
      case EOF:
        break;
      default:
        this.error("Identifier or parenthesis is expected");
    }
  } else {
    switch (this.tokenType) {
      case Ident:
      case LeftParenthesis:
      case Function2: {
        condition = this.Condition("media");
        break;
      }
      case LeftCurlyBracket:
      case Semicolon:
      case EOF:
        break;
      default:
        this.error("Identifier or parenthesis is expected");
    }
  }
  return {
    type: "MediaQuery",
    loc: this.getLocation(start, this.tokenStart),
    modifier,
    mediaType,
    condition
  };
}
function generate27(node) {
  if (node.mediaType) {
    if (node.modifier) {
      this.token(Ident, node.modifier);
    }
    this.token(Ident, node.mediaType);
    if (node.condition) {
      this.token(Ident, "and");
      this.node(node.condition);
    }
  } else if (node.condition) {
    this.node(node.condition);
  }
}

// node_modules/css-tree/lib/syntax/node/MediaQueryList.js
var MediaQueryList_exports = {};
__export(MediaQueryList_exports, {
  generate: () => generate28,
  name: () => name27,
  parse: () => parse28,
  structure: () => structure27
});
var name27 = "MediaQueryList";
var structure27 = {
  children: [[
    "MediaQuery"
  ]]
};
function parse28() {
  const children = this.createList();
  this.skipSC();
  while (!this.eof) {
    children.push(this.MediaQuery());
    if (this.tokenType !== Comma) {
      break;
    }
    this.next();
  }
  return {
    type: "MediaQueryList",
    loc: this.getLocationFromList(children),
    children
  };
}
function generate28(node) {
  this.children(node, () => this.token(Comma, ","));
}

// node_modules/css-tree/lib/syntax/node/NestingSelector.js
var NestingSelector_exports = {};
__export(NestingSelector_exports, {
  generate: () => generate29,
  name: () => name28,
  parse: () => parse29,
  structure: () => structure28
});
var AMPERSAND5 = 38;
var name28 = "NestingSelector";
var structure28 = {};
function parse29() {
  const start = this.tokenStart;
  this.eatDelim(AMPERSAND5);
  return {
    type: "NestingSelector",
    loc: this.getLocation(start, this.tokenStart)
  };
}
function generate29() {
  this.token(Delim, "&");
}

// node_modules/css-tree/lib/syntax/node/Nth.js
var Nth_exports = {};
__export(Nth_exports, {
  generate: () => generate30,
  name: () => name29,
  parse: () => parse30,
  structure: () => structure29
});
var name29 = "Nth";
var structure29 = {
  nth: ["AnPlusB", "Identifier"],
  selector: ["SelectorList", null]
};
function parse30() {
  this.skipSC();
  const start = this.tokenStart;
  let end = start;
  let selector2 = null;
  let nth2;
  if (this.lookupValue(0, "odd") || this.lookupValue(0, "even")) {
    nth2 = this.Identifier();
  } else {
    nth2 = this.AnPlusB();
  }
  end = this.tokenStart;
  this.skipSC();
  if (this.lookupValue(0, "of")) {
    this.next();
    selector2 = this.SelectorList();
    end = this.tokenStart;
  }
  return {
    type: "Nth",
    loc: this.getLocation(start, end),
    nth: nth2,
    selector: selector2
  };
}
function generate30(node) {
  this.node(node.nth);
  if (node.selector !== null) {
    this.token(Ident, "of");
    this.node(node.selector);
  }
}

// node_modules/css-tree/lib/syntax/node/Number.js
var Number_exports = {};
__export(Number_exports, {
  generate: () => generate31,
  name: () => name30,
  parse: () => parse31,
  structure: () => structure30
});
var name30 = "Number";
var structure30 = {
  value: String
};
function parse31() {
  return {
    type: "Number",
    loc: this.getLocation(this.tokenStart, this.tokenEnd),
    value: this.consume(Number2)
  };
}
function generate31(node) {
  this.token(Number2, node.value);
}

// node_modules/css-tree/lib/syntax/node/Operator.js
var Operator_exports = {};
__export(Operator_exports, {
  generate: () => generate32,
  name: () => name31,
  parse: () => parse32,
  structure: () => structure31
});
var name31 = "Operator";
var structure31 = {
  value: String
};
function parse32() {
  const start = this.tokenStart;
  this.next();
  return {
    type: "Operator",
    loc: this.getLocation(start, this.tokenStart),
    value: this.substrToCursor(start)
  };
}
function generate32(node) {
  this.tokenize(node.value);
}

// node_modules/css-tree/lib/syntax/node/Parentheses.js
var Parentheses_exports = {};
__export(Parentheses_exports, {
  generate: () => generate33,
  name: () => name32,
  parse: () => parse33,
  structure: () => structure32
});
var name32 = "Parentheses";
var structure32 = {
  children: [[]]
};
function parse33(readSequence2, recognizer) {
  const start = this.tokenStart;
  let children = null;
  this.eat(LeftParenthesis);
  children = readSequence2.call(this, recognizer);
  if (!this.eof) {
    this.eat(RightParenthesis);
  }
  return {
    type: "Parentheses",
    loc: this.getLocation(start, this.tokenStart),
    children
  };
}
function generate33(node) {
  this.token(LeftParenthesis, "(");
  this.children(node);
  this.token(RightParenthesis, ")");
}

// node_modules/css-tree/lib/syntax/node/Percentage.js
var Percentage_exports = {};
__export(Percentage_exports, {
  generate: () => generate34,
  name: () => name33,
  parse: () => parse34,
  structure: () => structure33
});
var name33 = "Percentage";
var structure33 = {
  value: String
};
function parse34() {
  return {
    type: "Percentage",
    loc: this.getLocation(this.tokenStart, this.tokenEnd),
    value: this.consumeNumber(Percentage)
  };
}
function generate34(node) {
  this.token(Percentage, node.value + "%");
}

// node_modules/css-tree/lib/syntax/node/PseudoClassSelector.js
var PseudoClassSelector_exports = {};
__export(PseudoClassSelector_exports, {
  generate: () => generate35,
  name: () => name34,
  parse: () => parse35,
  structure: () => structure34,
  walkContext: () => walkContext6
});
var name34 = "PseudoClassSelector";
var walkContext6 = "function";
var structure34 = {
  name: String,
  children: [["Raw"], null]
};
function parse35() {
  const start = this.tokenStart;
  let children = null;
  let name50;
  let nameLowerCase;
  this.eat(Colon);
  if (this.tokenType === Function2) {
    name50 = this.consumeFunctionName();
    nameLowerCase = name50.toLowerCase();
    if (this.lookupNonWSType(0) == RightParenthesis) {
      children = this.createList();
    } else if (hasOwnProperty.call(this.pseudo, nameLowerCase)) {
      this.skipSC();
      children = this.pseudo[nameLowerCase].call(this);
      this.skipSC();
    } else {
      children = this.createList();
      children.push(
        this.Raw(null, false)
      );
    }
    this.eat(RightParenthesis);
  } else {
    name50 = this.consume(Ident);
  }
  return {
    type: "PseudoClassSelector",
    loc: this.getLocation(start, this.tokenStart),
    name: name50,
    children
  };
}
function generate35(node) {
  this.token(Colon, ":");
  if (node.children === null) {
    this.token(Ident, node.name);
  } else {
    this.token(Function2, node.name + "(");
    this.children(node);
    this.token(RightParenthesis, ")");
  }
}

// node_modules/css-tree/lib/syntax/node/PseudoElementSelector.js
var PseudoElementSelector_exports = {};
__export(PseudoElementSelector_exports, {
  generate: () => generate36,
  name: () => name35,
  parse: () => parse36,
  structure: () => structure35,
  walkContext: () => walkContext7
});
var name35 = "PseudoElementSelector";
var walkContext7 = "function";
var structure35 = {
  name: String,
  children: [["Raw"], null]
};
function parse36() {
  const start = this.tokenStart;
  let children = null;
  let name50;
  let nameLowerCase;
  this.eat(Colon);
  this.eat(Colon);
  if (this.tokenType === Function2) {
    name50 = this.consumeFunctionName();
    nameLowerCase = name50.toLowerCase();
    if (this.lookupNonWSType(0) == RightParenthesis) {
      children = this.createList();
    } else if (hasOwnProperty.call(this.pseudo, nameLowerCase)) {
      this.skipSC();
      children = this.pseudo[nameLowerCase].call(this);
      this.skipSC();
    } else {
      children = this.createList();
      children.push(
        this.Raw(null, false)
      );
    }
    this.eat(RightParenthesis);
  } else {
    name50 = this.consume(Ident);
  }
  return {
    type: "PseudoElementSelector",
    loc: this.getLocation(start, this.tokenStart),
    name: name50,
    children
  };
}
function generate36(node) {
  this.token(Colon, ":");
  this.token(Colon, ":");
  if (node.children === null) {
    this.token(Ident, node.name);
  } else {
    this.token(Function2, node.name + "(");
    this.children(node);
    this.token(RightParenthesis, ")");
  }
}

// node_modules/css-tree/lib/syntax/node/Ratio.js
var Ratio_exports = {};
__export(Ratio_exports, {
  generate: () => generate37,
  name: () => name36,
  parse: () => parse37,
  structure: () => structure36
});
var SOLIDUS6 = 47;
function consumeTerm() {
  this.skipSC();
  switch (this.tokenType) {
    case Number2:
      return this.Number();
    case Function2:
      return this.Function(this.readSequence, this.scope.Value);
    default:
      this.error("Number of function is expected");
  }
}
var name36 = "Ratio";
var structure36 = {
  left: ["Number", "Function"],
  right: ["Number", "Function", null]
};
function parse37() {
  const start = this.tokenStart;
  const left = consumeTerm.call(this);
  let right = null;
  this.skipSC();
  if (this.isDelim(SOLIDUS6)) {
    this.eatDelim(SOLIDUS6);
    right = consumeTerm.call(this);
  }
  return {
    type: "Ratio",
    loc: this.getLocation(start, this.tokenStart),
    left,
    right
  };
}
function generate37(node) {
  this.node(node.left);
  this.token(Delim, "/");
  if (node.right) {
    this.node(node.right);
  } else {
    this.node(Number2, 1);
  }
}

// node_modules/css-tree/lib/syntax/node/Raw.js
var Raw_exports = {};
__export(Raw_exports, {
  generate: () => generate38,
  name: () => name37,
  parse: () => parse38,
  structure: () => structure37
});
function getOffsetExcludeWS() {
  if (this.tokenIndex > 0) {
    if (this.lookupType(-1) === WhiteSpace) {
      return this.tokenIndex > 1 ? this.getTokenStart(this.tokenIndex - 1) : this.firstCharOffset;
    }
  }
  return this.tokenStart;
}
var name37 = "Raw";
var structure37 = {
  value: String
};
function parse38(consumeUntil, excludeWhiteSpace) {
  const startOffset = this.getTokenStart(this.tokenIndex);
  let endOffset;
  this.skipUntilBalanced(this.tokenIndex, consumeUntil || this.consumeUntilBalanceEnd);
  if (excludeWhiteSpace && this.tokenStart > startOffset) {
    endOffset = getOffsetExcludeWS.call(this);
  } else {
    endOffset = this.tokenStart;
  }
  return {
    type: "Raw",
    loc: this.getLocation(startOffset, endOffset),
    value: this.substring(startOffset, endOffset)
  };
}
function generate38(node) {
  this.tokenize(node.value);
}

// node_modules/css-tree/lib/syntax/node/Rule.js
var Rule_exports = {};
__export(Rule_exports, {
  generate: () => generate39,
  name: () => name38,
  parse: () => parse39,
  structure: () => structure38,
  walkContext: () => walkContext8
});
function consumeRaw4() {
  return this.Raw(this.consumeUntilLeftCurlyBracket, true);
}
function consumePrelude() {
  const prelude = this.SelectorList();
  if (prelude.type !== "Raw" && this.eof === false && this.tokenType !== LeftCurlyBracket) {
    this.error();
  }
  return prelude;
}
var name38 = "Rule";
var walkContext8 = "rule";
var structure38 = {
  prelude: ["SelectorList", "Raw"],
  block: ["Block"]
};
function parse39() {
  const startToken = this.tokenIndex;
  const startOffset = this.tokenStart;
  let prelude;
  let block;
  if (this.parseRulePrelude) {
    prelude = this.parseWithFallback(consumePrelude, consumeRaw4);
  } else {
    prelude = consumeRaw4.call(this, startToken);
  }
  block = this.Block(true);
  return {
    type: "Rule",
    loc: this.getLocation(startOffset, this.tokenStart),
    prelude,
    block
  };
}
function generate39(node) {
  this.node(node.prelude);
  this.node(node.block);
}

// node_modules/css-tree/lib/syntax/node/Scope.js
var Scope_exports = {};
__export(Scope_exports, {
  generate: () => generate40,
  name: () => name39,
  parse: () => parse40,
  structure: () => structure39
});
var name39 = "Scope";
var structure39 = {
  root: ["SelectorList", "Raw", null],
  limit: ["SelectorList", "Raw", null]
};
function parse40() {
  let root = null;
  let limit = null;
  this.skipSC();
  const startOffset = this.tokenStart;
  if (this.tokenType === LeftParenthesis) {
    this.next();
    this.skipSC();
    root = this.parseWithFallback(
      this.SelectorList,
      () => this.Raw(false, true)
    );
    this.skipSC();
    this.eat(RightParenthesis);
  }
  if (this.lookupNonWSType(0) === Ident) {
    this.skipSC();
    this.eatIdent("to");
    this.skipSC();
    this.eat(LeftParenthesis);
    this.skipSC();
    limit = this.parseWithFallback(
      this.SelectorList,
      () => this.Raw(false, true)
    );
    this.skipSC();
    this.eat(RightParenthesis);
  }
  return {
    type: "Scope",
    loc: this.getLocation(startOffset, this.tokenStart),
    root,
    limit
  };
}
function generate40(node) {
  if (node.root) {
    this.token(LeftParenthesis, "(");
    this.node(node.root);
    this.token(RightParenthesis, ")");
  }
  if (node.limit) {
    this.token(Ident, "to");
    this.token(LeftParenthesis, "(");
    this.node(node.limit);
    this.token(RightParenthesis, ")");
  }
}

// node_modules/css-tree/lib/syntax/node/Selector.js
var Selector_exports = {};
__export(Selector_exports, {
  generate: () => generate41,
  name: () => name40,
  parse: () => parse41,
  structure: () => structure40
});
var name40 = "Selector";
var structure40 = {
  children: [[
    "TypeSelector",
    "IdSelector",
    "ClassSelector",
    "AttributeSelector",
    "PseudoClassSelector",
    "PseudoElementSelector",
    "Combinator"
  ]]
};
function parse41() {
  const children = this.readSequence(this.scope.Selector);
  if (this.getFirstListNode(children) === null) {
    this.error("Selector is expected");
  }
  return {
    type: "Selector",
    loc: this.getLocationFromList(children),
    children
  };
}
function generate41(node) {
  this.children(node);
}

// node_modules/css-tree/lib/syntax/node/SelectorList.js
var SelectorList_exports = {};
__export(SelectorList_exports, {
  generate: () => generate42,
  name: () => name41,
  parse: () => parse42,
  structure: () => structure41,
  walkContext: () => walkContext9
});
var name41 = "SelectorList";
var walkContext9 = "selector";
var structure41 = {
  children: [[
    "Selector",
    "Raw"
  ]]
};
function parse42() {
  const children = this.createList();
  while (!this.eof) {
    children.push(this.Selector());
    if (this.tokenType === Comma) {
      this.next();
      continue;
    }
    break;
  }
  return {
    type: "SelectorList",
    loc: this.getLocationFromList(children),
    children
  };
}
function generate42(node) {
  this.children(node, () => this.token(Comma, ","));
}

// node_modules/css-tree/lib/syntax/node/String.js
var String_exports = {};
__export(String_exports, {
  generate: () => generate43,
  name: () => name42,
  parse: () => parse43,
  structure: () => structure42
});

// node_modules/css-tree/lib/utils/string.js
var REVERSE_SOLIDUS = 92;
var QUOTATION_MARK = 34;
var APOSTROPHE2 = 39;
function decode(str) {
  const len = str.length;
  const firstChar = str.charCodeAt(0);
  const start = firstChar === QUOTATION_MARK || firstChar === APOSTROPHE2 ? 1 : 0;
  const end = start === 1 && len > 1 && str.charCodeAt(len - 1) === firstChar ? len - 2 : len - 1;
  let decoded = "";
  for (let i = start; i <= end; i++) {
    let code2 = str.charCodeAt(i);
    if (code2 === REVERSE_SOLIDUS) {
      if (i === end) {
        if (i !== len - 1) {
          decoded = str.substr(i + 1);
        }
        break;
      }
      code2 = str.charCodeAt(++i);
      if (isValidEscape(REVERSE_SOLIDUS, code2)) {
        const escapeStart = i - 1;
        const escapeEnd = consumeEscaped(str, escapeStart);
        i = escapeEnd - 1;
        decoded += decodeEscaped(str.substring(escapeStart + 1, escapeEnd));
      } else {
        if (code2 === 13 && str.charCodeAt(i + 1) === 10) {
          i++;
        }
      }
    } else {
      decoded += str[i];
    }
  }
  return decoded;
}
function encode(str, apostrophe) {
  const quote = apostrophe ? "'" : '"';
  const quoteCode = apostrophe ? APOSTROPHE2 : QUOTATION_MARK;
  let encoded = "";
  let wsBeforeHexIsNeeded = false;
  for (let i = 0; i < str.length; i++) {
    const code2 = str.charCodeAt(i);
    if (code2 === 0) {
      encoded += "\uFFFD";
      continue;
    }
    if (code2 <= 31 || code2 === 127) {
      encoded += "\\" + code2.toString(16);
      wsBeforeHexIsNeeded = true;
      continue;
    }
    if (code2 === quoteCode || code2 === REVERSE_SOLIDUS) {
      encoded += "\\" + str.charAt(i);
      wsBeforeHexIsNeeded = false;
    } else {
      if (wsBeforeHexIsNeeded && (isHexDigit(code2) || isWhiteSpace(code2))) {
        encoded += " ";
      }
      encoded += str.charAt(i);
      wsBeforeHexIsNeeded = false;
    }
  }
  return quote + encoded + quote;
}

// node_modules/css-tree/lib/syntax/node/String.js
var name42 = "String";
var structure42 = {
  value: String
};
function parse43() {
  return {
    type: "String",
    loc: this.getLocation(this.tokenStart, this.tokenEnd),
    value: decode(this.consume(String2))
  };
}
function generate43(node) {
  this.token(String2, encode(node.value));
}

// node_modules/css-tree/lib/syntax/node/StyleSheet.js
var StyleSheet_exports = {};
__export(StyleSheet_exports, {
  generate: () => generate44,
  name: () => name43,
  parse: () => parse44,
  structure: () => structure43,
  walkContext: () => walkContext10
});
var EXCLAMATIONMARK4 = 33;
function consumeRaw5() {
  return this.Raw(null, false);
}
var name43 = "StyleSheet";
var walkContext10 = "stylesheet";
var structure43 = {
  children: [[
    "Comment",
    "CDO",
    "CDC",
    "Atrule",
    "Rule",
    "Raw"
  ]]
};
function parse44() {
  const start = this.tokenStart;
  const children = this.createList();
  let child;
  scan:
    while (!this.eof) {
      switch (this.tokenType) {
        case WhiteSpace:
          this.next();
          continue;
        case Comment:
          if (this.charCodeAt(this.tokenStart + 2) !== EXCLAMATIONMARK4) {
            this.next();
            continue;
          }
          child = this.Comment();
          break;
        case CDO:
          child = this.CDO();
          break;
        case CDC:
          child = this.CDC();
          break;
        // CSS Syntax Module Level 3
        // §2.2 Error handling
        // At the "top level" of a stylesheet, an <at-keyword-token> starts an at-rule.
        case AtKeyword:
          child = this.parseWithFallback(this.Atrule, consumeRaw5);
          break;
        // Anything else starts a qualified rule ...
        default:
          child = this.parseWithFallback(this.Rule, consumeRaw5);
      }
      children.push(child);
    }
  return {
    type: "StyleSheet",
    loc: this.getLocation(start, this.tokenStart),
    children
  };
}
function generate44(node) {
  this.children(node);
}

// node_modules/css-tree/lib/syntax/node/SupportsDeclaration.js
var SupportsDeclaration_exports = {};
__export(SupportsDeclaration_exports, {
  generate: () => generate45,
  name: () => name44,
  parse: () => parse45,
  structure: () => structure44
});
var name44 = "SupportsDeclaration";
var structure44 = {
  declaration: "Declaration"
};
function parse45() {
  const start = this.tokenStart;
  this.eat(LeftParenthesis);
  this.skipSC();
  const declaration = this.Declaration();
  if (!this.eof) {
    this.eat(RightParenthesis);
  }
  return {
    type: "SupportsDeclaration",
    loc: this.getLocation(start, this.tokenStart),
    declaration
  };
}
function generate45(node) {
  this.token(LeftParenthesis, "(");
  this.node(node.declaration);
  this.token(RightParenthesis, ")");
}

// node_modules/css-tree/lib/syntax/node/TypeSelector.js
var TypeSelector_exports = {};
__export(TypeSelector_exports, {
  generate: () => generate46,
  name: () => name45,
  parse: () => parse46,
  structure: () => structure45
});
var ASTERISK5 = 42;
var VERTICALLINE3 = 124;
function eatIdentifierOrAsterisk() {
  if (this.tokenType !== Ident && this.isDelim(ASTERISK5) === false) {
    this.error("Identifier or asterisk is expected");
  }
  this.next();
}
var name45 = "TypeSelector";
var structure45 = {
  name: String
};
function parse46() {
  const start = this.tokenStart;
  if (this.isDelim(VERTICALLINE3)) {
    this.next();
    eatIdentifierOrAsterisk.call(this);
  } else {
    eatIdentifierOrAsterisk.call(this);
    if (this.isDelim(VERTICALLINE3)) {
      this.next();
      eatIdentifierOrAsterisk.call(this);
    }
  }
  return {
    type: "TypeSelector",
    loc: this.getLocation(start, this.tokenStart),
    name: this.substrToCursor(start)
  };
}
function generate46(node) {
  this.tokenize(node.name);
}

// node_modules/css-tree/lib/syntax/node/UnicodeRange.js
var UnicodeRange_exports = {};
__export(UnicodeRange_exports, {
  generate: () => generate47,
  name: () => name46,
  parse: () => parse47,
  structure: () => structure46
});
var PLUSSIGN8 = 43;
var HYPHENMINUS6 = 45;
var QUESTIONMARK3 = 63;
function eatHexSequence(offset, allowDash) {
  let len = 0;
  for (let pos = this.tokenStart + offset; pos < this.tokenEnd; pos++) {
    const code2 = this.charCodeAt(pos);
    if (code2 === HYPHENMINUS6 && allowDash && len !== 0) {
      eatHexSequence.call(this, offset + len + 1, false);
      return -1;
    }
    if (!isHexDigit(code2)) {
      this.error(
        allowDash && len !== 0 ? "Hyphen minus" + (len < 6 ? " or hex digit" : "") + " is expected" : len < 6 ? "Hex digit is expected" : "Unexpected input",
        pos
      );
    }
    if (++len > 6) {
      this.error("Too many hex digits", pos);
    }
    ;
  }
  this.next();
  return len;
}
function eatQuestionMarkSequence(max) {
  let count = 0;
  while (this.isDelim(QUESTIONMARK3)) {
    if (++count > max) {
      this.error("Too many question marks");
    }
    this.next();
  }
}
function startsWith2(code2) {
  if (this.charCodeAt(this.tokenStart) !== code2) {
    this.error((code2 === PLUSSIGN8 ? "Plus sign" : "Hyphen minus") + " is expected");
  }
}
function scanUnicodeRange() {
  let hexLength = 0;
  switch (this.tokenType) {
    case Number2:
      hexLength = eatHexSequence.call(this, 1, true);
      if (this.isDelim(QUESTIONMARK3)) {
        eatQuestionMarkSequence.call(this, 6 - hexLength);
        break;
      }
      if (this.tokenType === Dimension || this.tokenType === Number2) {
        startsWith2.call(this, HYPHENMINUS6);
        eatHexSequence.call(this, 1, false);
        break;
      }
      break;
    case Dimension:
      hexLength = eatHexSequence.call(this, 1, true);
      if (hexLength > 0) {
        eatQuestionMarkSequence.call(this, 6 - hexLength);
      }
      break;
    default:
      this.eatDelim(PLUSSIGN8);
      if (this.tokenType === Ident) {
        hexLength = eatHexSequence.call(this, 0, true);
        if (hexLength > 0) {
          eatQuestionMarkSequence.call(this, 6 - hexLength);
        }
        break;
      }
      if (this.isDelim(QUESTIONMARK3)) {
        this.next();
        eatQuestionMarkSequence.call(this, 5);
        break;
      }
      this.error("Hex digit or question mark is expected");
  }
}
var name46 = "UnicodeRange";
var structure46 = {
  value: String
};
function parse47() {
  const start = this.tokenStart;
  this.eatIdent("u");
  scanUnicodeRange.call(this);
  return {
    type: "UnicodeRange",
    loc: this.getLocation(start, this.tokenStart),
    value: this.substrToCursor(start)
  };
}
function generate47(node) {
  this.tokenize(node.value);
}

// node_modules/css-tree/lib/syntax/node/Url.js
var Url_exports = {};
__export(Url_exports, {
  generate: () => generate48,
  name: () => name47,
  parse: () => parse48,
  structure: () => structure47
});

// node_modules/css-tree/lib/utils/url.js
var SPACE3 = 32;
var REVERSE_SOLIDUS2 = 92;
var QUOTATION_MARK2 = 34;
var APOSTROPHE3 = 39;
var LEFTPARENTHESIS3 = 40;
var RIGHTPARENTHESIS3 = 41;
function decode2(str) {
  const len = str.length;
  let start = 4;
  let end = str.charCodeAt(len - 1) === RIGHTPARENTHESIS3 ? len - 2 : len - 1;
  let decoded = "";
  while (start < end && isWhiteSpace(str.charCodeAt(start))) {
    start++;
  }
  while (start < end && isWhiteSpace(str.charCodeAt(end))) {
    end--;
  }
  for (let i = start; i <= end; i++) {
    let code2 = str.charCodeAt(i);
    if (code2 === REVERSE_SOLIDUS2) {
      if (i === end) {
        if (i !== len - 1) {
          decoded = str.substr(i + 1);
        }
        break;
      }
      code2 = str.charCodeAt(++i);
      if (isValidEscape(REVERSE_SOLIDUS2, code2)) {
        const escapeStart = i - 1;
        const escapeEnd = consumeEscaped(str, escapeStart);
        i = escapeEnd - 1;
        decoded += decodeEscaped(str.substring(escapeStart + 1, escapeEnd));
      } else {
        if (code2 === 13 && str.charCodeAt(i + 1) === 10) {
          i++;
        }
      }
    } else {
      decoded += str[i];
    }
  }
  return decoded;
}
function encode2(str) {
  let encoded = "";
  let wsBeforeHexIsNeeded = false;
  for (let i = 0; i < str.length; i++) {
    const code2 = str.charCodeAt(i);
    if (code2 === 0) {
      encoded += "\uFFFD";
      continue;
    }
    if (code2 <= 31 || code2 === 127) {
      encoded += "\\" + code2.toString(16);
      wsBeforeHexIsNeeded = true;
      continue;
    }
    if (code2 === SPACE3 || code2 === REVERSE_SOLIDUS2 || code2 === QUOTATION_MARK2 || code2 === APOSTROPHE3 || code2 === LEFTPARENTHESIS3 || code2 === RIGHTPARENTHESIS3) {
      encoded += "\\" + str.charAt(i);
      wsBeforeHexIsNeeded = false;
    } else {
      if (wsBeforeHexIsNeeded && isHexDigit(code2)) {
        encoded += " ";
      }
      encoded += str.charAt(i);
      wsBeforeHexIsNeeded = false;
    }
  }
  return "url(" + encoded + ")";
}

// node_modules/css-tree/lib/syntax/node/Url.js
var name47 = "Url";
var structure47 = {
  value: String
};
function parse48() {
  const start = this.tokenStart;
  let value;
  switch (this.tokenType) {
    case Url:
      value = decode2(this.consume(Url));
      break;
    case Function2:
      if (!this.cmpStr(this.tokenStart, this.tokenEnd, "url(")) {
        this.error("Function name must be `url`");
      }
      this.eat(Function2);
      this.skipSC();
      value = decode(this.consume(String2));
      this.skipSC();
      if (!this.eof) {
        this.eat(RightParenthesis);
      }
      break;
    default:
      this.error("Url or Function is expected");
  }
  return {
    type: "Url",
    loc: this.getLocation(start, this.tokenStart),
    value
  };
}
function generate48(node) {
  this.token(Url, encode2(node.value));
}

// node_modules/css-tree/lib/syntax/node/Value.js
var Value_exports = {};
__export(Value_exports, {
  generate: () => generate49,
  name: () => name48,
  parse: () => parse49,
  structure: () => structure48
});
var name48 = "Value";
var structure48 = {
  children: [[]]
};
function parse49() {
  const start = this.tokenStart;
  const children = this.readSequence(this.scope.Value);
  return {
    type: "Value",
    loc: this.getLocation(start, this.tokenStart),
    children
  };
}
function generate49(node) {
  this.children(node);
}

// node_modules/css-tree/lib/syntax/node/WhiteSpace.js
var WhiteSpace_exports = {};
__export(WhiteSpace_exports, {
  generate: () => generate50,
  name: () => name49,
  parse: () => parse50,
  structure: () => structure49
});
var SPACE4 = Object.freeze({
  type: "WhiteSpace",
  loc: null,
  value: " "
});
var name49 = "WhiteSpace";
var structure49 = {
  value: String
};
function parse50() {
  this.eat(WhiteSpace);
  return SPACE4;
}
function generate50(node) {
  this.token(WhiteSpace, node.value);
}

// node_modules/css-tree/lib/syntax/config/lexer.js
var lexer_default = {
  generic: true,
  cssWideKeywords,
  ...data_default,
  node: node_exports
};

// node_modules/css-tree/lib/syntax/scope/index.js
var scope_exports = {};
__export(scope_exports, {
  AtrulePrelude: () => atrulePrelude_default,
  Selector: () => selector_default,
  Value: () => value_default
});

// node_modules/css-tree/lib/syntax/scope/default.js
var NUMBERSIGN4 = 35;
var ASTERISK6 = 42;
var PLUSSIGN9 = 43;
var HYPHENMINUS7 = 45;
var SOLIDUS7 = 47;
var U2 = 117;
function defaultRecognizer(context) {
  switch (this.tokenType) {
    case Hash:
      return this.Hash();
    case Comma:
      return this.Operator();
    case LeftParenthesis:
      return this.Parentheses(this.readSequence, context.recognizer);
    case LeftSquareBracket:
      return this.Brackets(this.readSequence, context.recognizer);
    case String2:
      return this.String();
    case Dimension:
      return this.Dimension();
    case Percentage:
      return this.Percentage();
    case Number2:
      return this.Number();
    case Function2:
      return this.cmpStr(this.tokenStart, this.tokenEnd, "url(") ? this.Url() : this.Function(this.readSequence, context.recognizer);
    case Url:
      return this.Url();
    case Ident:
      if (this.cmpChar(this.tokenStart, U2) && this.cmpChar(this.tokenStart + 1, PLUSSIGN9)) {
        return this.UnicodeRange();
      } else {
        return this.Identifier();
      }
    case Delim: {
      const code2 = this.charCodeAt(this.tokenStart);
      if (code2 === SOLIDUS7 || code2 === ASTERISK6 || code2 === PLUSSIGN9 || code2 === HYPHENMINUS7) {
        return this.Operator();
      }
      if (code2 === NUMBERSIGN4) {
        this.error("Hex or identifier is expected", this.tokenStart + 1);
      }
      break;
    }
  }
}

// node_modules/css-tree/lib/syntax/scope/atrulePrelude.js
var atrulePrelude_default = {
  getNode: defaultRecognizer
};

// node_modules/css-tree/lib/syntax/scope/selector.js
var NUMBERSIGN5 = 35;
var AMPERSAND6 = 38;
var ASTERISK7 = 42;
var PLUSSIGN10 = 43;
var SOLIDUS8 = 47;
var FULLSTOP3 = 46;
var GREATERTHANSIGN4 = 62;
var VERTICALLINE4 = 124;
var TILDE3 = 126;
function onWhiteSpace(next, children) {
  if (children.last !== null && children.last.type !== "Combinator" && next !== null && next.type !== "Combinator") {
    children.push({
      // FIXME: this.Combinator() should be used instead
      type: "Combinator",
      loc: null,
      name: " "
    });
  }
}
function getNode() {
  switch (this.tokenType) {
    case LeftSquareBracket:
      return this.AttributeSelector();
    case Hash:
      return this.IdSelector();
    case Colon:
      if (this.lookupType(1) === Colon) {
        return this.PseudoElementSelector();
      } else {
        return this.PseudoClassSelector();
      }
    case Ident:
      return this.TypeSelector();
    case Number2:
    case Percentage:
      return this.Percentage();
    case Dimension:
      if (this.charCodeAt(this.tokenStart) === FULLSTOP3) {
        this.error("Identifier is expected", this.tokenStart + 1);
      }
      break;
    case Delim: {
      const code2 = this.charCodeAt(this.tokenStart);
      switch (code2) {
        case PLUSSIGN10:
        case GREATERTHANSIGN4:
        case TILDE3:
        case SOLIDUS8:
          return this.Combinator();
        case FULLSTOP3:
          return this.ClassSelector();
        case ASTERISK7:
        case VERTICALLINE4:
          return this.TypeSelector();
        case NUMBERSIGN5:
          return this.IdSelector();
        case AMPERSAND6:
          return this.NestingSelector();
      }
      break;
    }
  }
}
var selector_default = {
  onWhiteSpace,
  getNode
};

// node_modules/css-tree/lib/syntax/function/expression.js
function expression_default() {
  return this.createSingleNodeList(
    this.Raw(null, false)
  );
}

// node_modules/css-tree/lib/syntax/function/var.js
function var_default() {
  const children = this.createList();
  this.skipSC();
  children.push(this.Identifier());
  this.skipSC();
  if (this.tokenType === Comma) {
    children.push(this.Operator());
    const startIndex = this.tokenIndex;
    const value = this.parseCustomProperty ? this.Value(null) : this.Raw(this.consumeUntilExclamationMarkOrSemicolon, false);
    if (value.type === "Value" && value.children.isEmpty) {
      for (let offset = startIndex - this.tokenIndex; offset <= 0; offset++) {
        if (this.lookupType(offset) === WhiteSpace) {
          value.children.appendData({
            type: "WhiteSpace",
            loc: null,
            value: " "
          });
          break;
        }
      }
    }
    children.push(value);
  }
  return children;
}

// node_modules/css-tree/lib/syntax/scope/value.js
function isPlusMinusOperator(node) {
  return node !== null && node.type === "Operator" && (node.value[node.value.length - 1] === "-" || node.value[node.value.length - 1] === "+");
}
var value_default = {
  getNode: defaultRecognizer,
  onWhiteSpace(next, children) {
    if (isPlusMinusOperator(next)) {
      next.value = " " + next.value;
    }
    if (isPlusMinusOperator(children.last)) {
      children.last.value += " ";
    }
  },
  "expression": expression_default,
  "var": var_default
};

// node_modules/css-tree/lib/syntax/atrule/container.js
var nonContainerNameKeywords = /* @__PURE__ */ new Set(["none", "and", "not", "or"]);
var container_default = {
  parse: {
    prelude() {
      const children = this.createList();
      if (this.tokenType === Ident) {
        const name50 = this.substring(this.tokenStart, this.tokenEnd);
        if (!nonContainerNameKeywords.has(name50.toLowerCase())) {
          children.push(this.Identifier());
        }
      }
      children.push(this.Condition("container"));
      return children;
    },
    block(nested = false) {
      return this.Block(nested);
    }
  }
};

// node_modules/css-tree/lib/syntax/atrule/font-face.js
var font_face_default = {
  parse: {
    prelude: null,
    block() {
      return this.Block(true);
    }
  }
};

// node_modules/css-tree/lib/syntax/atrule/import.js
function parseWithFallback(parse52, fallback) {
  return this.parseWithFallback(
    () => {
      try {
        return parse52.call(this);
      } finally {
        this.skipSC();
        if (this.lookupNonWSType(0) !== RightParenthesis) {
          this.error();
        }
      }
    },
    fallback || (() => this.Raw(null, true))
  );
}
var parseFunctions = {
  layer() {
    this.skipSC();
    const children = this.createList();
    const node = parseWithFallback.call(this, this.Layer);
    if (node.type !== "Raw" || node.value !== "") {
      children.push(node);
    }
    return children;
  },
  supports() {
    this.skipSC();
    const children = this.createList();
    const node = parseWithFallback.call(
      this,
      this.Declaration,
      () => parseWithFallback.call(this, () => this.Condition("supports"))
    );
    if (node.type !== "Raw" || node.value !== "") {
      children.push(node);
    }
    return children;
  }
};
var import_default3 = {
  parse: {
    prelude() {
      const children = this.createList();
      switch (this.tokenType) {
        case String2:
          children.push(this.String());
          break;
        case Url:
        case Function2:
          children.push(this.Url());
          break;
        default:
          this.error("String or url() is expected");
      }
      this.skipSC();
      if (this.tokenType === Ident && this.cmpStr(this.tokenStart, this.tokenEnd, "layer")) {
        children.push(this.Identifier());
      } else if (this.tokenType === Function2 && this.cmpStr(this.tokenStart, this.tokenEnd, "layer(")) {
        children.push(this.Function(null, parseFunctions));
      }
      this.skipSC();
      if (this.tokenType === Function2 && this.cmpStr(this.tokenStart, this.tokenEnd, "supports(")) {
        children.push(this.Function(null, parseFunctions));
      }
      if (this.lookupNonWSType(0) === Ident || this.lookupNonWSType(0) === LeftParenthesis) {
        children.push(this.MediaQueryList());
      }
      return children;
    },
    block: null
  }
};

// node_modules/css-tree/lib/syntax/atrule/layer.js
var layer_default = {
  parse: {
    prelude() {
      return this.createSingleNodeList(
        this.LayerList()
      );
    },
    block() {
      return this.Block(false);
    }
  }
};

// node_modules/css-tree/lib/syntax/atrule/media.js
var media_default = {
  parse: {
    prelude() {
      return this.createSingleNodeList(
        this.MediaQueryList()
      );
    },
    block(nested = false) {
      return this.Block(nested);
    }
  }
};

// node_modules/css-tree/lib/syntax/atrule/nest.js
var nest_default = {
  parse: {
    prelude() {
      return this.createSingleNodeList(
        this.SelectorList()
      );
    },
    block() {
      return this.Block(true);
    }
  }
};

// node_modules/css-tree/lib/syntax/atrule/page.js
var page_default = {
  parse: {
    prelude() {
      return this.createSingleNodeList(
        this.SelectorList()
      );
    },
    block() {
      return this.Block(true);
    }
  }
};

// node_modules/css-tree/lib/syntax/atrule/scope.js
var scope_default = {
  parse: {
    prelude() {
      return this.createSingleNodeList(
        this.Scope()
      );
    },
    block(nested = false) {
      return this.Block(nested);
    }
  }
};

// node_modules/css-tree/lib/syntax/atrule/starting-style.js
var starting_style_default = {
  parse: {
    prelude: null,
    block(nested = false) {
      return this.Block(nested);
    }
  }
};

// node_modules/css-tree/lib/syntax/atrule/supports.js
var supports_default = {
  parse: {
    prelude() {
      return this.createSingleNodeList(
        this.Condition("supports")
      );
    },
    block(nested = false) {
      return this.Block(nested);
    }
  }
};

// node_modules/css-tree/lib/syntax/atrule/index.js
var atrule_default = {
  container: container_default,
  "font-face": font_face_default,
  import: import_default3,
  layer: layer_default,
  media: media_default,
  nest: nest_default,
  page: page_default,
  scope: scope_default,
  "starting-style": starting_style_default,
  supports: supports_default
};

// node_modules/css-tree/lib/syntax/pseudo/lang.js
function parseLanguageRangeList() {
  const children = this.createList();
  this.skipSC();
  loop: while (!this.eof) {
    switch (this.tokenType) {
      case Ident:
        children.push(this.Identifier());
        break;
      case String2:
        children.push(this.String());
        break;
      case Comma:
        children.push(this.Operator());
        break;
      case RightParenthesis:
        break loop;
      default:
        this.error("Identifier, string or comma is expected");
    }
    this.skipSC();
  }
  return children;
}

// node_modules/css-tree/lib/syntax/pseudo/index.js
var selectorList = {
  parse() {
    return this.createSingleNodeList(
      this.SelectorList()
    );
  }
};
var selector = {
  parse() {
    return this.createSingleNodeList(
      this.Selector()
    );
  }
};
var identList = {
  parse() {
    return this.createSingleNodeList(
      this.Identifier()
    );
  }
};
var langList = {
  parse: parseLanguageRangeList
};
var nth = {
  parse() {
    return this.createSingleNodeList(
      this.Nth()
    );
  }
};
var pseudo_default = {
  "dir": identList,
  "has": selectorList,
  "lang": langList,
  "matches": selectorList,
  "is": selectorList,
  "-moz-any": selectorList,
  "-webkit-any": selectorList,
  "where": selectorList,
  "not": selectorList,
  "nth-child": nth,
  "nth-last-child": nth,
  "nth-last-of-type": nth,
  "nth-of-type": nth,
  "slotted": selector,
  "host": selector,
  "host-context": selector
};

// node_modules/css-tree/lib/syntax/node/index-parse.js
var index_parse_exports = {};
__export(index_parse_exports, {
  AnPlusB: () => parse2,
  Atrule: () => parse3,
  AtrulePrelude: () => parse4,
  AttributeSelector: () => parse5,
  Block: () => parse6,
  Brackets: () => parse7,
  CDC: () => parse8,
  CDO: () => parse9,
  ClassSelector: () => parse10,
  Combinator: () => parse11,
  Comment: () => parse12,
  Condition: () => parse13,
  Declaration: () => parse14,
  DeclarationList: () => parse15,
  Dimension: () => parse16,
  Feature: () => parse17,
  FeatureFunction: () => parse18,
  FeatureRange: () => parse19,
  Function: () => parse20,
  GeneralEnclosed: () => parse21,
  Hash: () => parse22,
  IdSelector: () => parse24,
  Identifier: () => parse23,
  Layer: () => parse25,
  LayerList: () => parse26,
  MediaQuery: () => parse27,
  MediaQueryList: () => parse28,
  NestingSelector: () => parse29,
  Nth: () => parse30,
  Number: () => parse31,
  Operator: () => parse32,
  Parentheses: () => parse33,
  Percentage: () => parse34,
  PseudoClassSelector: () => parse35,
  PseudoElementSelector: () => parse36,
  Ratio: () => parse37,
  Raw: () => parse38,
  Rule: () => parse39,
  Scope: () => parse40,
  Selector: () => parse41,
  SelectorList: () => parse42,
  String: () => parse43,
  StyleSheet: () => parse44,
  SupportsDeclaration: () => parse45,
  TypeSelector: () => parse46,
  UnicodeRange: () => parse47,
  Url: () => parse48,
  Value: () => parse49,
  WhiteSpace: () => parse50
});

// node_modules/css-tree/lib/syntax/config/parser.js
var parser_default = {
  parseContext: {
    default: "StyleSheet",
    stylesheet: "StyleSheet",
    atrule: "Atrule",
    atrulePrelude(options) {
      return this.AtrulePrelude(options.atrule ? String(options.atrule) : null);
    },
    mediaQueryList: "MediaQueryList",
    mediaQuery: "MediaQuery",
    condition(options) {
      return this.Condition(options.kind);
    },
    rule: "Rule",
    selectorList: "SelectorList",
    selector: "Selector",
    block() {
      return this.Block(true);
    },
    declarationList: "DeclarationList",
    declaration: "Declaration",
    value: "Value"
  },
  features: {
    supports: {
      selector() {
        return this.Selector();
      }
    },
    container: {
      style() {
        return this.Declaration();
      }
    }
  },
  scope: scope_exports,
  atrule: atrule_default,
  pseudo: pseudo_default,
  node: index_parse_exports
};

// node_modules/css-tree/lib/syntax/config/walker.js
var walker_default = {
  node: node_exports
};

// node_modules/css-tree/lib/syntax/index.js
var syntax_default = create_default({
  ...lexer_default,
  ...parser_default,
  ...walker_default
});

// node_modules/css-tree/lib/utils/clone.js
function clone(node) {
  const result = {};
  for (const key of Object.keys(node)) {
    let value = node[key];
    if (value) {
      if (Array.isArray(value) || value instanceof List) {
        value = value.map(clone);
      } else if (value.constructor === Object) {
        value = clone(value);
      }
    }
    result[key] = value;
  }
  return result;
}

// node_modules/css-tree/lib/index.js
var {
  tokenize: tokenize2,
  parse: parse51,
  generate: generate51,
  lexer,
  createLexer,
  walk: walk2,
  find,
  findLast,
  findAll,
  toPlainObject,
  fromPlainObject,
  fork
} = syntax_default;

// node_modules/@asamuzakjp/dom-selector/src/js/utility.js
var import_nwsapi = __toESM(require_nwsapi(), 1);
var import_bidi_js = __toESM(require_bidi(), 1);
var import_is_potential_custom_element_name = __toESM(require_is_potential_custom_element_name(), 1);

// node_modules/@asamuzakjp/dom-selector/src/js/constant.js
var ATTR_SELECTOR = "AttributeSelector";
var CLASS_SELECTOR = "ClassSelector";
var COMBINATOR = "Combinator";
var IDENT = "Identifier";
var ID_SELECTOR = "IdSelector";
var NOT_SUPPORTED_ERR = "NotSupportedError";
var NTH = "Nth";
var PS_CLASS_SELECTOR = "PseudoClassSelector";
var PS_ELEMENT_SELECTOR = "PseudoElementSelector";
var SELECTOR = "Selector";
var STRING = "String";
var SYNTAX_ERR = "SyntaxError";
var TARGET_ALL = "all";
var TARGET_FIRST = "first";
var TARGET_LINEAL = "lineal";
var TARGET_SELF = "self";
var TYPE_SELECTOR = "TypeSelector";
var BIT_01 = 1;
var BIT_02 = 2;
var BIT_04 = 4;
var BIT_08 = 8;
var BIT_16 = 16;
var BIT_32 = 32;
var BIT_FFFF = 65535;
var DUO = 2;
var HEX = 16;
var TYPE_FROM = 8;
var TYPE_TO = -1;
var ELEMENT_NODE = 1;
var TEXT_NODE = 3;
var DOCUMENT_NODE = 9;
var DOCUMENT_FRAGMENT_NODE = 11;
var DOCUMENT_POSITION_PRECEDING = 2;
var DOCUMENT_POSITION_CONTAINS = 8;
var SHOW_ALL = 4294967295;
var SHOW_CONTAINER = 1281;
var ALPHA_NUM = "[A-Z\\d]+";
var CHILD_IDX = "(?:first|last|only)-(?:child|of-type)";
var DIGIT = "(?:0|[1-9]\\d*)";
var LANG_PART = `(?:-${ALPHA_NUM})*`;
var PSEUDO_CLASS = `(?:any-)?link|${CHILD_IDX}|checked|empty|indeterminate|read-(?:only|write)|target`;
var ANB = `[+-]?(?:${DIGIT}n?|n)|(?:[+-]?${DIGIT})?n\\s*[+-]\\s*${DIGIT}`;
var COMBO = "\\s?[\\s>~+]\\s?";
var DESCEND = "\\s?[\\s>]\\s?";
var LOGIC_IS = `:is\\(\\s*[^)]+\\s*\\)`;
var N_TH = `nth-(?:last-)?(?:child|of-type)\\(\\s*(?:even|odd|${ANB})\\s*\\)`;
var SUB_TYPE = "\\[[^|\\]]+\\]|[#.:][\\w-]+";
var SUB_TYPE_WO_PSEUDO = "\\[[^|\\]]+\\]|[#.][\\w-]+";
var TAG_TYPE = "\\*|[A-Za-z][\\w-]*";
var TAG_TYPE_I = "\\*|[A-Z][\\w-]*";
var COMPOUND = `(?:${TAG_TYPE}|(?:${TAG_TYPE})?(?:${SUB_TYPE})+)`;
var COMPOUND_L = `(?:${TAG_TYPE}|(?:${TAG_TYPE})?(?:${SUB_TYPE}|${LOGIC_IS})+)`;
var COMPOUND_I = `(?:${TAG_TYPE_I}|(?:${TAG_TYPE_I})?(?:${SUB_TYPE})+)`;
var COMPOUND_WO_PSEUDO = `(?:${TAG_TYPE}|(?:${TAG_TYPE})?(?:${SUB_TYPE_WO_PSEUDO})+)`;
var COMPLEX = `${COMPOUND}(?:${COMBO}${COMPOUND})*`;
var COMPLEX_L = `${COMPOUND_L}(?:${COMBO}${COMPOUND_L})*`;
var HAS_COMPOUND = `has\\([\\s>]?\\s*${COMPOUND_WO_PSEUDO}\\s*\\)`;
var LOGIC_COMPOUND = `(?:is|not)\\(\\s*${COMPOUND_L}(?:\\s*,\\s*${COMPOUND_L})*\\s*\\)`;
var LOGIC_COMPLEX = `(?:is|not)\\(\\s*${COMPLEX_L}(?:\\s*,\\s*${COMPLEX_L})*\\s*\\)`;
var FORM_PARTS = Object.freeze([
  "button",
  "input",
  "select",
  "textarea"
]);
var INPUT_BUTTON = Object.freeze(["button", "reset", "submit"]);
var INPUT_CHECK = Object.freeze(["checkbox", "radio"]);
var INPUT_DATE = Object.freeze([
  "date",
  "datetime-local",
  "month",
  "time",
  "week"
]);
var INPUT_TEXT = Object.freeze([
  "email",
  "password",
  "search",
  "tel",
  "text",
  "url"
]);
var INPUT_EDIT = Object.freeze([
  ...INPUT_DATE,
  ...INPUT_TEXT,
  "number"
]);
var INPUT_LTR = Object.freeze([
  ...INPUT_CHECK,
  "color",
  "date",
  "image",
  "number",
  "range",
  "time"
]);
var KEYS_LOGICAL = /* @__PURE__ */ new Set(["has", "is", "not", "where"]);

// node_modules/@asamuzakjp/dom-selector/src/js/utility.js
var KEYS_DIR_AUTO = /* @__PURE__ */ new Set([...INPUT_BUTTON, ...INPUT_TEXT, "hidden"]);
var KEYS_DIR_LTR = new Set(INPUT_LTR);
var KEYS_INPUT_EDIT = new Set(INPUT_EDIT);
var KEYS_NODE_DIR_EXCLUDE = /* @__PURE__ */ new Set(["bdi", "script", "style", "textarea"]);
var KEYS_NODE_FOCUSABLE = /* @__PURE__ */ new Set(["button", "select", "textarea"]);
var KEYS_NODE_FOCUSABLE_SVG = /* @__PURE__ */ new Set([
  "clipPath",
  "defs",
  "desc",
  "linearGradient",
  "marker",
  "mask",
  "metadata",
  "pattern",
  "radialGradient",
  "script",
  "style",
  "symbol",
  "title"
]);
var REG_ATTR_SIMPLE = /^\[[A-Z\d-]{1,255}(?:="?[A-Z\d\s-]{1,255}"?)?\]$/i;
var REG_TAG_SIMPLE = new RegExp(`^(?:${TAG_TYPE})$`);
var REG_EXCLUDE_BASIC = /[|\\]|::|[^\u0021-\u007F\s]|\[\s*[\w$*=^|~-]+(?:(?:"[\w$*=^|~\s'-]+"|'[\w$*=^|~\s"-]+')?(?:\s+[\w$*=^|~-]+)+|"[^"\]]{1,255}|'[^'\]]{1,255})\s*\]|:(?:is|where)\(\s*\)/;
var REG_COMPLEX = new RegExp(`${COMPOUND_I}${COMBO}${COMPOUND_I}`, "i");
var REG_DESCEND = new RegExp(`${COMPOUND_I}${DESCEND}${COMPOUND_I}`, "i");
var REG_LOGIC_COMPLEX = new RegExp(
  `:(?!${PSEUDO_CLASS}|${N_TH}|${LOGIC_COMPLEX})`
);
var REG_LOGIC_COMPOUND = new RegExp(
  `:(?!${PSEUDO_CLASS}|${N_TH}|${LOGIC_COMPOUND})`
);
var REG_LOGIC_HAS_COMPOUND = new RegExp(
  `:(?!${PSEUDO_CLASS}|${N_TH}|${LOGIC_COMPOUND}|${HAS_COMPOUND})`
);
var REG_END_WITH_HAS = new RegExp(`:${HAS_COMPOUND}$`);
var REG_WO_LOGICAL = new RegExp(`:(?!${PSEUDO_CLASS}|${N_TH})`);
var REG_IS_HTML = /^(?:application\/xhtml\+x|text\/ht)ml$/;
var REG_IS_XML = /^(?:application\/(?:[\w\-.]+\+)?|image\/[\w\-.]+\+|text\/)xml$/;
var getType = (o) => Object.prototype.toString.call(o).slice(TYPE_FROM, TYPE_TO);
var generateException = (msg, name50, globalObject = globalThis) => {
  return new globalObject.DOMException(msg, name50);
};
var findNestedHas = (leaf) => {
  return leaf.name === "has";
};
var findLogicalWithNestedHas = (leaf) => {
  if (KEYS_LOGICAL.has(leaf.name) && find(leaf, findNestedHas)) {
    return leaf;
  }
  return null;
};
var filterNodesByAnB = (nodes, anb) => {
  const { a, b, reverse } = anb;
  const processedNodes = reverse ? [...nodes].reverse() : nodes;
  const l = nodes.length;
  const matched = [];
  if (a === 0) {
    if (b > 0 && b <= l) {
      matched.push(processedNodes[b - 1]);
    }
    return matched;
  }
  let startIndex = b - 1;
  if (a > 0) {
    while (startIndex < 0) {
      startIndex += a;
    }
    for (let i = startIndex; i < l; i += a) {
      matched.push(processedNodes[i]);
    }
  } else if (startIndex >= 0) {
    for (let i = startIndex; i >= 0; i += a) {
      matched.push(processedNodes[i]);
    }
    return matched.reverse();
  }
  return matched;
};
var resolveContent = (node) => {
  if (!node?.nodeType) {
    throw new TypeError(`Unexpected type ${getType(node)}`);
  }
  let document;
  let root;
  let shadow;
  switch (node.nodeType) {
    case DOCUMENT_NODE: {
      document = node;
      root = node;
      break;
    }
    case DOCUMENT_FRAGMENT_NODE: {
      const { host, mode, ownerDocument } = node;
      document = ownerDocument;
      root = node;
      shadow = host && (mode === "close" || mode === "open");
      break;
    }
    case ELEMENT_NODE: {
      document = node.ownerDocument;
      let refNode = node;
      while (refNode) {
        const { host, mode, nodeType, parentNode } = refNode;
        if (nodeType === DOCUMENT_FRAGMENT_NODE) {
          shadow = host && (mode === "close" || mode === "open");
          break;
        } else if (parentNode) {
          refNode = parentNode;
        } else {
          break;
        }
      }
      root = refNode;
      break;
    }
    default: {
      throw new TypeError(`Unexpected node ${node.nodeName}`);
    }
  }
  return [document, root, !!shadow];
};
var traverseNode = (node, walker, force = false) => {
  if (!node?.nodeType) {
    throw new TypeError(`Unexpected type ${getType(node)}`);
  }
  if (!walker) {
    return null;
  }
  let refNode = walker.currentNode;
  if (refNode === node) {
    return refNode;
  } else if (force || refNode.contains(node)) {
    refNode = walker.nextNode();
    while (refNode) {
      if (refNode === node) {
        break;
      }
      refNode = walker.nextNode();
    }
    return refNode;
  } else {
    if (refNode !== walker.root) {
      let bool;
      while (refNode) {
        if (refNode === node) {
          bool = true;
          break;
        } else if (refNode === walker.root || refNode.contains(node)) {
          break;
        }
        refNode = walker.parentNode();
      }
      if (bool) {
        return refNode;
      }
    }
    if (node.nodeType === ELEMENT_NODE) {
      let bool;
      while (refNode) {
        if (refNode === node) {
          bool = true;
          break;
        }
        refNode = walker.nextNode();
      }
      if (bool) {
        return refNode;
      }
    }
  }
  return null;
};
var isCustomElement = (node, opt = {}) => {
  if (!node?.nodeType) {
    throw new TypeError(`Unexpected type ${getType(node)}`);
  }
  if (node.nodeType !== ELEMENT_NODE) {
    return false;
  }
  const { localName, ownerDocument } = node;
  const { formAssociated } = opt;
  const window = ownerDocument.defaultView;
  let elmConstructor;
  const attr = node.getAttribute("is");
  if (attr) {
    elmConstructor = (0, import_is_potential_custom_element_name.default)(attr) && window.customElements.get(attr);
  } else {
    elmConstructor = (0, import_is_potential_custom_element_name.default)(localName) && window.customElements.get(localName);
  }
  if (elmConstructor) {
    if (formAssociated) {
      return !!elmConstructor.formAssociated;
    }
    return true;
  }
  return false;
};
var getSlottedTextContent = (node) => {
  if (!node?.nodeType) {
    throw new TypeError(`Unexpected type ${getType(node)}`);
  }
  if (typeof node.assignedNodes !== "function") {
    return null;
  }
  const nodes = node.assignedNodes();
  if (nodes.length) {
    let text = "";
    const l = nodes.length;
    for (let i = 0; i < l; i++) {
      const item = nodes[i];
      text = item.textContent.trim();
      if (text) {
        break;
      }
    }
    return text;
  }
  return node.textContent.trim();
};
var getDirectionality = (node) => {
  if (!node?.nodeType) {
    throw new TypeError(`Unexpected type ${getType(node)}`);
  }
  if (node.nodeType !== ELEMENT_NODE) {
    return null;
  }
  const { dir: dirAttr, localName, parentNode } = node;
  const { getEmbeddingLevels } = (0, import_bidi_js.default)();
  if (dirAttr === "ltr" || dirAttr === "rtl") {
    return dirAttr;
  } else if (dirAttr === "auto") {
    let text = "";
    switch (localName) {
      case "input": {
        if (!node.type || KEYS_DIR_AUTO.has(node.type)) {
          text = node.value;
        } else if (KEYS_DIR_LTR.has(node.type)) {
          return "ltr";
        }
        break;
      }
      case "slot": {
        text = getSlottedTextContent(node);
        break;
      }
      case "textarea": {
        text = node.value;
        break;
      }
      default: {
        const items = [].slice.call(node.childNodes);
        for (const item of items) {
          const {
            dir: itemDir,
            localName: itemLocalName,
            nodeType: itemNodeType,
            textContent: itemTextContent
          } = item;
          if (itemNodeType === TEXT_NODE) {
            text = itemTextContent.trim();
          } else if (itemNodeType === ELEMENT_NODE && !KEYS_NODE_DIR_EXCLUDE.has(itemLocalName) && (!itemDir || itemDir !== "ltr" && itemDir !== "rtl")) {
            if (itemLocalName === "slot") {
              text = getSlottedTextContent(item);
            } else {
              text = itemTextContent.trim();
            }
          }
          if (text) {
            break;
          }
        }
      }
    }
    if (text) {
      const {
        paragraphs: [{ level }]
      } = getEmbeddingLevels(text);
      if (level % 2 === 1) {
        return "rtl";
      }
    } else if (parentNode) {
      const { nodeType: parentNodeType } = parentNode;
      if (parentNodeType === ELEMENT_NODE) {
        return getDirectionality(parentNode);
      }
    }
  } else if (localName === "input" && node.type === "tel") {
    return "ltr";
  } else if (localName === "bdi") {
    const text = node.textContent.trim();
    if (text) {
      const {
        paragraphs: [{ level }]
      } = getEmbeddingLevels(text);
      if (level % 2 === 1) {
        return "rtl";
      }
    }
  } else if (parentNode) {
    if (localName === "slot") {
      const text = getSlottedTextContent(node);
      if (text) {
        const {
          paragraphs: [{ level }]
        } = getEmbeddingLevels(text);
        if (level % 2 === 1) {
          return "rtl";
        }
        return "ltr";
      }
    }
    const { nodeType: parentNodeType } = parentNode;
    if (parentNodeType === ELEMENT_NODE) {
      return getDirectionality(parentNode);
    }
  }
  return "ltr";
};
var getLanguageAttribute = (node) => {
  if (!node?.nodeType) {
    throw new TypeError(`Unexpected type ${getType(node)}`);
  }
  if (node.nodeType !== ELEMENT_NODE) {
    return null;
  }
  const { contentType } = node.ownerDocument;
  const isHtml = REG_IS_HTML.test(contentType);
  const isXml = REG_IS_XML.test(contentType);
  let isShadow = false;
  let current = node;
  while (current) {
    switch (current.nodeType) {
      case ELEMENT_NODE: {
        if (isHtml && current.hasAttribute("lang")) {
          return current.getAttribute("lang");
        } else if (isXml && current.hasAttribute("xml:lang")) {
          return current.getAttribute("xml:lang");
        }
        break;
      }
      case DOCUMENT_FRAGMENT_NODE: {
        if (current.host) {
          isShadow = true;
        }
        break;
      }
      case DOCUMENT_NODE:
      default: {
        return null;
      }
    }
    if (isShadow) {
      current = current.host;
      isShadow = false;
    } else if (current.parentNode) {
      current = current.parentNode;
    } else {
      break;
    }
  }
  return null;
};
var isContentEditable = (node) => {
  if (!node?.nodeType) {
    throw new TypeError(`Unexpected type ${getType(node)}`);
  }
  if (node.nodeType !== ELEMENT_NODE) {
    return false;
  }
  if (typeof node.isContentEditable === "boolean") {
    return node.isContentEditable;
  } else if (node.ownerDocument.designMode === "on") {
    return true;
  } else {
    let attr;
    if (node.hasAttribute("contenteditable")) {
      attr = node.getAttribute("contenteditable");
    } else {
      attr = "inherit";
    }
    switch (attr) {
      case "":
      case "true": {
        return true;
      }
      case "plaintext-only": {
        return true;
      }
      case "false": {
        return false;
      }
      default: {
        if (node?.parentNode?.nodeType === ELEMENT_NODE) {
          return isContentEditable(node.parentNode);
        }
        return false;
      }
    }
  }
};
var isVisible = (node) => {
  if (node?.nodeType !== ELEMENT_NODE) {
    return false;
  }
  const window = node.ownerDocument.defaultView;
  const { display, visibility } = window.getComputedStyle(node);
  return display !== "none" && visibility === "visible";
};
var isFocusVisible = (node) => {
  if (node?.nodeType !== ELEMENT_NODE) {
    return false;
  }
  const { localName, type } = node;
  switch (localName) {
    case "input": {
      if (!type || KEYS_INPUT_EDIT.has(type)) {
        return true;
      }
      return false;
    }
    case "textarea": {
      return true;
    }
    default: {
      return isContentEditable(node);
    }
  }
};
var isFocusableArea = (node) => {
  if (node?.nodeType !== ELEMENT_NODE) {
    return false;
  }
  if (!node.isConnected) {
    return false;
  }
  const window = node.ownerDocument.defaultView;
  if (node instanceof window.HTMLElement) {
    if (Number.isInteger(parseInt(node.getAttribute("tabindex")))) {
      return true;
    }
    if (isContentEditable(node)) {
      return true;
    }
    const { localName, parentNode } = node;
    switch (localName) {
      case "a": {
        if (node.href || node.hasAttribute("href")) {
          return true;
        }
        return false;
      }
      case "iframe": {
        return true;
      }
      case "input": {
        if (node.disabled || node.hasAttribute("disabled") || node.hidden || node.hasAttribute("hidden")) {
          return false;
        }
        return true;
      }
      case "summary": {
        if (parentNode.localName === "details") {
          let child = parentNode.firstElementChild;
          let bool = false;
          while (child) {
            if (child.localName === "summary") {
              bool = child === node;
              break;
            }
            child = child.nextElementSibling;
          }
          return bool;
        }
        return false;
      }
      default: {
        if (KEYS_NODE_FOCUSABLE.has(localName) && !(node.disabled || node.hasAttribute("disabled"))) {
          return true;
        }
      }
    }
  } else if (node instanceof window.SVGElement) {
    if (Number.isInteger(parseInt(node.getAttributeNS(null, "tabindex")))) {
      const ns = "http://www.w3.org/2000/svg";
      let bool;
      let refNode = node;
      while (refNode.namespaceURI === ns) {
        bool = KEYS_NODE_FOCUSABLE_SVG.has(refNode.localName);
        if (bool) {
          break;
        }
        if (refNode?.parentNode?.namespaceURI === ns) {
          refNode = refNode.parentNode;
        } else {
          break;
        }
      }
      if (bool) {
        return false;
      }
      return true;
    }
    if (node.localName === "a" && (node.href || node.hasAttributeNS(null, "href"))) {
      return true;
    }
  }
  return false;
};
var getNamespaceURI = (ns, node) => {
  if (typeof ns !== "string") {
    throw new TypeError(`Unexpected type ${getType(ns)}`);
  } else if (!node?.nodeType) {
    throw new TypeError(`Unexpected type ${getType(node)}`);
  }
  if (!ns || node.nodeType !== ELEMENT_NODE) {
    return null;
  }
  const { attributes } = node;
  let res;
  for (const attr of attributes) {
    const { name: name50, namespaceURI, prefix, value } = attr;
    if (name50 === `xmlns:${ns}`) {
      res = value;
    } else if (prefix === ns) {
      res = namespaceURI;
    }
    if (res) {
      break;
    }
  }
  return res ?? null;
};
var isNamespaceDeclared = (ns = "", node = {}) => {
  if (!ns || typeof ns !== "string" || node?.nodeType !== ELEMENT_NODE) {
    return false;
  }
  if (node.lookupNamespaceURI(ns)) {
    return true;
  }
  const root = node.ownerDocument.documentElement;
  let parent = node;
  let res;
  while (parent) {
    res = getNamespaceURI(ns, parent);
    if (res || parent === root) {
      break;
    }
    parent = parent.parentNode;
  }
  return !!res;
};
var isPreceding = (nodeA, nodeB) => {
  if (!nodeA?.nodeType) {
    throw new TypeError(`Unexpected type ${getType(nodeA)}`);
  } else if (!nodeB?.nodeType) {
    throw new TypeError(`Unexpected type ${getType(nodeB)}`);
  }
  if (nodeA.nodeType !== ELEMENT_NODE || nodeB.nodeType !== ELEMENT_NODE) {
    return false;
  }
  const posBit = nodeB.compareDocumentPosition(nodeA);
  const res = posBit & DOCUMENT_POSITION_PRECEDING || posBit & DOCUMENT_POSITION_CONTAINS;
  return !!res;
};
var compareNodes = (a, b) => {
  if (isPreceding(b, a)) {
    return 1;
  }
  return -1;
};
var sortNodes = (nodes = []) => {
  const arr = [...nodes];
  if (arr.length > 1) {
    arr.sort(compareNodes);
  }
  return arr;
};
var initNwsapi = (window, document) => {
  if (!window?.DOMException) {
    throw new TypeError(`Unexpected global object ${getType(window)}`);
  }
  if (document?.nodeType !== DOCUMENT_NODE) {
    document = window.document;
  }
  const nw = (0, import_nwsapi.default)({
    document,
    DOMException: window.DOMException
  });
  nw.configure({
    LOGERRORS: false
  });
  return nw;
};
var filterSelector = (selector2, target) => {
  const isQuerySelectorAll = target === TARGET_ALL;
  if (!selector2 || typeof selector2 !== "string" || /null|undefined/.test(selector2)) {
    return false;
  }
  if (selector2.includes("/") || REG_EXCLUDE_BASIC.test(selector2)) {
    return false;
  }
  if (selector2.includes("[")) {
    const index = selector2.lastIndexOf("[");
    if (selector2.indexOf("]", index) === -1) {
      return false;
    }
  }
  if (target === TARGET_FIRST) {
    return REG_ATTR_SIMPLE.test(selector2);
  }
  if (target === TARGET_ALL && REG_TAG_SIMPLE.test(selector2)) {
    return false;
  }
  if (selector2.includes(":")) {
    if (isQuerySelectorAll && REG_DESCEND.test(selector2)) {
      return false;
    }
    const isComplex = isQuerySelectorAll ? false : REG_COMPLEX.test(selector2);
    if (selector2.includes(":has(")) {
      if (isQuerySelectorAll) {
        return false;
      }
      if (!isComplex || REG_LOGIC_HAS_COMPOUND.test(selector2)) {
        return false;
      }
      return REG_END_WITH_HAS.test(selector2);
    }
    if (/(?:is|not)\(/.test(selector2)) {
      if (isComplex) {
        return !REG_LOGIC_COMPLEX.test(selector2);
      } else {
        return !REG_LOGIC_COMPOUND.test(selector2);
      }
    }
    if (REG_WO_LOGICAL.test(selector2)) {
      return false;
    }
  }
  return true;
};

// node_modules/@asamuzakjp/dom-selector/src/js/parser.js
var AST_SORT_ORDER = /* @__PURE__ */ new Map([
  [PS_ELEMENT_SELECTOR, BIT_01],
  [ID_SELECTOR, BIT_02],
  [CLASS_SELECTOR, BIT_04],
  [TYPE_SELECTOR, BIT_08],
  [ATTR_SELECTOR, BIT_16],
  [PS_CLASS_SELECTOR, BIT_32]
]);
var KEYS_PS_CLASS_STATE = /* @__PURE__ */ new Set([
  "checked",
  "closed",
  "disabled",
  "empty",
  "enabled",
  "in-range",
  "indeterminate",
  "invalid",
  "open",
  "out-of-range",
  "placeholder-shown",
  "read-only",
  "read-write",
  "valid"
]);
var KEYS_SHADOW_HOST = /* @__PURE__ */ new Set(["host", "host-context"]);
var REG_EMPTY_PS_FUNC = /(?<=:(?:dir|has|host(?:-context)?|is|lang|not|nth-(?:last-)?(?:child|of-type)|where))\(\s+\)/g;
var REG_SHADOW_PS_ELEMENT = /^part|slotted$/;
var U_FFFD = "\uFFFD";
var unescapeSelector = (selector2 = "") => {
  if (typeof selector2 === "string" && selector2.indexOf("\\", 0) >= 0) {
    const arr = selector2.split("\\");
    const selectorItems = [arr[0]];
    const l = arr.length;
    for (let i = 1; i < l; i++) {
      const item = arr[i];
      if (item === "" && i === l - 1) {
        selectorItems.push(U_FFFD);
      } else if (item === "") {
        selectorItems.push("\\");
        i++;
        if (i < l) {
          selectorItems.push(arr[i]);
        }
      } else {
        const hexExists = /^([\da-f]{1,6}\s?)/i.exec(item);
        if (hexExists) {
          const [, hex] = hexExists;
          let str;
          try {
            const low = parseInt("D800", HEX);
            const high = parseInt("DFFF", HEX);
            const deci = parseInt(hex, HEX);
            if (deci === 0 || deci >= low && deci <= high) {
              str = U_FFFD;
            } else {
              str = String.fromCodePoint(deci);
            }
          } catch (e) {
            str = U_FFFD;
          }
          let postStr = "";
          if (item.length > hex.length) {
            postStr = item.substring(hex.length);
          }
          selectorItems.push(`${str}${postStr}`);
        } else if (/^[\n\r\f]/.test(item)) {
          selectorItems.push(`\\${item}`);
        } else {
          selectorItems.push(item);
        }
      }
    }
    return selectorItems.join("");
  }
  return selector2;
};
var preprocess = (value) => {
  if (typeof value !== "string") {
    if (value === void 0 || value === null) {
      return getType(value).toLowerCase();
    } else if (Array.isArray(value)) {
      return value.join(",");
    } else if (Object.hasOwn(value, "toString")) {
      return value.toString();
    } else {
      throw new DOMException(`Invalid selector ${value}`, SYNTAX_ERR);
    }
  }
  let selector2 = value;
  let index = 0;
  while (index >= 0) {
    index = selector2.indexOf("#", index);
    if (index < 0) {
      break;
    }
    const preHash = selector2.substring(0, index + 1);
    let postHash = selector2.substring(index + 1);
    const codePoint = postHash.codePointAt(0);
    if (codePoint > BIT_FFFF) {
      const str = `\\${codePoint.toString(HEX)} `;
      if (postHash.length === DUO) {
        postHash = str;
      } else {
        postHash = `${str}${postHash.substring(DUO)}`;
      }
    }
    selector2 = `${preHash}${postHash}`;
    index++;
  }
  selector2 = selector2.replace(/\f|\r\n?/g, "\n").replace(/[\0\uD800-\uDFFF]|\\$/g, U_FFFD);
  if (selector2 === "&") {
    return "";
  }
  return selector2.replace(/\x26/g, ":scope");
};
var parseSelector = (sel) => {
  const selector2 = preprocess(sel);
  if (/^$|^\s*>|,\s*$/.test(selector2)) {
    throw new DOMException(`Invalid selector ${selector2}`, SYNTAX_ERR);
  }
  try {
    return parse51(selector2, {
      context: "selectorList"
    });
  } catch (e) {
    const { message } = e;
    if (/^(?:"\]"|Attribute selector [()\s,=~^$*|]+) is expected$/.test(
      message
    ) && !selector2.endsWith("]")) {
      const index = selector2.lastIndexOf("[");
      const selPart = selector2.substring(index);
      if (selPart.includes('"')) {
        const quotes = selPart.match(/"/g).length;
        if (quotes % 2) {
          return parseSelector(`${selector2}"]`);
        }
        return parseSelector(`${selector2}]`);
      }
      return parseSelector(`${selector2}]`);
    } else if (message === '")" is expected') {
      if (REG_EMPTY_PS_FUNC.test(selector2)) {
        return parseSelector(`${selector2.replaceAll(REG_EMPTY_PS_FUNC, "()")}`);
      } else if (!selector2.endsWith(")")) {
        return parseSelector(`${selector2})`);
      } else {
        throw new DOMException(`Invalid selector ${selector2}`, SYNTAX_ERR);
      }
    } else {
      throw new DOMException(`Invalid selector ${selector2}`, SYNTAX_ERR);
    }
  }
};
var walkAST = (ast = {}, toObject = false) => {
  const branches = /* @__PURE__ */ new Set();
  const info = {
    hasForgivenPseudoFunc: false,
    hasHasPseudoFunc: false,
    hasLogicalPseudoFunc: false,
    hasNotPseudoFunc: false,
    hasNthChildOfSelector: false,
    hasNestedSelector: false,
    hasStatePseudoClass: false
  };
  const opt = {
    enter(node) {
      switch (node.type) {
        case CLASS_SELECTOR: {
          if (/^-?\d/.test(node.name)) {
            throw new DOMException(
              `Invalid selector .${node.name}`,
              SYNTAX_ERR
            );
          }
          break;
        }
        case ID_SELECTOR: {
          if (/^-?\d/.test(node.name)) {
            throw new DOMException(
              `Invalid selector #${node.name}`,
              SYNTAX_ERR
            );
          }
          break;
        }
        case PS_CLASS_SELECTOR: {
          if (KEYS_LOGICAL.has(node.name)) {
            info.hasNestedSelector = true;
            info.hasLogicalPseudoFunc = true;
            if (node.name === "has") {
              info.hasHasPseudoFunc = true;
            } else if (node.name === "not") {
              info.hasNotPseudoFunc = true;
            } else {
              info.hasForgivenPseudoFunc = true;
            }
          } else if (KEYS_PS_CLASS_STATE.has(node.name)) {
            info.hasStatePseudoClass = true;
          } else if (KEYS_SHADOW_HOST.has(node.name) && Array.isArray(node.children) && node.children.length) {
            info.hasNestedSelector = true;
          }
          break;
        }
        case PS_ELEMENT_SELECTOR: {
          if (REG_SHADOW_PS_ELEMENT.test(node.name)) {
            info.hasNestedSelector = true;
          }
          break;
        }
        case NTH: {
          if (node.selector) {
            info.hasNestedSelector = true;
            info.hasNthChildOfSelector = true;
          }
          break;
        }
        case SELECTOR: {
          branches.add(node.children);
          break;
        }
        default:
      }
    }
  };
  const clonedAst = clone(ast);
  walk2(toObject ? toPlainObject(clonedAst) : clonedAst, opt);
  if (info.hasNestedSelector === true) {
    findAll(clonedAst, (node, item, list) => {
      if (list) {
        if (node.type === PS_CLASS_SELECTOR && KEYS_LOGICAL.has(node.name)) {
          const itemList = list.filter((i) => {
            const { name: name50, type } = i;
            return type === PS_CLASS_SELECTOR && KEYS_LOGICAL.has(name50);
          });
          for (const { children } of itemList) {
            for (const { children: grandChildren } of children) {
              for (const { children: greatGrandChildren } of grandChildren) {
                if (branches.has(greatGrandChildren)) {
                  branches.delete(greatGrandChildren);
                }
              }
            }
          }
        } else if (node.type === PS_CLASS_SELECTOR && KEYS_SHADOW_HOST.has(node.name) && Array.isArray(node.children) && node.children.length) {
          const itemList = list.filter((i) => {
            const { children, name: name50, type } = i;
            const res = type === PS_CLASS_SELECTOR && KEYS_SHADOW_HOST.has(name50) && Array.isArray(children) && children.length;
            return res;
          });
          for (const { children } of itemList) {
            for (const { children: grandChildren } of children) {
              if (branches.has(grandChildren)) {
                branches.delete(grandChildren);
              }
            }
          }
        } else if (node.type === PS_ELEMENT_SELECTOR && REG_SHADOW_PS_ELEMENT.test(node.name)) {
          const itemList = list.filter((i) => {
            const { name: name50, type } = i;
            const res = type === PS_ELEMENT_SELECTOR && REG_SHADOW_PS_ELEMENT.test(name50);
            return res;
          });
          for (const { children } of itemList) {
            for (const { children: grandChildren } of children) {
              if (branches.has(grandChildren)) {
                branches.delete(grandChildren);
              }
            }
          }
        } else if (node.type === NTH && node.selector) {
          const itemList = list.filter((i) => {
            const { selector: selector2, type } = i;
            const res = type === NTH && selector2;
            return res;
          });
          for (const { selector: selector2 } of itemList) {
            const { children } = selector2;
            for (const { children: grandChildren } of children) {
              if (branches.has(grandChildren)) {
                branches.delete(grandChildren);
              }
            }
          }
        }
      }
    });
  }
  return {
    info,
    branches: [...branches]
  };
};
var compareASTNodes = (a, b) => {
  const bitA = AST_SORT_ORDER.get(a.type);
  const bitB = AST_SORT_ORDER.get(b.type);
  if (bitA === bitB) {
    return 0;
  } else if (bitA > bitB) {
    return 1;
  } else {
    return -1;
  }
};
var sortAST = (asts) => {
  const arr = [...asts];
  if (arr.length > 1) {
    arr.sort(compareASTNodes);
  }
  return arr;
};
var parseAstName = (selector2) => {
  let prefix;
  let localName;
  if (selector2 && typeof selector2 === "string") {
    if (selector2.indexOf("|") > -1) {
      [prefix, localName] = selector2.split("|");
    } else {
      prefix = "*";
      localName = selector2;
    }
  } else {
    throw new DOMException(`Invalid selector ${selector2}`, SYNTAX_ERR);
  }
  return {
    prefix,
    localName
  };
};

// node_modules/@asamuzakjp/dom-selector/src/js/matcher.js
var KEYS_FORM_PS_DISABLED = /* @__PURE__ */ new Set([
  ...FORM_PARTS,
  "fieldset",
  "optgroup",
  "option"
]);
var KEYS_INPUT_EDIT2 = new Set(INPUT_EDIT);
var REG_LANG_VALID = new RegExp(`^(?:\\*-)?${ALPHA_NUM}${LANG_PART}$`, "i");
var matchPseudoElementSelector = (astName, astType, opt = {}) => {
  const { forgive, globalObject, warn } = opt;
  if (astType !== PS_ELEMENT_SELECTOR) {
    throw new TypeError(`Unexpected ast type ${getType(astType)}`);
  }
  switch (astName) {
    case "after":
    case "backdrop":
    case "before":
    case "cue":
    case "cue-region":
    case "first-letter":
    case "first-line":
    case "file-selector-button":
    case "marker":
    case "placeholder":
    case "selection":
    case "target-text": {
      if (warn) {
        throw generateException(
          `Unsupported pseudo-element ::${astName}`,
          NOT_SUPPORTED_ERR,
          globalObject
        );
      }
      break;
    }
    case "part":
    case "slotted": {
      if (warn) {
        throw generateException(
          `Unsupported pseudo-element ::${astName}()`,
          NOT_SUPPORTED_ERR,
          globalObject
        );
      }
      break;
    }
    default: {
      if (astName.startsWith("-webkit-")) {
        if (warn) {
          throw generateException(
            `Unsupported pseudo-element ::${astName}`,
            NOT_SUPPORTED_ERR,
            globalObject
          );
        }
      } else if (!forgive) {
        throw generateException(
          `Unknown pseudo-element ::${astName}`,
          SYNTAX_ERR,
          globalObject
        );
      }
    }
  }
};
var matchDirectionPseudoClass = (ast, node) => {
  const { name: name50 } = ast;
  if (!name50) {
    const type = name50 === "" ? "(empty String)" : getType(name50);
    throw new TypeError(`Unexpected ast type ${type}`);
  }
  const dir = getDirectionality(node);
  return name50 === dir;
};
var matchLanguagePseudoClass = (ast, node) => {
  const elementLang = getLanguageAttribute(node);
  if (elementLang === null) {
    return false;
  }
  if (ast._langRegex !== void 0) {
    if (ast._langPattern === "*") {
      return elementLang !== "";
    }
    if (ast._langRegex === null) {
      return false;
    }
    return ast._langRegex.test(elementLang);
  }
  const { name: name50, type, value } = ast;
  let langPattern;
  if (type === STRING && value) {
    langPattern = value;
  } else if (type === IDENT && name50) {
    langPattern = unescapeSelector(name50);
  }
  ast._langPattern = langPattern;
  if (typeof langPattern !== "string") {
    ast._langRegex = null;
    return false;
  }
  if (langPattern === "*") {
    ast._langRegex = null;
    return elementLang !== "";
  }
  if (!REG_LANG_VALID.test(langPattern)) {
    ast._langRegex = null;
    return false;
  }
  let matcherRegex;
  if (langPattern.indexOf("-") > -1) {
    const [langMain, langSub, ...langRest] = langPattern.split("-");
    const extendedMain = langMain === "*" ? `${ALPHA_NUM}${LANG_PART}` : `${langMain}${LANG_PART}`;
    const extendedSub = `-${langSub}${LANG_PART}`;
    let extendedRest = "";
    for (let i = 0; i < langRest.length; i++) {
      extendedRest += `-${langRest[i]}${LANG_PART}`;
    }
    matcherRegex = new RegExp(
      `^${extendedMain}${extendedSub}${extendedRest}$`,
      "i"
    );
  } else {
    matcherRegex = new RegExp(`^${langPattern}${LANG_PART}$`, "i");
  }
  ast._langRegex = matcherRegex;
  return matcherRegex.test(elementLang);
};
var matchDisabledPseudoClass = (astName, node) => {
  const { localName, parentNode } = node;
  if (!KEYS_FORM_PS_DISABLED.has(localName) && !isCustomElement(node, { formAssociated: true })) {
    return false;
  }
  let isDisabled = false;
  if (node.disabled || node.hasAttribute("disabled")) {
    isDisabled = true;
  } else if (localName === "option") {
    if (parentNode && parentNode.localName === "optgroup" && (parentNode.disabled || parentNode.hasAttribute("disabled"))) {
      isDisabled = true;
    }
  } else if (localName !== "optgroup") {
    let current = parentNode;
    while (current) {
      if (current.localName === "fieldset" && (current.disabled || current.hasAttribute("disabled"))) {
        let legend;
        let element = current.firstElementChild;
        while (element) {
          if (element.localName === "legend") {
            legend = element;
            break;
          }
          element = element.nextElementSibling;
        }
        if (!legend || !legend.contains(node)) {
          isDisabled = true;
        }
        break;
      }
      current = current.parentNode;
    }
  }
  if (astName === "disabled") {
    return isDisabled;
  }
  return !isDisabled;
};
var matchReadOnlyPseudoClass = (astName, node) => {
  const { localName } = node;
  let isReadOnly = false;
  switch (localName) {
    case "textarea":
    case "input": {
      const isEditableInput = !node.type || KEYS_INPUT_EDIT2.has(node.type);
      if (localName === "textarea" || isEditableInput) {
        isReadOnly = node.readOnly || node.hasAttribute("readonly") || node.disabled || node.hasAttribute("disabled");
      } else {
        isReadOnly = true;
      }
      break;
    }
    default: {
      isReadOnly = !isContentEditable(node);
    }
  }
  if (astName === "read-only") {
    return isReadOnly;
  }
  return !isReadOnly;
};
var matchAttributeSelector = (ast, node, opt = {}) => {
  const {
    flags: astFlags,
    matcher: astMatcher,
    name: astName,
    value: astValue
  } = ast;
  const { check, forgive, globalObject } = opt;
  if (typeof astFlags === "string" && !/^[is]$/i.test(astFlags) && !forgive) {
    const css = generate51(ast);
    throw generateException(
      `Invalid selector ${css}`,
      SYNTAX_ERR,
      globalObject
    );
  }
  const { attributes } = node;
  if (!attributes || !attributes.length) {
    return false;
  }
  let caseInsensitive;
  if (node.ownerDocument.contentType === "text/html") {
    if (typeof astFlags === "string" && /^s$/i.test(astFlags)) {
      caseInsensitive = false;
    } else {
      caseInsensitive = true;
    }
  } else if (typeof astFlags === "string" && /^i$/i.test(astFlags)) {
    caseInsensitive = true;
  } else {
    caseInsensitive = false;
  }
  let astAttrName = unescapeSelector(astName.name);
  if (caseInsensitive) {
    astAttrName = astAttrName.toLowerCase();
  }
  const attrValues = /* @__PURE__ */ new Set();
  if (astAttrName.indexOf("|") > -1) {
    const { prefix: astPrefix, localName: astLocalName } = parseAstName(astAttrName);
    for (const item of attributes) {
      let { name: itemName, value: itemValue } = item;
      if (caseInsensitive) {
        itemName = itemName.toLowerCase();
        itemValue = itemValue.toLowerCase();
      }
      const colonIdx = itemName.indexOf(":");
      switch (astPrefix) {
        case "": {
          if (astLocalName === itemName) {
            attrValues.add(itemValue);
          }
          break;
        }
        case "*": {
          if (colonIdx > -1) {
            const itemLocalName = itemName.substring(colonIdx + 1).replace(/^:/, "");
            if (itemLocalName === astLocalName) {
              attrValues.add(itemValue);
            }
          } else if (astLocalName === itemName) {
            attrValues.add(itemValue);
          }
          break;
        }
        default: {
          if (!check) {
            if (forgive) {
              return false;
            }
            const css = generate51(ast);
            throw generateException(
              `Invalid selector ${css}`,
              SYNTAX_ERR,
              globalObject
            );
          }
          if (colonIdx > -1) {
            const itemPrefix = itemName.substring(0, colonIdx);
            const itemLocalName = itemName.substring(colonIdx + 1).replace(/^:/, "");
            if (itemPrefix === "xml" && itemLocalName === "lang") {
              continue;
            } else if (astPrefix === itemPrefix && astLocalName === itemLocalName) {
              const namespaceDeclared = isNamespaceDeclared(astPrefix, node);
              if (namespaceDeclared) {
                attrValues.add(itemValue);
              }
            }
          }
        }
      }
    }
  } else {
    for (let { name: itemName, value: itemValue } of attributes) {
      if (caseInsensitive) {
        itemName = itemName.toLowerCase();
        itemValue = itemValue.toLowerCase();
      }
      const colonIdx = itemName.indexOf(":");
      if (colonIdx > -1) {
        const itemPrefix = itemName.substring(0, colonIdx);
        const itemLocalName = itemName.substring(colonIdx + 1).replace(/^:/, "");
        if (!itemPrefix && astAttrName === `:${itemLocalName}`) {
          attrValues.add(itemValue);
        } else if (itemPrefix === "xml" && itemLocalName === "lang") {
          continue;
        } else if (astAttrName === itemLocalName) {
          attrValues.add(itemValue);
        }
      } else if (astAttrName === itemName) {
        attrValues.add(itemValue);
      }
    }
  }
  if (!attrValues.size) {
    return false;
  }
  const { name: astIdentValue, value: astStringValue } = astValue ?? {};
  let attrValue;
  if (astIdentValue) {
    if (caseInsensitive) {
      attrValue = unescapeSelector(astIdentValue).toLowerCase();
    } else {
      attrValue = unescapeSelector(astIdentValue);
    }
  } else if (astStringValue) {
    if (caseInsensitive) {
      attrValue = astStringValue.toLowerCase();
    } else {
      attrValue = astStringValue;
    }
  } else if (astStringValue === "") {
    attrValue = astStringValue;
  }
  switch (astMatcher) {
    case "=": {
      return typeof attrValue === "string" && attrValues.has(attrValue);
    }
    case "~=": {
      if (attrValue && typeof attrValue === "string") {
        if (/\s/.test(attrValue)) {
          return false;
        }
        if (ast._tildeTarget === void 0) {
          ast._tildeTarget = ` ${attrValue} `;
        }
        const target = ast._tildeTarget;
        for (const value of attrValues) {
          if (` ${value.replace(/[\t\r\n\f]/g, " ")} `.includes(target)) {
            return true;
          }
        }
      }
      return false;
    }
    case "|=": {
      if (attrValue && typeof attrValue === "string") {
        for (const value of attrValues) {
          if (value === attrValue || value.startsWith(`${attrValue}-`)) {
            return true;
          }
        }
      }
      return false;
    }
    case "^=": {
      if (attrValue && typeof attrValue === "string") {
        for (const value of attrValues) {
          if (value.startsWith(`${attrValue}`)) {
            return true;
          }
        }
      }
      return false;
    }
    case "$=": {
      if (attrValue && typeof attrValue === "string") {
        for (const value of attrValues) {
          if (value.endsWith(`${attrValue}`)) {
            return true;
          }
        }
      }
      return false;
    }
    case "*=": {
      if (attrValue && typeof attrValue === "string") {
        for (const value of attrValues) {
          if (value.includes(`${attrValue}`)) {
            return true;
          }
        }
      }
      return false;
    }
    case null:
    default: {
      return true;
    }
  }
};
var matchTypeSelector = (ast, node, opt = {}) => {
  const astName = unescapeSelector(ast.name);
  const { localName, namespaceURI, prefix } = node;
  const { check, forgive, globalObject } = opt;
  let { prefix: astPrefix, localName: astLocalName } = parseAstName(
    astName,
    node
  );
  const isHTML = node.ownerDocument.contentType === "text/html" && (!namespaceURI || namespaceURI === "http://www.w3.org/1999/xhtml");
  if (isHTML && localName === astLocalName && !astName.includes("|")) {
    return true;
  }
  const firstChar = localName.charCodeAt(0);
  const isAlphabet = firstChar >= 65 && firstChar <= 90 || firstChar >= 97 && firstChar <= 122;
  if (isHTML && isAlphabet) {
    astPrefix = astPrefix.toLowerCase();
    astLocalName = astLocalName.toLowerCase();
  }
  let nodePrefix;
  let nodeLocalName;
  const colonIdx = localName.indexOf(":");
  if (colonIdx > -1) {
    nodePrefix = localName.substring(0, colonIdx);
    nodeLocalName = localName.substring(colonIdx + 1);
  } else {
    nodePrefix = prefix || "";
    nodeLocalName = localName;
  }
  const isUniversal = astLocalName === "*";
  switch (astPrefix) {
    case "": {
      return !nodePrefix && !namespaceURI && (isUniversal || astLocalName === nodeLocalName);
    }
    case "*": {
      return isUniversal || astLocalName === nodeLocalName;
    }
    default: {
      if (!check) {
        if (forgive) {
          return false;
        }
        const css = generate51(ast);
        throw generateException(
          `Invalid selector ${css}`,
          SYNTAX_ERR,
          globalObject
        );
      }
      const astNS = node.lookupNamespaceURI(astPrefix);
      const nodeNS = node.lookupNamespaceURI(nodePrefix);
      if (astNS === nodeNS && astPrefix === nodePrefix) {
        return isUniversal || astLocalName === nodeLocalName;
      } else if (!forgive && !astNS) {
        throw generateException(
          `Undeclared namespace ${astPrefix}`,
          SYNTAX_ERR,
          globalObject
        );
      }
      return false;
    }
  }
};

// node_modules/@asamuzakjp/dom-selector/src/js/finder.js
var DIR_NEXT = "next";
var DIR_PREV = "prev";
var KEYS_FORM = /* @__PURE__ */ new Set([...FORM_PARTS, "fieldset", "form"]);
var KEYS_FORM_PS_VALID = /* @__PURE__ */ new Set([...FORM_PARTS, "form"]);
var KEYS_INPUT_CHECK = new Set(INPUT_CHECK);
var KEYS_INPUT_PLACEHOLDER = /* @__PURE__ */ new Set([...INPUT_TEXT, "number"]);
var KEYS_INPUT_RANGE = /* @__PURE__ */ new Set([...INPUT_DATE, "number", "range"]);
var KEYS_INPUT_REQUIRED = /* @__PURE__ */ new Set([...INPUT_CHECK, ...INPUT_EDIT, "file"]);
var KEYS_INPUT_RESET = /* @__PURE__ */ new Set(["button", "reset"]);
var KEYS_INPUT_SUBMIT = /* @__PURE__ */ new Set(["image", "submit"]);
var KEYS_MODIFIER = /* @__PURE__ */ new Set([
  "Alt",
  "AltGraph",
  "CapsLock",
  "Control",
  "Fn",
  "FnLock",
  "Hyper",
  "Meta",
  "NumLock",
  "ScrollLock",
  "Shift",
  "Super",
  "Symbol",
  "SymbolLock"
]);
var KEYS_PS_UNCACHE = /* @__PURE__ */ new Set([
  "any-link",
  "defined",
  "dir",
  "link",
  "scope"
]);
var KEYS_PS_NTH_OF_TYPE = /* @__PURE__ */ new Set([
  "first-of-type",
  "last-of-type",
  "only-of-type"
]);
var Finder = class {
  /* private fields */
  #ast;
  #astCache;
  #check;
  #descendant;
  #document;
  #documentCache;
  #documentURL;
  #event;
  #eventHandlers;
  #filterLeavesCache;
  #focus;
  #invalidate;
  #invalidateResults;
  #lastFocusVisible;
  #node;
  #nodeWalker;
  #nodes;
  #noexcept;
  #pseudoElement;
  #results;
  #root;
  #rootWalker;
  #scoped;
  #selector;
  #selectorAST;
  #shadow;
  #verifyShadowHost;
  #walkers;
  #warn;
  #window;
  /**
   * constructor
   * @param {object} window - The window object.
   */
  constructor(window) {
    this.#window = window;
    this.#astCache = /* @__PURE__ */ new WeakMap();
    this.#documentCache = /* @__PURE__ */ new WeakMap();
    this.#event = null;
    this.#focus = null;
    this.#lastFocusVisible = null;
    this.#eventHandlers = /* @__PURE__ */ new Set([
      {
        keys: ["focus", "focusin"],
        handler: this._handleFocusEvent
      },
      {
        keys: ["keydown", "keyup"],
        handler: this._handleKeyboardEvent
      },
      {
        keys: ["mouseover", "mousedown", "mouseup", "click", "mouseout"],
        handler: this._handleMouseEvent
      }
    ]);
    this.#filterLeavesCache = /* @__PURE__ */ new WeakMap();
    this._registerEventListeners();
    this.clearResults(true);
  }
  /**
   * Handles errors.
   * @param {Error} e - The error object.
   * @param {object} [opt] - Options.
   * @param {boolean} [opt.noexcept] - If true, exceptions are not thrown.
   * @throws {Error} Throws an error.
   * @returns {void}
   */
  onError = (e, opt = {}) => {
    const noexcept = opt.noexcept ?? this.#noexcept;
    if (noexcept) {
      return;
    }
    const isDOMException = e instanceof DOMException || e instanceof this.#window.DOMException;
    if (isDOMException) {
      if (e.name === NOT_SUPPORTED_ERR) {
        if (this.#warn) {
          console.warn(e.message);
        }
        return;
      }
      throw new this.#window.DOMException(e.message, e.name);
    }
    if (e.name in this.#window) {
      throw new this.#window[e.name](e.message, { cause: e });
    }
    throw e;
  };
  /**
   * Sets up the finder.
   * @param {string} selector - The CSS selector.
   * @param {object} node - Document, DocumentFragment, or Element.
   * @param {object} [opt] - Options.
   * @param {boolean} [opt.check] - Indicates if running in internal check().
   * @param {boolean} [opt.noexcept] - If true, exceptions are not thrown.
   * @param {boolean} [opt.warn] - If true, console warnings are enabled.
   * @returns {object} The finder instance.
   */
  setup = (selector2, node, opt = {}) => {
    const { check, noexcept, warn } = opt;
    this.#check = !!check;
    this.#noexcept = !!noexcept;
    this.#warn = !!warn;
    [this.#document, this.#root, this.#shadow] = resolveContent(node);
    this.#documentURL = null;
    this.#node = node;
    this.#scoped = this.#node !== this.#root && this.#node.nodeType === ELEMENT_NODE;
    this.#selector = selector2;
    this.#pseudoElement = [];
    this.#walkers = /* @__PURE__ */ new WeakMap();
    this.#nodeWalker = null;
    this.#rootWalker = null;
    this.#verifyShadowHost = null;
    this.clearResults();
    return this;
  };
  /**
   * Clear cached results.
   * @param {boolean} all - clear all results
   * @returns {void}
   */
  clearResults = (all = false) => {
    this.#invalidateResults = /* @__PURE__ */ new WeakMap();
    if (all) {
      this.#results = /* @__PURE__ */ new WeakMap();
      this.#filterLeavesCache = /* @__PURE__ */ new WeakMap();
    }
  };
  /**
   * Handles focus events.
   * @private
   * @param {Event} evt - The event object.
   * @returns {void}
   */
  _handleFocusEvent = (evt) => {
    this.#focus = evt;
  };
  /**
   * Handles keyboard events.
   * @private
   * @param {Event} evt - The event object.
   * @returns {void}
   */
  _handleKeyboardEvent = (evt) => {
    const { key } = evt;
    if (!KEYS_MODIFIER.has(key)) {
      this.#event = evt;
    }
  };
  /**
   * Handles mouse events.
   * @private
   * @param {Event} evt - The event object.
   * @returns {void}
   */
  _handleMouseEvent = (evt) => {
    this.#event = evt;
  };
  /**
   * Registers event listeners.
   * @private
   * @returns {Array.<void>} An array of return values from addEventListener.
   */
  _registerEventListeners = () => {
    const func = [];
    for (const eventHandler of this.#eventHandlers) {
      const { keys, handler } = eventHandler;
      const l = keys.length;
      for (let i = 0; i < l; i++) {
        const key = keys[i];
        func.push(
          this.#window.addEventListener(key, handler, {
            capture: true,
            passive: true
          })
        );
      }
    }
    return func;
  };
  /**
   * Processes selector branches into the internal AST structure.
   * @private
   * @param {Array.<Array.<object>>} branches - The branches from walkAST.
   * @param {string} selector - The original selector for error reporting.
   * @returns {{ast: Array, descendant: boolean}}
   * An object with the AST, descendant flag.
   */
  _processSelectorBranches = (branches, selector2) => {
    let descendant = false;
    const ast = [];
    const l = branches.length;
    for (let i = 0; i < l; i++) {
      const items = [...branches[i]];
      const branch = [];
      let item = items.shift();
      if (item && item.type !== COMBINATOR) {
        const leaves = /* @__PURE__ */ new Set();
        while (item) {
          if (item.type === COMBINATOR) {
            const [nextItem] = items;
            if (!nextItem || nextItem.type === COMBINATOR) {
              const msg = `Invalid selector ${selector2}`;
              this.onError(generateException(msg, SYNTAX_ERR, this.#window));
              return { ast: [], descendant: false, invalidate: false };
            }
            if (item.name === " " || item.name === ">") {
              descendant = true;
            }
            branch.push({ combo: item, leaves: sortAST(leaves) });
            leaves.clear();
          } else {
            if (item.name && typeof item.name === "string") {
              const unescapedName = unescapeSelector(item.name);
              if (unescapedName !== item.name) {
                item.name = unescapedName;
              }
              if (/[|:]/.test(unescapedName)) {
                item.namespace = true;
              }
            }
            leaves.add(item);
          }
          if (items.length) {
            item = items.shift();
          } else {
            branch.push({ combo: null, leaves: sortAST(leaves) });
            leaves.clear();
            break;
          }
        }
      }
      ast.push({ branch, dir: null, filtered: false, find: false });
    }
    return { ast, descendant };
  };
  /**
   * Corresponds AST and nodes.
   * @private
   * @param {string} selector - The CSS selector.
   * @returns {Array.<Array.<object>>} An array with the AST and nodes.
   */
  _correspond = (selector2) => {
    const nodes = [];
    this.#descendant = false;
    this.#invalidate = false;
    let ast;
    if (this.#documentCache.has(this.#document)) {
      const cachedItem = this.#documentCache.get(this.#document);
      if (cachedItem && cachedItem.has(`${selector2}`)) {
        const item = cachedItem.get(`${selector2}`);
        ast = item.ast;
        this.#descendant = item.descendant;
        this.#invalidate = item.invalidate;
        this.#selectorAST = item.selectorAST;
      }
    }
    if (ast) {
      const l = ast.length;
      for (let i = 0; i < l; i++) {
        ast[i].dir = null;
        ast[i].filtered = false;
        ast[i].find = false;
        nodes[i] = [];
      }
    } else {
      this.#selectorAST = parseSelector(selector2);
      const { branches, info } = walkAST(this.#selectorAST, true);
      const {
        hasHasPseudoFunc,
        hasLogicalPseudoFunc,
        hasNthChildOfSelector,
        hasStatePseudoClass
      } = info;
      this.#invalidate = hasHasPseudoFunc || hasStatePseudoClass || !!(hasLogicalPseudoFunc && hasNthChildOfSelector);
      const processed = this._processSelectorBranches(branches, selector2);
      ast = processed.ast;
      this.#descendant = processed.descendant;
      let cachedItem;
      if (this.#documentCache.has(this.#document)) {
        cachedItem = this.#documentCache.get(this.#document);
      } else {
        cachedItem = /* @__PURE__ */ new Map();
      }
      cachedItem.set(`${selector2}`, {
        ast,
        descendant: this.#descendant,
        invalidate: this.#invalidate,
        selectorAST: this.#selectorAST
      });
      this.#documentCache.set(this.#document, cachedItem);
      for (let i = 0; i < ast.length; i++) {
        nodes[i] = [];
      }
    }
    return [ast, nodes];
  };
  /**
   * Creates a TreeWalker.
   * @private
   * @param {object} node - The Document, DocumentFragment, or Element node.
   * @param {object} [opt] - Options.
   * @param {boolean} [opt.force] - Force creation of a new TreeWalker.
   * @param {number} [opt.whatToShow] - The NodeFilter whatToShow value.
   * @returns {object} The TreeWalker object.
   */
  _createTreeWalker = (node, opt = {}) => {
    const { force = false, whatToShow = SHOW_CONTAINER } = opt;
    if (force) {
      return this.#document.createTreeWalker(node, whatToShow);
    } else if (this.#walkers.has(node)) {
      return this.#walkers.get(node);
    }
    const walker = this.#document.createTreeWalker(node, whatToShow);
    this.#walkers.set(node, walker);
    return walker;
  };
  /**
   * Gets selector branches from cache or parses them.
   * @private
   * @param {object} selector - The AST.
   * @returns {Array.<Array.<object>>} The selector branches.
   */
  _getSelectorBranches = (selector2) => {
    if (this.#astCache.has(selector2)) {
      return this.#astCache.get(selector2);
    }
    const { branches } = walkAST(selector2);
    this.#astCache.set(selector2, branches);
    return branches;
  };
  /**
   * Gets the children of a node, optionally filtered by a selector.
   * @private
   * @param {object} parentNode - The parent element.
   * @param {Array.<Array.<object>>} selectorBranches - The selector branches.
   * @param {object} opt - Options.
   * @returns {Array.<object>} An array of child nodes.
   */
  _getFilteredChildren = (parentNode, selectorBranches, opt) => {
    const children = [];
    let childNode = parentNode.firstElementChild;
    while (childNode) {
      if (selectorBranches) {
        let isMatch = false;
        const l = selectorBranches.length;
        for (let i = 0; i < l; i++) {
          const leaves = selectorBranches[i];
          if (this._matchLeaves(leaves, childNode, opt)) {
            isMatch = true;
            break;
          }
        }
        if (isMatch) {
          if (this.#node === childNode) {
            children.push(childNode);
          } else if (isVisible(childNode)) {
            children.push(childNode);
          }
        }
      } else {
        children.push(childNode);
      }
      childNode = childNode.nextElementSibling;
    }
    return children;
  };
  /**
   * Collects nth-child nodes.
   * @private
   * @param {object} anb - An+B options.
   * @param {number} anb.a - The 'a' value.
   * @param {number} anb.b - The 'b' value.
   * @param {boolean} [anb.reverse] - If true, reverses the order.
   * @param {object} [anb.selector] - The AST.
   * @param {object} node - The Element node.
   * @param {object} opt - Options.
   * @returns {Set.<object>} A collection of matched nodes.
   */
  _collectNthChild = (anb, node, opt) => {
    const { a, b, selector: selector2 } = anb;
    const { parentNode } = node;
    if (!parentNode) {
      const matchedNode = /* @__PURE__ */ new Set();
      if (node === this.#root && a * 1 + b * 1 === 1) {
        if (selector2) {
          const selectorBranches2 = this._getSelectorBranches(selector2);
          const l = selectorBranches2.length;
          for (let i = 0; i < l; i++) {
            const leaves = selectorBranches2[i];
            if (this._matchLeaves(leaves, node, opt)) {
              matchedNode.add(node);
              break;
            }
          }
        } else {
          matchedNode.add(node);
        }
      }
      return matchedNode;
    }
    const selectorBranches = selector2 ? this._getSelectorBranches(selector2) : null;
    const children = this._getFilteredChildren(
      parentNode,
      selectorBranches,
      opt
    );
    const matchedNodes = filterNodesByAnB(children, anb);
    return new Set(matchedNodes);
  };
  /**
   * Collects nth-of-type nodes.
   * @private
   * @param {object} anb - An+B options.
   * @param {number} anb.a - The 'a' value.
   * @param {number} anb.b - The 'b' value.
   * @param {boolean} [anb.reverse] - If true, reverses the order.
   * @param {object} node - The Element node.
   * @returns {Set.<object>} A collection of matched nodes.
   */
  _collectNthOfType = (anb, node) => {
    const { parentNode } = node;
    if (!parentNode) {
      if (node === this.#root && anb.a * 1 + anb.b * 1 === 1) {
        return /* @__PURE__ */ new Set([node]);
      }
      return /* @__PURE__ */ new Set();
    }
    const typedSiblings = [];
    let sibling = parentNode.firstElementChild;
    while (sibling) {
      if (sibling.localName === node.localName && sibling.namespaceURI === node.namespaceURI && sibling.prefix === node.prefix) {
        typedSiblings.push(sibling);
      }
      sibling = sibling.nextElementSibling;
    }
    const matchedNodes = filterNodesByAnB(typedSiblings, anb);
    return new Set(matchedNodes);
  };
  /**
   * Matches An+B.
   * @private
   * @param {object} ast - The AST.
   * @param {object} node - The Element node.
   * @param {string} nthName - The name of the nth pseudo-class.
   * @param {object} opt - Options.
   * @returns {Set.<object>} A collection of matched nodes.
   */
  _matchAnPlusB = (ast, node, nthName, opt) => {
    const {
      nth: { a, b, name: nthIdentName },
      selector: selector2
    } = ast;
    const anbMap = /* @__PURE__ */ new Map();
    if (nthIdentName) {
      if (nthIdentName === "even") {
        anbMap.set("a", 2);
        anbMap.set("b", 0);
      } else if (nthIdentName === "odd") {
        anbMap.set("a", 2);
        anbMap.set("b", 1);
      }
      if (nthName.indexOf("last") > -1) {
        anbMap.set("reverse", true);
      }
    } else {
      if (typeof a === "string" && /-?\d+/.test(a)) {
        anbMap.set("a", a * 1);
      } else {
        anbMap.set("a", 0);
      }
      if (typeof b === "string" && /-?\d+/.test(b)) {
        anbMap.set("b", b * 1);
      } else {
        anbMap.set("b", 0);
      }
      if (nthName.indexOf("last") > -1) {
        anbMap.set("reverse", true);
      }
    }
    if (nthName === "nth-child" || nthName === "nth-last-child") {
      if (selector2) {
        anbMap.set("selector", selector2);
      }
      const anb = Object.fromEntries(anbMap);
      const nodes = this._collectNthChild(anb, node, opt);
      return nodes;
    } else if (nthName === "nth-of-type" || nthName === "nth-last-of-type") {
      const anb = Object.fromEntries(anbMap);
      const nodes = this._collectNthOfType(anb, node);
      return nodes;
    }
    return /* @__PURE__ */ new Set();
  };
  /**
   * Matches the :has() pseudo-class function.
   * @private
   * @param {Array.<object>} astLeaves - The AST leaves.
   * @param {object} node - The Element node.
   * @param {object} [opt] - Options.
   * @returns {boolean} The result.
   */
  _matchHasPseudoFunc = (astLeaves, node, opt = {}) => {
    if (Array.isArray(astLeaves) && astLeaves.length) {
      const leaves = [...astLeaves];
      const [leaf] = leaves;
      const { type: leafType } = leaf;
      let combo;
      if (leafType === COMBINATOR) {
        combo = leaves.shift();
      } else {
        combo = {
          name: " ",
          type: COMBINATOR
        };
      }
      const twigLeaves = [];
      while (leaves.length) {
        const [item] = leaves;
        const { type: itemType } = item;
        if (itemType === COMBINATOR) {
          break;
        } else {
          twigLeaves.push(leaves.shift());
        }
      }
      const twig = {
        combo,
        leaves: twigLeaves
      };
      opt.dir = DIR_NEXT;
      const nodes = this._collectCombinatorMatches(twig, node, opt, []);
      if (nodes.length) {
        if (leaves.length) {
          let bool = false;
          for (const nextNode of nodes) {
            bool = this._matchHasPseudoFunc(leaves, nextNode, opt);
            if (bool) {
              break;
            }
          }
          return bool;
        }
        return true;
      }
    }
    return false;
  };
  /**
   * Evaluates the :has() pseudo-class.
   * @private
   * @param {object} astData - The AST data.
   * @param {object} node - The Element node.
   * @param {object} [opt] - Options.
   * @returns {?object} The matched node.
   */
  _evaluateHasPseudo = (astData, node, opt = {}) => {
    const { branches } = astData;
    let bool = false;
    const l = branches.length;
    for (let i = 0; i < l; i++) {
      const leaves = branches[i];
      bool = this._matchHasPseudoFunc(leaves, node, opt);
      if (bool) {
        break;
      }
    }
    if (!bool) {
      return null;
    }
    if ((opt.isShadowRoot || this.#shadow) && node.nodeType === DOCUMENT_FRAGMENT_NODE) {
      return this.#verifyShadowHost ? node : null;
    }
    return node;
  };
  /**
   * Matches logical pseudo-class functions.
   * @private
   * @param {object} astData - The AST data.
   * @param {object} node - The Element node.
   * @param {object} [opt] - Options.
   * @returns {?object} The matched node.
   */
  _matchLogicalPseudoFunc = (astData, node, opt = {}) => {
    const { astName, branches, twigBranches } = astData;
    if (astName === "has") {
      return this._evaluateHasPseudo(astData, node, opt);
    }
    const isShadowRoot = (opt.isShadowRoot || this.#shadow) && node.nodeType === DOCUMENT_FRAGMENT_NODE;
    if (isShadowRoot) {
      let invalid = false;
      for (const branch of branches) {
        if (branch.length > 1) {
          invalid = true;
          break;
        } else if (astName === "not") {
          const [{ type: childAstType }] = branch;
          if (childAstType !== PS_CLASS_SELECTOR) {
            invalid = true;
            break;
          }
        }
      }
      if (invalid) {
        return null;
      }
    }
    opt.forgive = astName === "is" || astName === "where";
    const l = twigBranches.length;
    let bool;
    for (let i = 0; i < l; i++) {
      const branch = twigBranches[i];
      const lastIndex = branch.length - 1;
      const { leaves } = branch[lastIndex];
      bool = this._matchLeaves(leaves, node, opt);
      if (bool && lastIndex > 0) {
        let nextNodes = /* @__PURE__ */ new Set([node]);
        for (let j = lastIndex - 1; j >= 0; j--) {
          const twig = branch[j];
          const arr = [];
          opt.dir = DIR_PREV;
          for (const nextNode of nextNodes) {
            this._collectCombinatorMatches(twig, nextNode, opt, arr);
          }
          if (arr.length) {
            if (j === 0) {
              bool = true;
            } else {
              nextNodes = new Set(arr);
            }
          } else {
            bool = false;
            break;
          }
        }
      }
      if (bool) {
        break;
      }
    }
    if (astName === "not") {
      if (bool) {
        return null;
      }
      return node;
    } else if (bool) {
      return node;
    }
    return null;
  };
  /**
   * Matches pseudo-class selector.
   * @private
   * @see https://html.spec.whatwg.org/#pseudo-classes
   * @param {object} ast - The AST.
   * @param {object} node - The Element node.
   * @param {object} [opt] - Options.
   * @param {boolean} [opt.forgive] - Ignores unknown or invalid selectors.
   * @param {boolean} [opt.warn] - If true, console warnings are enabled.
   * @returns {Set.<object>} A collection of matched nodes.
   */
  _matchPseudoClassSelector(ast, node, opt = {}) {
    const { children: astChildren, name: astName } = ast;
    const { localName, parentNode } = node;
    const { forgive, warn = this.#warn } = opt;
    const matched = /* @__PURE__ */ new Set();
    if (Array.isArray(astChildren) && KEYS_LOGICAL.has(astName)) {
      if (!astChildren.length && astName !== "is" && astName !== "where") {
        const css = generate51(ast);
        const msg = `Invalid selector ${css}`;
        return this.onError(generateException(msg, SYNTAX_ERR, this.#window));
      }
      let astData;
      if (this.#astCache.has(ast)) {
        astData = this.#astCache.get(ast);
      } else {
        const { branches } = walkAST(ast);
        if (astName === "has") {
          let forgiven = false;
          const l = astChildren.length;
          for (let i = 0; i < l; i++) {
            const child = astChildren[i];
            const item = find(child, findLogicalWithNestedHas);
            if (item) {
              const itemName = item.name;
              if (itemName === "is" || itemName === "where") {
                forgiven = true;
                break;
              } else {
                const css = generate51(ast);
                const msg = `Invalid selector ${css}`;
                return this.onError(
                  generateException(msg, SYNTAX_ERR, this.#window)
                );
              }
            }
          }
          if (forgiven) {
            return matched;
          }
          astData = {
            astName,
            branches
          };
        } else {
          const twigBranches = [];
          const l = branches.length;
          for (let i = 0; i < l; i++) {
            const [...leaves] = branches[i];
            const branch = [];
            const leavesSet = /* @__PURE__ */ new Set();
            let item = leaves.shift();
            while (item) {
              if (item.type === COMBINATOR) {
                branch.push({
                  combo: item,
                  leaves: [...leavesSet]
                });
                leavesSet.clear();
              } else if (item) {
                leavesSet.add(item);
              }
              if (leaves.length) {
                item = leaves.shift();
              } else {
                branch.push({
                  combo: null,
                  leaves: [...leavesSet]
                });
                leavesSet.clear();
                break;
              }
            }
            twigBranches.push(branch);
          }
          astData = {
            astName,
            branches,
            twigBranches
          };
          this.#astCache.set(ast, astData);
        }
      }
      const res = this._matchLogicalPseudoFunc(astData, node, opt);
      if (res) {
        matched.add(res);
      }
    } else if (Array.isArray(astChildren)) {
      if (/^nth-(?:last-)?(?:child|of-type)$/.test(astName)) {
        if (astChildren.length !== 1) {
          const css = generate51(ast);
          return this.onError(
            generateException(
              `Invalid selector ${css}`,
              SYNTAX_ERR,
              this.#window
            )
          );
        }
        const [branch] = astChildren;
        const nodes = this._matchAnPlusB(branch, node, astName, opt);
        return nodes;
      } else {
        switch (astName) {
          // :dir()
          case "dir": {
            if (astChildren.length !== 1) {
              const css = generate51(ast);
              return this.onError(
                generateException(
                  `Invalid selector ${css}`,
                  SYNTAX_ERR,
                  this.#window
                )
              );
            }
            const [astChild] = astChildren;
            const res = matchDirectionPseudoClass(astChild, node);
            if (res) {
              matched.add(node);
            }
            break;
          }
          // :lang()
          case "lang": {
            if (!astChildren.length) {
              const css = generate51(ast);
              return this.onError(
                generateException(
                  `Invalid selector ${css}`,
                  SYNTAX_ERR,
                  this.#window
                )
              );
            }
            let bool;
            for (const astChild of astChildren) {
              bool = matchLanguagePseudoClass(astChild, node);
              if (bool) {
                break;
              }
            }
            if (bool) {
              matched.add(node);
            }
            break;
          }
          // :state()
          case "state": {
            if (isCustomElement(node)) {
              const [{ value: stateValue }] = astChildren;
              if (stateValue) {
                if (node[stateValue]) {
                  matched.add(node);
                } else {
                  for (const i in node) {
                    const prop = node[i];
                    if (prop instanceof this.#window.ElementInternals) {
                      if (prop?.states?.has(stateValue)) {
                        matched.add(node);
                      }
                      break;
                    }
                  }
                }
              }
            }
            break;
          }
          case "current":
          case "heading":
          case "nth-col":
          case "nth-last-col": {
            if (warn) {
              this.onError(
                generateException(
                  `Unsupported pseudo-class :${astName}()`,
                  NOT_SUPPORTED_ERR,
                  this.#window
                )
              );
            }
            break;
          }
          // Ignore :host() and :host-context().
          case "host":
          case "host-context": {
            break;
          }
          // Deprecated in CSS Selectors 3.
          case "contains": {
            if (warn) {
              this.onError(
                generateException(
                  `Unknown pseudo-class :${astName}()`,
                  NOT_SUPPORTED_ERR,
                  this.#window
                )
              );
            }
            break;
          }
          default: {
            if (!forgive) {
              this.onError(
                generateException(
                  `Unknown pseudo-class :${astName}()`,
                  SYNTAX_ERR,
                  this.#window
                )
              );
            }
          }
        }
      }
    } else if (KEYS_PS_NTH_OF_TYPE.has(astName)) {
      if (node === this.#root) {
        matched.add(node);
      } else if (parentNode) {
        switch (astName) {
          case "first-of-type": {
            const [node1] = this._collectNthOfType(
              {
                a: 0,
                b: 1
              },
              node
            );
            if (node1) {
              matched.add(node1);
            }
            break;
          }
          case "last-of-type": {
            const [node1] = this._collectNthOfType(
              {
                a: 0,
                b: 1,
                reverse: true
              },
              node
            );
            if (node1) {
              matched.add(node1);
            }
            break;
          }
          // 'only-of-type' is handled by default.
          default: {
            const [node1] = this._collectNthOfType(
              {
                a: 0,
                b: 1
              },
              node
            );
            if (node1 === node) {
              const [node2] = this._collectNthOfType(
                {
                  a: 0,
                  b: 1,
                  reverse: true
                },
                node
              );
              if (node2 === node) {
                matched.add(node);
              }
            }
          }
        }
      }
    } else {
      switch (astName) {
        case "disabled":
        case "enabled": {
          const isMatch = matchDisabledPseudoClass(astName, node);
          if (isMatch) {
            matched.add(node);
          }
          break;
        }
        case "read-only":
        case "read-write": {
          const isMatch = matchReadOnlyPseudoClass(astName, node);
          if (isMatch) {
            matched.add(node);
          }
          break;
        }
        case "any-link":
        case "link": {
          if ((localName === "a" || localName === "area") && node.hasAttribute("href")) {
            matched.add(node);
          }
          break;
        }
        case "local-link": {
          if ((localName === "a" || localName === "area") && node.hasAttribute("href")) {
            if (!this.#documentURL) {
              this.#documentURL = new URL(this.#document.URL);
            }
            const { href, origin, pathname } = this.#documentURL;
            const attrURL = new URL(node.getAttribute("href"), href);
            if (attrURL.origin === origin && attrURL.pathname === pathname) {
              matched.add(node);
            }
          }
          break;
        }
        case "visited": {
          break;
        }
        case "hover": {
          const { target, type } = this.#event ?? {};
          if (/^(?:click|mouse(?:down|over|up))$/.test(type) && target?.nodeType === ELEMENT_NODE && node.contains(target)) {
            matched.add(node);
          }
          break;
        }
        case "active": {
          const { buttons, target, type } = this.#event ?? {};
          if (type === "mousedown" && buttons & 1 && target?.nodeType === ELEMENT_NODE && node.contains(target)) {
            matched.add(node);
          }
          break;
        }
        case "target": {
          if (!this.#documentURL) {
            this.#documentURL = new URL(this.#document.URL);
          }
          const { hash } = this.#documentURL;
          if (node.id && hash === `#${node.id}` && this.#document.contains(node)) {
            matched.add(node);
          }
          break;
        }
        case "target-within": {
          if (!this.#documentURL) {
            this.#documentURL = new URL(this.#document.URL);
          }
          const { hash } = this.#documentURL;
          if (hash) {
            const id = hash.replace(/^#/, "");
            let current = this.#document.getElementById(id);
            while (current) {
              if (current === node) {
                matched.add(node);
                break;
              }
              current = current.parentNode;
            }
          }
          break;
        }
        case "scope": {
          if (this.#node.nodeType === ELEMENT_NODE) {
            if (!this.#shadow && node === this.#node) {
              matched.add(node);
            }
          } else if (node === this.#document.documentElement) {
            matched.add(node);
          }
          break;
        }
        case "focus": {
          const activeElement = this.#document.activeElement;
          if (node === activeElement && isFocusableArea(node)) {
            matched.add(node);
          } else if (activeElement.shadowRoot) {
            const activeShadowElement = activeElement.shadowRoot.activeElement;
            let current = activeShadowElement;
            while (current) {
              if (current.nodeType === DOCUMENT_FRAGMENT_NODE) {
                const { host } = current;
                if (host === activeElement) {
                  if (isFocusableArea(node)) {
                    matched.add(node);
                  } else {
                    matched.add(host);
                  }
                }
                break;
              } else {
                current = current.parentNode;
              }
            }
          }
          break;
        }
        case "focus-visible": {
          if (node === this.#document.activeElement && isFocusableArea(node)) {
            let bool;
            if (isFocusVisible(node)) {
              bool = true;
            } else if (this.#focus) {
              const { relatedTarget, target: focusTarget } = this.#focus;
              if (focusTarget === node) {
                if (isFocusVisible(relatedTarget)) {
                  bool = true;
                } else if (this.#event) {
                  const {
                    altKey: eventAltKey,
                    ctrlKey: eventCtrlKey,
                    key: eventKey,
                    metaKey: eventMetaKey,
                    target: eventTarget,
                    type: eventType
                  } = this.#event;
                  if (eventTarget === relatedTarget) {
                    if (this.#lastFocusVisible === null) {
                      bool = true;
                    } else if (focusTarget === this.#lastFocusVisible) {
                      bool = true;
                    }
                  } else if (eventKey === "Tab") {
                    if (eventType === "keydown" && eventTarget !== node || eventType === "keyup" && eventTarget === node) {
                      if (eventTarget === focusTarget) {
                        if (this.#lastFocusVisible === null) {
                          bool = true;
                        } else if (eventTarget === this.#lastFocusVisible && relatedTarget === null) {
                          bool = true;
                        }
                      } else {
                        bool = true;
                      }
                    }
                  } else if (eventKey) {
                    if ((eventType === "keydown" || eventType === "keyup") && !eventAltKey && !eventCtrlKey && !eventMetaKey && eventTarget === node) {
                      bool = true;
                    }
                  }
                } else if (relatedTarget === null || relatedTarget === this.#lastFocusVisible) {
                  bool = true;
                }
              }
            }
            if (bool) {
              this.#lastFocusVisible = node;
              matched.add(node);
            } else if (this.#lastFocusVisible === node) {
              this.#lastFocusVisible = null;
            }
          }
          break;
        }
        case "focus-within": {
          const activeElement = this.#document.activeElement;
          if (node.contains(activeElement) && isFocusableArea(activeElement)) {
            matched.add(node);
          } else if (activeElement.shadowRoot) {
            const activeShadowElement = activeElement.shadowRoot.activeElement;
            if (node.contains(activeShadowElement)) {
              matched.add(node);
            } else {
              let current = activeShadowElement;
              while (current) {
                if (current.nodeType === DOCUMENT_FRAGMENT_NODE) {
                  const { host } = current;
                  if (host === activeElement && node.contains(host)) {
                    matched.add(node);
                  }
                  break;
                } else {
                  current = current.parentNode;
                }
              }
            }
          }
          break;
        }
        case "open":
        case "closed": {
          if (localName === "details" || localName === "dialog") {
            if (node.hasAttribute("open")) {
              if (astName === "open") {
                matched.add(node);
              }
            } else if (astName === "closed") {
              matched.add(node);
            }
          }
          break;
        }
        case "placeholder-shown": {
          let placeholder;
          if (node.placeholder) {
            placeholder = node.placeholder;
          } else if (node.hasAttribute("placeholder")) {
            placeholder = node.getAttribute("placeholder");
          }
          if (typeof placeholder === "string" && !/[\r\n]/.test(placeholder)) {
            let targetNode;
            if (localName === "textarea") {
              targetNode = node;
            } else if (localName === "input") {
              if (node.hasAttribute("type")) {
                if (KEYS_INPUT_PLACEHOLDER.has(node.getAttribute("type"))) {
                  targetNode = node;
                }
              } else {
                targetNode = node;
              }
            }
            if (targetNode && node.value === "") {
              matched.add(node);
            }
          }
          break;
        }
        case "checked": {
          const attrType = node.getAttribute("type");
          if (node.checked && localName === "input" && (attrType === "checkbox" || attrType === "radio") || node.selected && localName === "option") {
            matched.add(node);
          }
          break;
        }
        case "indeterminate": {
          if (node.indeterminate && localName === "input" && node.type === "checkbox" || localName === "progress" && !node.hasAttribute("value")) {
            matched.add(node);
          } else if (localName === "input" && node.type === "radio" && !node.hasAttribute("checked")) {
            const nodeName = node.name;
            let parent = node.parentNode;
            while (parent) {
              if (parent.localName === "form") {
                break;
              }
              parent = parent.parentNode;
            }
            if (!parent) {
              parent = this.#document.documentElement;
            }
            const walker = this._createTreeWalker(parent);
            let refNode = traverseNode(parent, walker);
            refNode = walker.firstChild();
            let checked;
            while (refNode) {
              if (refNode.localName === "input" && refNode.getAttribute("type") === "radio") {
                if (refNode.hasAttribute("name")) {
                  if (refNode.getAttribute("name") === nodeName) {
                    checked = !!refNode.checked;
                  }
                } else {
                  checked = !!refNode.checked;
                }
                if (checked) {
                  break;
                }
              }
              refNode = walker.nextNode();
            }
            if (!checked) {
              matched.add(node);
            }
          }
          break;
        }
        case "default": {
          const attrType = node.getAttribute("type");
          if (localName === "button" && !(node.hasAttribute("type") && KEYS_INPUT_RESET.has(attrType)) || localName === "input" && node.hasAttribute("type") && KEYS_INPUT_SUBMIT.has(attrType)) {
            let form = node.parentNode;
            while (form) {
              if (form.localName === "form") {
                break;
              }
              form = form.parentNode;
            }
            if (form) {
              const walker = this._createTreeWalker(form);
              let refNode = traverseNode(form, walker);
              refNode = walker.firstChild();
              while (refNode) {
                const nodeName = refNode.localName;
                const nodeAttrType = refNode.getAttribute("type");
                let m;
                if (nodeName === "button") {
                  m = !(refNode.hasAttribute("type") && KEYS_INPUT_RESET.has(nodeAttrType));
                } else if (nodeName === "input") {
                  m = refNode.hasAttribute("type") && KEYS_INPUT_SUBMIT.has(nodeAttrType);
                }
                if (m) {
                  if (refNode === node) {
                    matched.add(node);
                  }
                  break;
                }
                refNode = walker.nextNode();
              }
            }
          } else if (localName === "input" && node.hasAttribute("type") && node.hasAttribute("checked") && KEYS_INPUT_CHECK.has(attrType)) {
            matched.add(node);
          } else if (localName === "option" && node.hasAttribute("selected")) {
            matched.add(node);
          }
          break;
        }
        case "valid":
        case "invalid": {
          if (KEYS_FORM_PS_VALID.has(localName)) {
            let valid;
            if (node.checkValidity()) {
              if (node.maxLength >= 0) {
                if (node.maxLength >= node.value.length) {
                  valid = true;
                }
              } else {
                valid = true;
              }
            }
            if (valid) {
              if (astName === "valid") {
                matched.add(node);
              }
            } else if (astName === "invalid") {
              matched.add(node);
            }
          } else if (localName === "fieldset") {
            const walker = this._createTreeWalker(node);
            let refNode = traverseNode(node, walker);
            refNode = walker.firstChild();
            let valid;
            if (!refNode) {
              valid = true;
            } else {
              while (refNode) {
                if (KEYS_FORM_PS_VALID.has(refNode.localName)) {
                  if (refNode.checkValidity()) {
                    if (refNode.maxLength >= 0) {
                      valid = refNode.maxLength >= refNode.value.length;
                    } else {
                      valid = true;
                    }
                  } else {
                    valid = false;
                  }
                  if (!valid) {
                    break;
                  }
                }
                refNode = walker.nextNode();
              }
            }
            if (valid) {
              if (astName === "valid") {
                matched.add(node);
              }
            } else if (astName === "invalid") {
              matched.add(node);
            }
          }
          break;
        }
        case "in-range":
        case "out-of-range": {
          const attrType = node.getAttribute("type");
          if (localName === "input" && !(node.readOnly || node.hasAttribute("readonly")) && !(node.disabled || node.hasAttribute("disabled")) && KEYS_INPUT_RANGE.has(attrType)) {
            const flowed = node.validity.rangeUnderflow || node.validity.rangeOverflow;
            if (astName === "out-of-range" && flowed) {
              matched.add(node);
            } else if (astName === "in-range" && !flowed && (node.hasAttribute("min") || node.hasAttribute("max") || attrType === "range")) {
              matched.add(node);
            }
          }
          break;
        }
        case "required":
        case "optional": {
          let required;
          let optional;
          if (localName === "select" || localName === "textarea") {
            if (node.required || node.hasAttribute("required")) {
              required = true;
            } else {
              optional = true;
            }
          } else if (localName === "input") {
            if (node.hasAttribute("type")) {
              const attrType = node.getAttribute("type");
              if (KEYS_INPUT_REQUIRED.has(attrType)) {
                if (node.required || node.hasAttribute("required")) {
                  required = true;
                } else {
                  optional = true;
                }
              } else {
                optional = true;
              }
            } else if (node.required || node.hasAttribute("required")) {
              required = true;
            } else {
              optional = true;
            }
          }
          if (astName === "required" && required) {
            matched.add(node);
          } else if (astName === "optional" && optional) {
            matched.add(node);
          }
          break;
        }
        case "root": {
          if (node === this.#document.documentElement) {
            matched.add(node);
          }
          break;
        }
        case "empty": {
          if (node.hasChildNodes()) {
            const walker = this._createTreeWalker(node, {
              force: true,
              whatToShow: SHOW_ALL
            });
            let refNode = walker.firstChild();
            let bool;
            while (refNode) {
              bool = refNode.nodeType !== ELEMENT_NODE && refNode.nodeType !== TEXT_NODE;
              if (!bool) {
                break;
              }
              refNode = walker.nextSibling();
            }
            if (bool) {
              matched.add(node);
            }
          } else {
            matched.add(node);
          }
          break;
        }
        case "first-child": {
          if (parentNode && node === parentNode.firstElementChild || node === this.#root) {
            matched.add(node);
          }
          break;
        }
        case "last-child": {
          if (parentNode && node === parentNode.lastElementChild || node === this.#root) {
            matched.add(node);
          }
          break;
        }
        case "only-child": {
          if (parentNode && node === parentNode.firstElementChild && node === parentNode.lastElementChild || node === this.#root) {
            matched.add(node);
          }
          break;
        }
        case "defined": {
          if (node.hasAttribute("is") || localName.includes("-")) {
            if (isCustomElement(node)) {
              matched.add(node);
            }
          } else if (node instanceof this.#window.HTMLElement || node instanceof this.#window.SVGElement) {
            matched.add(node);
          }
          break;
        }
        case "popover-open": {
          break;
        }
        // Ignore :host.
        case "host": {
          break;
        }
        // Legacy pseudo-elements.
        case "after":
        case "before":
        case "first-letter":
        case "first-line": {
          if (warn) {
            this.onError(
              generateException(
                `Unsupported pseudo-element ::${astName}`,
                NOT_SUPPORTED_ERR,
                this.#window
              )
            );
          }
          break;
        }
        // Not supported.
        case "autofill":
        case "blank":
        case "buffering":
        case "current":
        case "fullscreen":
        case "future":
        case "has-slotted":
        case "heading":
        case "modal":
        case "muted":
        case "past":
        case "paused":
        case "picture-in-picture":
        case "playing":
        case "seeking":
        case "stalled":
        case "user-invalid":
        case "user-valid":
        case "volume-locked":
        case "-webkit-autofill": {
          if (warn) {
            this.onError(
              generateException(
                `Unsupported pseudo-class :${astName}`,
                NOT_SUPPORTED_ERR,
                this.#window
              )
            );
          }
          break;
        }
        default: {
          if (astName.startsWith("-webkit-")) {
            if (warn) {
              this.onError(
                generateException(
                  `Unsupported pseudo-class :${astName}`,
                  NOT_SUPPORTED_ERR,
                  this.#window
                )
              );
            }
          } else if (!forgive) {
            this.onError(
              generateException(
                `Unknown pseudo-class :${astName}`,
                SYNTAX_ERR,
                this.#window
              )
            );
          }
        }
      }
    }
    return matched;
  }
  /**
   * Evaluates the :host() pseudo-class.
   * @private
   * @param {Array.<object>} leaves - The AST leaves.
   * @param {object} host - The host element.
   * @param {object} ast - The original AST for error reporting.
   * @returns {boolean} True if matched.
   */
  _evaluateHostPseudo = (leaves, host, ast) => {
    const l = leaves.length;
    for (let i = 0; i < l; i++) {
      const leaf = leaves[i];
      if (leaf.type === COMBINATOR) {
        const css = generate51(ast);
        const msg = `Invalid selector ${css}`;
        this.onError(generateException(msg, SYNTAX_ERR, this.#window));
        return false;
      }
      if (!this._matchSelector(leaf, host).has(host)) {
        return false;
      }
    }
    return true;
  };
  /**
   * Evaluates the :host-context() pseudo-class.
   * @private
   * @param {Array.<object>} leaves - The AST leaves.
   * @param {object} host - The host element.
   * @param {object} ast - The original AST for error reporting.
   * @returns {boolean} True if matched.
   */
  _evaluateHostContextPseudo = (leaves, host, ast) => {
    let parent = host;
    while (parent) {
      let bool;
      const l = leaves.length;
      for (let i = 0; i < l; i++) {
        const leaf = leaves[i];
        if (leaf.type === COMBINATOR) {
          const css = generate51(ast);
          const msg = `Invalid selector ${css}`;
          this.onError(generateException(msg, SYNTAX_ERR, this.#window));
          return false;
        }
        bool = this._matchSelector(leaf, parent).has(parent);
        if (!bool) {
          break;
        }
      }
      if (bool) {
        return true;
      }
      parent = parent.parentNode;
    }
    return false;
  };
  /**
   * Matches shadow host pseudo-classes.
   * @private
   * @param {object} ast - The AST.
   * @param {object} node - The DocumentFragment node.
   * @returns {?object} The matched node.
   */
  _matchShadowHostPseudoClass = (ast, node) => {
    const { children: astChildren, name: astName } = ast;
    if (!Array.isArray(astChildren)) {
      if (astName === "host") {
        return node;
      }
      const msg = `Invalid selector :${astName}`;
      return this.onError(generateException(msg, SYNTAX_ERR, this.#window));
    }
    if (astName !== "host" && astName !== "host-context") {
      const msg = `Invalid selector :${astName}()`;
      return this.onError(generateException(msg, SYNTAX_ERR, this.#window));
    }
    if (astChildren.length !== 1) {
      const css = generate51(ast);
      const msg = `Invalid selector ${css}`;
      return this.onError(generateException(msg, SYNTAX_ERR, this.#window));
    }
    const { host } = node;
    const { branches } = walkAST(astChildren[0]);
    const [branch] = branches;
    const [...leaves] = branch;
    let isMatch = false;
    if (astName === "host") {
      isMatch = this._evaluateHostPseudo(leaves, host, ast);
    } else {
      isMatch = this._evaluateHostContextPseudo(leaves, host, ast);
    }
    return isMatch ? node : null;
  };
  /**
   * Matches a selector for element nodes.
   * @private
   * @param {object} ast - The AST.
   * @param {object} node - The Element node.
   * @param {object} opt - Options.
   * @returns {Set.<object>} A collection of matched nodes.
   */
  _matchSelectorForElement = (ast, node, opt) => {
    const { type: astType } = ast;
    const astName = unescapeSelector(ast.name);
    const matched = /* @__PURE__ */ new Set();
    switch (astType) {
      case ATTR_SELECTOR: {
        if (matchAttributeSelector(ast, node, opt)) {
          matched.add(node);
        }
        break;
      }
      case ID_SELECTOR: {
        if (node.id === astName) {
          matched.add(node);
        }
        break;
      }
      case CLASS_SELECTOR: {
        if (node.classList.contains(astName)) {
          matched.add(node);
        }
        break;
      }
      case PS_CLASS_SELECTOR: {
        return this._matchPseudoClassSelector(ast, node, opt);
      }
      case TYPE_SELECTOR: {
        if (matchTypeSelector(ast, node, opt)) {
          matched.add(node);
        }
        break;
      }
      // PS_ELEMENT_SELECTOR is handled by default.
      default: {
        try {
          if (this.#check) {
            const css = generate51(ast);
            this.#pseudoElement.push(css);
            matched.add(node);
          } else {
            matchPseudoElementSelector(astName, astType, opt);
          }
        } catch (e) {
          this.onError(e);
        }
      }
    }
    return matched;
  };
  /**
   * Matches a selector for a shadow root.
   * @private
   * @param {object} ast - The AST.
   * @param {object} node - The DocumentFragment node.
   * @param {object} [opt] - Options.
   * @returns {Set.<object>} A collection of matched nodes.
   */
  _matchSelectorForShadowRoot = (ast, node, opt = {}) => {
    const { name: astName } = ast;
    if (KEYS_LOGICAL.has(astName)) {
      opt.isShadowRoot = true;
      return this._matchPseudoClassSelector(ast, node, opt);
    }
    const matched = /* @__PURE__ */ new Set();
    if (astName === "host" || astName === "host-context") {
      const res = this._matchShadowHostPseudoClass(ast, node, opt);
      if (res) {
        this.#verifyShadowHost = true;
        matched.add(res);
      }
    }
    return matched;
  };
  /**
   * Matches a selector.
   * @private
   * @param {object} ast - The AST.
   * @param {object} node - The Document, DocumentFragment, or Element node.
   * @param {object} opt - Options.
   * @returns {Set.<object>} A collection of matched nodes.
   */
  _matchSelector = (ast, node, opt) => {
    if (node.nodeType === ELEMENT_NODE) {
      return this._matchSelectorForElement(ast, node, opt);
    }
    if (this.#shadow && node.nodeType === DOCUMENT_FRAGMENT_NODE && ast.type === PS_CLASS_SELECTOR) {
      return this._matchSelectorForShadowRoot(ast, node, opt);
    }
    return /* @__PURE__ */ new Set();
  };
  /**
   * Matches leaves.
   * @private
   * @param {Array.<object>} leaves - The AST leaves.
   * @param {object} node - The node.
   * @param {object} opt - Options.
   * @returns {boolean} The result.
   */
  _matchLeaves = (leaves, node, opt) => {
    const results = this.#invalidate ? this.#invalidateResults : this.#results;
    let result = results.get(leaves);
    if (result && result.has(node)) {
      const { matched } = result.get(node);
      return matched;
    }
    let cacheable = true;
    if (node.nodeType === ELEMENT_NODE && KEYS_FORM.has(node.localName)) {
      cacheable = false;
    }
    let bool;
    const l = leaves.length;
    for (let i = 0; i < l; i++) {
      const leaf = leaves[i];
      switch (leaf.type) {
        case ATTR_SELECTOR:
        case ID_SELECTOR: {
          cacheable = false;
          break;
        }
        case PS_CLASS_SELECTOR: {
          if (KEYS_PS_UNCACHE.has(leaf.name)) {
            cacheable = false;
          }
          break;
        }
        default: {
        }
      }
      bool = this._matchSelector(leaf, node, opt).has(node);
      if (!bool) {
        break;
      }
    }
    if (cacheable) {
      if (!result) {
        result = /* @__PURE__ */ new WeakMap();
      }
      result.set(node, {
        matched: bool
      });
      results.set(leaves, result);
    }
    return bool;
  };
  /**
   * Returns a cached slice of the leaves array (excluding the first item).
   * @private
   * @param {Array.<object>} leaves - The original AST leaves array.
   * @returns {Array.<object>} The filtered leaves.
   */
  _getFilterLeaves = (leaves) => {
    if (this.#filterLeavesCache.has(leaves)) {
      return this.#filterLeavesCache.get(leaves);
    }
    const filterLeaves = leaves.slice(1);
    this.#filterLeavesCache.set(leaves, filterLeaves);
    return filterLeaves;
  };
  /**
   * Traverses all descendant nodes and collects matches.
   * @private
   * @param {object} baseNode - The base Element node or Element.shadowRoot.
   * @param {Array.<object>} leaves - The AST leaves.
   * @param {object} opt - Options.
   * @returns {Set.<object>} A collection of matched nodes.
   */
  _traverseAllDescendants = (baseNode, leaves, opt) => {
    const walker = this._createTreeWalker(baseNode);
    traverseNode(baseNode, walker);
    let currentNode = walker.firstChild();
    const nodes = /* @__PURE__ */ new Set();
    while (currentNode) {
      if (this._matchLeaves(leaves, currentNode, opt)) {
        nodes.add(currentNode);
      }
      currentNode = walker.nextNode();
    }
    return nodes;
  };
  /**
   * Finds descendant nodes.
   * @private
   * @param {Array.<object>} leaves - The AST leaves.
   * @param {object} baseNode - The base Element node or Element.shadowRoot.
   * @param {object} opt - Options.
   * @returns {Set.<object>} A collection of matched nodes.
   */
  _findDescendantNodes = (leaves, baseNode, opt) => {
    const [leaf] = leaves;
    const filterLeaves = this._getFilterLeaves(leaves);
    const { type: leafType } = leaf;
    switch (leafType) {
      case ID_SELECTOR: {
        const canUseGetElementById = !this.#shadow && baseNode.nodeType === ELEMENT_NODE && this.#root.nodeType !== ELEMENT_NODE;
        if (canUseGetElementById) {
          const leafName = unescapeSelector(leaf.name);
          const nodes = /* @__PURE__ */ new Set();
          const foundNode = this.#root.getElementById(leafName);
          if (foundNode && foundNode !== baseNode && baseNode.contains(foundNode)) {
            const isCompoundSelector = filterLeaves.length > 0;
            if (!isCompoundSelector || this._matchLeaves(filterLeaves, foundNode, opt)) {
              nodes.add(foundNode);
            }
          }
          return nodes;
        }
        return this._traverseAllDescendants(baseNode, leaves, opt);
      }
      case PS_ELEMENT_SELECTOR: {
        const leafName = unescapeSelector(leaf.name);
        matchPseudoElementSelector(leafName, leafType, opt);
        return /* @__PURE__ */ new Set();
      }
      default: {
        return this._traverseAllDescendants(baseNode, leaves, opt);
      }
    }
  };
  /**
   * Collects combinator matches into an array without creating intermediate sets.
   * @private
   * @param {object} twig - The twig object.
   * @param {object} node - The Element node.
   * @param {object} [opt] - Options.
   * @param {string} [opt.dir] - The find direction.
   * @param {Array.<object>} matched - The collector array.
   * @returns {Array.<object>} The collector array.
   */
  _collectCombinatorMatches = (twig, node, opt = {}, matched = []) => {
    const {
      combo: { name: comboName },
      leaves
    } = twig;
    const { dir } = opt;
    switch (comboName) {
      case "+": {
        const refNode = dir === DIR_NEXT ? node.nextElementSibling : node.previousElementSibling;
        if (refNode && this._matchLeaves(leaves, refNode, opt)) {
          matched.push(refNode);
        }
        break;
      }
      case "~": {
        let refNode = dir === DIR_NEXT ? node.nextElementSibling : node.previousElementSibling;
        while (refNode) {
          if (this._matchLeaves(leaves, refNode, opt)) {
            matched.push(refNode);
          }
          refNode = dir === DIR_NEXT ? refNode.nextElementSibling : refNode.previousElementSibling;
        }
        break;
      }
      case ">": {
        if (dir === DIR_NEXT) {
          let refNode = node.firstElementChild;
          while (refNode) {
            if (this._matchLeaves(leaves, refNode, opt)) {
              matched.push(refNode);
            }
            refNode = refNode.nextElementSibling;
          }
        } else {
          const { parentNode } = node;
          if (parentNode && this._matchLeaves(leaves, parentNode, opt)) {
            matched.push(parentNode);
          }
        }
        break;
      }
      case " ":
      default: {
        if (dir === DIR_NEXT) {
          for (const refNode of this._findDescendantNodes(leaves, node, opt)) {
            matched.push(refNode);
          }
        } else {
          const ancestors = [];
          let refNode = node.parentNode;
          while (refNode) {
            if (this._matchLeaves(leaves, refNode, opt)) {
              ancestors.push(refNode);
            }
            refNode = refNode.parentNode;
          }
          if (ancestors.length) {
            matched.push(...ancestors.reverse());
          }
        }
      }
    }
    return matched;
  };
  /**
   * Matches a combinator.
   * @private
   * @param {object} twig - The twig object.
   * @param {object} node - The Element node.
   * @param {object} opt - Options.
   * @returns {Set.<object>} A collection of matched nodes.
   */
  _matchCombinator = (twig, node, opt) => new Set(this._collectCombinatorMatches(twig, node, opt));
  /**
   * Traverses with a TreeWalker and collects nodes matching the leaves.
   * @private
   * @param {TreeWalker} walker - The TreeWalker instance to use.
   * @param {Array} leaves - The AST leaves to match against.
   * @param {object} [opt] - Traversal options.
   * @param {Node} [opt.boundaryNode] - The node to stop traversal at.
   * @param {boolean} [opt.force] - Force traversal to the next node.
   * @param {Node} [opt.startNode] - The node to start traversal from.
   * @param {string} [opt.targetType] - The type of target ('all' or 'first').
   * @returns {Array.<Node>} An array of matched nodes.
   */
  _traverseAndCollectNodes = (walker, leaves, opt = {}) => {
    const { boundaryNode, force, startNode, targetType } = opt;
    const collectedNodes = [];
    let currentNode = traverseNode(startNode, walker, !!force);
    if (!currentNode) {
      return [];
    }
    if (currentNode.nodeType !== ELEMENT_NODE) {
      currentNode = walker.nextNode();
    } else if (currentNode === startNode && currentNode !== this.#root) {
      currentNode = walker.nextNode();
    }
    const matchOpt = {
      warn: this.#warn
    };
    while (currentNode) {
      if (boundaryNode) {
        if (currentNode === boundaryNode) {
          break;
        } else if (targetType === TARGET_ALL && !boundaryNode.contains(currentNode)) {
          break;
        }
      }
      if (this._matchLeaves(leaves, currentNode, matchOpt) && currentNode !== this.#node) {
        collectedNodes.push(currentNode);
        if (targetType !== TARGET_ALL) {
          break;
        }
      }
      currentNode = walker.nextNode();
    }
    return collectedNodes;
  };
  /**
   * Finds matched node(s) preceding this.#node.
   * @private
   * @param {Array.<object>} leaves - The AST leaves.
   * @param {object} node - The node to start from.
   * @param {object} [opt] - Options.
   * @param {boolean} [opt.force] - If true, traverses only to the next node.
   * @param {string} [opt.targetType] - The target type.
   * @returns {Array.<object>} A collection of matched nodes.
   */
  _findPrecede = (leaves, node, opt = {}) => {
    const { force, targetType } = opt;
    if (!this.#rootWalker) {
      this.#rootWalker = this._createTreeWalker(this.#root);
    }
    return this._traverseAndCollectNodes(this.#rootWalker, leaves, {
      force,
      targetType,
      boundaryNode: this.#node,
      startNode: node
    });
  };
  /**
   * Finds matched node(s) in #nodeWalker.
   * @private
   * @param {Array.<object>} leaves - The AST leaves.
   * @param {object} node - The node to start from.
   * @param {object} [opt] - Options.
   * @param {boolean} [opt.precede] - If true, finds preceding nodes.
   * @returns {Array.<object>} A collection of matched nodes.
   */
  _findNodeWalker = (leaves, node, opt = {}) => {
    const { precede, ...traversalOpts } = opt;
    if (precede) {
      const precedeNodes = this._findPrecede(leaves, this.#root, opt);
      if (precedeNodes.length) {
        return precedeNodes;
      }
    }
    if (!this.#nodeWalker) {
      this.#nodeWalker = this._createTreeWalker(this.#node);
    }
    return this._traverseAndCollectNodes(this.#nodeWalker, leaves, {
      startNode: node,
      ...traversalOpts
    });
  };
  /**
   * Matches the node itself.
   * @private
   * @param {Array} leaves - The AST leaves.
   * @returns {Array} An array containing [nodes, filtered, pseudoElement].
   */
  _matchSelf = (leaves) => {
    const matched = this._matchLeaves(leaves, this.#node, {
      check: this.#check,
      warn: this.#warn
    });
    const nodes = matched ? [this.#node] : [];
    return [nodes, matched, this.#pseudoElement];
  };
  /**
   * Finds lineal nodes (self and ancestors).
   * @private
   * @param {Array} leaves - The AST leaves.
   * @param {object} [opt] - Options.
   * @param {boolean} [opt.complex] - If true, the selector is complex.
   * @returns {Array} An array containing [nodes, filtered].
   */
  _findLineal = (leaves, opt = {}) => {
    const { complex } = opt;
    const nodes = [];
    const matchOpts = { warn: this.#warn };
    const selfMatched = this._matchLeaves(leaves, this.#node, matchOpts);
    if (selfMatched) {
      nodes.push(this.#node);
    }
    if (!selfMatched || complex) {
      let currentNode = this.#node.parentNode;
      while (currentNode) {
        if (this._matchLeaves(leaves, currentNode, matchOpts)) {
          nodes.push(currentNode);
        }
        currentNode = currentNode.parentNode;
      }
    }
    const filtered = nodes.length > 0;
    return [nodes, filtered];
  };
  /**
   * Finds entry nodes for pseudo-element selectors.
   * @private
   * @param {object} leaf - The pseudo-element leaf from the AST.
   * @param {Array.<object>} filterLeaves - Leaves for compound selectors.
   * @param {string} targetType - The type of target to find.
   * @returns {object} The result { nodes, filtered, pending }.
   */
  _findEntryNodesForPseudoElement = (leaf, filterLeaves, targetType) => {
    let nodes = [];
    let filtered = false;
    if (targetType === TARGET_SELF && this.#check) {
      const css = generate51(leaf);
      this.#pseudoElement.push(css);
      if (filterLeaves.length) {
        [nodes, filtered] = this._matchSelf(filterLeaves);
      } else {
        nodes.push(this.#node);
        filtered = true;
      }
    } else {
      matchPseudoElementSelector(leaf.name, leaf.type, { warn: this.#warn });
    }
    return { nodes, filtered, pending: false };
  };
  /**
   * Finds entry nodes for ID selectors.
   * @private
   * @param {object} twig - The current twig from the AST branch.
   * @param {string} targetType - The type of target to find.
   * @param {object} [opt] - Options.
   * @param {boolean} [opt.complex] - If true, the selector is complex.
   * @param {boolean} [opt.precede] - If true, finds preceding nodes.
   * @returns {object} The result { nodes, filtered, pending }.
   */
  _findEntryNodesForId = (twig, targetType, opt = {}) => {
    const { leaves } = twig;
    const [leaf] = leaves;
    const filterLeaves = this._getFilterLeaves(leaves);
    const { complex, precede } = opt;
    let nodes = [];
    let filtered = false;
    if (targetType === TARGET_SELF) {
      [nodes, filtered] = this._matchSelf(leaves);
    } else if (targetType === TARGET_LINEAL) {
      [nodes, filtered] = this._findLineal(leaves, { complex });
    } else if (targetType === TARGET_FIRST && this.#root.nodeType !== ELEMENT_NODE) {
      const node = this.#root.getElementById(leaf.name);
      if (node) {
        if (filterLeaves.length) {
          if (this._matchLeaves(filterLeaves, node, { warn: this.#warn })) {
            nodes.push(node);
            filtered = true;
          }
        } else {
          nodes.push(node);
          filtered = true;
        }
      }
    } else {
      nodes = this._findNodeWalker(leaves, this.#node, { precede, targetType });
      filtered = nodes.length > 0;
    }
    return { nodes, filtered, pending: false };
  };
  /**
   * Finds entry nodes for class selectors.
   * @private
   * @param {Array.<object>} leaves - The AST leaves for the selector.
   * @param {string} targetType - The type of target to find.
   * @param {object} [opt] - Options.
   * @param {boolean} [opt.complex] - If true, the selector is complex.
   * @param {boolean} [opt.precede] - If true, finds preceding nodes.
   * @returns {object} The result { nodes, filtered, pending }.
   */
  _findEntryNodesForClass = (leaves, targetType, opt = {}) => {
    const { complex, precede } = opt;
    let nodes = [];
    let filtered = false;
    if (targetType === TARGET_SELF) {
      [nodes, filtered] = this._matchSelf(leaves);
    } else if (targetType === TARGET_LINEAL) {
      [nodes, filtered] = this._findLineal(leaves, { complex });
    } else {
      nodes = this._findNodeWalker(leaves, this.#node, { precede, targetType });
      filtered = nodes.length > 0;
    }
    return { nodes, filtered, pending: false };
  };
  /**
   * Finds entry nodes for type selectors.
   * @private
   * @param {Array.<object>} leaves - The AST leaves for the selector.
   * @param {string} targetType - The type of target to find.
   * @param {object} [opt] - Options.
   * @param {boolean} [opt.complex] - If true, the selector is complex.
   * @param {boolean} [opt.precede] - If true, finds preceding nodes.
   * @returns {object} The result { nodes, filtered, pending }.
   */
  _findEntryNodesForType = (leaves, targetType, opt = {}) => {
    const { complex, precede } = opt;
    let nodes = [];
    let filtered = false;
    if (targetType === TARGET_SELF) {
      [nodes, filtered] = this._matchSelf(leaves);
    } else if (targetType === TARGET_LINEAL) {
      [nodes, filtered] = this._findLineal(leaves, { complex });
    } else {
      nodes = this._findNodeWalker(leaves, this.#node, { precede, targetType });
      filtered = nodes.length > 0;
    }
    return { nodes, filtered, pending: false };
  };
  /**
   * Finds entry nodes for other selector types (default case).
   * @private
   * @param {object} twig - The current twig from the AST branch.
   * @param {string} targetType - The type of target to find.
   * @param {object} [opt] - Options.
   * @param {boolean} [opt.complex] - If true, the selector is complex.
   * @param {boolean} [opt.precede] - If true, finds preceding nodes.
   * @returns {object} The result { nodes, filtered, pending }.
   */
  _findEntryNodesForOther = (twig, targetType, opt = {}) => {
    const { leaves } = twig;
    const [leaf] = leaves;
    const filterLeaves = this._getFilterLeaves(leaves);
    const { complex, precede } = opt;
    let nodes = [];
    let filtered = false;
    let pending = false;
    if (targetType !== TARGET_LINEAL && /host(?:-context)?/.test(leaf.name)) {
      let shadowRoot = null;
      if (this.#shadow && this.#node.nodeType === DOCUMENT_FRAGMENT_NODE) {
        shadowRoot = this._matchShadowHostPseudoClass(leaf, this.#node);
      } else if (filterLeaves.length && this.#node.nodeType === ELEMENT_NODE) {
        shadowRoot = this._matchShadowHostPseudoClass(
          leaf,
          this.#node.shadowRoot
        );
      }
      if (shadowRoot) {
        let bool = true;
        const l = filterLeaves.length;
        for (let i = 0; i < l; i++) {
          const filterLeaf = filterLeaves[i];
          switch (filterLeaf.name) {
            case "host":
            case "host-context": {
              const matchedNode = this._matchShadowHostPseudoClass(
                filterLeaf,
                shadowRoot
              );
              bool = matchedNode === shadowRoot;
              break;
            }
            case "has": {
              bool = this._matchPseudoClassSelector(
                filterLeaf,
                shadowRoot,
                {}
              ).has(shadowRoot);
              break;
            }
            default: {
              bool = false;
            }
          }
          if (!bool) {
            break;
          }
        }
        if (bool) {
          nodes.push(shadowRoot);
          filtered = true;
        }
      }
    } else if (targetType === TARGET_SELF) {
      [nodes, filtered] = this._matchSelf(leaves);
    } else if (targetType === TARGET_LINEAL) {
      [nodes, filtered] = this._findLineal(leaves, { complex });
    } else if (targetType === TARGET_FIRST) {
      nodes = this._findNodeWalker(leaves, this.#node, { precede, targetType });
      filtered = nodes.length > 0;
    } else {
      pending = true;
    }
    return { nodes, filtered, pending };
  };
  /**
   * Finds entry nodes.
   * @private
   * @param {object} twig - The twig object.
   * @param {string} targetType - The target type.
   * @param {object} [opt] - Options.
   * @param {boolean} [opt.complex] - If true, the selector is complex.
   * @param {string} [opt.dir] - The find direction.
   * @returns {object} An object with nodes and their state.
   */
  _findEntryNodes = (twig, targetType, opt = {}) => {
    const { leaves } = twig;
    const [leaf] = leaves;
    const filterLeaves = this._getFilterLeaves(leaves);
    const { complex = false, dir = DIR_PREV } = opt;
    const precede = dir === DIR_NEXT && this.#node.nodeType === ELEMENT_NODE && this.#node !== this.#root;
    let result;
    switch (leaf.type) {
      case PS_ELEMENT_SELECTOR: {
        result = this._findEntryNodesForPseudoElement(
          leaf,
          filterLeaves,
          targetType
        );
        break;
      }
      case ID_SELECTOR: {
        result = this._findEntryNodesForId(twig, targetType, {
          complex,
          precede
        });
        break;
      }
      case CLASS_SELECTOR: {
        result = this._findEntryNodesForClass(leaves, targetType, {
          complex,
          precede
        });
        break;
      }
      case TYPE_SELECTOR: {
        result = this._findEntryNodesForType(leaves, targetType, {
          complex,
          precede
        });
        break;
      }
      default: {
        result = this._findEntryNodesForOther(twig, targetType, {
          complex,
          precede
        });
      }
    }
    return {
      compound: filterLeaves.length > 0,
      filtered: result.filtered,
      nodes: result.nodes,
      pending: result.pending
    };
  };
  /**
   * Determines the direction and starting twig for a selector branch.
   * @private
   * @param {Array.<object>} branch - The AST branch.
   * @param {string} targetType - The type of target to find.
   * @returns {object} An object with the direction and starting twig.
   */
  _determineTraversalStrategy = (branch, targetType) => {
    const branchLen = branch.length;
    const firstTwig = branch[0];
    const lastTwig = branch[branchLen - 1];
    if (branchLen === 1) {
      return { dir: DIR_PREV, twig: firstTwig };
    }
    const {
      leaves: [{ name: firstName, type: firstType }]
    } = firstTwig;
    const {
      leaves: [{ name: lastName, type: lastType }]
    } = lastTwig;
    const { combo: firstCombo } = firstTwig;
    if (this.#selector.includes(":scope") || lastType === PS_ELEMENT_SELECTOR || lastType === ID_SELECTOR) {
      return { dir: DIR_PREV, twig: lastTwig };
    }
    if (firstType === ID_SELECTOR) {
      return { dir: DIR_NEXT, twig: firstTwig };
    }
    if (firstName === "*" && firstType === TYPE_SELECTOR) {
      return { dir: DIR_PREV, twig: lastTwig };
    }
    if (lastName === "*" && lastType === TYPE_SELECTOR) {
      return { dir: DIR_NEXT, twig: firstTwig };
    }
    if (branchLen === 2) {
      if (targetType === TARGET_FIRST) {
        return { dir: DIR_PREV, twig: lastTwig };
      }
      const { name: comboName } = firstCombo;
      if (comboName === "+" || comboName === "~") {
        return { dir: DIR_PREV, twig: lastTwig };
      }
    } else if (branchLen > 2 && this.#scoped && targetType === TARGET_FIRST) {
      if (lastType === TYPE_SELECTOR) {
        return { dir: DIR_PREV, twig: lastTwig };
      }
      let isChildOrDescendant = false;
      for (const { combo } of branch) {
        if (combo) {
          const { name: comboName } = combo;
          isChildOrDescendant = comboName === ">" || comboName === " ";
          if (!isChildOrDescendant) {
            break;
          }
        }
      }
      if (isChildOrDescendant) {
        return { dir: DIR_PREV, twig: lastTwig };
      }
    }
    return { dir: DIR_NEXT, twig: firstTwig };
  };
  /**
   * Processes pending items not resolved with a direct strategy.
   * @private
   * @param {Set.<Map>} pendingItems - The set of pending items.
   */
  _processPendingItems = (pendingItems) => {
    if (!pendingItems.size) {
      return;
    }
    if (!this.#rootWalker) {
      this.#rootWalker = this._createTreeWalker(this.#root);
    }
    const walker = this.#rootWalker;
    let node = this.#root;
    if (this.#scoped) {
      node = this.#node;
    }
    let nextNode = traverseNode(node, walker);
    while (nextNode) {
      const isWithinScope = this.#node.nodeType !== ELEMENT_NODE || nextNode === this.#node || this.#node.contains(nextNode);
      if (isWithinScope) {
        for (const pendingItem of pendingItems) {
          const { leaves } = pendingItem.get("twig");
          if (this._matchLeaves(leaves, nextNode, { warn: this.#warn })) {
            const index = pendingItem.get("index");
            this.#ast[index].filtered = true;
            this.#ast[index].find = true;
            this.#nodes[index].push(nextNode);
          }
        }
      } else if (this.#scoped) {
        break;
      }
      nextNode = walker.nextNode();
    }
  };
  /**
   * Collects nodes.
   * @private
   * @param {string} targetType - The target type.
   * @returns {Array.<Array.<object>>} An array containing the AST and nodes.
   */
  _collectNodes = (targetType) => {
    [this.#ast, this.#nodes] = this._correspond(this.#selector);
    const ast = this.#ast.values();
    if (targetType === TARGET_ALL || targetType === TARGET_FIRST) {
      const pendingItems = /* @__PURE__ */ new Set();
      let i = 0;
      for (const { branch } of ast) {
        const complex = branch.length > 1;
        const { dir, twig } = this._determineTraversalStrategy(
          branch,
          targetType
        );
        const { compound, filtered, nodes, pending } = this._findEntryNodes(
          twig,
          targetType,
          { complex, dir }
        );
        if (nodes.length) {
          this.#ast[i].find = true;
          this.#nodes[i] = nodes;
        } else if (pending) {
          pendingItems.add(
            /* @__PURE__ */ new Map([
              ["index", i],
              ["twig", twig]
            ])
          );
        }
        this.#ast[i].dir = dir;
        this.#ast[i].filtered = filtered || !compound;
        i++;
      }
      this._processPendingItems(pendingItems);
    } else {
      let i = 0;
      for (const { branch } of ast) {
        const twig = branch[branch.length - 1];
        const complex = branch.length > 1;
        const dir = DIR_PREV;
        const { compound, filtered, nodes } = this._findEntryNodes(
          twig,
          targetType,
          { complex, dir }
        );
        if (nodes.length) {
          this.#ast[i].find = true;
          this.#nodes[i] = nodes;
        }
        this.#ast[i].dir = dir;
        this.#ast[i].filtered = filtered || !compound;
        i++;
      }
    }
    return [this.#ast, this.#nodes];
  };
  /**
   * Gets combined nodes.
   * @private
   * @param {object} twig - The twig object.
   * @param {object} nodes - A collection of nodes.
   * @param {string} dir - The direction.
   * @returns {Array.<object>} A collection of matched nodes.
   */
  _getCombinedNodes = (twig, nodes, dir) => {
    const arr = [];
    for (const node of nodes) {
      this._collectCombinatorMatches(
        twig,
        node,
        { dir, warn: this.#warn },
        arr
      );
    }
    return arr;
  };
  /**
   * Matches a node in the 'next' direction.
   * @private
   * @param {Array} branch - The branch.
   * @param {Set.<object>} nodes - A collection of Element nodes.
   * @param {object} [opt] - Options.
   * @param {object} [opt.combo] - The combo object.
   * @param {number} [opt.index] - The index.
   * @returns {?object} The matched node.
   */
  _matchNodeNext = (branch, nodes, opt = {}) => {
    const { combo, index } = opt;
    const { combo: nextCombo, leaves } = branch[index];
    const twig = {
      combo,
      leaves
    };
    const nextNodes = this._getCombinedNodes(twig, nodes, DIR_NEXT);
    if (nextNodes.length) {
      if (index === branch.length - 1) {
        if (nextNodes.length === 1) {
          return nextNodes[0];
        }
        const [nextNode] = sortNodes(nextNodes);
        return nextNode;
      }
      return this._matchNodeNext(branch, nextNodes, {
        combo: nextCombo,
        index: index + 1
      });
    }
    return null;
  };
  /**
   * Matches a node in the 'previous' direction.
   * @private
   * @param {Array} branch - The branch.
   * @param {object} node - The Element node.
   * @param {object} [opt] - Options.
   * @param {number} [opt.index] - The index.
   * @returns {?object} The node.
   */
  _matchNodePrev = (branch, node, opt = {}) => {
    const { index } = opt;
    const twig = branch[index];
    const nextNodes = this._getCombinedNodes(twig, [node], DIR_PREV);
    if (nextNodes.length) {
      if (index === 0) {
        return node;
      }
      let matched;
      for (const nextNode of nextNodes) {
        matched = this._matchNodePrev(branch, nextNode, {
          index: index - 1
        });
        if (matched) {
          break;
        }
      }
      if (matched) {
        return node;
      }
    }
    return null;
  };
  /**
   * Processes a complex selector branch to find all matching nodes.
   * @private
   * @param {Array} branch - The selector branch from the AST.
   * @param {Array} entryNodes - The initial set of nodes to start from.
   * @param {string} dir - The direction of traversal ('next' or 'prev').
   * @returns {Set.<object>} A set of all matched nodes.
   */
  _processComplexBranchAll = (branch, entryNodes, dir) => {
    const matchedNodes = /* @__PURE__ */ new Set();
    const branchLen = branch.length;
    const lastIndex = branchLen - 1;
    if (dir === DIR_NEXT) {
      const { combo: firstCombo } = branch[0];
      for (const node of entryNodes) {
        let combo = firstCombo;
        let nextNodes = [node];
        for (let j = 1; j < branchLen; j++) {
          const { combo: nextCombo, leaves } = branch[j];
          const twig = { combo, leaves };
          const nodesArr = this._getCombinedNodes(twig, nextNodes, dir);
          if (nodesArr.length) {
            if (j === lastIndex) {
              for (const nextNode of nodesArr) {
                matchedNodes.add(nextNode);
              }
            }
            combo = nextCombo;
            nextNodes = nodesArr;
          } else {
            break;
          }
        }
      }
    } else {
      for (const node of entryNodes) {
        let nextNodes = [node];
        for (let j = lastIndex - 1; j >= 0; j--) {
          const twig = branch[j];
          const nodesArr = this._getCombinedNodes(twig, nextNodes, dir);
          if (nodesArr.length) {
            if (j === 0) {
              matchedNodes.add(node);
            }
            nextNodes = nodesArr;
          } else {
            break;
          }
        }
      }
    }
    return matchedNodes;
  };
  /**
   * Processes a complex selector branch to find the first matching node.
   * @private
   * @param {Array} branch - The selector branch from the AST.
   * @param {Array} entryNodes - The initial set of nodes to start from.
   * @param {string} dir - The direction of traversal ('next' or 'prev').
   * @param {string} targetType - The type of search (e.g., 'first').
   * @returns {?object} The first matched node, or null.
   */
  _processComplexBranchFirst = (branch, entryNodes, dir, targetType) => {
    const branchLen = branch.length;
    const lastIndex = branchLen - 1;
    if (dir === DIR_NEXT) {
      const { combo: entryCombo } = branch[0];
      for (const node of entryNodes) {
        const matchedNode = this._matchNodeNext(branch, /* @__PURE__ */ new Set([node]), {
          combo: entryCombo,
          index: 1
        });
        if (matchedNode) {
          if (this.#node.nodeType === ELEMENT_NODE) {
            if (matchedNode !== this.#node && this.#node.contains(matchedNode)) {
              return matchedNode;
            }
          } else {
            return matchedNode;
          }
        }
      }
      const { leaves: entryLeaves } = branch[0];
      const [entryNode] = entryNodes;
      if (this.#node.contains(entryNode)) {
        let [refNode] = this._findNodeWalker(entryLeaves, entryNode, {
          targetType
        });
        while (refNode) {
          const matchedNode = this._matchNodeNext(branch, /* @__PURE__ */ new Set([refNode]), {
            combo: entryCombo,
            index: 1
          });
          if (matchedNode) {
            if (this.#node.nodeType === ELEMENT_NODE) {
              if (matchedNode !== this.#node && this.#node.contains(matchedNode)) {
                return matchedNode;
              }
            } else {
              return matchedNode;
            }
          }
          [refNode] = this._findNodeWalker(entryLeaves, refNode, {
            targetType,
            force: true
          });
        }
      }
    } else {
      for (const node of entryNodes) {
        const matchedNode = this._matchNodePrev(branch, node, {
          index: lastIndex - 1
        });
        if (matchedNode) {
          return matchedNode;
        }
      }
      if (targetType === TARGET_FIRST) {
        const { leaves: entryLeaves } = branch[lastIndex];
        const [entryNode] = entryNodes;
        let [refNode] = this._findNodeWalker(entryLeaves, entryNode, {
          targetType
        });
        while (refNode) {
          const matchedNode = this._matchNodePrev(branch, refNode, {
            index: lastIndex - 1
          });
          if (matchedNode) {
            return refNode;
          }
          [refNode] = this._findNodeWalker(entryLeaves, refNode, {
            targetType,
            force: true
          });
        }
      }
    }
    return null;
  };
  /**
   * Finds matched nodes.
   * @param {string} targetType - The target type.
   * @returns {Set.<object>} A collection of matched nodes.
   */
  find = (targetType) => {
    let collection;
    try {
      collection = this._collectNodes(targetType);
    } catch (e) {
      if (this.#check) {
        let pseudoElement;
        if (this.#pseudoElement.length) {
          pseudoElement = this.#pseudoElement.join("");
        } else {
          pseudoElement = null;
        }
        return {
          pseudoElement,
          match: false,
          ast: this.#selectorAST ?? null
        };
      } else {
        throw e;
      }
    }
    const [[...branches], collectedNodes] = collection;
    const l = branches.length;
    let sort = l > 1 && targetType === TARGET_ALL && this.#selector.includes(":scope");
    let nodes = /* @__PURE__ */ new Set();
    for (let i = 0; i < l; i++) {
      const { branch, dir, find: find2 } = branches[i];
      if (!branch.length || !find2) {
        continue;
      }
      const entryNodes = collectedNodes[i];
      const lastIndex = branch.length - 1;
      if (lastIndex === 0) {
        if ((targetType === TARGET_ALL || targetType === TARGET_FIRST) && this.#node.nodeType === ELEMENT_NODE) {
          for (const node of entryNodes) {
            if (node !== this.#node && this.#node.contains(node)) {
              nodes.add(node);
              if (targetType === TARGET_FIRST) {
                break;
              }
            }
          }
        } else if (targetType === TARGET_ALL) {
          if (nodes.size) {
            for (const node of entryNodes) {
              nodes.add(node);
            }
            sort = true;
          } else {
            nodes = new Set(entryNodes);
          }
        } else {
          if (entryNodes.length) {
            nodes.add(entryNodes[0]);
          }
        }
      } else {
        if (targetType === TARGET_ALL) {
          const newNodes = this._processComplexBranchAll(
            branch,
            entryNodes,
            dir
          );
          if (nodes.size) {
            for (const newNode of newNodes) {
              nodes.add(newNode);
            }
            sort = true;
          } else {
            nodes = newNodes;
          }
        } else {
          const matchedNode = this._processComplexBranchFirst(
            branch,
            entryNodes,
            dir,
            targetType
          );
          if (matchedNode) {
            nodes.add(matchedNode);
          }
        }
      }
    }
    if (this.#check) {
      const match = !!nodes.size;
      let pseudoElement;
      if (this.#pseudoElement.length) {
        pseudoElement = this.#pseudoElement.join("");
      } else {
        pseudoElement = null;
      }
      return {
        match,
        pseudoElement,
        ast: this.#selectorAST
      };
    }
    if (targetType === TARGET_FIRST || targetType === TARGET_ALL) {
      nodes.delete(this.#node);
    }
    if ((sort || targetType === TARGET_FIRST) && nodes.size > 1) {
      return new Set(sortNodes(nodes));
    }
    return nodes;
  };
  /**
   * Gets AST for selector.
   * @param {string} selector - The selector text.
   * @returns {object} The AST for the selector.
   */
  getAST = (selector2) => {
    return parseSelector(selector2);
  };
};

// node_modules/@asamuzakjp/dom-selector/src/index.js
var CACHE_SIZE = 2048;
var DOMSelector = class {
  /* private fields */
  #window;
  #document;
  #finder;
  #idlUtils;
  #nwsapi;
  #cache;
  /**
   * Creates an instance of DOMSelector.
   * @param {Window} window - The window object.
   * @param {Document} document - The document object.
   * @param {object} [opt] - Options.
   */
  constructor(window, document, opt = {}) {
    const { cacheSize, idlUtils } = opt;
    this.#window = window;
    this.#document = document ?? window.document;
    this.#finder = new Finder(window);
    this.#idlUtils = idlUtils;
    this.#nwsapi = initNwsapi(window, document);
    this.#cache = new GenerationalCache(cacheSize ?? CACHE_SIZE);
  }
  /**
   * Clears the internal cache of finder results.
   * @returns {void}
   */
  clear = () => {
    this.#finder.clearResults(true);
  };
  /**
   * Parses a selector and extracts the rightmost subject keys (Id, Class, Tag).
   * @param {string} selector - The CSS selector to parse.
   * @returns {Array<{id: string|null, className: string|null, tag: string|null}>} The list of extracted keys for each selector group.
   */
  extractSubjects = (selector2) => {
    if (!selector2 || typeof selector2 !== "string") {
      return [{ id: null, className: null, tag: null }];
    }
    const cacheKey = `extract_${selector2}`;
    let subjects = this.#cache.get(cacheKey);
    if (subjects !== void 0) {
      return subjects;
    }
    subjects = [];
    try {
      const ast = this.#finder.getAST(selector2);
      if (ast?.type === "SelectorList") {
        for (const selectorNode of ast.children) {
          let idKey = null;
          let classKey = null;
          let tagKey = null;
          let current = selectorNode.children.tail;
          while (current) {
            const node = current.data;
            if (node.type === COMBINATOR) {
              break;
            }
            if (node.type === ID_SELECTOR) {
              idKey = idKey ?? unescapeSelector(node.name);
            } else if (node.type === CLASS_SELECTOR) {
              classKey = classKey ?? unescapeSelector(node.name);
            } else if (node.type === TYPE_SELECTOR) {
              const { localName } = parseAstName(unescapeSelector(node.name));
              if (localName !== "*") {
                tagKey = tagKey ?? localName.toLowerCase();
              }
            }
            current = current.prev;
          }
          subjects.push({ id: idKey, className: classKey, tag: tagKey });
        }
      }
    } catch (e) {
    }
    if (!subjects.length) {
      subjects.push({ id: null, className: null, tag: null });
    }
    this.#cache.set(cacheKey, subjects);
    return subjects;
  };
  /**
   * Checks if an element matches a CSS selector.
   * @param {string} selector - The CSS selector to check against.
   * @param {Element} node - The element node to check.
   * @param {object} [opt] - Optional parameters.
   * @returns {CheckResult} An object containing the check result.
   */
  check = (selector2, node, opt = {}) => {
    if (!node?.nodeType) {
      const e = new this.#window.TypeError(`Unexpected type ${getType(node)}`);
      return this.#finder.onError(e, opt);
    } else if (node.nodeType !== ELEMENT_NODE) {
      const e = new this.#window.TypeError(`Unexpected node ${node.nodeName}`);
      return this.#finder.onError(e, opt);
    }
    const document = node.ownerDocument;
    if (document === this.#document && document.contentType === "text/html" && document.documentElement && node.parentNode) {
      const cacheKey = `check_${selector2}`;
      let filterMatches = this.#cache.get(cacheKey);
      if (filterMatches === void 0) {
        filterMatches = filterSelector(selector2, TARGET_SELF);
        this.#cache.set(cacheKey, filterMatches);
      }
      if (filterMatches) {
        try {
          const n = this.#idlUtils ? this.#idlUtils.wrapperForImpl(node) : node;
          const match = this.#nwsapi.match(selector2, n);
          let ast = null;
          if (match) {
            const astCacheKey = `check_ast_${selector2}`;
            ast = this.#cache.get(astCacheKey);
            if (ast === void 0) {
              ast = this.#finder.getAST(selector2);
              this.#cache.set(astCacheKey, ast);
            }
          }
          return {
            match,
            ast,
            pseudoElement: null
          };
        } catch (e) {
        }
      }
    }
    if (this.#idlUtils) {
      node = this.#idlUtils.wrapperForImpl(node);
    }
    opt.check = true;
    opt.noexcept = true;
    opt.warn = false;
    return this.#finder.setup(selector2, node, opt).find(TARGET_SELF);
  };
  /**
   * Returns true if the element matches the selector.
   * @param {string} selector - The CSS selector to match against.
   * @param {Element} node - The element node to test.
   * @param {object} [opt] - Optional parameters.
   * @returns {boolean} `true` if the element matches, or `false` otherwise.
   */
  matches = (selector2, node, opt = {}) => {
    if (!node?.nodeType) {
      const e = new this.#window.TypeError(`Unexpected type ${getType(node)}`);
      return this.#finder.onError(e, opt);
    } else if (node.nodeType !== ELEMENT_NODE) {
      const e = new this.#window.TypeError(`Unexpected node ${node.nodeName}`);
      return this.#finder.onError(e, opt);
    }
    const document = node.ownerDocument;
    if (document === this.#document && document.contentType === "text/html" && document.documentElement && node.parentNode) {
      const cacheKey = `matches_${selector2}`;
      let filterMatches = this.#cache.get(cacheKey);
      if (filterMatches === void 0) {
        filterMatches = filterSelector(selector2, TARGET_SELF);
        this.#cache.set(cacheKey, filterMatches);
      }
      if (filterMatches) {
        try {
          const n = this.#idlUtils ? this.#idlUtils.wrapperForImpl(node) : node;
          return this.#nwsapi.match(selector2, n);
        } catch (e) {
        }
      }
    }
    let res;
    try {
      if (this.#idlUtils) {
        node = this.#idlUtils.wrapperForImpl(node);
      }
      const nodes = this.#finder.setup(selector2, node, opt).find(TARGET_SELF);
      res = nodes.size;
    } catch (e) {
      this.#finder.onError(e, opt);
    }
    return !!res;
  };
  /**
   * Traverses up the DOM tree to find the first node that matches the selector.
   * @param {string} selector - The CSS selector to match against.
   * @param {Element} node - The element from which to start traversing.
   * @param {object} [opt] - Optional parameters.
   * @returns {?Element} The first matching ancestor element, or `null`.
   */
  closest = (selector2, node, opt = {}) => {
    if (!node?.nodeType) {
      const e = new this.#window.TypeError(`Unexpected type ${getType(node)}`);
      return this.#finder.onError(e, opt);
    } else if (node.nodeType !== ELEMENT_NODE) {
      const e = new this.#window.TypeError(`Unexpected node ${node.nodeName}`);
      return this.#finder.onError(e, opt);
    }
    const document = node.ownerDocument;
    if (document === this.#document && document.contentType === "text/html" && document.documentElement && node.parentNode) {
      const cacheKey = `closest_${selector2}`;
      let filterMatches = this.#cache.get(cacheKey);
      if (filterMatches === void 0) {
        filterMatches = filterSelector(selector2, TARGET_LINEAL);
        this.#cache.set(cacheKey, filterMatches);
      }
      if (filterMatches) {
        try {
          const n = this.#idlUtils ? this.#idlUtils.wrapperForImpl(node) : node;
          return this.#nwsapi.closest(selector2, n);
        } catch (e) {
        }
      }
    }
    let res;
    try {
      if (this.#idlUtils) {
        node = this.#idlUtils.wrapperForImpl(node);
      }
      const nodes = this.#finder.setup(selector2, node, opt).find(TARGET_LINEAL);
      if (nodes.size) {
        let refNode = node;
        while (refNode) {
          if (nodes.has(refNode)) {
            res = refNode;
            break;
          }
          refNode = refNode.parentNode;
        }
      }
    } catch (e) {
      this.#finder.onError(e, opt);
    }
    return res ?? null;
  };
  /**
   * Returns the first element within the subtree that matches the selector.
   * @param {string} selector - The CSS selector to match.
   * @param {Document|DocumentFragment|Element} node - The node to find within.
   * @param {object} [opt] - Optional parameters.
   * @returns {?Element} The first matching element, or `null`.
   */
  querySelector = (selector2, node, opt = {}) => {
    if (!node?.nodeType) {
      const e = new this.#window.TypeError(`Unexpected type ${getType(node)}`);
      return this.#finder.onError(e, opt);
    }
    const document = node.nodeType === DOCUMENT_NODE ? node : node.ownerDocument;
    if (document === this.#document && document.contentType === "text/html" && document.documentElement && (node.nodeType !== DOCUMENT_FRAGMENT_NODE || !node.host)) {
      const cacheKey = `querySelector_${selector2}`;
      let filterMatches = this.#cache.get(cacheKey);
      if (filterMatches === void 0) {
        filterMatches = filterSelector(selector2, TARGET_FIRST);
        this.#cache.set(cacheKey, filterMatches);
      }
      if (filterMatches) {
        try {
          const n = this.#idlUtils ? this.#idlUtils.wrapperForImpl(node) : node;
          return this.#nwsapi.first(selector2, n);
        } catch (e) {
        }
      }
    }
    let res;
    try {
      if (this.#idlUtils) {
        node = this.#idlUtils.wrapperForImpl(node);
      }
      const nodes = this.#finder.setup(selector2, node, opt).find(TARGET_FIRST);
      if (nodes.size) {
        [res] = [...nodes];
      }
    } catch (e) {
      this.#finder.onError(e, opt);
    }
    return res ?? null;
  };
  /**
   * Returns an array of elements within the subtree that match the selector.
   * Note: This method returns an Array, not a NodeList.
   * @param {string} selector - The CSS selector to match.
   * @param {Document|DocumentFragment|Element} node - The node to find within.
   * @param {object} [opt] - Optional parameters.
   * @returns {Array<Element>} An array of elements, or an empty array.
   */
  querySelectorAll = (selector2, node, opt = {}) => {
    if (!node?.nodeType) {
      const e = new this.#window.TypeError(`Unexpected type ${getType(node)}`);
      return this.#finder.onError(e, opt);
    }
    const document = node.nodeType === DOCUMENT_NODE ? node : node.ownerDocument;
    if (document === this.#document && document.contentType === "text/html" && document.documentElement && (node.nodeType !== DOCUMENT_FRAGMENT_NODE || !node.host)) {
      const cacheKey = `querySelectorAll_${selector2}`;
      let filterMatches = this.#cache.get(cacheKey);
      if (filterMatches === void 0) {
        filterMatches = filterSelector(selector2, TARGET_ALL);
        this.#cache.set(cacheKey, filterMatches);
      }
      if (filterMatches) {
        try {
          const n = this.#idlUtils ? this.#idlUtils.wrapperForImpl(node) : node;
          return this.#nwsapi.select(selector2, n);
        } catch (e) {
        }
      }
    }
    let res;
    try {
      if (this.#idlUtils) {
        node = this.#idlUtils.wrapperForImpl(node);
      }
      const nodes = this.#finder.setup(selector2, node, opt).find(TARGET_ALL);
      if (nodes.size) {
        res = [...nodes];
      }
    } catch (e) {
      this.#finder.onError(e, opt);
    }
    return res ?? [];
  };
};
// Annotate the CommonJS export names for ESM import in node:
0 && (module.exports = {
  DOMSelector
});
/*! Bundled license information:

@asamuzakjp/dom-selector/src/index.js:
  (*!
   * DOM Selector - A CSS selector engine.
   * @license MIT
   * @copyright asamuzaK (Kazz)
   * @see {@link https://github.com/asamuzaK/domSelector/blob/main/LICENSE}
   *)
*/

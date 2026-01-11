// worker.js
// This Web Worker receives a JSON string from the main thread, parses it
// and posts the resulting object back to the main thread. Using a worker
// prevents the main UI thread from blocking while parsing large files.

self.onmessage = function (event) {
  const text = event.data;
  let result = [];
  try {
    result = JSON.parse(text);
  } catch (e) {
    // Parsing failed; post an empty array to signal failure
    console.error('Worker failed to parse JSON:', e);
  }
  self.postMessage(result);
};
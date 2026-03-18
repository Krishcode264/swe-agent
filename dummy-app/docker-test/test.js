const { multiply } = require('./math');

const result = multiply(2, 5);
const expected = 10;

if (result === expected) {
  console.log('SUCCESS: Test passed!');
  process.exit(0);
} else {
  console.error(`FAILURE: Test failed! Expected ${expected}, but got ${result}`);
  process.exit(1);
}

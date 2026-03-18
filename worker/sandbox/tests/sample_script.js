/**
 * This is a sample buggy file for testing the execution engine.
 * Goal: Fix the discount calculation.
 */
function applyDiscount(price, percentage) {
    // BUG: It's adding instead of subtracting the discount!
    return price - (price * (percentage / 100));
}

const itemPrice = 100;
const discount = 20;
console.log(`Original: ${itemPrice}, Discount: ${discount}%, Result: ${applyDiscount(itemPrice, discount)}`);

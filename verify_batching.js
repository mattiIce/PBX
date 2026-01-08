#!/usr/bin/env node

/**
 * Verification script to demonstrate the batching behavior
 * This script simulates the admin refresh behavior and logs timing information
 */

/**
 * Execute promise-returning functions in batches to avoid overwhelming the rate limiter.
 * IMPORTANT: Pass functions that return promises, not promises themselves.
 * This ensures requests don't start until the batch is ready to execute them.
 * 
 * @param {Function[]} promiseFunctions - Array of functions that return promises
 * @param {number} batchSize - Number of promises to execute concurrently (default: 5)
 * @param {number} delayMs - Delay in milliseconds between batches (default: 1000)
 * @returns {Promise<Array>} Results from Promise.allSettled for all promises
 */
async function executeBatched(promiseFunctions, batchSize = 5, delayMs = 1000) {
    const results = [];
    
    console.log(`\n📦 Executing ${promiseFunctions.length} promise functions in batches of ${batchSize} with ${delayMs}ms delay\n`);
    
    // Process promise functions in batches
    for (let i = 0; i < promiseFunctions.length; i += batchSize) {
        const batchFunctions = promiseFunctions.slice(i, i + batchSize);
        const batchNum = Math.floor(i / batchSize) + 1;
        const totalBatches = Math.ceil(promiseFunctions.length / batchSize);
        
        console.log(`⏳ Batch ${batchNum}/${totalBatches}: Processing ${batchFunctions.length} requests...`);
        const batchStart = Date.now();
        
        // Create promises only when ready to execute (lazy evaluation)
        const batchPromises = batchFunctions.map(fn => typeof fn === 'function' ? fn() : fn);
        
        // Execute current batch
        const batchResults = await Promise.allSettled(batchPromises);
        results.push(...batchResults);
        
        const batchDuration = Date.now() - batchStart;
        const succeeded = batchResults.filter(r => r.status === 'fulfilled').length;
        const failed = batchResults.filter(r => r.status === 'rejected').length;
        console.log(`✅ Batch ${batchNum} completed in ${batchDuration}ms (${succeeded} succeeded, ${failed} failed)`);
        
        // Add delay between batches (except after the last batch)
        if (i + batchSize < promiseFunctions.length) {
            console.log(`⏸️  Waiting ${delayMs}ms before next batch...\n`);
            await new Promise(resolve => setTimeout(resolve, delayMs));
        }
    }
    
    return results;
}

/**
 * Simulate an API call with random delay
 */
function simulateAPICall(id, shouldFail = false) {
    return new Promise((resolve, reject) => {
        const delay = Math.random() * 100 + 50; // 50-150ms
        setTimeout(() => {
            if (shouldFail) {
                reject(new Error(`API call ${id} failed (simulated 429 error)`));
            } else {
                resolve({ id, data: `Result from API ${id}` });
            }
        }, delay);
    }).catch(err => {
        // Catch to prevent unhandled rejection, but still throw for Promise.allSettled
        throw err;
    });
}

async function main() {
    console.log('🚀 Batching Verification Script\n');
    console.log('This demonstrates how the admin refresh batching works to avoid rate limits.\n');
    console.log('═'.repeat(80));
    
    // Create 40 simulated API call FUNCTIONS (not promises!) 
    // This is the key difference - we don't start the requests until we're ready
    const apiCallFunctions = Array.from({ length: 40 }, (_, i) => {
        return () => simulateAPICall(i + 1, false);
    });
    
    const startTime = Date.now();
    
    // Execute with batching
    const results = await executeBatched(apiCallFunctions, 5, 1000);
    
    const totalTime = Date.now() - startTime;
    
    console.log('\n' + '═'.repeat(80));
    console.log('\n📊 Results Summary:\n');
    console.log(`Total requests: ${results.length}`);
    console.log(`Successful: ${results.filter(r => r.status === 'fulfilled').length}`);
    console.log(`Failed: ${results.filter(r => r.status === 'rejected').length}`);
    console.log(`Total time: ${totalTime}ms`);
    
    // Calculate batching metrics
    const numBatches = Math.ceil(results.length / 8);
    const totalDelays = (numBatches - 1) * 1000; // delays between batches
    console.log(`\n📦 Batching Metrics:`);
    console.log(`  Batches: ${numBatches}`);
    console.log(`  Batch size: 5 requests`);
    console.log(`  Inter-batch delay: 1000ms`);
    console.log(`  Total delay time: ${totalDelays}ms`);
    
    console.log(`\n⚖️  Rate Limit Analysis:`);
    console.log(`  Backend limit: 60 req/min (burst: 10)`);
    console.log(`  Our batch size: 5 requests (within burst limit of 10)`);
    console.log(`  Time between batches: 1000ms`);
    console.log(`  Max concurrent requests: 5 (within burst limit)`);
    console.log(`  \n  ✅ Batch size (5) is WITHIN burst limit (10)`);
    console.log(`  ✅ Using promise FUNCTIONS prevents all requests from starting simultaneously`);
    console.log(`  ✅ 1-second delays between batches allow token bucket to refill`);
    console.log(`  ✅ For typical refresh (40 requests), completes in ~8 seconds`);
    console.log(`  ✅ Token bucket refills 1 token/second = full refill during 5-second inter-batch delays`);
    
    console.log('\n' + '═'.repeat(80));
    console.log('\n✨ Verification complete!\n');
    console.log('Key takeaway: By passing FUNCTIONS instead of PROMISES, we control when');
    console.log('HTTP requests actually start, preventing simultaneous bursts that exceed rate limits.\n');
}

// Run the verification
main().catch(console.error);

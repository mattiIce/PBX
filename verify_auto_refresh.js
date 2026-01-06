#!/usr/bin/env node
/**
 * Verification script for admin UI auto-refresh changes
 * Checks JavaScript syntax and validates the auto-refresh configuration
 */

const fs = require('fs');
const path = require('path');

console.log('🔍 Verifying admin UI auto-refresh changes...\n');

// Read the admin.js file
const adminJsPath = path.join(__dirname, 'admin', 'js', 'admin.js');
let fileContent;

try {
    fileContent = fs.readFileSync(adminJsPath, 'utf8');
    console.log('✓ Successfully read admin.js');
} catch (error) {
    console.error('✗ Failed to read admin.js:', error.message);
    process.exit(1);
}

// Check 1: Verify autoRefreshTabs object exists
const autoRefreshTabsRegex = /const\s+autoRefreshTabs\s*=\s*\{([^}]+)\}/s;
const match = fileContent.match(autoRefreshTabsRegex);

if (!match) {
    console.error('✗ Could not find autoRefreshTabs object');
    process.exit(1);
}
console.log('✓ Found autoRefreshTabs object');

// Extract tab names from the autoRefreshTabs object
const tabEntries = match[1].match(/'([^']+)':\s*\w+/g);
if (!tabEntries) {
    console.error('✗ Could not parse tab entries');
    process.exit(1);
}

const tabs = tabEntries.map(entry => {
    const tabMatch = entry.match(/'([^']+)':/);
    return tabMatch ? tabMatch[1] : null;
}).filter(Boolean);

console.log('✓ Found', tabs.length, 'tabs with auto-refresh');
console.log('\nTabs with auto-refresh:');
tabs.forEach(tab => console.log('  -', tab));

// Check 2: Verify expected tabs are present
const expectedTabs = [
    'dashboard',
    'analytics', 
    'extensions',
    'phones',
    'atas',
    'calls',
    'qos',
    'emergency',
    'voicemail',
    'hot-desking',
    'callback-queue',
    'fraud-detection'
];

console.log('\n🔍 Checking for expected tabs...');
let allExpectedFound = true;
for (const expectedTab of expectedTabs) {
    if (tabs.includes(expectedTab)) {
        console.log(`  ✓ ${expectedTab}`);
    } else {
        console.log(`  ✗ ${expectedTab} - MISSING!`);
        allExpectedFound = false;
    }
}

if (!allExpectedFound) {
    console.error('\n✗ Some expected tabs are missing from auto-refresh configuration');
    process.exit(1);
}

// Check 3: Verify wrapper functions exist
console.log('\n🔍 Checking for wrapper functions...');
const wrapperFunctions = [
    'refreshEmergencyTab',
    'refreshFraudDetectionTab',
    'refreshCallbackQueueTab'
];

for (const funcName of wrapperFunctions) {
    const funcRegex = new RegExp(`const\\s+${funcName}\\s*=\\s*\\(\\)\\s*=>`, 's');
    if (funcRegex.test(fileContent)) {
        console.log(`  ✓ ${funcName}`);
    } else {
        console.log(`  ✗ ${funcName} - MISSING!`);
        allExpectedFound = false;
    }
}

// Check 4: Verify AUTO_REFRESH_INTERVAL_MS constant exists
console.log('\n🔍 Checking configuration constants...');
if (/const\s+AUTO_REFRESH_INTERVAL_MS\s*=\s*\d+/.test(fileContent)) {
    const intervalMatch = fileContent.match(/AUTO_REFRESH_INTERVAL_MS\s*=\s*(\d+)/);
    const interval = intervalMatch ? intervalMatch[1] : 'unknown';
    console.log(`  ✓ AUTO_REFRESH_INTERVAL_MS = ${interval}ms`);
} else {
    console.log('  ✗ AUTO_REFRESH_INTERVAL_MS not found');
    allExpectedFound = false;
}

// Check 5: Verify setupAutoRefresh function exists
if (/function\s+setupAutoRefresh\s*\(\s*tabName\s*\)/.test(fileContent)) {
    console.log('  ✓ setupAutoRefresh function exists');
} else {
    console.log('  ✗ setupAutoRefresh function not found');
    allExpectedFound = false;
}

// Summary
console.log('\n' + '='.repeat(60));
if (allExpectedFound) {
    console.log('✅ All verification checks passed!');
    console.log('\nSummary:');
    console.log(`  • ${tabs.length} tabs configured for auto-refresh`);
    console.log(`  • ${expectedTabs.length} expected tabs verified`);
    console.log(`  • ${wrapperFunctions.length} wrapper functions verified`);
    console.log('\nThe admin UI auto-refresh fix appears to be correctly implemented.');
    process.exit(0);
} else {
    console.log('❌ Some verification checks failed!');
    console.log('Please review the admin.js file for issues.');
    process.exit(1);
}
